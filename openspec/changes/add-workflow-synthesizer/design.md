# Design: add-workflow-synthesizer

## 概述

为 `guide` 推荐器引入一个**只读阶段感知综合器** (phase-aware synthesizer)：
读取 sessions.json / handoff / iteration.json / git 状态，产出结构化
`WorkflowRecommendation`，覆盖 12 条推荐路径。`guide.md` 调用综合器后将结构化
结果转为一行 `RECOMMEND` + `REASON`，向后兼容现有 `scan-state.sh` 契约。

## 目标

- 只读：不写任何 `.rddf/state/` 文件，不调用 openspec CLI
- 确定性：相同输入 -> 相同输出（无随机性、无时间依赖）
- 可测试：每条推荐路径至少 1 个单元测试（共 10+ 测试覆盖）
- 单一职责：仅产出推荐，不执行推荐
- 零外部依赖：标准库 + 已有内部模块 (`state_reader`)

## 架构

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
                                                                          +
        +-------------------------+--------+
        |                         |
+-------v------+          +-------v-------+
| git worktree |          | openspec/     |
| list         |          | changes/      |
+--------------+          +---------------+
```

## 数据模型

### `PhaseStatus` dataclass

阶段状态摘要。每个阶段 (arch/plan/ship) 一个布尔完成状态 + 详情。

```python
@dataclass(frozen=True)
class PhaseStatus:
    phase: str            # "arch" | "plan" | "ship"
    done: bool            # phase 是否已 emit handoff
    detail: str           # 人类可读详情 (e.g. "adr_count=5", "active_changes=3")
```

### `WorkflowRecommendation` dataclass

综合器输出根对象。

```python
@dataclass(frozen=True)
class WorkflowRecommendation:
    suggested_action: str          # e.g. "guide-plan", "guide-ship"
    reason: str                    # 人类可读原因 (一句话)
    confidence: str                # "high" | "medium" | "low"
    phase_status: tuple[PhaseStatus, ...]   # 三阶段状态快照
    unblocked_changes: tuple[str, ...]      # 当前可立即 ship 的 change 列表
    active_session: Optional[str]           # 当前绑定的 rds_id, 或 None
    orphaned_sessions: tuple[str, ...]      # 可被 resume 的 orphaned rds_id 列表
```

## 推荐决策树 (12 条优先级路径)

复刻 `scan-state.sh::scan_state()` 的 11-priority 决策，并补充 rddf-session
orphaned 推荐路径。优先级从高到低：

| # | 条件 | suggested_action | reason |
|---|------|------------------|--------|
| 1 | arch-handoff 缺失 | `guide-arch` | 无 arch-handoff -> 进入架构定义 |
| 2 | arch-handoff 存在 + adr_count < 1 | `guide-arch` | arch-done 未完成 (ADR 数量不足 -> 回到 adr-create 阶段) |
| 3 | arch-handoff 存在 + plan-handoff 缺失 | `guide-plan` | 架构定义已完成 -> 进入变更生成 |
| 4 | plan-handoff 存在 + active_changes == 0 | `guide-ship` | plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档) |
| 5 | plan-handoff 存在 + active_changes > 0 | `guide-ship` | 变更生成已完成 -> 进入变更执行 |
| 6 | worktree 有未完成任务 (tasks.md 含 `- [ ]`) | `guide-ship` | worktree 存在,任务未完成 -> 继续执行 |
| 7 | detached worktrees 存在 | `guide-ship` | {N} 个 worktree 在跑（可能在分离终端） |
| 8 | worktree 任务全部完成 | `guide-ship` | worktree 存在,任务已完成 -> 进入 archive |
| 9 | 有已 commit 的 change (无 worktree) | `guide-ship` | 有已 commit 的 change 待建 worktree |
| 10 | 无 roadmap.md | `guide-arch` | 无 roadmap.md -> 进入架构定义 |
| 11 | 无 openspec/changes/ | `guide-plan` | 无 change -> 进入变更生成 |
| 12 | proposal-suggestions.md 有 pending | `guide-plan` | 有 change 待创建 -> 继续 propose |
| 13 | default | `guide-ship` | 无待创建 change -> 准备 ship |

### unblocked_changes 计算

从 `iteration.json` 的 `changes` 数组中过滤出 status in
`("proposed", "in_worktree")` 且 `blocker is None` 的 change name 列表。
按 name 排序保证确定性。`iteration.json` 缺失或无 changes 时返回空 tuple。

### active_session / orphaned_sessions 计算

从 `sessions.json` 读取：
- `active_session`：state == "active" 且 owner_opencode_session_id 匹配
  `OPENCODE_SESSION_ID` 环境变量的 session。若环境变量未设置，返回 None。
- `orphaned_sessions`：state == "orphaned" 的 session_id 列表，按 started_at 倒序。

### confidence 计算

- `high`：路径 1-5 (handoff-based，确定性高)
- `medium`：路径 6-9 (worktree/git-based)
- `low`：路径 10-13 (fallback paths)

## 模块边界

`skills/_lib/workflow_synthesizer.py` (~250 行)：

```python
"""Read-only workflow state synthesizer for the guide recommender."""
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Tuple

