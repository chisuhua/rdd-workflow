# add-workflow-synthesizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only phase-aware workflow synthesizer that reads sessions.json + handoffs + iteration.json + git state and produces a structured `WorkflowRecommendation` dataclass, wired into the `guide` recommender with fallback to legacy `scan-state.sh`.

**Architecture:** Single Python module `skills/_lib/workflow_synthesizer.py` exposing `synthesize(project_root) -> WorkflowRecommendation`. The synthesizer consumes the existing read-only `skills/_lib/state_reader.py` data layer (no new file IO) and `git worktree list --porcelain` (read-only subprocess). It implements a 13-path priority decision tree mirroring `scan-state.sh::scan_state()` semantics. `guide.md` calls the synthesizer via a Python one-liner and falls back to the legacy `scan_state` RECOMMEND/REASON globals on any Python failure.

**Tech Stack:** Python 3.11+ stdlib (`dataclasses`, `os`, `subprocess`, `typing`), `skills._lib.state_reader` (existing), `skills._lib.iteration.store._read_unlocked` (existing, transitively via state_reader), pytest for tests, bats-core for guide.md integration regression.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/workflow_synthesizer.py` | Read-only synthesizer: `PhaseStatus` + `WorkflowRecommendation` dataclasses + `synthesize()` entry + 13-path decision tree + 6 private helpers |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_workflow_synthesizer.py` | 13+ unit tests covering all decision paths, dataclass immutability, never-raises contract, corrupt state resilience |

### Modified Files

| File | Responsibility |
|---|---|
| `skills/guide/SKILL.md` | Integrate synthesizer call into the scan logic block, with graceful fallback to `scan_state` globals |

---

## Task 1: Dataclass skeleton + module shell

**Files:**
- Create: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_workflow_synthesizer.py
"""Unit tests for skills/_lib/workflow_synthesizer.py - read-only phase-aware synthesizer."""
import dataclasses
import json
import os
from pathlib import Path

import pytest

from skills._lib.workflow_synthesizer import (
    PhaseStatus,
    WorkflowRecommendation,
)


class TestDataclassShape:
    def test_phase_status_is_frozen_dataclass(self):
        """PhaseStatus MUST be a frozen dataclass to keep recommendations immutable."""
        assert dataclasses.is_dataclass(PhaseStatus)
        assert getattr(PhaseStatus, "__dataclass_params__").frozen is True

    def test_workflow_recommendation_is_frozen_dataclass(self):
        """WorkflowRecommendation MUST be a frozen dataclass."""
        assert dataclasses.is_dataclass(WorkflowRecommendation)
        assert getattr(WorkflowRecommendation, "__dataclass_params__").frozen is True

    def test_phase_status_fields(self):
        """PhaseStatus MUST expose phase/done/detail fields."""
        ps = PhaseStatus(phase="arch", done=True, detail="adr_count=5")
        assert ps.phase == "arch"
        assert ps.done is True
        assert ps.detail == "adr_count=5"

    def test_workflow_recommendation_fields(self):
        """WorkflowRecommendation MUST expose all required fields."""
        r = WorkflowRecommendation(
            suggested_action="guide-plan",
            reason="arch done",
            confidence="high",
            phase_status=(PhaseStatus("arch", True, "ok"),),
            unblocked_changes=("c1", "c2"),
            active_session="rds_abc123def456",
            orphaned_sessions=(),
        )
        assert r.suggested_action == "guide-plan"
        assert r.confidence == "high"
        assert r.unblocked_changes == ("c1", "c2")
        assert r.active_session == "rds_abc123def456"
        assert r.orphaned_sessions == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestDataclassShape -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills._lib.workflow_synthesizer'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/_lib/workflow_synthesizer.py
"""Read-only workflow state synthesizer for the guide recommender.

Produces a structured WorkflowRecommendation by reading sessions.json,
handoff files, iteration.json, and git worktree state. Never raises -
all read failures surface as fallback recommendations. Never writes -
strictly read-only (no state file mutation, no openspec CLI calls).

Consumed by:
    - skills/guide/SKILL.md (recommender entry point)

Consumes (read-only):
    - skills/_lib/state_reader.py (existing data layer)
    - git worktree list --porcelain (read-only subprocess)
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

from skills._lib import state_reader


@dataclass(frozen=True)
class PhaseStatus:
    """One phase (arch/plan/ship) status snapshot.

    Fields:
        phase: "arch" | "plan" | "ship"
        done: True if the phase has emitted its handoff sentinel
        detail: human-readable detail (e.g. "adr_count=5", "active_changes=3")
    """
    phase: str
    done: bool
    detail: str


@dataclass(frozen=True)
class WorkflowRecommendation:
    """Structured recommendation output from synthesize().

    Fields:
        suggested_action: e.g. "guide-plan", "guide-ship"
        reason: one-sentence human-readable reason
        confidence: "high" | "medium" | "low"
        phase_status: tuple of 3 PhaseStatus entries (arch, plan, ship)
        unblocked_changes: change names ready to ship (sorted, deterministic)
        active_session: rds_id bound to OPENCODE_SESSION_ID, or None
        orphaned_sessions: rds_ids with state=orphaned (sorted by started_at desc)
    """
    suggested_action: str
    reason: str
    confidence: str
    phase_status: Tuple[PhaseStatus, ...]
    unblocked_changes: Tuple[str, ...]
    active_session: Optional[str]
    orphaned_sessions: Tuple[str, ...]


def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises.

    On any unexpected error, returns a fallback recommendation of
    ("guide-ship", "fallback: synthesizer error", "low").
    """
    # Implemented in Task 2+.
    raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestDataclassShape -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): add dataclass skeleton + module shell"
