---
name: guide-ship
description: Ship-side state machine for OpenSpec workflow — guides user from committed changes through worktree creation, spec-workflow plan generation, execution, archive, and cleanup. Owns git worktrees and tasks.md progress. Called by user when starting work on a committed change.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+. Plan generation delegated to spec-workflow/writing-plans (v2.0 自包含,无外部 skill 依赖).
metadata:
  author: sisyphus
  version: "2.0.1"  # v2.0.1: add post-archive fill suggestion hook for skeleton changes
  evolved-from: "split from guide.md v3.0; v2.0 移除 prometheus-planning 间接层, 直接调用内置 skill"
  user-invocable: true
---

# OpenSpec 工作流 — Ship-Side Guide

本技能是 OpenSpec 工作流的 **ship 端状态机**：负责在 git 提交 OpenSpec change artifacts 之后的所有工作——为已提交的 change 创建 worktree、生成实施计划、监控执行、归档清理。spec 端（`guide-arch` / `guide-plan`）在 artifacts 提交后发出 "ready for guide-ship" 交接信号，本技能接管从 worktree 到归档的全流程。

**职责边界**：
- **拥有**：git worktree、`.rddf/plans/<name>.md`、归档（merge → archive → cleanup）
- **不拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md` 的创建与提交（这些由 `guide-arch` / `guide-plan` 处理）
- **状态持久化**：不写状态文件；ship 端状态由 git worktree 列表和 `tasks.md` 进度反映（on-the-fly 读取）

**v2.0 简化**：v2.0 起,本技能直接调用内置的 `spec-workflow/writing-plans` 技能生成计划(无中间检测层)。原 `prometheus-planning` 间接层已删除。

**调用方式**：

```
skill_use("guide-ship")   # 无参数版本
```

---

## Phase 1: plan — Commit + 执行模式选择 + 计划

**入口条件**：spec 端已完成且 `openspec/changes/<name>/{proposal,design,tasks}.md` 已 git 提交（可用 `git show HEAD:<path>` 验证）。

**前置说明**：

每个 change 独立经历 plan→execute→archive。用户选择要处理的 change 后，自动检测并行冲突，选择执行模式：

| 模式 | 适用场景 | 机制 |
|------|---------|------|
| ⚡ 轻量模式 | 单 change、无并行 worktree | 直接在当前仓库创建 branch 执行，跳过 worktree |
| 🔀 worktree 模式 | 多 change 并行或有活跃 worktree | 创建隔离 worktree，互不干扰 |

**行为**：

1. 展示所有活跃 changes 的状态列表
2. 用户选择要处理的 change（或选「全部处理」）
3. 对选中的 change 执行 COMMIT GATE
4. **自动检测并行冲突**：
   - 无其他 worktree 且仅此一个 change → ⚡ 轻量模式（创建 branch，跳过 worktree）
   - 已有其他 worktree 或多个 change → 🔀 worktree 模式（创建 branch + worktree）
5. 生成实施计划
6. 进入执行模式选择

**展示所有活跃 changes 的状态**：

```bash
# Reconstruct ACTIVE_CHANGES from filesystem (was in spec-side before refactor)
ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | xargs -n1 basename 2>/dev/null | tr '\n' ' ')

