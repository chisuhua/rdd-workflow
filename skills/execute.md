---
name: execute
description: 在 worktree 隔离环境执行 OpenSpec change 的实施计划。基于 .rddf/plans/ 执行,强制 TDD 5 步结构(Write failing test → Verify fail → Implement → Verify pass → Commit)。被 guide-ship 在 plan 阶段后调用。v2.0 整合原 spec-workflow/executing-plans 的 TDD 纪律。
license: MIT
compatibility: Requires openspec CLI and git worktree.
metadata:
  version: "2.0"
  author: sisyphus
  evolved-from: "v1.0 P0 roadmap + v2.0 嵌入 TDD 5 步纪律,取代 spec-workflow/executing-plans"
  user-invocable: true
---

# OpenSpec 工作流 — Execute

在 git worktree 隔离环境中执行 OpenSpec change 的实施计划。

## 工作流位置

```
worktree (openspec/<name>): 本技能在此执行
    │
    ├── 读取 .rddf/plans/<name>.md（Prometheus 详细计划）
    ├── 循环执行每个 Work Unit
    │     ├── 委托 deep/unspecified-high 代理实现
    │     ├── cmake --build + ctest 验证
    │     └── sed 更新 tasks.md（[x]）通知 openspec CLI
    ├── 全部完成 → 提示运行 status
    └──
```

## 与 openspec-apply-change 的关系

本技能是 `openspec-apply-change` 的扩展版本。区别：

| 维度 | openspec-apply-change | 本技能 |
|------|----------------------|--------|
| 任务来源 | `openspec instructions apply --json`（tasks.md） | `.rddf/plans/<name>.md`（Prometheus 分解） |
| 执行环境 | 当前目录 | worktree 隔离（`.rddf/wt/<name>/`） |
| 进度反馈 | 无自动回写 | 每个 Work Unit 完成后 `sed` 更新 tasks.md |

## 输入

- change name（可选，从 git branch 自动推断）

## 工作模式

```
此技能始终在 git worktree 隔离环境中执行。
所有代码修改和构建都在独立的 .rddf/wt/<name>/ 目录中进行。
```

### 模式自动识别

```bash
# Round A: extracted to _lib/select_worktree.sh (L54-L168, ~113 lines)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/select_worktree.sh" ]; then
  source "$SCRIPT_DIR/_lib/select_worktree.sh"
fi
auto_detect_worktree_context || exit 1
```

> **为什么必须在 worktree 内执行？**
> - 避免对 default branch（`master`/`main`/`develop`，由 `find_default_branch` 检测）的直接修改
> - 独立构建目录（`.rddf/wt/<name>/build/`）互不干扰
> - 支持并行执行多个 change（每个 worktree 独立）
> - 隔离 git 操作，merge 时无冲突

## 执行步骤

### Step 1：确认在 worktree 内

```bash
# P0-7 fix: inline worktree path resolver. git worktree list emits
# P3-3c: 删除 P0-7 引入的 inline wt path helper (silent bug — 见 status.md 注释).
# 如果未来需要 wt 路径解析, 直接 source _lib/worktree.sh::wt_path_for_branch.
echo "✅ 在 worktree 中: $(pwd)"
echo "   Branch: $(git branch --show-current)"
echo "   Change: $CHANGE_NAME"
```

### Step 2：验证 worktree 构建环境

```bash
# 检查 build 目录，不存在则创建（首次构建）
if [ ! -d "build" ]; then
    echo "⏳ 首次构建（ccache 冷缓存）..."
    # ccache 通过 CCACHE_DIR/CCACHE_PREFIX 等环境变量全局配置
    # 此处不设 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache，避免与 CMakeLists.txt 预设冲突
    cmake -B build
fi

# 获取 CPU 核心数（跨平台兼容）
get_nproc() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        # macOS/BSD
        sysctl -n hw.ncpu 2>/dev/null || echo 4
    else
        echo 4
    fi
}

cmake --build build -j$(get_nproc) 2>&1 | tail -5
# ccache 如果已安装会自动生效（通过 CMake 预设或环境变量）
# 冷构建约 30s，后续增量 <5s
```

### Step 3：Review 计划 (Critique)

读取 plan 文件并进行批判性 review：

```bash
PLAN_FILE=".rddf/plans/$CHANGE_NAME.md"
test -f "$PLAN_FILE" || { echo "❌ 计划文件不存在"; exit 1; }
```

**Review checklist**（逐项检查）:
1. **Spec 覆盖**：plan 的每个 Task 是否对应 proposal/design 中的需求？标记空缺。
2. **占位符扫描**：检查是否有 `TBD`、`TODO`、`Similar to Task N` 等占位符。
3. **类型一致性**：后序 Task 中使用的类型/函数名是否与前面定义的一致？
4. **文件路径**：每个 `**Files:**` 中的路径是否合理？（不要求文件已存在，但路径要有意义）

**发现问题** → STOP，回到 guide-ship 重新 `skill_use("spec-workflow/writing-plans")`。

**无问题** → 继续 Step 4。

### Step 4：执行 Work Units (TDD 5 步)

