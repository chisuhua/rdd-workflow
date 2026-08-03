---
name: guide-ship
description: Ship-side state machine for OpenSpec workflow — guides user from committed changes through worktree creation, rdd-workflow plan generation, execution, archive, and cleanup. Owns git worktrees and tasks.md progress. Called by user when starting work on a committed change.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+. Plan generation delegated to rdd-workflow-writing-plans (v2.0 自包含,无外部 skill 依赖).
metadata:
  version: "3.0"  # v3.0 rename (BREAKING); see ADR-0023
  author: sisyphus
  evolved-from: "split from guide.md v3.0; v2.0 移除 prometheus-planning 间接层, 直接调用内置 skill"
  user-invocable: true
---

# OpenSpec 工作流 — Ship-Side Guide

本技能是 OpenSpec 工作流的 **ship 端状态机**：负责在 git 提交 OpenSpec change artifacts 之后的所有工作——为已提交的 change 创建 worktree、生成实施计划、监控执行、归档清理。spec 端（`guide-arch` / `guide-plan`）在 artifacts 提交后发出 "ready for guide-ship" 交接信号，本技能接管从 worktree 到归档的全流程。

**职责边界**：
- **拥有**：git worktree、`.rddf/plans/<name>.md`、归档（merge → archive → cleanup）
- **不拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md` 的创建与提交（这些由 `guide-arch` / `guide-plan` 处理）
- **状态持久化**：不写状态文件；ship 端状态由 git worktree 列表和 `tasks.md` 进度反映（on-the-fly 读取）

**v2.0 简化**：v2.0 起,本技能直接调用内置的 `rdd-workflow-writing-plans` 技能生成计划(无中间检测层)。原 `prometheus-planning` 间接层已删除。

**调用方式**：

```
skill_use("guide-ship")   # 无参数版本
```

---

## Phase 1: plan — Commit + 执行模式选择 + 计划

**入口条件**：spec 端已完成且 `openspec/changes/<name>/{proposal,design,tasks}.md` 已 git 提交（可用 `git show HEAD:<path>` 验证）。

**rddf-session 入口 hook**（ADR-0017）：创建或查找当前 opencode session 的 `stage_ship` rddf-session（parent=最新 stage_plan）：

```bash
# rddf-session 入口 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
# stage_ship parent: latest stage_plan (auto-resolved by helper)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
```

**环境健康快照**（rdd-env-check cache 接入，命中输出单行）：

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/ship_env_check.sh"
run_ship_env_check
```

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
4. **Quick Finish 检测**：若 tasks.md 剩余 ≤2 个 trivial 任务且无未提交代码变更，提示用户选择 Quick Finish（跳过 worktree/plan/execute）或标准流程
5. **自动检测并行冲突**：
   - 无其他 worktree 且仅此一个 change → ⚡ 轻量模式（创建 branch，跳过 worktree）
   - 已有其他 worktree 或多个 change → 🔀 worktree 模式（创建 branch + worktree）
6. 生成实施计划
7. 进入执行模式选择

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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```

**选项 1/2 执行内容**（以 fix-ns-pollution 为例）：

```bash
# === Phase 1: thin orchestrator - heavy lifting in scripts/ship_plan.sh ===
# Skip plan generation via SKIP_PROMETHEUS_PLANNING=yes (escape hatch; not recommended)
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CHANGE_NAME="${CHANGE_NAME:-fix-ns-pollution}"  # default for documentation

