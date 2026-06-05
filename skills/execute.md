---
name: execute
description: 在 worktree 隔离环境执行 OpenSpec change 的实施计划。基于 Prometheus 生成的 .sisyphus/plans/ 执行。被 guide-ship 在 plan 阶段后调用。
license: MIT
compatibility: Requires openspec CLI and git worktree.
metadata:
  author: sisyphus
  version: "2.5"  # P0: Roadmap 进度更新和阶段门控检查
  generatedBy: "2.0"
---

# OpenSpec 工作流 — Execute

在 git worktree 隔离环境中执行 OpenSpec change 的实施计划。

## 工作流位置

```
worktree (openspec/<name>): 本技能在此执行
    │
    ├── 读取 .sisyphus/plans/<name>.md（Prometheus 详细计划）
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
| 任务来源 | `openspec instructions apply --json`（tasks.md） | `.sisyphus/plans/<name>.md`（Prometheus 分解） |
| 执行环境 | 当前目录 | worktree 隔离（`.zcf/<name>-wt/`） |
| 进度反馈 | 无自动回写 | 每个 Work Unit 完成后 `sed` 更新 tasks.md |

## 输入

- change name（可选，从 git branch 自动推断）

## 工作模式

```
此技能始终在 git worktree 隔离环境中执行。
所有代码修改和构建都在独立的 .zcf/<name>-wt/ 目录中进行。
```

### 模式自动识别

```bash
# Source helper (worktree-aware functions)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/worktree.sh" ]; then
  source "$SCRIPT_DIR/_lib/worktree.sh"
fi

# 自动检测项目根目录（用于全局安装的技能）
# P0-8: use main_repo_root (works in both main repo and worktrees)
PROJECT_ROOT=$(main_repo_root)
[ -d "$PROJECT_ROOT" ] || PROJECT_ROOT=$(pwd)
export PROJECT_ROOT
# 检测当前 git 上下文
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")

# 列出所有 worktree 以确定关系
WORKTREE_LIST=$(git worktree list)

# 判断是否在 worktree 内
if echo "$CURRENT_BRANCH" | grep -q '^openspec/'; then
    CHANGE_NAME=$(echo "$CURRENT_BRANCH" | sed 's/^openspec\///')
    WORKTREE_PATH=$(pwd)
    HAS_WORKTREE=true
    
    # 验证当前目录确实是对应的 worktree 目录
    MAIN_WT_PATH=$(echo "$WORKTREE_LIST" | grep "openspec/$CHANGE_NAME" | awk '{print $1}')
    if [ "$MAIN_WT_PATH" != "$(pwd)" ]; then
        echo "⚠️ 分支名与 worktree 路径不匹配"
        echo "   branch: openspec/$CHANGE_NAME"
        echo "   worktree from list: $MAIN_WT_PATH"
        echo "   current dir: $(pwd)"
    fi