每个 Work Unit（对应 plan 中的一个 `### Task N:`）按 **TDD 5 步结构** 执行：

```bash
# 对每个 Work Unit:
for each work_unit in plan.tasks (按依赖顺序):
    # 必须是 TDD 5 步，不允许跳过或合并
    #
    # Step 1: Write the failing test
    # Step 2: Run test to verify it fails
    # Step 3: Write minimal implementation
    # Step 4: Run test to verify it passes
    # Step 5: Commit
    #
    task(
        category="deep",
        load_skills=[],
        run_in_background=false,
        prompt="
            WORKTREE: $(pwd)（在此目录下工作）
            目标：实现以下 Work Unit 的 5 个 TDD Step:

            <work_unit description>

            强制 TDD 5 步结构（禁止简化为“纯实现”或“仅写代码”）:

            Step 1 — 先写测试：
              根据 proposal/design 的描述，写出覆盖本 Task 需求的测试代码。
              测试文件: <task_files_test_path>

            Step 2 — 运行验证失败：
              执行测试命令，确认测试因功能不存在而失败。
              Run: pytest <test_path> -v

            Step 3 — 写最小实现：
              写刚好能让测试通过的最小实现代码。
              生产文件: <task_files_create_or_modify_path>

            Step 4 — 运行验证通过：
              重新执行测试命令，确认通过。
              Run: pytest <test_path> -v

            Step 5 — Commit：
              git add <test_files> <implementation_files>
              git commit -m \"<commit message>\"

            完成后：
              用 sed -i 's/- \\[ \\]/- [x]/' openspec/changes/<CHANGE_NAME>/tasks.md 标记完成
        "
    )
```

**立即停止的情况**（不要强行执行，问人）：
- 测试在 Step 2 中不失败（测试有误，没有真的测试新功能）
- 测试在 Step 4 中仍失败（实现不对，或测试本身有 bug）
- 同一 Step 连续失败 2 次以上
- 计划中的文件路径不存在或明显不合理

### Step 6：全部完成后输出报告

### Step 7：输出明确的下一步操作指引

执行完成后，输出清晰的后续操作指引：

```bash
# 获取最终进度
COMPLETE=$(grep -c '^- \[x\]' "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md")
TOTAL=$(grep -c '^- \[' "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md")

# 同步 iteration.json (current sprint tracker). 失败 graceful 退出.
# v2.0.2 安全修复: bash 变量通过环境变量传递 (os.environ),
# 不用 '$VAR' 直接拼到 Python 源码. 避免单引号路径/注入风险.
PROJECT_ROOT="$PROJECT_ROOT" \
CHANGE_NAME="$CHANGE_NAME" \
COMPLETE="$COMPLETE" \
TOTAL="$TOTAL" \
python3 -c '
import os, sys
try:
    from skills._lib import iteration as it_mod
    data = it_mod.load(os.environ["PROJECT_ROOT"])
    data = it_mod.set_tasks_done(
        data,
        os.environ["CHANGE_NAME"],
        done=int(os.environ.get("COMPLETE", "0") or 0),
        total=int(os.environ.get("TOTAL", "0") or 0),
    )
    it_mod.save(os.environ["PROJECT_ROOT"], data)
except Exception as e:
    print(f"⚠️  iteration.json 同步失败: {e}", file=sys.stderr)
    sys.exit(0)
' 2>&1 | grep -v "^$" || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 执行完成"
echo ""
echo "Change: $CHANGE_NAME"
echo "当前进度：$COMPLETE/$TOTAL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 下一步操作："
echo ""
echo "1. 在主 session 查看最新进度："
echo "   skill_use(\"guide\")"
echo "   → 进入 Execute 监控模式"
echo ""
echo "2. 直接归档（如果已完成所有任务）："
echo "   cd \"$PROJECT_ROOT\""
echo "   skill_use(\"status $CHANGE_NAME --archive\")"
echo ""
echo "3. 继续处理其他 worktree："
echo "   skill_use(\"guide-ship\")   # 内部选择 change"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ============================================================
# P0 FIX: 执行完毕后自动检查是否还有其他 worktree 需要处理
# ============================================================
# 使用 awk 检查分支名（第三列）而非路径，避免路径含 openspec/ 的误匹配
# P0-7 修复：`git worktree list` 默认输出字段为
#   $1=path  $2=<sha>  $3=[branch]
# 因此分支在 $3，旧 awk '$2 ~ /^openspec\//' 永远匹配不到。
# 使用 _lib/worktree.sh::wt_path_for_branch（该文件已 source），统一走 --porcelain 解析
OTHER_WTS=""
CURRENT_WT=$(wt_path_for_branch "$CHANGE_NAME")
for wt in $(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}'); do
  if [ "$wt" != "$CURRENT_WT" ]; then
    OTHER_WTS="$OTHER_WTS $wt"
  fi
done
OTHER_WTS=$(echo $OTHER_WTS | wc -w)
if [ "$OTHER_WTS" -gt 0 ]; then
    echo ""
    echo "📋 发现其他 $OTHER_WTS 个 worktree:"
    # 输出 $1 (path) 和 $3 ([branch])，read 拆为 path + branch
    # $3 在 `git worktree list` 默认格式里是 "[branch]"，要去掉方括号才能跟 openspec/$CHANGE_NAME 比较
    git worktree list | awk '$3 ~ /^\[openspec\// {print $1, $3}' | while read -r path branch; do
        # branch 形如 "[openspec/xxx]"，去括号得 "openspec/xxx"
        branch_clean="${branch#[}"; branch_clean="${branch_clean%]}"
        if [ -n "$branch_clean" ] && [ "$branch_clean" != "openspec/$CHANGE_NAME" ]; then
            name=$(echo "$branch_clean" | sed 's|openspec/||')
            echo "   - $name → $path"
        fi
    done
    echo ""
    echo "请选择:"
    echo "1. 切换到另一个 worktree 继续执行"
    echo "2. 返回主 session（skill_use(\"guide\"))"
    echo "i. 其他输入"
fi
```

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，按以下 case 分支处理：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