echo "📋 所有活跃 Changes:"
echo ""
echo "| 变更 | Artifacts | Worktree | 计划文件 |"
echo "|-----|-----------|----------|---------|"
# git show HEAD:<path> 要求相对于 repo root 的相对路径。
# 把整个表格生成放在 (cd ... && ...) 子 shell 里,这样 git show 可以用相对路径。
(cd "$PROJECT_ROOT" 2>/dev/null && for name in $ACTIVE_CHANGES; do
    committed=$(git show HEAD:"openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
    wt_path="$PROJECT_ROOT/.rddf/wt/${name}"
    wt_exists=$([ -d "$wt_path" ] && git worktree list | grep -q "$wt_path" && echo "✅" || echo "❌")
    plan_exists=$([ -f "$wt_path/.rddf/plans/$name.md" ] 2>/dev/null && echo "✅" || echo "❌")
    echo "| $name | $committed | $wt_exists | $plan_exists |"
done)
```

**选择要处理的 change**：

```
Plan 阶段

📋 活跃 Changes:
| 变更 | Artifacts | Worktree | 计划文件 |
|-----|-----------|----------|---------|
| fix-ns-pollution | ✅ | ❌ | ❌ |
| add-stream-pipes | ✅ | ❌ | ❌ |

请选择:
1. 为 fix-ns-pollution 创建 worktree + 生成计划
2. 为 add-stream-pipes 创建 worktree + 生成计划
3. 批量处理：全部为已提交的变化创建 worktree
4. 🔄 切换当前焦点变更（选择另一个变更作为焦点）
0. 退出（worktree 保留，下次 skill_use("guide-ship") 可继续）
i. 其他输入
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

**选项 1/2 执行内容**（以 fix-ns-pollution 为例）：

```bash
CHANGE_NAME="fix-ns-pollution"

# COMMIT GATE - 脏检测
if [ -n "$(git status --porcelain "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/")" ]; then
    echo "⚠️  检测到未提交的修改，提示用户提交或放弃"
fi

# COMMIT GATE - 是否已 commit
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    if ! (cd "$PROJECT_ROOT" 2>/dev/null && git show HEAD:"openspec/changes/$CHANGE_NAME/.openspec.yaml" > /dev/null 2>&1); then
        echo "❌ Artifacts 尚未提交，请先提交"
    fi
else
    echo "❌ 当前仓库没有任何提交（HEAD 不存在）"
    echo "请先 git commit 一些文件后再执行 plan"
    exit 1
fi

# ============================================================
# PARALLEL CONFLICT DETECTION
# 自动检测是否存在并行冲突，决定执行模式
# ============================================================
EXISTING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | wc -l || echo 0)
TOTAL_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l || echo 0)

if [ "$EXISTING_WT" -gt 0 ] || [ "$TOTAL_CHANGES" -gt 1 ]; then
    MODE="worktree"
    echo "🔀 并行风险: $EXISTING_WT worktrees, $TOTAL_CHANGES changes → worktree 隔离模式"
else
    MODE="lightweight"
    echo "⚡ 无并行冲突 → 轻量模式（跳过 worktree）"
fi

# ============================================================
# HANDOFF STATE READ (P2-5)
# ============================================================
HANDOFF_FILE="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"
if [ -f "$HANDOFF_FILE" ]; then
    echo "📋 Reading plan-done handoff state..."
    cat "$HANDOFF_FILE"
    echo ""
    python3 -c "
import json, datetime, sys
try:
    with open('$HANDOFF_FILE') as f:
        data = json.load(f)
    data['ship_started_at'] = datetime.datetime.now().isoformat()
    with open('$HANDOFF_FILE', 'w') as f:
        json.dump(data, f, indent=2)
    print('✅ Handoff state updated: ship_started_at set')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'⚠️  Failed to update handoff: {e}', file=sys.stderr)
    sys.exit(0)
" 2>/dev/null
fi

# 创建 branch（如不存在）
if ! git branch --list "openspec/$CHANGE_NAME" | grep -q "openspec/$CHANGE_NAME"; then
    git branch "openspec/$CHANGE_NAME" HEAD
fi

# ============================================================
# MODE-SPECIFIC SETUP
# ============================================================
if [ "$MODE" = "worktree" ]; then
    # --- Worktree 模式 ---
    if [ -d "$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}" ]; then
        if git worktree list | grep -q "$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"; then
            echo "⚠️  Worktree 已存在"
        else
            echo "❌ 目录冲突，请先清理: rm -rf \"$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}\""
        fi
    else
        git worktree add "$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}" "openspec/$CHANGE_NAME"
    fi

    # WORKTREE VERIFICATION GATE (P0 FIX)
    WT_PATH="$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"
    WT_BRANCH=$(git worktree list --porcelain | awk -v path="$WT_PATH" '
        $1 == "worktree" && $2 == path { found=1; next }
        found && $1 == "branch" { print $2; exit }
        found && $1 == "detached" { print "DETACHED"; exit }
    ')
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Worktree 验证"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Worktree 路径: $WT_PATH"
    echo "  分支状态: ${WT_BRANCH:-未找到}"

    if [ "$WT_BRANCH" = "DETACHED" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "❌ 错误：Worktree 处于 detached HEAD 状态！"
        echo ""
        echo "  请执行以下命令修复："
        echo "    cd $WT_PATH"
        echo "    git checkout openspec/$CHANGE_NAME"
        echo ""
        echo "  或删除 worktree 重新创建："
        echo "    git worktree remove $WT_PATH"
        echo "    git branch -D openspec/$CHANGE_NAME"
        echo "    skill_use(\"guide-ship\")  # 重新进入 Plan 阶段"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 1
    elif [ -z "$WT_BRANCH" ]; then
        echo "⚠️  警告：无法确定 worktree 分支状态"
    fi

    EXPECTED_BRANCH="refs/heads/openspec/$CHANGE_NAME"
    if [ "$WT_BRANCH" != "$EXPECTED_BRANCH" ] && [ "$WT_BRANCH" != "openspec/$CHANGE_NAME" ]; then
        echo "⚠️  警告：Worktree 分支 $WT_BRANCH 与预期不符"
    fi
    echo "✅ Worktree 验证通过"
else
    # --- 轻量模式 ---
    # 切换到 change 分支（直接在当前仓库，不创建 worktree）
    if ! git checkout "openspec/$CHANGE_NAME" 2>/dev/null; then
        echo "❌ 切换分支失败: openspec/$CHANGE_NAME"
        exit 1
    fi
    WT_PATH="$PROJECT_ROOT"  # 计划在执行时使用当前目录
    echo "⚡ 轻量模式: 已切换到 openspec/$CHANGE_NAME, 跳过 worktree"
fi
```

```bash
# === Implementation plan generation ===
# v2.0 简化: 直接调用内置的 spec-workflow/writing-plans 技能
if [ "$MODE" = "worktree" ]; then
    cd "$WT_PATH" || { echo "❌ 进入 worktree 失败: $WT_PATH"; exit 1; }
else
    cd "$PROJECT_ROOT" || { echo "❌ 进入项目根目录失败"; exit 1; }
fi

# Skill-level bypass for users who intentionally skip plan generation (known risk).
if [ "${SKIP_PROMETHEUS_PLANNING:-no}" = "yes" ]; then
    echo "⚠️  跳过实施计划生成 (SKIP_PROMETHEUS_PLANNING=yes)"
    echo "   execute.md 阶段将无 .rddf/plans/<name>.md 可读"
    touch ".rddf/plans/$CHANGE_NAME.md"
    echo "- [ ] (占位任务) 手工填充 .rddf/plans/$CHANGE_NAME.md" >> ".rddf/plans/$CHANGE_NAME.md"
else
    # 直接调用内置 skill (无中间检测层,无外部依赖)
    if ! skill_use("spec-workflow/writing-plans") 2>/dev/null; then
        echo "❌ 实施计划生成失败"
        echo "   spec-workflow/writing-plans 技能未找到,检查安装是否完整"
        exit 1
    fi

    # 契约验证 (双重保险)
    if [ ! -f ".rddf/plans/$CHANGE_NAME.md" ]; then
        echo "❌ 计划文件缺失: .rddf/plans/$CHANGE_NAME.md"
        exit 1
    fi
    PLAN_TASK_COUNT=$(grep -c '^### Task' ".rddf/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
    PLAN_STEP_COUNT=$(grep -c '^- \[ \]' ".rddf/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
    if [ "$PLAN_TASK_COUNT" -eq 0 ] || [ "$PLAN_STEP_COUNT" -eq 0 ]; then
        echo "❌ 计划文件存在但无 Task 或 Step (Tasks: $PLAN_TASK_COUNT, Steps: $PLAN_STEP_COUNT)"
        exit 1
    fi
    echo "✅ 实施计划已生成: $PLAN_TASK_COUNT Tasks / $PLAN_STEP_COUNT Steps (TDD 5 步结构)"
fi

# ============================================================
# v2.0 钩子: 更新 iteration.json (current sprint tracker)
# 在计划生成成功后, 立即把 status 从 proposed 切到 in_worktree,
# 并写入 worktree_path + plan_path + tasks_total. 失败 graceful 退出.
# ============================================================
# v2.0.2 安全修复: bash 变量通过环境变量传递 (os.environ),
# 不用 '$VAR' 直接拼到 Python 源码. 避免单引号路径/注入风险.
PROJECT_ROOT="$PROJECT_ROOT" \
CHANGE_NAME="$CHANGE_NAME" \
MODE="$MODE" \
WT_PATH="$WT_PATH" \
PLAN_STEP_COUNT="$PLAN_STEP_COUNT" \
python3 -c '
import os, sys
try:
    from skills._lib import iteration as it_mod
except ImportError as e:
    print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
    sys.exit(0)
try:
    project_root = os.environ["PROJECT_ROOT"]
    change_name = os.environ["CHANGE_NAME"]
    mode = os.environ.get("MODE", "")
    wt_path = os.environ.get("WT_PATH", "")
    plan_step_count = os.environ.get("PLAN_STEP_COUNT", "0")
    data = it_mod.load(project_root)
    kwargs = {
        "name": change_name,
        "status": "in_worktree",
        "plan_path": f".rddf/plans/{change_name}.md",
        "tasks_total": int(plan_step_count or 0),
    }
    if mode == "worktree" and wt_path:
        kwargs["worktree_path"] = f".rddf/wt/{change_name}"
    data = it_mod.add_or_update_change(data, **kwargs)
    it_mod.save(project_root, data)
    print("✅ iteration.json: status=in_worktree, plan_path 已记录")
except Exception as e:
    print(f"⚠️  iteration.json 更新失败 (非致命): {e}", file=sys.stderr)
    sys.exit(0)
' 2>&1 | grep -v "^$" || true
```

**环境就绪 → 进入执行模式选择**：

```
${CHANGE_NAME} 已就绪（${MODE}模式），请选择执行方式：

📋 ${CHANGE_NAME} 状态:
  执行模式: ${MODE}（$([ "$MODE" = "worktree" ] && echo "隔离 worktree" || echo "当前仓库分支")）
  $([ "$MODE" = "worktree" ] && echo "Worktree: $WT_PATH" || echo "分支: openspec/$CHANGE_NAME")
  计划文件: .rddf/plans/${CHANGE_NAME}.md

请选择执行方式:
1. 🔒 在此 session 执行（阻塞）— 等待任务完成后返回
2. 🔓 分离执行（新终端）— 给出操作指引，立即返回
0. 退出（下次 skill_use("guide-ship") 可继续）
i. 其他输入
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

**选项 1（阻塞执行）执行内容**：

```bash
if [ "$MODE" = "worktree" ]; then
    cd "$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}" || exit 1
else
    cd "$PROJECT_ROOT" || exit 1
fi
skill_use("execute")
cd "$PROJECT_ROOT" || exit 1
# execute 会阻塞直到所有任务完成
```

**选项 2（分离执行）输出指引**：

```bash
echo ""
echo "🔓 分离执行指引"
echo ""
echo "为 ${CHANGE_NAME} 启动分离执行（${MODE}模式）："
echo ""
if [ "$MODE" = "worktree" ]; then
    echo "1. 在新终端中执行："
    echo "   cd $(pwd)/\"$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}\""
else
    echo "1. 在新终端中执行："
    echo "   cd $(pwd)/\"$PROJECT_ROOT\""
    echo "   git checkout openspec/$CHANGE_NAME"
fi
echo "   skill_use(\"execute\")"
echo ""
echo "2. execute 结果会自动写入 tasks.md"
echo ""
echo "3. 完成后，在此 session 运行 guide-ship 查看最新进度"
echo ""
echo "当前状态：${CHANGE_NAME} 等待分离执行（${MODE}模式）"
```

## Phase 1.5: 环境就绪验证 + 监控选择

**返回 Plan 前的检查 — 是否进入监控**：

```bash
# 检查活跃的 openspec/* 分支（含 worktree 和轻量模式）
WORKTREE_COUNT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | wc -l || echo 0)
LIGHTWEIGHT_COUNT=$(git branch 2>/dev/null | grep -c "openspec/" || echo 0)
TOTAL_ACTIVE=$((WORKTREE_COUNT + LIGHTWEIGHT_COUNT))