else
    # ============================================================
    # P0 修复：不在 worktree 内时，提供自动引导而非直接退出
    # ============================================================
    echo "⚠️  当前不在 worktree 内"
    echo ""
    
    # 检查是否有已创建的 worktree
    WT_INFO=$(git worktree list | grep "openspec/" | awk '{print $1, $3}')
    
    if [ -z "$WT_INFO" ]; then
        echo "❌ 无已创建的 worktree"
        echo ""
        echo "请先执行 guide-ship 技能创建 worktree："
        echo "  skill_use(\"guide-ship\")   # 内部选择 change"
        echo ""
        echo "可用 change 列表："
        ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | grep -v archive/ | while read dir; do
            name=$(basename "$dir")
            echo "  - $name"
        done
        exit 1
    fi
    
    # 有 worktree 存在，显示选择菜单
    WT_COUNT=$(echo "$WT_INFO" | grep -c .)
    echo "📋 发现 $WT_COUNT 个已创建的 worktree："
    echo ""
    WORKTREE_COUNT=0
    while read -r wt_path wt_branch; do
        WORKTREE_COUNT=$((WORKTREE_COUNT + 1))
        name=$(echo "$wt_branch" | sed 's|^openspec/||')
        plan_file="$wt_path/.sisyphus/plans/$name.md"
        if [ -f "$plan_file" ]; then
            status="✅ 有计划文件"
        else
            status="⏳ 无计划文件"
        fi
        echo "  $WORKTREE_COUNT. $name"
        echo "     路径: $wt_path"
        echo "     分支: $wt_branch"
        echo "     状态: $status"
        echo ""
    done <<< "$WT_INFO"
    
    # P0-9 修复：用 EXECUTE_CHOICE 环境变量取代 read -p
    # 原因：read -p 在 AI/CI 等非交互环境会从 stdin 读取，永远阻塞直到输入
    # 新行为：
    #   - 默认选择 1（最常见：进入主 worktree）
    #   - 可通过 EXECUTE_CHOICE=N 覆盖选择 N
    #   - 多 worktree 场景下提示用户可通过环境变量覆盖
    WT_COUNT=$(echo "$WT_INFO" | grep -c .)
    choice="${EXECUTE_CHOICE:-1}"
    if [ -z "${EXECUTE_CHOICE:-}" ] && [ "$WT_COUNT" -gt 1 ]; then
        echo "ℹ️  多个 worktree 检测到，默认选择 1（可通过 EXECUTE_CHOICE=N 覆盖）"
    fi
    selected_line=$(echo "$WT_INFO" | sed -n "${choice}p")
    
    if [ -z "$selected_line" ]; then
        echo "❌ 无效选择，请设置 EXECUTE_CHOICE=1..$WT_COUNT"
        exit 1
    fi
    
    target_path=$(echo "$selected_line" | awk '{print $1}')
    target_branch=$(echo "$selected_line" | awk '{print $2}')
    
    echo ""
    echo "正在切换到 worktree：$target_path"
    cd "$target_path"
    CHANGE_NAME=$(echo "$target_branch" | sed 's|^openspec/||')
    echo "✅ 已切换到: $(pwd)"
    echo "   Branch: $(git branch --show-current)"
    echo "   Change: $CHANGE_NAME"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 提示：下次可直接使用以下命令进入此 worktree"
    echo "   cd $target_path"
    echo "   skill_use(\"execute\")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi
```

> **为什么必须在 worktree 内执行？**
> - 避免对 main 分支的直接修改
> - 独立构建目录（`.zcf/<name>-wt/build/`）互不干扰
> - 支持并行执行多个 change（每个 worktree 独立）
> - 隔离 git 操作，merge 时无冲突

## 执行步骤

### Step 1：确认在 worktree 内

```bash
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

### Step 3：读取 Prometheus 计划

```bash
PLAN_FILE=".sisyphus/plans/$CHANGE_NAME.md"
test -f "$PLAN_FILE" || { echo "❌ 计划文件不存在"; exit 1; }
```

解析计划中的 Work Units：
- 标记依赖关系
- 识别可并行执行的独立单元
- 识别串行依赖链

### Step 4：并行执行

```bash
# 对可并行执行的 Work Units，同时委托多个子代理
for each parallel_group in plan.parallel_groups:
    # 同组内 Work Units 无依赖关系
    for each work_unit in parallel_group:
        task(
            category="deep",
            load_skills=[],
            run_in_background=true,
            prompt="
                WORKTREE: $PROJECT_ROOT/.zcf/<CHANGE_NAME>-wt（在此目录下工作）
                目标：实现 Work Unit: <description>
                参考计划文件：.sisyphus/plans/<CHANGE_NAME>.md
                完成后：
                  1. 使用 awk 更新 $PROJECT_ROOT/openspec/changes/<CHANGE_NAME>/tasks.md 标记 [x]
                  2. cmake --build $PROJECT_ROOT/.zcf/<CHANGE_NAME>-wt/build -j$(nproc) 验证
            "
        )
    
    # 等待所有并行任务完成
    wait_for_all()
    
    # 执行串行依赖链中的下一个 Work Unit
```

