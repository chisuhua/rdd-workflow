# Guide-ship quick finish path for near-complete changes — 技术设计

## 设计目标

为 `guide-ship` Phase 1 添加 quick-finish 检测路径，当 change 剩余任务 ≤2 且均为 trivial 类型（文档/状态更新）时，跳过 worktree 创建、plan 生成、execute 三件套，直接进入 review → archive。

## 实现方案

### 核心变更：`ship_plan.sh` 新增 `detect_quick_finish()`

在 `skills/guide-ship/scripts/ship_plan.sh` 中新增函数：

```bash
# detect_quick_finish <project_root> <change_name>
#   读取 .rddf/plans/<change_name>.md（或 tasks.md），统计剩余 `[ ]` 任务。
#   如果剩余任务 ≤ 2 且所有任务均为文档/状态更新类型（匹配关键词：
#   update, proposal, suggestion, doc, status, changelog, readme），
#   输出 "quick_finish" 并返回 0（触发 quick-finish 路径）。
#   否则输出 "standard" 并返回 0（走标准路径）。
#   若 tasks.md 不存在，输出 "no_tasks" 并返回 1。
#
# 判断逻辑：
#   1. 读取 tasks.md 中所有 `[ ]` 开头的任务行
#   2. 如果任务数 > 2 → 不触发
#   3. 如果任一任务包含非 trivial 关键词（implement, add, create, build,
#      refactor, test, function, class, module, API）→ 不触发
#   4. 如果存在未提交的代码变更（git status 显示非 tasks.md 修改）→ 不触发
#   5. 否则 → 触发 quick-finish
```

### 判断逻辑详细说明

**trivial 任务关键词**（匹配即视为 trivial）：
- `update`, `proposal`, `suggestion`, `doc`, `status`, `changelog`, `readme`, `md`, `bump`, `version`, `release`, `note`, `comment`

**非 trivial 关键词**（匹配即视为非 trivial，阻止 quick-finish）：
- `implement`, `add`, `create`, `build`, `refactor`, `test`, `function`, `class`, `module`, `api`, `feature`, `logic`, `handler`, `controller`, `schema`, `migration`, `script`

**代码变更检查**：
- `git status --porcelain` 检查是否有非 tasks.md 的修改
- 如果有未提交的代码变更，不允许 quick-finish（需要先提交）

### 集成到 `run_ship_phase1`

在 `run_ship_phase1()` 中，COMMIT GATE 之后、execution mode 检测之前，插入 quick-finish 检测：

```bash
run_ship_phase1() {
  local project_root="$1"
  local change_name="$2"

  # 0) HANDOFF STATE READ
  read_plan_handoff "$project_root"

  # 1) COMMIT GATE
  if ! check_artifacts_committed "$project_root" "$change_name"; then
    return 1
  fi

  # 1.5) QUICK-FINISH DETECTION（新增）
  local quick_finish_result
  quick_finish_result=$(detect_quick_finish "$project_root" "$change_name") || true
  if [ "$quick_finish_result" = "quick_finish" ]; then
    # 展示剩余任务详情，让用户选择
    echo "🚀 检测到 quick-finish 条件：剩余任务 ≤ 2 且均为 trivial"
    echo "  选项 A: Quick Finish（跳过 worktree/plan/execute，直接 review → archive）"
    echo "  选项 B: 标准流程（完整 worktree → plan → execute）"
    echo "请选择 (A/B):"
    # 由 AI 代理读取用户选择
    export QUICK_FINISH_DETECTED=yes
    return 0
  fi

  # 2) PARALLEL CONFLICT DETECTION → execution mode
  MODE=$(detect_execution_mode "$project_root" "$change_name") || return 1
  # ... 后续不变
}
```

### 用户交互流程

```
Scenario: 用户进入 guide-ship，change 仅剩 1 个 trivial 任务

guide-ship Phase 1:
  → COMMIT GATE: 通过（所有代码已提交）
  → QUICK-FINISH DETECTION: 触发
  → 输出:
     🚀 Quick Finish 可用！
     ┌─────────────────────────────────────────────┐
     │ 剩余任务: 1                                  │
     │ 1. [ ] Update proposal-suggestions.md status │
     │                                               │
     │ 选项 A: Quick Finish（推荐）                  │
     │   跳过 worktree/plan/execute，直接 review    │
     │   → archive                                  │
     │                                               │
     │ 选项 B: 标准流程                             │
     │   完整 worktree → plan → execute → archive   │
     └─────────────────────────────────────────────┘
     Quick Finish 选择: (A/B)
```

### 归档集成

quick-finish 路径的归档流程：
1. 直接在 main repo 中执行剩余任务
2. 调用 `git add + commit` 提交任务变更
3. 调用 `archive_change_for_mode` 执行归档
4. 清理 `.plan-handoff.json`（如果存在）

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/guide-ship/scripts/ship_plan.sh` | 修改 | 新增 `detect_quick_finish()` 函数，更新 `run_ship_phase1()` |
| `skills/guide-ship/SKILL.md` | 修改 | Phase 1 流程中新增 quick-finish 分支说明 |
| `tests/integration/test_ship_quick_finish.bats` | 新增 | 2 个 bats 测试：触发/不触发 quick-finish |

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| trivial 关键词误判（把非 trivial 任务判为 trivial） | 关键词匹配采用保守策略：任何非 trivial 关键词都阻止 quick-finish |
| 用户误选 Quick Finish 后需要标准流程 | 在 Quick Finish 选项中提供选项 B 回退到标准流程 |
| tasks.md 格式不一致导致解析失败 | 检测失败时回退到标准流程，不阻塞用户 |
| 归档后 iteration.json 未更新 | 归档 hook 统一处理，quick-finish 调用与标准流程相同的 archive 函数 |