if [ "$TOTAL_ACTIVE" -gt 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 发现 $WORKTREE_COUNT worktrees + $LIGHTWEIGHT_COUNT 轻量分支 已就绪"
    echo ""
    echo "请选择:"
    echo "1. ✅ 进入 Execute 监控模式（查看所有 change 进度）"
    echo "2. 🔄 继续返回 Plan 阶段（处理其他 change）"
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

---

## Phase 2: execute — 监控与执行

**定位**：Execute 阶段是**监控模式**——读取 tasks.md 进度、显示所有 worktree 状态、提供执行入口。不是实际执行者。

**前置检测（每次入口执行）**：

```bash
# 读取所有 tasks.md 的实际进度（支持 worktree + 轻量模式）
echo "📋 所有 Changes 实际进度:"

LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

# 收集所有活跃的 openspec/* 分支（含 worktree 和轻量模式）
# 从 worktree 列表获取
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
    name=$(echo "$branch" | sed 's|openspec/||')
    tasks_file="$wt/openspec/changes/$name/tasks.md"
    mode="worktree"
    if [ -f "$tasks_file" ]; then
        total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null || echo 0)
        done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0)
        progress="${done}/${total}"
    else
        progress="? (文件不存在)"
    fi
    echo "  $name → $progress [$mode]"
done

# 补充轻量模式（有 openspec/ 分支但不在 worktree 列表中的）
if git branch | grep -q "openspec/"; then
    for branch in $(git branch | grep "openspec/" | sed 's/.*openspec\///'); do
        # 跳过已在 worktree 列表中的
        in_wt=false
        for wt in "${wt_list[@]}"; do
            wt_branch=$(git worktree list | grep -F "$wt" | awk '{print $3}' | sed 's|openspec/||')
            [ "$wt_branch" = "$branch" ] && in_wt=true && break
        done
        $in_wt && continue

        tasks_file="$PROJECT_ROOT/openspec/changes/$branch/tasks.md"
        CURRENT_BRANCH=$(git branch --show-current)
        if [ "$CURRENT_BRANCH" = "openspec/$branch" ]; then
            mode="轻量(当前)"
        else
            mode="轻量"
        fi
        if [ -f "$tasks_file" ]; then
            total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null || echo 0)
            done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0)
            progress="${done}/${total}"
        else
            progress="? (文件不存在)"
        fi
        echo "  $branch → $progress [$mode]"
    done
fi

echo ""
echo "上次检测: $LAST_CHECK"
```

**菜单选项**：

```
Execute 阶段（监控模式）

📋 所有 Changes 状态:（实时读取 tasks.md）
| 变更 | 模式 | 进度 | 执行状态 |
|-----|------|------|---------|
| fix-ns-pollution | worktree | 1/3 | 🔒 执行中 |
| add-stream-pipes | 轻量 | 2/5 | 🔓 分离执行 |

上次检测: 2026-05-18 10:35:00

请选择:
1. 🔒 在此 session 执行 fix-ns-pollution（阻塞）
2. 🔓 分离执行 fix-ns-pollution（新终端）
3. 🔒 在此 session 执行 add-stream-pipes（阻塞）
4. 🔓 分离执行 add-stream-pipes（新终端）
5. 📋 查看任务列表（指定变更）
6. 🔧 运行构建验证（指定变更）
7. 🔄 刷新进度（重新读取所有 tasks.md）
8. ↩️ 返回 Plan 阶段（创建更多 worktree）
0. 退出（下次 skill_use("guide-ship") 继续）
i. 其他输入
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

**选项 7（刷新进度）执行内容**：

```bash
# 重新读取所有 tasks.md 进度
echo "🔄 正在刷新进度..."
LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")
# 重新显示表格
# 用户选择后继续循环
```

**选项 1/3（阻塞执行）执行内容**：

```bash
CHANGE_NAME="fix-ns-pollution"
WORKTREE_PATH="$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"

if [ -d "$WORKTREE_PATH" ] && git worktree list | grep -q "$WORKTREE_PATH"; then
    cd "$WORKTREE_PATH" || { echo "❌ 无法进入 worktree 目录: $WORKTREE_PATH"; exit 1; }
else
    # 轻量模式：检查是否已在正确分支
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "openspec/$CHANGE_NAME" ]; then
        git checkout "openspec/$CHANGE_NAME" 2>/dev/null || {
            echo "❌ 无法切换到 openspec/$CHANGE_NAME，请先创建分支"
            exit 1
        }
    fi
    echo "⚡ 轻量模式: 当前分支 openspec/$CHANGE_NAME"