from skills._lib import state_reader


@dataclass(frozen=True)
class PhaseStatus: ...


@dataclass(frozen=True)
class WorkflowRecommendation: ...


def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises."""


def _phase_status_arch(handoff): ...
def _phase_status_plan(handoff): ...
def _phase_status_ship(iteration): ...
def _unblocked_changes(iteration): ...
def _active_session(sessions): ...
def _orphaned_sessions(sessions): ...
def _worktree_in_progress(project_root): ...
def _committed_change_in_head(project_root): ...
def _decision_tree(...): ...   # 12-path priority logic
```

## 集成到 guide.md

### 修改点

`skills/guide/SKILL.md` 中的"扫描逻辑"段：

**before** (bash-only via `scan-state.sh`):
```bash
source ".../scripts/scan-state.sh"
scan_state "$PROJECT_ROOT"
echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"
```

**after** (Python synthesizer + bash fallback):
```bash
source ".../scripts/scan-state.sh"
scan_state "$PROJECT_ROOT"

# v2.1: structured recommendation from synthesizer (read-only, no side effects).
# Falls back gracefully on Python/import errors to the legacy scan_state result.
if command -v python3 >/dev/null 2>&1; then
  RECO_JSON=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import json, os
from skills._lib.workflow_synthesizer import synthesize
r = synthesize(os.environ["PY_PROJECT_ROOT"])
print(json.dumps({
    "suggested_action": r.suggested_action,
    "reason": r.reason,
    "confidence": r.confidence,
    "unblocked_changes": list(r.unblocked_changes),
    "active_session": r.active_session,
    "orphaned_sessions": list(r.orphaned_sessions),
}))
' 2>/dev/null) && [ -n "$RECO_JSON" ]
  then
    RECOMMEND=$(echo "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["suggested_action"])')
    REASON=$(echo "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])')
  fi
fi

echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"
```

### 向后兼容性

- `RECOMMEND` / `REASON` 环境变量契约保留
- Python synthesizer 失败时回退到 `scan-state.sh` 结果
- `scan_session_binding` 函数和 `BINDING_LINES` 输出保留
- 所有现有 `tests/integration/test_guide_skill.bats` 必须通过

## 验收标准映射

| Acceptance (from proposal.md) | Implementation |
|-------------------------------|----------------|
| synthesizer 输出 WorkflowRecommendation with 置信度 | `WorkflowRecommendation.confidence: str` |
| 10 个测试覆盖每一条推荐路径 | `tests/unit/test_workflow_synthesizer.py` 13+ 测试覆盖 12 路径 + 边界 |
| 只读模块，不写 sessions.json | `synthesize()` 只调用 `state_reader.*` (read-only) + `subprocess.run(["git", ...])` (read-only) |
| scan-state.sh 集成 synthesizer 输出到 CONTEXT_LINES | guide.md 调用 Python synthesizer 并 fallback 到 scan_state |
| 推荐逻辑：resume/restart/start-arch/all-done 决策树 | 12-path `_decision_tree()` |
| 不修改 sessions_schema.json | synthesizer 不写 schema；只读 sessions list via `state_reader.read_sessions` |
| 不自动执行推荐（仅建议，用户确认） | `synthesize()` 返回 dataclass，不调用任何 skill / CLI |

## 影响范围

- **新增**：
  - `skills/_lib/workflow_synthesizer.py` (~250 行)
  - `tests/unit/test_workflow_synthesizer.py` (~400 行, 13+ 测试)
- **修改**：
  - `skills/guide/SKILL.md` (扫描逻辑段，+30 行 Python 调用 + fallback)
- **不动**：
  - `skills/_lib/schemas/sessions_schema.json` (只读)
  - `skills/_lib/state_reader.py` (复用，不修改)
  - `skills/guide/scripts/scan-state.sh` (保留作为 fallback)

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| Python synthesizer 在某些环境无 python3 | fallback 到 scan-state.sh |
| state_reader 中 iteration 读失败 | synthesize() 整体 try-except，返回 fallback recommendation |
| 决策树与 scan_state 语义漂移 | 单元测试断言每条路径输出与 scan-state.sh 一致 |
| 性能 (subprocess 调用 git) | list_worktrees 已封装为单次调用，<10ms |

## Out of Scope

- 不实现 dashboard 展示（与 add-guide-dashboard 互补，留给后续 change）
- 不修改 sessions.json schema
- 不实现自动执行推荐
- 不替换 scan-state.sh（保留为 fallback）
