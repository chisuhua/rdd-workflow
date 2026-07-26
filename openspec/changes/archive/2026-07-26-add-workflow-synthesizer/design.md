## Context

`guide` 推荐器当前依赖 `scan-state.sh` 的纯 bash 实现，输出两个扁平字符串 (`RECOMMEND` + `REASON`)。缺少结构化信息：阶段状态、可执行 change 列表、session 绑定状态、working tree 健康度。当 `guide.md` 需要展示交互式菜单（含 resume/restart/start-arch/all-done 选项）时，扁平字符串不足以支撑。

在 v2.0 中，`guide.md` 的扫描逻辑块 (~200 行) 内嵌在 SKILL.md 中，维护成本高、无法直接测试。需求包括：
- **结构化推荐**：不仅输出 suggested_action，还要包含置信度、阶段状态、unblocked changes、session 绑定、orphaned sessions
- **交互式菜单**：`guide_entry.sh` 需要 `all_options` 列表驱动菜单渲染
- **只读契约**：模块不写任何 `.rddf/state/` 文件，不调用 openspec CLI
- **可测试性**：每条推荐路径至少 1 个单元测试

## Goals / Non-Goals

**Goals:**
- `skills/_lib/workflow_synthesizer.py` — 只读结构化推荐引擎，13 条决策路径
- `skills/_lib/state_reader.py` — 共享只读数据层（8 函数），被 synthesizer/status/feature 等 4+ 子系统消费
- `skills/guide/scripts/guide_entry.sh` — 集成 synthesizer 调用 + fallback 到 scan_state + 交互式菜单
- `tests/unit/test_workflow_synthesizer.py` — 54 测试覆盖所有路径和边界
- 保留 `RECOMMEND` / `REASON` 环境变量契约（向后兼容）
- Python synthesizer 失败时回退到 `scan-state.sh` 结果

**Non-Goals:**
- 不修改 `sessions_schema.json`（只读）
- 不自动执行推荐（仅建议，用户确认）
- 不替换 `scan-state.sh`（保留为 fallback）

## Decisions

### Decision 1: 独立模块 vs 内嵌到 guide.md

- **Why**: 内嵌 ~200 行 Python 代码到 SKILL.md 会降低可维护性和可测试性。独立模块可被 `pytest` 直接测试。
- **How**: `workflow_synthesizer.py` 是独立模块，`synthesize(project_root)` 是唯一公共入口。
- **Alternative**: 内嵌到 guide.md 的 bash heredoc 中
- **Rejected**: 不可测试，不可复用

### Decision 2: state_reader 作为独立层

- **Why**: synthesizer、status CLI、feature CLI、guide-arch/plan/ship intake 都需要读取相同状态文件。集中到一个模块避免重复。
- **How**: 8 个函数，每个读取一个特定状态源。所有函数 never-raises，返回 `None`/`[]` 而不是异常。
- **Alternative**: 每个消费者各自读文件
- **Rejected**: 重复代码，不一致的错误处理

### Decision 3: 13 条决策路径优先级（与 scan-state.sh 一致）

- **Why**: 保持与 `scan-state.sh::scan_state()` 的语义一致，确保迁移后推荐结果不变。
- **How**: `_decision_tree()` 以 handoff 状态为最高优先级，worktree/git 状态次之，fallback 最低。
- **Alternative**: 重写决策逻辑
- **Rejected**: 会引入与 scan_state 的语义漂移

### Decision 4: 仅标准库依赖

- **Why**: 不引入新依赖，避免安装/兼容性问题。`state_reader` 中的 `iteration.store` 是已存在的内部模块。
- **How**: 使用 `dataclasses`、`os`、`subprocess`、`typing` 等标准库。
- **Alternative**: 使用 pydantic 做 dataclass
- **Rejected**: 增加依赖，收益有限

## Architecture

```
+---------------------+      +-----------------------+
|   guide.md          |----->| workflow_synthesizer  |
|   (recommender)     |      | .synthesize()         |
+---------------------+      +-----------+-----------+
                                          |
        reads (read-only)                |
        +------------------------+-------+----------+
        |                        |                  |
+-------v------+   +-------------v----+   +---------v---------+
| sessions.json|   | arch/plan handoff|   | iteration.json    |
| (rddf-session)|  | (phase done gate)|   | (current sprint)  |
+--------------+   +------------------+   +-------------------+

        +-------------------------+--------+
        |                         |
+-------v------+          +-------v-------+
| git worktree |          | openspec/     |
| list         |          | changes/      |
+--------------+          +---------------+
```