fi
skill_use("execute")
# 阻塞等待所有任务完成
cd "$(git rev-parse --show-toplevel)"
```

**选项 2/4（分离执行）输出指引**：

```bash
echo ""
echo "🔓 分离执行指引"
echo ""
echo "为 ${CHANGE_NAME} 启动分离执行："
echo ""
echo "1. 在新终端中执行："
echo "   cd $(pwd)/\"$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}\""
echo "   skill_use(\"execute\")"
echo ""
echo "2. execute 结果会自动写入 tasks.md"
echo ""
echo "3. 完成后，在此 session 运行 guide-ship 查看最新进度"
echo ""
echo "当前状态：${CHANGE_NAME} 🔓 分离执行中"
```

**状态更新**：将执行状态设为 🔓，下次入口时通过 tasks.md 同步实际进度。

**监控说明**：

- Guide-ship 不执行任务，只监控
- 进度来自 tasks.md 的 `grep -c "^- \[x\]"`
- 执行状态列说明：
  - 🔒 执行中 — 此 session 正在阻塞执行
  - 🔓 分离执行 — 在新终端执行，不阻塞
  - ⏳ 等待 — 未开始
  - ✅ 完成 — 所有任务完成

---

## Phase 2.5: review — 执行后审查

**入口条件**：execute 完成（tasks.md 中所有 `[ ]` 已变 `[x]`），或用户主动选择审查。

**前置说明**：

execute 在 worktree 中执行 change 后，可能产生三类新债务：
- **范围内债务**：当前 change 的 scope 内不完整（测试覆盖不全、遗漏边角情况）
- **旁效应债务**：独立的代码遗留问题（修 A 文件时发现 B 文件有遗留 TODO）
- **架构漂移**：执行结果偏离 ADR 定义的目标架构

本阶段自动扫描这些债务，分类，并提供回流机制。默认可跳过，不影响 archive。

**1. 采集债务**：

```bash
CHANGE_NAME="<从 Phase 2 获得>"
WT_PATH="$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"