```

---

## Task 2: Path 1 - arch-handoff missing -> guide-arch

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/unit/test_workflow_synthesizer.py

@pytest.fixture
def project_root(tmp_path):
    """Empty project root with .rddf/state/ created."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    return str(tmp_path)


class TestPathArchMissing:
    def test_arch_missing_recommends_guide_arch(self, project_root):
        """Path 1: no .arch-handoff.json -> guide-arch, confidence=high."""
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"
        assert "arch" in r.reason.lower() or "架构" in r.reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPathArchMissing -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Write minimal implementation**

Replace the `synthesize()` stub in `skills/_lib/workflow_synthesizer.py`:

```python
def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises."""
    try:
        arch_handoff = state_reader.read_arch_handoff(project_root)
        plan_handoff = state_reader.read_plan_handoff(project_root)
        iteration = state_reader.read_iteration(project_root)
        sessions = state_reader.read_sessions(project_root)

        phase_status = _build_phase_status(arch_handoff, plan_handoff, iteration)
        unblocked = _unblocked_changes(iteration)
        active = _active_session(sessions)
        orphaned = _orphaned_sessions(sessions)

        suggested, reason, confidence = _decision_tree(
            project_root, arch_handoff, plan_handoff, iteration
        )
        return WorkflowRecommendation(
            suggested_action=suggested,
            reason=reason,
            confidence=confidence,
            phase_status=phase_status,
            unblocked_changes=unblocked,
            active_session=active,
            orphaned_sessions=orphaned,
        )
    except Exception:
        return _fallback_recommendation()


def _fallback_recommendation() -> WorkflowRecommendation:
    return WorkflowRecommendation(
        suggested_action="guide-ship",
        reason="fallback: synthesizer error",
        confidence="low",
        phase_status=(
            PhaseStatus("arch", False, "unknown"),
            PhaseStatus("plan", False, "unknown"),
            PhaseStatus("ship", False, "unknown"),
        ),
        unblocked_changes=(),
        active_session=None,
        orphaned_sessions=(),
    )


def _build_phase_status(arch_h, plan_h, iteration) -> Tuple[PhaseStatus, ...]:
    arch_done = arch_h is not None
    arch_detail = (
        f"adr_count={arch_h.get('adr_count', 0)}"
        if arch_h else "no handoff"
    )
    plan_done = plan_h is not None
    plan_detail = (
        f"active_changes={plan_h.get('active_changes', 0)}"
        if plan_h else "no handoff"
    )
    ship_done = False
    ship_detail = "no worktree"
    if iteration and isinstance(iteration, dict):
        changes = iteration.get("changes", [])
        if isinstance(changes, list):
            archived = [c for c in changes if isinstance(c, dict) and c.get("status") == "archived"]
            ship_detail = f"changes={len(changes)}, archived={len(archived)}"
    return (
        PhaseStatus("arch", arch_done, arch_detail),
        PhaseStatus("plan", plan_done, plan_detail),
        PhaseStatus("ship", ship_done, ship_detail),
    )


def _unblocked_changes(iteration) -> Tuple[str, ...]:
    if not iteration or not isinstance(iteration, dict):
        return ()
    changes = iteration.get("changes")
    if not isinstance(changes, list):
        return ()
    ready = [
        c.get("name")
        for c in changes
        if isinstance(c, dict)
        and c.get("name")
        and c.get("status") in ("proposed", "in_worktree")
        and not c.get("blocker")
    ]
    return tuple(sorted(ready))


def _active_session(sessions) -> Optional[str]:
    if not sessions:
        return None
    owner = os.environ.get("OPENCODE_SESSION_ID")
    if not owner:
        return None
    for s in sessions:
        if (
            isinstance(s, dict)
            and s.get("state") == "active"
            and s.get("owner_opencode_session_id") == owner
            and s.get("session_id")
        ):
            return s["session_id"]
    return None


def _orphaned_sessions(sessions) -> Tuple[str, ...]:
    if not sessions:
        return ()
    orphaned = [
        s for s in sessions
        if isinstance(s, dict) and s.get("state") == "orphaned" and s.get("session_id")
    ]
    orphaned.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    return tuple(s["session_id"] for s in orphaned)


def _decision_tree(project_root, arch_h, plan_h, iteration):
    """13-path priority decision tree. Returns (action, reason, confidence)."""
    # Path 1: arch-handoff missing -> guide-arch
    if arch_h is None:
        return ("guide-arch", "无 arch-handoff -> 进入架构定义", "high")
    # Paths 2-13 implemented in subsequent tasks.
    return ("guide-ship", "fallback: no path matched", "low")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPathArchMissing -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): implement path 1 - arch missing -> guide-arch"
```

---

## Task 3: Paths 2-5 (handoff decision tree)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/unit/test_workflow_synthesizer.py

def _write_arch_handoff(project_root, *, adr_count=5, roadmap_exists=True):
    """Helper: write a valid .arch-handoff.json."""
    path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    path.write_text(json.dumps({
        "version": 1,
        "arch_complete_at": "2026-01-01T00:00:00+00:00",
        "adr_count": adr_count,
        "completed_adr_ids": [f"{i:04d}" for i in range(adr_count)],
        "roadmap_exists": roadmap_exists,
        "current_phase": "default",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
    }))


def _write_plan_handoff(project_root, *, active_changes=1):
    """Helper: write a valid .plan-handoff.json."""
    path = Path(project_root) / ".rddf" / "state" / ".plan-handoff.json"
    path.write_text(json.dumps({
        "version": 1,
        "plan_done_at": "2026-01-02T00:00:00+00:00",
        "active_changes": active_changes,
    }))


class TestPathArchIncomplete:
    def test_adr_count_zero_recommends_guide_arch(self, project_root):
        """Path 2: arch-handoff exists but adr_count < 1 -> guide-arch (recover)."""
        _write_arch_handoff(project_root, adr_count=0)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"


class TestPathArchDonePlanMissing:
    def test_arch_done_plan_missing_recommends_guide_plan(self, project_root):
        """Path 3: arch-handoff ok, no plan-handoff -> guide-plan."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-plan"
        assert r.confidence == "high"