# source 与调用必须同一行: AI 平台可能把代码块拆到多个 bash 进程,
# 拆行会导致 "run_ship_phase1: command not found" (与 detect_execution_mode 同款根因)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_plan.sh" && run_ship_phase1 "$PROJECT_ROOT" "$CHANGE_NAME"
```

> **AI 编排环境**: 当 bash 子进程无 `skill_use` 命令时（AI 编排者调用辅助脚本），计划生成由编排者完成——编排者需按 `rdd-workflow-writing-plans` 规范生成 `.rddf/plans/<change_name>.md`。`ship_plan.sh` 会降级输出指引而非报错中断。

**v2.1: wave scheduler entry check**（入口扫描可推进的 changes）：

```bash
# v2.1: wave scheduler entry check - suggest changes ready to advance
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_lib_dir)/wave_scheduler_hooks.sh"
wave_scheduler_entry_check "$PROJECT_ROOT" "guide-ship"
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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
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
WORKTREE_COUNT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\//' | wc -l | tr -d '[:space:]' || echo 0)
LIGHTWEIGHT_COUNT=$(git branch 2>/dev/null | grep -c "openspec/" || true)
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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```

---

## Phase 2: execute — 监控与执行

**定位**：Execute 阶段是**监控模式**——读取 tasks.md 进度、显示所有 worktree 状态、提供执行入口。不是实际执行者。

**前置检测（每次入口执行）**：

```bash
# Round A: extracted to _lib/ship_monitor.sh (L260-L315, ~54 lines)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_monitor.sh"
run_ship_monitor
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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
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
# === Phase 2.5: thin orchestrator — heavy lifting in scripts/ship_review.sh ===
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_review.sh"
handle_review_action "$PROJECT_ROOT" "$CHANGE_NAME" "$WT_PATH" "$choice"
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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```

**归档流程（选项 1/2）**：

```bash
# === Phase 3: thin orchestrator — heavy lifting in scripts/ship_archive.sh ===
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_archive.sh"

ARCHIVE_MODE=$(detect_archive_mode "$PROJECT_ROOT" "$CHANGE_NAME")
echo "🔍 归档模式: $ARCHIVE_MODE"

check_feature_integrity "$PROJECT_ROOT" "$CHANGE_NAME"
archive_change_for_mode "$PROJECT_ROOT" "$CHANGE_NAME" "$ARCHIVE_MODE"
```

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```

---

**rddf-session heartbeat refresh**（ADR-0017）：archive 成功后，刷新对应 rddf-session 心跳（标记 stage_ship 仍在执行，直到 ship-done 才标 completed）：

```bash
# rddf-session heartbeat refresh (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_heartbeat stage_ship "$CHANGE_NAME"
```

## Phase 3 完成后: post-archive fill suggestion hook

**触发条件**: archive 成功完成后

**行为**:

1. 调用 `iteration.get_unblocked_planned(project_root)` 扫描 `iteration.json`
2. 找出所有 `status="planned"` 且 blocker 已归档的 change
3. 若有结果，输出建议信息（不自动调用 guide-plan fill）
4. 若无结果，保持现有输出不变

```bash
# Phase 3 post-archive: wave scheduler hook (v2.1) - supersedes post_archive_fill.sh
# WaveScheduler detects both planned (wave=fill) AND proposed (wave=ship) changes
# whose blockers have resolved. post_archive_fill.sh only handled planned.
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_lib_dir)/wave_scheduler_hooks.sh"
wave_scheduler_post_archive "$PROJECT_ROOT" "$CHANGE_NAME"
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

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```

**选项 1 执行**：

```
请选择要清理的 worktree:
1. fix-ns-pollution (.rddf/wt/fix-ns-pollution)
2. add-stream-pipes (.rddf/wt/add-stream-pipes)
```

**选项 2 执行**：

```bash
# === Phase 4: thin orchestrator - heavy lifting in scripts/ship_cleanup.sh ===
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_cleanup.sh"
cleanup_worktrees_and_branches "$PROJECT_ROOT"
```

---

## Phase 5: ship-done (Exit)

Triggered when all committed changes have been archived (or no changes remain).

**rddf-session 关闭 hook**（ADR-0017）：所有 changes 归档完成后，将 `stage_ship` rddf-session 标记为 completed：

```bash
# rddf-session 关闭 hook (ADR-0017) — extracted to _lib/rddf_session_hooks.sh
# Documented behavior change (P3-4c): ship now prints 'not found, skipping'
# when sessions.json missing, consistent with arch/plan close.
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_close stage_ship ship-done guide-ship
```

**Loop check:**

```bash
# Phase 5 loop check - extracted to scripts/ship_done.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_done.sh"
check_remaining_work "$PROJECT_ROOT"
```

**Orphaned rddf-sessions prompt**: When `.rddf/state/sessions.json` contains orphaned rddf-sessions, `check_remaining_work` prints the first three IDs (with `+N more` if there are more) and adds option 5 to the ship-done menu. Choosing option 5 launches the rddf-session cleanup skill; no automatic cleanup occurs.

**输入处理**：

```bash
# 输入处理 — extracted to _lib/ship_case_handler.sh
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
source "$(resolve_rdd_skill_dir guide-ship)/scripts/ship_case_handler.sh"
handle_invalid_choice "$choice"
```