echo "🔍 扫描 execute 后变化..."

# 1a. 新增 TODO/FIXME 标记
if [ -d "$WT_PATH" ]; then
    cd "$WT_PATH"
    git diff HEAD -- '*.cpp' '*.h' '*.hpp' '*.py' '*.ts' 2>/dev/null \
      | grep '^+' | grep -E 'TODO|FIXME|HACK|WORKAROUND' \
      > /tmp/review_new_todos.txt 2>/dev/null
    NEW_TODO_COUNT=$(wc -l < /tmp/review_new_todos.txt 2>/dev/null || echo 0)
else
    NEW_TODO_COUNT=0
fi

# 1b. 测试回归检测
if [ -f "build/CTestTestfile.cmake" ] 2>/dev/null; then
    ctest --test-dir build --output-on-failure 2>/dev/null \
      | grep -E "FAILED|not ok" \
      > /tmp/review_test_failures.txt 2>/dev/null
    TEST_FAIL_COUNT=$(wc -l < /tmp/review_test_failures.txt 2>/dev/null || echo 0)
else
    TEST_FAIL_COUNT=0
fi

echo ""
echo "📋 债务扫描结果:"
echo "  新增 TODO/FIXME: $NEW_TODO_COUNT"
echo "  测试失败: $TEST_FAIL_COUNT"
```

**2. 分类展示（用户交互）**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 执行后审查 (Review Phase)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 ${CHANGE_NAME} (${done}/${total} tasks ✅)

🔍 债务扫描结果:
  新增 TODO/FIXME: [N] 条
  测试失败: [N] 个

请选择:
1. 🏠 范围內债务 → 追加到当前 change tasks.md（返回 execute）
2. 🔖 创建新 debt change → 加入 proposal-suggestions.md (type=debt)
3. 📐 架构漂移 → 回注 guide-arch (生成差距分析)
4. ⏭️  跳过 → 直接进入 archive（默认）
5. 📋 查看详细债务内容
i. 手动输入新 change 名称
```

**用户输入处理（case handler）**：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  1)
    # 范围內债务: 追加到 tasks.md
    echo "📝 追加范围內债务到 tasks.md..."
    if [ -f "/tmp/review_new_todos.txt" ] && [ -s "/tmp/review_new_todos.txt" ]; then
        cat >> "$WT_PATH/openspec/changes/$CHANGE_NAME/tasks.md" << 'EOF'

## Review 阶段 (execute 后追加)

EOF
        while IFS= read -r line; do
            file=$(echo "$line" | cut -d: -f1)
            text=$(echo "$line" | cut -d: -f2-)
            echo "- [ ] review: $file — $text" >> "$WT_PATH/openspec/changes/$CHANGE_NAME/tasks.md"
        done < /tmp/review_new_todos.txt
        echo "✅ 范围內债务已追加，返回 execute 继续执行..."
    else
        echo "⚠️  无范围內债务可追加"
    fi
    ;;
  2)
    # 旁效应债务: 创建新 change
    DEBT_NAME="cleanup-${CHANGE_NAME}-debt"
    echo "🔖 创建新 debt change: $DEBT_NAME"

    # 追加到 proposal-suggestions.md（type=debt）
    PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import os, json, subprocess
try:
    debt = {
        'name': '$DEBT_NAME',
        'priority': 'P2',
        'source': 'execute review: $CHANGE_NAME',
        'status': '待创建',
        'phase': 'default',
        'category': 'arch-design',
        'type': 'debt',
        'description': '## 架构依据\n- $CHANGE_NAME 执行后审查发现\n## 范围\n- 见 TODO 扫描结果\n## 关键场景\n- 常规清理\n## 技术约束\n- MUST NOT 影响已有功能\n## 验收标准\n- 新增测试通过\n',
        'effort': '1天'
    }
    path = os.path.join(os.environ['PY_PROJECT_ROOT'], 'proposal-suggestions.md')
    if os.path.isfile(path):
        with open(path) as f:
            entries = json.load(f)
    else:
        entries = []
    entries.append(debt)
    with open(path, 'w') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f'✅ 已追加到 proposal-suggestions.md: {debt[\"name\"]}')
except Exception as e:
    print(f'⚠️  追加失败: {e}')
"

    # 创建 openspec change 目录
    cd "$PROJECT_ROOT"
    openspec new change "$DEBT_NAME" 2>/dev/null || true

    # 文件冲突检测 → 自动增量 deps (v2.0.1)
    # ADR-0014 决策 3: re-deps 由文件冲突驱动, 非 change type
    echo ""
    echo "🔍 检查文件冲突 + 自动增量 deps..."
    
    # 用 iteration.list_active 获取活跃 (proposed/in_worktree/completed) change 列表
    ACTIVE_CHANGES_JSON=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 << 'PYEOF' 2>/dev/null