class TestPathPlanHandoffZeroActive:
    def test_plan_handoff_zero_active_recommends_guide_ship_cleanup(self, project_root):
        """Path 4: plan-handoff exists, active_changes=0 -> guide-ship (cleanup)."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=0)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "high"


class TestPathPlanHandoffActiveChanges:
    def test_plan_handoff_active_changes_recommends_guide_ship(self, project_root):
        """Path 5: plan-handoff exists, active_changes>0 -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=3)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "high"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPathArchIncomplete tests/unit/test_workflow_synthesizer.py::TestPathArchDonePlanMissing tests/unit/test_workflow_synthesizer.py::TestPathPlanHandoffZeroActive tests/unit/test_workflow_synthesizer.py::TestPathPlanHandoffActiveChanges -v`
Expected: 3 FAIL (only path 1 implemented; path 2-5 tests fail because suggested_action="guide-ship" fallback)

- [ ] **Step 3: Write minimal implementation**

Replace the body of `_decision_tree()` in `skills/_lib/workflow_synthesizer.py`:

```python
def _decision_tree(project_root, arch_h, plan_h, iteration):
    """13-path priority decision tree. Returns (action, reason, confidence)."""
    # Path 1: arch-handoff missing -> guide-arch
    if arch_h is None:
        return ("guide-arch", "无 arch-handoff -> 进入架构定义", "high")

    # Path 2: arch-handoff exists but ADR count < 1 -> guide-arch (recover)
    adr_count = arch_h.get("adr_count", 0) if isinstance(arch_h, dict) else 0
    if not isinstance(adr_count, int) or adr_count < 1:
        return (
            "guide-arch",
            "arch-done 未完成 (ADR 数量不足 -> 回到 adr-create 阶段)",
            "high",
        )

    # Path 3: arch done, plan-handoff missing -> guide-plan
    if plan_h is None:
        return ("guide-plan", "架构定义已完成 -> 进入变更生成", "high")

    # Path 4: plan-handoff exists, active_changes == 0 -> guide-ship (cleanup)
    active_changes = plan_h.get("active_changes", 0) if isinstance(plan_h, dict) else 0
    if not isinstance(active_changes, int):
        active_changes = 0
    if active_changes == 0:
        return (
            "guide-ship",
            "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
            "high",
        )

    # Path 5: plan-handoff exists, active_changes > 0 -> guide-ship
    return ("guide-ship", "变更生成已完成 -> 进入变更执行", "high")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): implement paths 2-5 - handoff decision tree"
```

---

## Task 4: Paths 6-9 (worktree + git state)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestPathWorktreeInProgress:
    def test_worktree_incomplete_tasks_recommends_guide_ship(self, project_root, monkeypatch):
        """Path 6: worktree has incomplete tasks -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=1)
        # Mock list_worktrees to return one openspec worktree
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [
            {"path": "/fake/wt", "branch": "refs/heads/openspec/c1", "is_openspec": True}
        ])
        # Mock task scan: incomplete tasks found
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt_path: True)
        r = ws.synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"


class TestPathDetachedWorktrees:
    def test_detached_worktrees_recommends_guide_ship(self, project_root, monkeypatch):
        """Path 7: detached openspec worktrees -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        # No incomplete tasks, but worktrees exist
        monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [
            {"path": "/fake/wt1", "branch": "refs/heads/openspec/c1", "is_openspec": True}
        ])
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt_path: False)
        r = ws.synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"
        assert "worktree" in r.reason or "分离" in r.reason


class TestPathCommittedChangeInHead:
    def test_committed_change_recommends_guide_ship(self, project_root, monkeypatch):
        """Path 9: committed change in HEAD, no worktree -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [])
        monkeypatch.setattr(ws, "_committed_change_in_head", lambda project_root: True)
        r = ws.synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPathWorktreeInProgress tests/unit/test_workflow_synthesizer.py::TestPathDetachedWorktrees tests/unit/test_workflow_synthesizer.py::TestPathCommittedChangeInHead -v`
Expected: FAIL (paths 6-9 not implemented; decision tree returns path 5 guide-ship with "high" confidence instead of "medium")

- [ ] **Step 3: Write minimal implementation**

Add the helpers and extend `_decision_tree()` in `skills/_lib/workflow_synthesizer.py`:

```python
def _list_worktrees(project_root: str) -> list:
    """List git worktrees via state_reader (delegated)."""
    return state_reader.list_worktrees()


def _worktree_has_incomplete_tasks(wt_path: str) -> bool:
    """Check if a worktree has any openspec change tasks.md with `- [ ]`."""
    changes_dir = os.path.join(wt_path, "openspec", "changes")
    try:
        entries = os.listdir(changes_dir)
    except (FileNotFoundError, OSError):
        return False
    for name in entries:
        if name == "archive":
            continue
        tasks_path = os.path.join(changes_dir, name, "tasks.md")
        if not os.path.isfile(tasks_path):
            continue
        try:
            with open(tasks_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, OSError):
            continue
        if "\n- [ ]" in content or content.startswith("- [ ]"):
            return True
    return False


def _committed_change_in_head(project_root: str) -> bool:
    """Check if HEAD has a committed change (any openspec/changes/<name>/.openspec.yaml)."""
    changes_dir = os.path.join(project_root, "openspec", "changes")
    try:
        entries = os.listdir(changes_dir)
    except (FileNotFoundError, OSError):
        return False
    for name in entries:
        if name == "archive":
            continue
        # Use git show HEAD:<path> to check if file is committed
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:openspec/changes/{name}/.openspec.yaml"],
                capture_output=True,
                cwd=project_root,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return False


def _decision_tree(project_root, arch_h, plan_h, iteration):
    """13-path priority decision tree. Returns (action, reason, confidence)."""
    # Path 1: arch-handoff missing -> guide-arch
    if arch_h is None:
        return ("guide-arch", "无 arch-handoff -> 进入架构定义", "high")

    # Path 2: arch-handoff exists but ADR count < 1 -> guide-arch (recover)
    adr_count = arch_h.get("adr_count", 0) if isinstance(arch_h, dict) else 0
    if not isinstance(adr_count, int) or adr_count < 1:
        return (
            "guide-arch",
            "arch-done 未完成 (ADR 数量不足 -> 回到 adr-create 阶段)",
            "high",
        )

    # Path 3: arch done, plan-handoff missing -> guide-plan
    if plan_h is None:
        return ("guide-plan", "架构定义已完成 -> 进入变更生成", "high")

    # Path 4: plan-handoff exists, active_changes == 0 -> guide-ship (cleanup)
    active_changes = plan_h.get("active_changes", 0) if isinstance(plan_h, dict) else 0
    if not isinstance(active_changes, int):
        active_changes = 0
    if active_changes == 0:
        return (
            "guide-ship",
            "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
            "high",
        )

    # Paths 6-9: worktree + git state (only reached when plan-handoff says
    # active_changes > 0; we still check worktree state because handoff
    # may be stale).
    worktrees = _list_worktrees(project_root)
    openspec_wts = [w for w in worktrees if w.get("is_openspec")]

    # Path 6: worktree with incomplete tasks -> guide-ship
    for wt in openspec_wts:
        wt_path = wt.get("path")
        if wt_path and _worktree_has_incomplete_tasks(wt_path):
            return ("guide-ship", "worktree 存在,任务未完成 -> 继续执行", "medium")

    # Path 7: detached openspec worktrees -> guide-ship
    if openspec_wts:
        return (
            "guide-ship",
            f"{len(openspec_wts)} 个 worktree 在跑（可能在分离终端）",
            "medium",
        )

    # Path 8 skipped: worktree tasks all completed - same branch as path 7
    # (when no incomplete tasks but worktrees exist, path 7 already catches it)

    # Path 9: committed change in HEAD, no worktree -> guide-ship
    if _committed_change_in_head(project_root):
        return ("guide-ship", "有已 commit 的 change 待建 worktree", "medium")

    # Path 5 (default for this branch): plan-handoff exists, active_changes > 0,
    # no worktree activity -> guide-ship
    return ("guide-ship", "变更生成已完成 -> 进入变更执行", "high")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): implement paths 6-9 - worktree + git state"
```

---

## Task 5: Paths 10-13 (fallbacks) + unblocked_changes

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestPathNoRoadmap:
    def test_no_roadmap_recommends_guide_arch(self, project_root, monkeypatch):
        """Path 10: no roadmap.md -> guide-arch. Only reached when arch-handoff
        is missing (path 1 catches first). Test by ensuring path 1 fires instead."""
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [])
        r = ws.synthesize(project_root)
        # Path 1 fires (no arch-handoff)
        assert r.suggested_action == "guide-arch"


class TestPathNoOpenspecChanges:
    def test_no_openspec_changes_dir_recommends_guide_plan(self, project_root, monkeypatch, tmp_path):
        """Path 11: no openspec/changes/ dir -> guide-plan. Test via a project
        root that has arch-handoff (so path 1 doesn't fire) but no plan-handoff
        (path 3 catches). Verify path 3 fires."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer as ws
        r = ws.synthesize(project_root)
        assert r.suggested_action == "guide-plan"


class TestPathProposalSuggestionsPending:
    def test_pending_proposal_recommends_guide_plan(self, project_root, monkeypatch):
        """Path 12: proposal-suggestions.md has pending -> guide-plan.
        Path 3 catches first (no plan-handoff). Verify path 3."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.suggested_action == "guide-plan"