# ============================================================
# P0: Roadmap 进度更新
# ============================================================
STATE_FILE="$PROJECT_ROOT/.rddf/state/roadmap-state.json"
if [ -f "$STATE_FILE" ] && [ -f "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/roadmap-meta.yaml" ]; then
    echo ""
    echo "📊 更新路线图进度..."
    
    python3 -c "
import json
import yaml

with open('$STATE_FILE') as f:
    state = json.load(f)

with open('$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/roadmap-meta.yaml') as f:
    meta = yaml.safe_load(f)

change_phase = meta.get('roadmap', {}).get('phase')
change_category = meta.get('roadmap', {}).get('category')

if change_phase and change_category:
    if change_phase in state['phases'] and change_category in state['phases'][change_phase]['categories']:
        cat_data = state['phases'][change_phase]['categories'][change_category]
        
        # 标记 change 完成
        if '$CHANGE_NAME' not in cat_data.get('completed_changes', []):
            cat_data.setdefault('completed_changes', []).append('$CHANGE_NAME')
        
        # 检查阶段是否完成
        all_complete = True
        for cat_id, cat_info in state['phases'][change_phase]['categories'].items():
            total = len(cat_info.get('changes', []))
            completed = len(cat_info.get('completed_changes', []))
            if completed < total:
                all_complete = False
                break
        
        state['phases'][change_phase]['gate_status']['all_changes_complete'] = all_complete
        
        with open('$STATE_FILE', 'w') as f:
            json.dump(state, f, indent=2)
        
        print(f'✅ 路线图进度已更新')
        if all_complete:
            print(f'🎉 阶段 {change_phase} 的所有 change 已完成！')
            print(f'   请检查阶段门控条件，准备进入下一阶段')
            print(f'   运行: skill_use(\"roadmap\", \"gate-report\")')
"
fi
```

**注意**：此输出在每个独立的 execute session 结束时显示，引导用户回到 guide 或继续其他操作。

## Work Unit 验证标准

每个 Work Unit 完成后必须通过：

```
1. LSP diagnostics：所有修改文件无 error
2. 编译：cmake --build build -j$(nproc) 成功（0 error, 0 warning）
3. 测试：ctest --output-on-failure 相关测试通过
```

任何验证失败 → 修复当前 Work Unit → 再继续下一个。

## tasks.md 回写规范

执行完成后必须同步 tasks.md 以通知 openspec CLI：

使用 `skills/_lib/tasks_writeback.sh` 辅助函数（Round B 提取自 execute.md L366-L399）：

```bash
source "$SCRIPT_DIR/_lib/tasks_writeback.sh"

# 方法 A：精确匹配单个任务（使用 awk index() + substr() 字面量匹配）
CHANGE_NAME="<name>" mark_task_done "实现UART寄存器配置"

# 方法 B：批量标记所有未完成任务（仅当全部完成时使用）
CHANGE_NAME="<name>" mark_all_tasks_done
```

**实现说明：**
- `mark_task_done` 用 awk `index()` + `substr()` 进行字面量匹配，不将任务描述中的 `[ ] . *` 解释为正则
- `mark_task_done` 用 exit code 验证替换是否实际发生（未匹配返回 1）
- 两者都内建 `mktemp` + `mv` 原子写入，避免并发场景文件冲突
- 需要 `CHANGE_NAME` 环境变量（由调用方设置）

## 常见问题处理

| 问题 | 检测 | 处理 |
|------|------|------|
| plan 文件不存在 | `test -f .rddf/plans/<name>.md` | 提示先执行 plan skill |
| change 不存在 | `openspec status` 失败 | 提示先 propose |
| worktree 不存在 | `test -d .rddf/wt/<name>` | 提示先执行 plan skill（含 worktree 创建） |
 | 构建失败 | `cmake --build` 非零退出 | 分析错误，修复后重试当前 Work Unit |
| worktree 路径查找 | `test -d .rddf/wt/<name>` 不可靠 | 用 `git worktree list \| awk '$3=="openspec/<name>" {print $1}'` 动态获取 |