import os, sys, json
try:
    from skills._lib import iteration as it
    d = it.load(os.environ.get("PY_PROJECT_ROOT", "."))
    out = it.list_active(d)
    # 排除 DEBT_NAME 自身
    names = [c["name"] for c in out if c["name"] != "$DEBT_NAME"]
    print(json.dumps(names))
except Exception as e:
    print("[]", file=sys.stderr)
PYEOF
)
    
    # 启发式冲突检测: debt change 与活跃 change 共享关键词
    CONFLICT_DETECTED=false
    if [ -n "$ACTIVE_CHANGES_JSON" ] && [ "$ACTIVE_CHANGES_JSON" != "[]" ]; then
        # 提取 DEBT_NAME 的关键词 (去掉 debt-/fix-/prefix-/cleanup- 前缀后的第一段)
        DEBT_KEYWORD=$(echo "$DEBT_NAME" | sed -E 's/^(debt|fix|prefix|cleanup)-?(.*)/\2/' | sed 's/-.*//')
        if [ -n "$DEBT_KEYWORD" ]; then
            for active_name in $(echo "$ACTIVE_CHANGES_JSON" | python3 -c "import sys, json; print(' '.join(json.load(sys.stdin)))"); do
                if echo "$active_name" | grep -qF "$DEBT_KEYWORD"; then
                    CONFLICT_DETECTED=true
                    echo "⚠️  潜在文件冲突: $DEBT_NAME 与 $active_name (共享关键词 '$DEBT_KEYWORD')"
                    break
                fi
            done
        fi
    fi
    
    if [ "$CONFLICT_DETECTED" = "true" ]; then
        echo "  → 自动增量 deps (将新 debt change 加入 .deps-candidates.json)..."
        # 追加到 .deps-candidates.json
        PY_PROJECT_ROOT="$PROJECT_ROOT" python3 << PYEOF
import os, json
p = os.path.join(os.environ.get("PY_PROJECT_ROOT", "."), ".rddf/state/.deps-candidates.json")
data = {"candidates": []}
if os.path.isfile(p):
    try:
        with open(p) as f:
            data = json.load(f)
            if not isinstance(data, dict) or "candidates" not in data:
                data = {"candidates": []}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"candidates": []}
candidates = data.get("candidates", [])
if "$DEBT_NAME" not in candidates:
    candidates.append("$DEBT_NAME")
    data["candidates"] = candidates
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ 已添加 $DEBT_NAME 到 .deps-candidates.json")
else:
    print(f"  ℹ️  $DEBT_NAME 已在 .deps-candidates.json 中")
PYEOF
        # 调用 deps
        if skill_use("deps") 2>/dev/null; then
            echo "✅ 增量 deps 完成, 新 debt change 已纳入依赖图"
            echo "   查看: cat .rddf/state/.deps-output.md"
        else
            echo "⚠️  skill_use(\"deps\") 调用失败, 请手动重跑"
            echo "   运行: skill_use(\"deps\")"
        fi
    else
        echo "✅ 无文件冲突（debt change '$DEBT_NAME' 与活跃 changes 无关键词重叠）"
        echo "   debt change 可安全 deferred 到下次 sprint"
    fi
    ;;
  3)
    # 架构漂移: 回注 guide-arch
    DRIFT_DOC="$PROJECT_ROOT/docs/architecture/${CHANGE_NAME}-drift-analysis.md"
    mkdir -p "$(dirname "$DRIFT_DOC")"
    cat > "$DRIFT_DOC" << DRIFTDOC
# 架构漂移分析: $CHANGE_NAME

> **来源**: execute 后 review Phase 2.5
> **生成日期**: $(date -Iseconds)
> **关联 change**: $CHANGE_NAME
> **状态**: 草案

## 检测到的漂移

$(cat /tmp/review_new_todos.txt 2>/dev/null | sed 's/^/- /' || echo '(未检测到)')

## 建议操作

1. 运行 skill_use("guide-arch") 审查是否需要修正 ADR
2. 如 ADR 需修正，回到 adr-create 阶段创建或修订 ADR
3. 修正后重新运行 guide-plan → deps

DRIFTDOC
    echo "✅ 差距分析已创建: $DRIFT_DOC"
    echo ""
    echo "💡 下一步: 运行 skill_use(\"guide-arch\") 进入架构审查"
    ;;
  4)
    echo "⏭️  跳过 review，直接进入 archive"
    ;;
  5)
    echo "📋 新增 TODO/FIXME 标记:"
    cat /tmp/review_new_todos.txt 2>/dev/null || echo "(无)"
    echo ""
    echo "📋 测试失败详情:"
    cat /tmp/review_test_failures.txt 2>/dev/null || echo "(无)"
    ;;
esac
```

**3. 门控（可选）**:

review 阶段的目的是分类记录债务，不阻断 archive。如果用户选择 "跳过"（选项 4），正常进入 Phase 3。门控检查通过 gate.py 的 `review_debt_recorded`（warning 级别）实现，见 `skills/_lib/gate.py`。

**4. deps 重新分析规则**:

旁效应债务 change 的 deps 重新分析由**文件冲突**驱动，不按 change type 判断：
- 新 debt change 修改的文件与已归档 change 的文件无重叠 → 跳过 deps（safe defer）
- 有重叠 → 建议重新 deps，将新 change 纳入依赖图

---

## Phase 3: archive — 状态检查与归档

**入口条件**：execute 已完成（所有 worktree 的任务都完成），或用户主动选择此阶段。

**前置说明**：

每个 change 独立归档。可以一次性归档所有已完成的 change，或逐个处理。

**展示所有 change 状态**：

```
Status 阶段