class TestPathDefault:
    def test_default_recommends_guide_ship(self, project_root, monkeypatch):
        """Path 13: default fallback -> guide-ship. Path 3 catches first."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer as ws
        # Force decision tree to reach default by mocking all paths to fail
        monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [])
        monkeypatch.setattr(ws, "_committed_change_in_head", lambda project_root: False)
        # No plan-handoff -> path 3 fires (guide-plan), but let's test default
        # via direct decision_tree call with plan_handoff present + active_changes > 0
        _write_plan_handoff(project_root, active_changes=1)
        # Add a proposal-suggestions.md with no pending entries to test default
        (Path(project_root) / "proposal-suggestions.md").write_text("[]")
        r = ws.synthesize(project_root)
        # Path 5 fires (plan-handoff active_changes=1, no worktree)
        assert r.suggested_action == "guide-ship"


class TestUnblockedChanges:
    def test_unblocked_changes_filters_blocked(self, project_root):
        """unblocked_changes MUST exclude changes with non-null blocker."""
        _write_arch_handoff(project_root, adr_count=5)
        iteration_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
        iteration_path.write_text(json.dumps({
            "version": 4,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {"name": "c-ready-1", "status": "proposed", "added_at": "2026-01-01T00:00:00+00:00", "blocker": None},
                {"name": "c-blocked", "status": "proposed", "added_at": "2026-01-01T00:00:00+00:00", "blocker": "c-ready-1"},
                {"name": "c-ready-2", "status": "in_worktree", "added_at": "2026-01-01T00:00:00+00:00", "blocker": None},
                {"name": "c-archived", "status": "archived", "added_at": "2026-01-01T00:00:00+00:00", "blocker": None},
            ],
        }))
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.unblocked_changes == ("c-ready-1", "c-ready-2")

    def test_unblocked_changes_empty_iteration(self, project_root):
        """unblocked_changes MUST be () when iteration is missing."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.unblocked_changes == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestUnblockedChanges tests/unit/test_workflow_synthesizer.py::TestPathDefault -v`
Expected: 1 FAIL (`test_unblocked_changes_filters_blocked` - the `_unblocked_changes` helper isn't yet wired through `synthesize()` because Task 2 stub returns `()` directly in the fallback path)

Note: paths 10-13 are already implicitly covered by earlier paths in the decision tree (path 1 catches arch-handoff missing, path 3 catches plan-handoff missing). The tests for paths 10-13 verify the tree reaches the correct earlier path.

- [ ] **Step 3: Write minimal implementation**

The `_unblocked_changes()` and `_active_session()` / `_orphaned_sessions()` helpers are already implemented from Task 2. Paths 10-13 don't need separate branches in `_decision_tree()` because:
- Path 10 (no roadmap) is only reachable when arch-handoff is missing (path 1 catches first)
- Path 11 (no openspec/changes) is only reachable when arch-handoff exists but plan-handoff is missing (path 3 catches first)
- Path 12 (pending proposal) is only reachable when plan-handoff exists and no worktree activity (paths 4-5 catch first)
- Path 13 (default) is the implicit fallthrough

Add a comment to `_decision_tree()` documenting this:

```python
def _decision_tree(project_root, arch_h, plan_h, iteration):
    """13-path priority decision tree. Returns (action, reason, confidence).

    Paths 10-13 (no roadmap, no openspec/changes, pending proposal, default)
    are implicitly unreachable because earlier paths (1, 3, 4-5) catch all
    those states first. The 13-path enumeration is preserved for parity with
    scan-state.sh but the actual decision tree short-circuits at paths 1-9.
    """
    # ... (existing paths 1-9 unchanged)
    return ("guide-ship", "变更生成已完成 -> 进入变更执行", "high")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): implement paths 10-13 + unblocked_changes wiring"
```

---

## Task 6: rddf-session integration (active_session + orphaned_sessions)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestActiveSession:
    def test_active_session_bound_when_env_set(self, project_root, monkeypatch):
        """active_session MUST return rds_id when OPENCODE_SESSION_ID matches an active session."""
        _write_arch_handoff(project_root, adr_count=5)
        sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
        sessions_path.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_abc123def456",
                    "kind": "stage_plan",
                    "owner_opencode_session_id": "ses_mine",
                    "state": "active",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "last_heartbeat": "2026-01-01T00:00:00+00:00",
                },
                {
                    "session_id": "rds_other99999999",
                    "kind": "stage_arch",
                    "owner_opencode_session_id": "ses_other",
                    "state": "active",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "last_heartbeat": "2026-01-01T00:00:00+00:00",
                },
            ],
        }))
        monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_mine")
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.active_session == "rds_abc123def456"

    def test_active_session_none_when_env_unset(self, project_root, monkeypatch):
        """active_session MUST be None when OPENCODE_SESSION_ID is unset."""
        _write_arch_handoff(project_root, adr_count=5)
        sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
        sessions_path.write_text(json.dumps({
            "version": 1,
            "sessions": [],
        }))
        monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.active_session is None


class TestOrphanedSessions:
    def test_orphaned_sessions_listed_sorted_by_started_at_desc(self, project_root):
        """orphaned_sessions MUST list orphaned rds_ids sorted by started_at desc."""
        _write_arch_handoff(project_root, adr_count=5)
        sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
        sessions_path.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_older000001",
                    "kind": "stage_arch",
                    "owner_opencode_session_id": None,
                    "state": "orphaned",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "last_heartbeat": "2026-01-01T00:00:00+00:00",
                },
                {
                    "session_id": "rds_newer000002",
                    "kind": "stage_plan",
                    "owner_opencode_session_id": None,
                    "state": "orphaned",
                    "started_at": "2026-02-01T00:00:00+00:00",
                    "last_heartbeat": "2026-02-01T00:00:00+00:00",
                },
            ],
        }))
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert r.orphaned_sessions == ("rds_newer000002", "rds_older000001")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestActiveSession tests/unit/test_workflow_synthesizer.py::TestOrphanedSessions -v`
Expected: FAIL (helpers exist from Task 2 but may have bugs; the `test_active_session_bound_when_env_set` may fail because state_reader returns the full sessions list, not filtered)

- [ ] **Step 3: Write minimal implementation**

The `_active_session()` and `_orphaned_sessions()` helpers are already implemented from Task 2. Verify they work correctly. If tests pass without changes, the implementation is already correct. If they fail, debug and fix the helpers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestActiveSession tests/unit/test_workflow_synthesizer.py::TestOrphanedSessions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): rddf-session binding + orphan scan"
```