### Step 5：串行依赖链执行

对存在依赖的 Work Units，按序执行：

```bash
for each work_unit in plan.serial_chain:
    委托 single deep 代理 → 验证 → 更新 tasks.md
```

### Step 6：全部完成后输出报告

### Step 7：输出明确的下一步操作指引

执行完成后，输出清晰的后续操作指引：

```bash
# 获取最终进度
COMPLETE=$(grep -c '^- \[x\]' "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md")
TOTAL=$(grep -c '^- \[' "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md")

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
# 内联 wt_path_for_branch_inline() 是为了避免 markdown bash 块对 _lib 函数的
# 隐式 source 依赖——每个块都自包含，跨 skill 直接复制也能工作。
# 注意：`git worktree list` 默认格式把分支名包在方括号里（[branch]），
# 所以比较时要把 br 也包成 "[openspec/$branch]"，否则 $3 == br 永远不成立。
wt_path_for_branch_inline() {
  local branch="${1:-}"
  [[ -z "$branch" ]] && return 1
  git worktree list 2>/dev/null | awk -v br="[openspec/$branch]" '$3 == br {print $1; exit}'
}
OTHER_WTS=""
CURRENT_WT=$(wt_path_for_branch_inline "$CHANGE_NAME")
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

# ============================================================
# P0: Roadmap 进度更新
# ============================================================
STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"
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

```bash
# 方法 A：已知任务描述，精确匹配（推荐）
# 使用 awk 的 index() 进行字面量匹配（不是 gsub 的正则匹配），
# 避免 TASK_DESC 中的正则元字符（如 [ ] . *）导致静默失败
TASK_DESC="实现UART寄存器配置"

# 使用 index() 精确查找，只在匹配时替换
# index() 返回子串位置（1-based），0 表示不匹配
TMPFILE=$(mktemp -t tasks_XXXXXX.md)
awk -v desc="- [ ] $TASK_DESC" -v repl="- [x] $TASK_DESC" '
  index($0, desc) { sub(desc, repl); changed=1 }
  { print }
  END { exit (changed ? 0 : 1) }
' "$PROJECT_ROOT/openspec/changes/<name>/tasks.md" > "$TMPFILE"

if [ $? -eq 0 ]; then
    mv "$TMPFILE" "$PROJECT_ROOT/openspec/changes/<name>/tasks.md"
    echo "✅ tasks.md 已更新"
else
    echo "⚠️  未找到匹配的任务描述: $TASK_DESC"
    rm -f "$TMPFILE"
fi

# 方法 B：批量标记所有未完成任务（仅当全部完成时使用）
TMPFILE=$(mktemp -t tasks_XXXXXX.md)
awk '{gsub(/- \[ \] /,"- [x] ")}1' \
  $PROJECT_ROOT/openspec/changes/<name>/tasks.md > "$TMPFILE" && \
  mv "$TMPFILE" $PROJECT_ROOT/openspec/changes/<name>/tasks.md

# 注意：
# - index() 进行字面量匹配，不会将 TASK_DESC 中的 [ ] . * 等解释为正则
# - 方法 A 使用 exit code 验证替换是否实际发生（方法 B 是全量替换无需验证）
# - mktemp 避免并发场景文件冲突
```

## 常见问题处理

| 问题 | 检测 | 处理 |
|------|------|------|
| plan 文件不存在 | `test -f .sisyphus/plans/<name>.md` | 提示先执行 plan skill |
| change 不存在 | `openspec status` 失败 | 提示先 propose |
| worktree 不存在 | `test -d .zcf/<name>-wt` | 提示先执行 plan skill（含 worktree 创建） |
 | 构建失败 | `cmake --build` 非零退出 | 分析错误，修复后重试当前 Work Unit |
| worktree 路径查找 | `test -d .zcf/<name>-wt` 不可靠 | 用 `git worktree list \| awk '$3=="openspec/<name>" {print $1}'` 动态获取 |