📋 所有 Changes 状态:
| 变更 | Worktree | 任务进度 | 状态 |
|-----|----------|---------|------|
| fix-ns-pollution | .rddf/wt/fix-ns-pollution | 3/3 ✅ | 可归档 |
| add-stream-pipes | .rddf/wt/add-stream-pipes | 2/5 🔄 | 进行中 |

请选择:
1. 归档 fix-ns-pollution（merge → archive → cleanup）
2. 归档 add-stream-pipes（需先完成所有任务）
3. 📊 全局概览（所有 change + worktree）
4. 🔍 详细检测（同步问题等）
5. ↩️ 返回 Execute 阶段
i. 其他输入
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

**归档流程（选项 1/2）**：

```bash
# 对选定的 change 执行归档
CHANGE_NAME="fix-ns-pollution"
DEFAULT_BRANCH=$(find_default_branch)

# 检测执行模式：有 worktree → worktree 模式，否则轻量模式
WT_PATH="$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"
if [ -d "$WT_PATH" ] && git worktree list | grep -q "$WT_PATH"; then
    ARCHIVE_MODE="worktree"
else
    ARCHIVE_MODE="lightweight"
fi

echo "🔍 归档模式: $ARCHIVE_MODE"

# Feature 完整性提示（v2.0.1 新增 — 非阻断）
PY_PROJECT_ROOT="$PROJECT_ROOT" python3 << 'PYEOF' 2>/dev/null
import os, sys
try:
    from skills._lib import iteration as it
    d = it.load(os.environ.get("PY_PROJECT_ROOT", "."))
    change_name = os.environ.get("CHANGE_NAME", "")
    feature = it.derive_feature_name(change_name)

    # 只有 feature- 前缀的 change 才检查 feature 完整性
    if not change_name.startswith("feature-"):
        sys.exit(0)

    progress = it.feature_progress(d)
    if feature not in progress:
        sys.exit(0)

    done, total = progress[feature]
    if total <= 1:
        sys.exit(0)  # 单 change feature，无需检查

    remaining = total - done
    if remaining > 1 or (remaining == 1 and any(c.get("status") != "archived" for c in d.get("changes", []) if it.derive_feature_name(c.get("name", "")) == feature and c.get("name") != change_name)):
        print(f"⚠️  Feature '{feature}' 完整性提示: 已归档 {done}/{total}")
        print(f"   还有 {total - done} 个 sub-change 未归档，此 feature 仍未完整")
        print(f"   归档不会阻断，请知悉")
except Exception:
    pass
PYEOF

# ============================================================
# 加载辅助函数
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/worktree.sh" ]; then
  source "$SCRIPT_DIR/_lib/worktree.sh"
fi
if [ -f "$SCRIPT_DIR/_lib/archive.sh" ]; then
  source "$SCRIPT_DIR/_lib/archive.sh"
fi

if [ "$ARCHIVE_MODE" = "worktree" ]; then
    # ============================================================
    # MERGE VERIFICATION GATE (P0 FIX, 仅 guide-ship 保留)
    # ============================================================
    echo "🔍 验证 worktree 分支状态..."

    WT_BRANCH=$(git worktree list --porcelain | awk -v path="$WT_PATH" '
        $1 == "worktree" && $2 == path { found=1; next }
        found && $1 == "branch" { print $2; exit }
        found && $1 == "detached" { print "DETACHED"; exit }
    ')

    if [ "$WT_BRANCH" = "DETACHED" ]; then
        echo "❌ 错误：Worktree 处于 detached HEAD，无法 merge"
        echo "   请先切换到正确分支："
        echo "   cd $WT_PATH && git checkout openspec/$CHANGE_NAME"
        exit 1
    fi

    # archive_change 内部完成: pre-merge check → checkout default → merge → verify → openspec archive → worktree/branch cleanup
    archive_change "$CHANGE_NAME"
    cd "$PROJECT_ROOT" || exit 1
else
    # ============================================================
    # 轻量模式归档：直接 merge branch + cleanup
    # ============================================================
    branch="openspec/$CHANGE_NAME"

    # 检查 branch 是否有新提交
    new_commits=$(git rev-list --count "$DEFAULT_BRANCH..$branch" 2>/dev/null || echo 0)
    if [ "$new_commits" -eq 0 ]; then
        echo "❌ 分支 $branch 无新提交，无需 merge"
        # 仍尝试 cleanup
    else
        echo "📦 Merge $branch → $DEFAULT_BRANCH ($new_commits 个新提交)"

        # 先切回 default branch
        git checkout "$DEFAULT_BRANCH" || { echo "❌ 无法切换到 $DEFAULT_BRANCH"; exit 1; }

        # --ff-only merge，不可快进时报错
        if git merge --ff-only "$branch" 2>/dev/null; then
            echo "✅ Fast-forward merge 到 $DEFAULT_BRANCH 完成"
        else
            echo "⚠️  Fast-forward 不可用，创建 merge commit"
            git merge --no-ff "$branch" -m "merge: $CHANGE_NAME change" || {
                echo "❌ merge 失败"
                exit 1
            }
        fi

        # openspec archive（CLI 调用）
        openspec archive "$CHANGE_NAME" --yes || {
            echo "⚠️  openspec archive 失败（可能是 CLI 未找到）"
        }
    fi

    # 删除分支
    if git branch -d "$branch" 2>/dev/null; then
        echo "✅ Branch 已删除: $branch"
    else
        echo "⚠️  Branch $branch 有未合并的提交"
        if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
            git branch -D "$branch" 2>/dev/null || true
        fi
    fi

    echo "✅ $CHANGE_NAME 已归档（轻量模式）"
fi

# ============================================================
# 归档后检查是否还有其他 change/worktree 需要处理
# ============================================================
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | grep -c . || true)
REMAINING_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l || true)

if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING_CHANGES" -gt 0 ]; then
    echo ""
    echo "📋 还有 $REMAINING_WT worktrees, $REMAINING_CHANGES changes 待处理"
    echo ""
    echo "请选择:"
    echo "1. 继续处理（进入 Execute/Plan 阶段）"
    echo "i. 其他输入"
else
    echo ""
    echo "📋 所有 change 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 进入 cleanup 阶段"
    echo "2. 完成 workflow（进入 ship-done）"
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

---

## Phase 3 完成后: post-archive fill suggestion hook

**触发条件**: archive 成功完成后

**行为**:

1. 调用 `iteration.get_unblocked_planned(project_root)` 扫描 `iteration.json`
2. 找出所有 `status="planned"` 且 blocker 状态为 `archived` 的 change
3. 若有结果，输出建议信息（不自动调用 guide-plan fill）
4. 若无结果，保持现有输出不变

**实现要点**（新增 `iteration.get_unblocked_planned()` 函数后调用）：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 扫描因本次归档而解除阻塞的 planned change
UNBLOCKED=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, sys
try:
    from skills._lib import iteration as it_mod
    data = it_mod.load(os.environ["PROJECT_ROOT"])
    unblocked = []
    for c in data.get("changes", []):
        if c.get("status") != "planned":
            continue
        blocker_name = c.get("blocker")
        if not blocker_name:
            unblocked.append(c["name"])
            continue
        # Look up blocker status
        blocker = next(
            (b for b in data.get("changes", []) if b.get("name") == blocker_name),
            None
        )
        if blocker and blocker.get("status") in ("completed", "archived"):
            unblocked.append(c["name"])
    for n in unblocked:
        print(n)
except Exception as e:
    print(f"⚠️ get_unblocked_planned failed: {e}", file=sys.stderr)
' 2>/dev/null)

if [ -n "$UNBLOCKED" ]; then
    echo ""
    echo "💡 Fill suggestion (post-archive):"
    echo "   以下 planned change 的 blocker 已解除，可填充："
    for name in $UNBLOCKED; do
        echo "     - $name"
    done
    echo "   运行 'skill_use(\"guide-plan\")' → 选择 '3. 填充骨架 change (fill)' 来填充下一个"
fi
```