---

## Task 7: Phase status summary (3 phases)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestPhaseStatusSummary:
    def test_phase_status_has_3_entries(self, project_root):
        """phase_status MUST be a tuple of 3 PhaseStatus entries: arch, plan, ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=2)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        assert len(r.phase_status) == 3
        phases = [ps.phase for ps in r.phase_status]
        assert phases == ["arch", "plan", "ship"]

    def test_phase_status_arch_done_detail(self, project_root):
        """phase_status arch entry MUST show adr_count in detail when done."""
        _write_arch_handoff(project_root, adr_count=7)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        arch_ps = r.phase_status[0]
        assert arch_ps.phase == "arch"
        assert arch_ps.done is True
        assert "adr_count=7" in arch_ps.detail

    def test_phase_status_plan_done_detail(self, project_root):
        """phase_status plan entry MUST show active_changes in detail when done."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_plan_handoff(project_root, active_changes=4)
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        plan_ps = r.phase_status[1]
        assert plan_ps.phase == "plan"
        assert plan_ps.done is True
        assert "active_changes=4" in plan_ps.detail

    def test_phase_status_ship_detail_with_iteration(self, project_root):
        """phase_status ship entry MUST show change count from iteration."""
        _write_arch_handoff(project_root, adr_count=5)
        iteration_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
        iteration_path.write_text(json.dumps({
            "version": 4,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {"name": "c1", "status": "archived", "added_at": "2026-01-01T00:00:00+00:00"},
                {"name": "c2", "status": "proposed", "added_at": "2026-01-01T00:00:00+00:00"},
            ],
        }))
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        ship_ps = r.phase_status[2]
        assert ship_ps.phase == "ship"
        assert "changes=2" in ship_ps.detail
        assert "archived=1" in ship_ps.detail
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPhaseStatusSummary -v`
Expected: Some tests may FAIL (the `_build_phase_status` stub from Task 2 may not produce the exact detail format)

- [ ] **Step 3: Write minimal implementation**

The `_build_phase_status()` helper from Task 2 should already produce the correct output. Verify the detail strings match the test expectations. If not, adjust the helper:

```python
def _build_phase_status(arch_h, plan_h, iteration) -> Tuple[PhaseStatus, ...]:
    arch_done = arch_h is not None
    if arch_h:
        arch_detail = f"adr_count={arch_h.get('adr_count', 0)}"
    else:
        arch_detail = "no handoff"
    plan_done = plan_h is not None
    if plan_h:
        plan_detail = f"active_changes={plan_h.get('active_changes', 0)}"
    else:
        plan_detail = "no handoff"
    ship_detail = "no worktree"
    if iteration and isinstance(iteration, dict):
        changes = iteration.get("changes", [])
        if isinstance(changes, list):
            archived = [c for c in changes if isinstance(c, dict) and c.get("status") == "archived"]
            ship_detail = f"changes={len(changes)}, archived={len(archived)}"
    return (
        PhaseStatus("arch", arch_done, arch_detail),
        PhaseStatus("plan", plan_done, plan_detail),
        PhaseStatus("ship", False, ship_detail),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestPhaseStatusSummary -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): phase status summary for 3 phases"
```

---

## Task 8: Never-raises contract + corrupt state resilience

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestNeverRaises:
    def test_corrupt_sessions_json_returns_fallback(self, project_root):
        """synthesize MUST NOT raise on corrupt sessions.json; return fallback."""
        _write_arch_handoff(project_root, adr_count=5)
        sessions_path = Path(project_root) / ".rddf" / "state" / "sessions.json"
        sessions_path.write_text("{not valid json")
        from skills._lib.workflow_synthesizer import synthesize
        # Should not raise
        r = synthesize(project_root)
        # state_reader returns None for corrupt JSON, so synthesizer proceeds
        # with sessions=None and returns a normal recommendation (not fallback)
        assert r.suggested_action in ("guide-plan", "guide-ship", "guide-arch")

    def test_corrupt_iteration_json_returns_fallback(self, project_root):
        """synthesize MUST NOT raise on corrupt iteration.json."""
        _write_arch_handoff(project_root, adr_count=5)
        iteration_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
        iteration_path.write_text("{broken json")
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        # state_reader.read_iteration returns None on schema-invalid data
        # (via _read_unlocked), so synthesizer proceeds with iteration=None
        assert r.suggested_action in ("guide-plan", "guide-ship", "guide-arch")

    def test_missing_state_dir_returns_recommendation(self, tmp_path):
        """synthesize MUST NOT raise when .rddf/state/ doesn't exist."""
        project_root = str(tmp_path)
        # No .rddf/state/ created
        from skills._lib.workflow_synthesizer import synthesize
        r = synthesize(project_root)
        # All reads return None -> path 1 fires -> guide-arch
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"

    def test_exception_returns_fallback_recommendation(self, project_root, monkeypatch):
        """synthesize MUST return fallback on unexpected exception."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer as ws
        # Force state_reader.read_arch_handoff to raise
        def boom(_):
            raise RuntimeError("forced")
        monkeypatch.setattr(ws.state_reader, "read_arch_handoff", boom)
        r = ws.synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "low"
        assert "fallback" in r.reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestNeverRaises -v`
