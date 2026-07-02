---
name: guide-ship
description: Ship-side state machine for OpenSpec workflow — guides user from committed changes through worktree creation, spec-workflow plan generation, execution, archive, and cleanup. Owns git worktrees and tasks.md progress. Called by user when starting work on a committed change.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+. Plan generation delegated to spec-workflow/writing-plans (v2.0 自包含,无外部 skill 依赖).
metadata:
  author: sisyphus
  version: "2.0"  # v2.0 重构: 直接调用 spec-workflow/writing-planning, 无中间检测层
  evolved-from: "split from guide.md v3.0; v2.0 移除 prometheus-planning 间接层, 直接调用内置 skill"
  user-invocable: true
---

# OpenSpec 工作流 — Ship-Side Guide

本技能是 OpenSpec 工作流的 **ship 端状态机**：负责在 git 提交 OpenSpec change artifacts 之后的所有工作——为已提交的 change 创建 worktree、生成实施计划、监控执行、归档清理。spec 端（`guide-spec`）在 artifacts 提交后发出 "ready for guide-ship" 交接信号，本技能接管从 worktree 到归档的全流程。

**职责边界**：
- **拥有**：git worktree、`.rddf/plans/<name>.md`、归档（merge → archive → cleanup）
- **不拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md` 的创建与提交（这些由 `guide-spec` 处理）
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
    wt_path="$PROJECT_ROOT/.spec-workflow/wt/${name}"
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
HANDOFF_FILE="$PROJECT_ROOT/.spec-workflow/.plan-handoff.json"
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
    echo "2. 回到 spec 端 (skill_use(\"guide-spec\")) — 创建更多 changes"
    echo "3. 本次 session 结束 — 退出 ship-done,稍后继续"
    echo "4. 项目完成 — 不再做任何 change(此项目归档)"
    echo "i. 其他输入"
else
    echo "✅ 所有 changes 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 继续处理 (skill_use(\"guide-ship\")) — 还有 worktree 要处理"
    echo "2. 回到 spec 端 (skill_use(\"guide-spec\")) — 创建更多 changes"
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