**关键约束**:
- 不自动调用 guide-plan fill（用户必须显式确认）
- 输出格式与现有 Phase 3 输出兼容
- 失败容错：iteration.json 读取失败时仅 stderr 警告，不阻塞 archive

---

## Phase 4: cleanup — 测试清理

**入口条件**：所有活跃 changes 均已归档后，或用户主动选择。

**菜单选项**：

```
清理选项

📋 Worktrees: (列出所有剩余 worktree)
📋 Branches: (列出所有 openspec/* branches)

请选择:
1. 🧹 清理指定 worktree + branch
2. 🗑️ 清理所有 worktree + openspec/* branches
3. 📝 输出测试总结报告（所有 changes 的执行记录）
4. ↩️ 返回上一阶段
i. 其他输入
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

**选项 1 执行**：

```
请选择要清理的 worktree:
1. fix-ns-pollution (.rddf/wt/fix-ns-pollution)
2. add-stream-pipes (.rddf/wt/add-stream-pipes)
```

**选项 2 执行**：

```bash
# 清理所有 worktree
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    git worktree remove "$wt" 2>/dev/null || true
done

# 清理所有 openspec/* branches
# 策略 (P2-9): 默认 -d 安全删除；显示最后提交供人审查；未合并时需显式 FORCE_BRANCH_DELETE=yes 才允许 -D
git branch | grep "openspec/" | while read branch; do
    LAST_COMMIT=$(git log -1 --format="%h %s" "$branch" 2>/dev/null)
    if git branch -d "$branch" 2>/dev/null; then
        echo "✅ $branch deleted (last: $LAST_COMMIT)"
    else
        echo "⚠️  $branch 有未合并的提交"
        echo "   最后提交: $LAST_COMMIT"
        if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
            git branch -D "$branch" 2>/dev/null || true
            echo "   强制删除(因 FORCE_BRANCH_DELETE=yes)"
        else
            echo "   跳过(设置 FORCE_BRANCH_DELETE=yes 强制删除)"
        fi
    fi
done

echo "✅ 所有 worktree 和 openspec/* branches 已清理"
```

---

## Phase 5: ship-done (Exit)

Triggered when all committed changes have been archived (or no changes remain).

**Loop check:**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# Count remaining unprocessed changes
REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l)

if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then
    echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"
    echo ""
    echo "请选择:"
    echo "1. 继续处理 (skill_use(\"guide-ship\")) — 还有 worktree 要处理"
    echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) — 创建更多 changes"
    echo "3. 本次 session 结束 — 退出 ship-done,稍后继续"
    echo "4. 项目完成 — 不再做任何 change(此项目归档)"
    echo "i. 其他输入"
else
    echo "✅ 所有 changes 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 继续处理 (skill_use(\"guide-ship\")) — 还有 worktree 要处理"
    echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) — 创建更多 changes"
    echo "3. 本次 session 结束 — 退出 ship-done,稍后继续"
    echo "4. 项目完成 — 不再做任何 change(此项目归档)"
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