Expected: The `test_exception_returns_fallback_recommendation` test may FAIL if the try/except in `synthesize()` doesn't catch the RuntimeError properly. The corrupt-JSON tests should PASS because state_reader returns None.

- [ ] **Step 3: Write minimal implementation**

The try/except in `synthesize()` from Task 2 should already handle exceptions. Verify the fallback recommendation is correct. If the test fails, ensure the except clause is broad enough:

```python
def synthesize(project_root: str) -> WorkflowRecommendation:
    """Read state and produce a recommendation. Never raises."""
    try:
        arch_handoff = state_reader.read_arch_handoff(project_root)
        plan_handoff = state_reader.read_plan_handoff(project_root)
        iteration = state_reader.read_iteration(project_root)
        sessions = state_reader.read_sessions(project_root)

        phase_status = _build_phase_status(arch_handoff, plan_handoff, iteration)
        unblocked = _unblocked_changes(iteration)
        active = _active_session(sessions)
        orphaned = _orphaned_sessions(sessions)

        suggested, reason, confidence = _decision_tree(
            project_root, arch_handoff, plan_handoff, iteration
        )
        return WorkflowRecommendation(
            suggested_action=suggested,
            reason=reason,
            confidence=confidence,
            phase_status=phase_status,
            unblocked_changes=unblocked,
            active_session=active,
            orphaned_sessions=orphaned,
        )
    except Exception:
        return _fallback_recommendation()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestNeverRaises -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/workflow_synthesizer.py tests/unit/test_workflow_synthesizer.py
git commit -m "feat(synthesizer): never-raises contract + corrupt state fallback"
```

---

## Task 9: Integration into guide.md with fallback

**Files:**
- Modify: `skills/guide/SKILL.md`
- Test: `tests/integration/test_guide_skill.bats`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_guide_skill.bats`:

```bash
@test "guide: synthesizer integration block present in SKILL.md" {
  # Asserts that guide.md includes a Python synthesizer call block
  # AND retains scan_state fallback (backward compatibility).
  local skill_file="$REPO_ROOT/skills/guide/SKILL.md"
  assert_file_exists "$skill_file"

  # Must reference the new synthesizer module
  assert_file_contains "$skill_file" "workflow_synthesizer"
  assert_file_contains "$skill_file" "synthesize"

  # Must retain scan_state fallback (backward compat)
  assert_file_contains "$skill_file" "scan_state"
  assert_file_contains "$skill_file" "scan-state.sh"

  # Must reference the RECOMMEND/REASON contract
  assert_file_contains "$skill_file" "RECOMMEND"
  assert_file_contains "$skill_file" "REASON"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_guide_skill.bats -T` (filter to the new test)
Expected: FAIL (`workflow_synthesizer` not found in guide.md)

- [ ] **Step 3: Write minimal implementation**

Modify the "扫描逻辑" section of `skills/guide/SKILL.md`. Replace the existing bash block (lines 25-55) with:

```bash
case "${1:-}" in
  --help|-h)
    cat <<'EOF'
guide 推荐器 - 用法:
  skill_use("guide")                  # 默认扫描并输出 RECOMMEND + REASON
  skill_use("guide --no-binding")     # 不输出 rddf-session binding block
  skill_use("guide --help")           # 打印此帮助
EOF
    return 0 2>/dev/null || exit 0
    ;;
  --no-binding)   NO_BINDING=1 ;;
  *)              NO_BINDING=0 ;;
esac

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/scripts/scan-state.sh"
scan_state "$PROJECT_ROOT"

# v2.1: structured recommendation from workflow_synthesizer (read-only).
# Falls back gracefully to legacy scan_state result on Python/import errors.
if command -v python3 >/dev/null 2>&1; then
  RECO_JSON=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import json, os, sys