### Data Model

- `PhaseStatus` (frozen): phase + done + detail — 三阶段状态快照
- `MenuOption` (frozen): id + label + description + action + group — 交互式菜单选项
- `WorkingTreeIssue` (frozen): category + path + detail + severity + auto_fixable + fix_command — 工作树问题
- `WorkflowRecommendation` (frozen): suggested_action + reason + confidence + phase_status + unblocked_changes + active_session + orphaned_sessions + all_options + wt_issues — 根推荐对象

### Decision Tree (13 条优先级路径)

| # | 条件 | suggested_action | confidence |
|---|------|------------------|------------|
| 1 | arch-handoff 缺失 | `guide-arch` | high |
| 2 | arch-handoff 存在 + adr_count < 1 | `guide-arch` | high |
| 3 | arch done + plan-handoff 缺失 | `guide-plan` | high |
| 4 | plan-handoff 存在 + active_changes == 0 | `guide-ship` | high |
| 5 | plan-handoff 存在 + active_changes > 0 | `guide-ship` | high |
| 6 | worktree 有未完成任务 | `guide-ship` | medium |
| 7 | detached worktrees 存在 | `guide-ship` | medium |
| 8 | worktree 任务全部完成 | `guide-ship` | medium |
| 9 | 有已 commit 的 change (无 worktree) | `guide-ship` | medium |
| 10-13 | fallback paths | `guide-arch`/`guide-plan`/`guide-ship` | low |

## API

### Python

```python
def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises."""

# state_reader (8 functions, all never-raises):
def read_arch_handoff(project_root: str) -> dict | None
def read_plan_handoff(project_root: str) -> dict | None
def read_iteration(project_root: str) -> dict | None
def read_sessions(project_root: str) -> list[dict] | None
def read_roadmap_state(project_root: str) -> dict | None
def list_worktrees() -> list[dict]  # empty on error
def list_change_dirs(project_root: str) -> list[str]  # empty on error
def read_proposal_approved(project_root: str) -> list[dict] | None
```

### Bash (guide_entry.sh env vars)

```
RECOMMEND         — "guide-ship" | "guide-plan" | "guide-arch"
REASON            — Chinese explanation
CONFIDENCE        — high / medium / low
ALL_OPTIONS_JSON  — JSON array of menu options
WT_ISSUES_JSON    — JSON array of worktree issues
BINDING_LINES     — bash array of session binding messages
```

## Test Plan

### Unit tests (`tests/unit/test_workflow_synthesizer.py`, 54 tests, ~797 行)

| Category | Tests | Coverage |
|----------|-------|----------|
| Dataclass shape | 4 | `PhaseStatus` + `WorkflowRecommendation` + `MenuOption` + `WorkingTreeIssue` frozen, fields |
| Decision paths | 13 (parametrized) | Paths 1-13, each with (suggested_action, confidence) assertion |
| Phase status | 3 | Detail strings for arch/plan/ship with correct metrics |
| unblocked_changes | 3 | Filtering, sorting, empty iteration |
| rddf-session | 2 | active_session binding, orphaned_sessions |
| Never-raises | 2 | Corrupt JSON, missing state dir |
| Determinism | 2 | Same output for same input |
| Working tree | 2 | Issue detection, deduplication |
| All options | 3 | Recommended first, stages, session, utilities |
| Fallback | 1 | Exception -> fallback recommendation |

### Integration tests (bats)

- `test_guide_skill.bats`: synthesizer integration block present + scan_state fallback retained
- `test_guide_entry.bats`: interactive menu mode with synthesizer

## Risk & Mitigation

| 风险 | 缓解 |
|------|------|
| Python synthesizer 在某些环境无 python3 | fallback 到 scan-state.sh |
| state_reader 中 iteration 读失败 | synthesize() 整体 try-except，返回 fallback recommendation |
| 决策树与 scan_state 语义漂移 | 13 条 parametrized 测试断言每条路径输出 |
| 性能 (subprocess 调用 git) | list_worktrees 已封装为单次调用，~10ms |
| guide_entry.sh 路径解析失败 | 4-tier fallback (env var → BASH_SOURCE → $0 → walk-up from cwd) |