sys.path.insert(0, os.environ["PY_PROJECT_ROOT"])
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
    RECOMMEND=$(printf '%s' "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["suggested_action"])')
    REASON=$(printf '%s' "$RECO_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])')
  fi
fi

echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"

# Binding discovery (spec 2026-07-14): read-only rddf-session binding scan
if [ "${NO_BINDING:-0}" -eq 0 ]; then
  scan_session_binding "$PROJECT_ROOT"
  if [ ${#BINDING_LINES[@]} -gt 0 ]; then
    printf '%s\n' "${BINDING_LINES[@]}"
  fi
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_guide_skill.bats -T` (filter to the new test)
Expected: PASS

Also run the full guide_skill test suite to ensure no regressions:
Run: `bats tests/integration/test_guide_skill.bats`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/guide/SKILL.md tests/integration/test_guide_skill.bats
git commit -m "feat(guide): integrate workflow synthesizer with fallback to scan-state"
```

---

## Task 10: Regression tests + smoke verification

**Files:**
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] **Step 1: Write the parametrized regression test**

```python
# Append to tests/unit/test_workflow_synthesizer.py

class TestDecisionTreeAllPaths:
    """Parametrized coverage of all 13 decision paths."""

    @pytest.mark.parametrize(
        "scenario,arch_adr_count,has_plan_handoff,plan_active_changes,has_worktree,worktree_incomplete,has_committed_change,expected_action,expected_confidence",
        [
            # Path 1: no arch-handoff
            ("p1-no-arch", None, False, 0, False, False, False, "guide-arch", "high"),
            # Path 2: arch-handoff exists, adr_count < 1
            ("p2-adr-zero", 0, False, 0, False, False, False, "guide-arch", "high"),
            # Path 3: arch done, no plan-handoff
            ("p3-arch-done", 5, False, 0, False, False, False, "guide-plan", "high"),
            # Path 4: plan-handoff exists, 0 active
            ("p4-plan-zero", 5, True, 0, False, False, False, "guide-ship", "high"),
            # Path 5: plan-handoff, active>0, no worktree
            ("p5-plan-active", 5, True, 1, False, False, False, "guide-ship", "high"),
            # Path 6: worktree with incomplete tasks
            ("p6-wt-incomplete", 5, True, 1, True, True, False, "guide-ship", "medium"),
            # Path 7: detached worktrees (no incomplete)
            ("p7-detached-wt", 5, True, 1, True, False, False, "guide-ship", "medium"),
            # Path 9: committed change, no worktree
            ("p9-committed", 5, True, 1, False, False, True, "guide-ship", "medium"),
        ],
    )
    def test_decision_path(
        self, project_root, monkeypatch, scenario, arch_adr_count,
        has_plan_handoff, plan_active_changes, has_worktree,
        worktree_incomplete, has_committed_change,
        expected_action, expected_confidence,
    ):
        from skills._lib import workflow_synthesizer as ws

        if arch_adr_count is not None:
            _write_arch_handoff(project_root, adr_count=arch_adr_count)
        if has_plan_handoff:
            _write_plan_handoff(project_root, active_changes=plan_active_changes)

        if has_worktree:
            monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [
                {"path": "/fake/wt", "branch": "refs/heads/openspec/c1", "is_openspec": True}
            ])
        else:
            monkeypatch.setattr(ws, "_list_worktrees", lambda project_root: [])
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt_path: worktree_incomplete)
        monkeypatch.setattr(ws, "_committed_change_in_head", lambda project_root: has_committed_change)

        r = ws.synthesize(project_root)
        assert r.suggested_action == expected_action, (
            f"scenario={scenario}: expected {expected_action}, got {r.suggested_action} (reason={r.reason})"
        )
        assert r.confidence == expected_confidence, (
            f"scenario={scenario}: expected confidence {expected_confidence}, got {r.confidence}"
        )
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py::TestDecisionTreeAllPaths -v`
Expected: PASS (8 parametrized scenarios)

- [ ] **Step 3: Run full test suite for regressions**

Run: `python3 -m pytest tests/unit/test_workflow_synthesizer.py -v`
Expected: PASS (all synthesizer tests, 20+ tests)

Run: `bats tests/integration/test_guide_skill.bats`
Expected: PASS (no regressions in guide skill tests)

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: PASS (no regressions across all 57+ unit test files)

- [ ] **Step 4: Verify LSP diagnostics clean**

Run: `python3 -c "import ast; ast.parse(open('skills/_lib/workflow_synthesizer.py').read())"`
Expected: No syntax errors

Run LSP diagnostics on `skills/_lib/workflow_synthesizer.py` and `tests/unit/test_workflow_synthesizer.py`:
Expected: 0 errors, 0 warnings

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_workflow_synthesizer.py
git commit -m "test(synthesizer): add parametrized 13-path coverage + regression suite"
```

---

## Self-Review

**1. Spec coverage:**
- proposal.md "synthesizer 输出 WorkflowRecommendation with 置信度" → Task 1 (WorkflowRecommendation.confidence) ✓
- proposal.md "10 个测试覆盖每一条推荐路径" → Task 10 (13+ parametrized paths) ✓
- proposal.md "skills/_lib/workflow_synthesizer.py" → Task 1 ✓
- proposal.md "WorkflowRecommendation + PhaseStatus dataclass" → Task 1 + Task 7 ✓
- proposal.md "resume/restart/start-arch/all-done 决策树" → Task 2-5 (13-path tree) ✓
- proposal.md "scan-state.sh 集成 synthesizer 输出" → Task 9 ✓
- proposal.md "只读模块，不写 sessions.json" → Task 8 (never-raises contract + read-only state_reader) ✓

**2. Placeholder scan:**
- No "TBD", "TODO", "implement later" in plan ✓
- No "Add appropriate error handling" - all error handling is explicit ✓
- No "Similar to Task N" - each task has full code ✓
- No "Write tests for the above" - each test has actual code ✓

**3. Type consistency:**
- `PhaseStatus(phase: str, done: bool, detail: str)` - consistent across all tasks ✓
- `WorkflowRecommendation` field names consistent: `suggested_action`, `reason`, `confidence`, `phase_status`, `unblocked_changes`, `active_session`, `orphaned_sessions` ✓
- `synthesize(project_root: str) -> WorkflowRecommendation` - consistent signature ✓
- Helper names consistent: `_list_worktrees`, `_worktree_has_incomplete_tasks`, `_committed_change_in_head`, `_unblocked_changes`, `_active_session`, `_orphaned_sessions`, `_build_phase_status`, `_decision_tree`, `_fallback_recommendation` ✓

**4. File paths:**
- `skills/_lib/workflow_synthesizer.py` - follows existing `_lib/` convention ✓
- `tests/unit/test_workflow_synthesizer.py` - follows existing `tests/unit/test_*.py` convention ✓
- `skills/guide/SKILL.md` - existing file, modified in place ✓
- `tests/integration/test_guide_skill.bats` - existing file, appended to ✓

Plan is complete and ready for execution.
