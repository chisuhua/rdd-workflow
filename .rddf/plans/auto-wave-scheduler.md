# auto-wave-scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 WaveScheduler 模块,自动检测 iteration.json 中 blocker 已解除的 planned/proposed changes,并通过 bash hook 集成到 guide-ship/guide-plan/guide-ship 入口和归档流程。

**Architecture:** 纯 Python 模块 `skills/_lib/wave_scheduler.py` 消费 iteration.json (v4) + 可选 deps-analysis.json,返回 `Recommendation` 列表。bash wrapper `skills/_lib/wave_scheduler_hooks.sh` 封装 Python 调用并通过 env-var 传递参数 (Oracle C1 safe)。集成点: guide-ship Phase 3 post-archive 替换 `post_archive_fill.sh`;guide-plan/guide-ship 入口添加 entry check。

**Tech Stack:** Python 3.11+ (dataclasses, typing), bash (env-var passing pattern), pytest, bats-core

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/wave_scheduler.py` | WaveScheduler 类 + Recommendation dataclass,纯 Python 逻辑 |
| `skills/_lib/wave_scheduler_hooks.sh` | bash wrapper,封装 Python 调用,提供 post_archive / entry_check 函数 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_wave_scheduler.py` | 单元测试: detect_unblocked / check_on_archive / check_on_entry / format_recommendations |
| `tests/integration/test_wave_scheduler_hook.bats` | 集成测试: bash wrapper 调用契约 + SKILL.md 引用检查 |

### Modified Files

| File | Change |
|---|---|
| `skills/guide-ship/SKILL.md` | Phase 3 post-archive 替换 source; Phase 1 入口添加 entry check |
| `skills/guide-plan/SKILL.md` | Phase 0 入口添加 entry check |

---

### Task 1: 创建 WaveScheduler 模块骨架 (Recommendation + WaveScheduler 类)

**Files:**
- Create: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_wave_scheduler.py`:

```python
"""Unit tests for skills/_lib/wave_scheduler.py - auto wave transition detector.

TDD contract: locks the behavior of WaveScheduler which consumes
iteration.json + deps-analysis.json and returns Recommendation list
for changes whose blockers have resolved.
"""
import pytest

from skills._lib.wave_scheduler import Recommendation, WaveScheduler


class TestRecommendationDataclass:
    def test_required_fields_present(self):
        """Recommendation must have: name, current_status, blocked_by,
        blocker_status, wave, reason, source."""
        rec = Recommendation(
            name="change-b",
            current_status="planned",
            blocked_by="change-a",
            blocker_status="archived",
            wave="fill",
            reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )
        assert rec.name == "change-b"
        assert rec.current_status == "planned"
        assert rec.blocked_by == "change-a"
        assert rec.blocker_status == "archived"
        assert rec.wave == "fill"
        assert rec.reason.startswith("blocker")
        assert rec.source == "iteration.blocker"

    def test_wave_must_be_fill_or_ship(self):
        """wave field semantic: 'fill' for planned->propose, 'ship' for proposed->guide-ship."""
        rec = Recommendation(
            name="c", current_status="proposed", blocked_by="a",
            blocker_status="archived", wave="ship",
            reason="r", source="iteration.blocker",
        )
        assert rec.wave == "ship"


class TestWaveSchedulerSkeleton:
    def test_can_instantiate(self):
        """WaveScheduler can be instantiated without args."""
        sched = WaveScheduler()
        assert sched is not None

    def test_detect_unblocked_returns_list(self):
        """detect_unblocked returns a list (empty for empty input)."""
        sched = WaveScheduler()
        result = sched.detect_unblocked({"changes": []})
        assert isinstance(result, list)
        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: FAIL with `ImportError: No module named 'skills._lib.wave_scheduler'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/wave_scheduler.py`:

```python
"""WaveScheduler - auto-detect when blocked changes become unblocked.

Consumes iteration.json (v4 schema) and optional deps-analysis.json (v1),
returns Recommendation list for changes whose blockers have resolved to
archived/completed status. Designed to be called from:
  - guide-ship Phase 3 post-archive hook
  - guide-plan / guide-ship entry hooks

Does NOT auto-invoke guide-plan/guide-ship - only emits recommendations
for the user to confirm.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Recommendation:
    """A single recommendation to advance a change through its wave.

    Fields:
        name: The change name to advance.
        current_status: The change's current status in iteration.json
                       ('planned' or 'proposed').
        blocked_by: Name of the change that was blocking this one.
        blocker_status: Status of the blocker when it resolved
                       ('archived' or 'completed').
        wave: 'fill' for planned->propose transition,
              'ship' for proposed->guide-ship transition.
        reason: Human-readable explanation.
        source: Where the blocker info came from -
               'iteration.blocker', 'manual_deps', or 'deps.blocks'.
    """
    name: str
    current_status: str
    blocked_by: str
    blocker_status: str
    wave: str
    reason: str
    source: str


class WaveScheduler:
    """Detect when blocked changes become unblocked and emit recommendations.

    Pure-Python, no IO. Callers (bash wrappers) handle file loading.
    """

    def detect_unblocked(self, iteration_data: dict, deps_data: Optional[dict] = None) -> list[Recommendation]:
        """Scan iteration_data for changes whose blockers have resolved.

        Args:
            iteration_data: Parsed iteration.json (v4 schema).
            deps_data: Optional parsed deps-analysis.json (v1) for
                      supplementary 'blocks' info.

        Returns:
            List of Recommendation for changes ready to advance.
            Empty list if no changes are ready or input is empty.
        """
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): add WaveScheduler module skeleton with Recommendation dataclass"
```

---

### Task 2: 实现 detect_unblocked - planned 状态 + iteration.blocker 字段

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wave_scheduler.py`:

```python
class TestDetectUnblockedPlanned:
    """detect_unblocked for planned status with iteration.blocker field."""

    def test_planned_with_archived_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=archived -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "change-b"
        assert r.current_status == "planned"
        assert r.blocked_by == "change-a"
        assert r.blocker_status == "archived"
        assert r.wave == "fill"
        assert r.source == "iteration.blocker"

    def test_planned_with_completed_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=completed -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].blocker_status == "completed"
        assert recs[0].wave == "fill"

    def test_planned_with_in_worktree_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=in_worktree -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_proposed_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=proposed -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "proposed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_no_blocker_returns_nothing(self):
        """planned + blocker=None -> 0 recs (covered by list_ready_for_fill elsewhere)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z"},
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_missing_blocker_entry_returns_nothing(self):
        """planned + blocker=X but X not in changes -> 0 recs (blocker not yet tracked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "ghost-change",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py::TestDetectUnblockedPlanned -v`
Expected: FAIL (returns `[]`, expected 1 rec)

- [ ] **Step 3: Write minimal implementation**

Replace `detect_unblocked` in `skills/_lib/wave_scheduler.py`:

```python
    # Statuses that count as "blocker resolved".
    _RESOLVED_STATUSES = ("archived", "completed")

    def detect_unblocked(self, iteration_data: dict, deps_data: Optional[dict] = None) -> list[Recommendation]:
        """Scan iteration_data for changes whose blockers have resolved.

        Args:
            iteration_data: Parsed iteration.json (v4 schema).
            deps_data: Optional parsed deps-analysis.json (v1) for
                      supplementary 'blocks' info. Currently unused;
                      reserved for future enhancement.

        Returns:
            List of Recommendation for changes ready to advance.
            Empty list if no changes are ready or input is empty.
        """
        if not iteration_data or not isinstance(iteration_data, dict):
            return []
        changes = iteration_data.get("changes") or []
        if not changes:
            return []
        # Index by name for blocker lookup
        by_name: dict[str, dict] = {
            c.get("name"): c for c in changes if c.get("name")
        }
        recs: list[Recommendation] = []
        for c in changes:
            name = c.get("name")
            if not name:
                continue
            status = c.get("status")
            if status != "planned":
                continue  # Task 3 will add 'proposed' branch
            blocker_name = c.get("blocker")
            if not blocker_name:
                continue  # No blocker -> already ready_for_fill, skip
            blocker_entry = by_name.get(blocker_name)
            if blocker_entry is None:
                continue  # Blocker not tracked, can't confirm resolution
            blocker_status = blocker_entry.get("status")
            if blocker_status not in self._RESOLVED_STATUSES:
                continue  # Still blocking
            recs.append(Recommendation(
                name=name,
                current_status=status,
                blocked_by=blocker_name,
                blocker_status=blocker_status,
                wave="fill",
                reason=f"blocker '{blocker_name}' is {blocker_status}",
                source="iteration.blocker",
            ))
        return recs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (all tests including TestDetectUnblockedPlanned)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): implement detect_unblocked for planned status with iteration.blocker"
```

---

### Task 3: 扩展 detect_unblocked - proposed 状态 (wave=ship)

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wave_scheduler.py`:

```python
class TestDetectUnblockedProposed:
    """detect_unblocked for proposed status (wave=ship)."""

    def test_proposed_with_archived_blocker_returns_ship_rec(self):
        """proposed + blocker=X + X.status=archived -> 1 ship recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "change-c"
        assert r.current_status == "proposed"
        assert r.blocked_by == "change-a"
        assert r.blocker_status == "archived"
        assert r.wave == "ship"
        assert r.source == "iteration.blocker"

    def test_proposed_with_completed_blocker_returns_ship_rec(self):
        """proposed + blocker=X + X.status=completed -> 1 ship rec."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].wave == "ship"
        assert recs[0].blocker_status == "completed"

    def test_proposed_with_in_worktree_blocker_returns_nothing(self):
        """proposed + blocker=in_worktree -> 0 recs."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_mixed_planned_and_proposed_both_unblocked(self):
        """Both planned and proposed changes unblocked -> 2 recs (one fill, one ship)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 2
        waves = {r.wave for r in recs}
        assert waves == {"fill", "ship"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py::TestDetectUnblockedProposed -v`
Expected: FAIL (proposed branch not implemented, returns [])

- [ ] **Step 3: Write minimal implementation**

In `skills/_lib/wave_scheduler.py`, modify the `status` check in `detect_unblocked`:

Replace:
```python
            if status != "planned":
                continue  # Task 3 will add 'proposed' branch
```

With:
```python
            if status == "planned":
                wave = "fill"
            elif status == "proposed":
                wave = "ship"
            else:
                continue  # archived/completed/in_worktree/review - skip
```

And update the `Recommendation(...)` call to use `wave=wave` instead of `wave="fill"`.

Final method body:
```python
    def detect_unblocked(self, iteration_data: dict, deps_data: Optional[dict] = None) -> list[Recommendation]:
        if not iteration_data or not isinstance(iteration_data, dict):
            return []
        changes = iteration_data.get("changes") or []
        if not changes:
            return []
        by_name: dict[str, dict] = {
            c.get("name"): c for c in changes if c.get("name")
        }
        recs: list[Recommendation] = []
        for c in changes:
            name = c.get("name")
            if not name:
                continue
            status = c.get("status")
            if status == "planned":
                wave = "fill"
            elif status == "proposed":
                wave = "ship"
            else:
                continue
            blocker_name = c.get("blocker")
            if not blocker_name:
                continue
            blocker_entry = by_name.get(blocker_name)
            if blocker_entry is None:
                continue
            blocker_status = blocker_entry.get("status")
            if blocker_status not in self._RESOLVED_STATUSES:
                continue
            recs.append(Recommendation(
                name=name,
                current_status=status,
                blocked_by=blocker_name,
                blocker_status=blocker_status,
                wave=wave,
                reason=f"blocker '{blocker_name}' is {blocker_status}",
                source="iteration.blocker",
            ))
        return recs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (all tests including TestDetectUnblockedProposed)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): extend detect_unblocked for proposed status (wave=ship)"
```

---

### Task 4: 扩展 detect_unblocked - manual_deps 多依赖检测

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wave_scheduler.py`:

```python
class TestDetectUnblockedManualDeps:
    """detect_unblocked for manual_deps field (ADR-0022)."""

    def test_manual_deps_all_archived_returns_fill_rec(self):
        """manual_deps=[A,B] all archived -> 1 fill rec, source=manual_deps."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "D"
        assert r.wave == "fill"
        assert r.source == "manual_deps"
        assert "A" in r.reason and "B" in r.reason

    def test_manual_deps_partial_archived_returns_nothing(self):
        """manual_deps=[A,B], A archived but B in_worktree -> 0 recs."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_manual_deps_single_archived_returns_fill_rec(self):
        """manual_deps=[A] with A archived -> 1 fill rec."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].source == "manual_deps"

    def test_manual_deps_takes_priority_when_blocker_none(self):
        """blocker=None but manual_deps present -> use manual_deps for detection."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": None,
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].source == "manual_deps"

    def test_manual_deps_completed_also_resolves(self):
        """manual_deps=[A] with A completed (not archived) -> also resolves."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].wave == "ship"
        assert recs[0].source == "manual_deps"

    def test_blocker_takes_priority_over_manual_deps(self):
        """If both blocker and manual_deps set, blocker wins (static analysis priority).
        But if blocker resolved AND manual_deps unresolved -> still blocked."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        # Blocker A is resolved but manual_deps B is not -> still blocked
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_both_blocker_and_manual_deps_resolved(self):
        """blocker=A (archived) + manual_deps=[A,B] both archived -> 1 rec.
        source = iteration.blocker (blocker takes precedence for source attribution)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        # blocker is the primary signal for source attribution
        assert recs[0].source == "iteration.blocker"
        assert recs[0].blocked_by == "A"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py::TestDetectUnblockedManualDeps -v`
Expected: FAIL (manual_deps branch not implemented)

- [ ] **Step 3: Write minimal implementation**

In `skills/_lib/wave_scheduler.py`, modify the loop body in `detect_unblocked`. Replace the section after `if not blocker_name: continue` through the append:

```python
            # Resolve blocker: iteration.blocker takes priority; if absent,
            # fall back to manual_deps[0]. Track all manual_deps for multi-check.
            manual_deps = c.get("manual_deps") or []
            blocker_name = c.get("blocker")
            source = "iteration.blocker"
            if blocker_name:
                # iteration.blocker is set (deps static analysis); use it as primary
                blocker_entry = by_name.get(blocker_name)
                if blocker_entry is None:
                    continue
                blocker_status = blocker_entry.get("status")
                if blocker_status not in self._RESOLVED_STATUSES:
                    continue  # Primary blocker unresolved
                # If manual_deps also present, ALL must be resolved
                if manual_deps:
                    unresolved_md = self._unresolved_manual_deps(manual_deps, by_name)
                    if unresolved_md:
                        continue  # Some manual_deps still blocking
            elif manual_deps:
                # No iteration.blocker but manual_deps declared - use manual_deps
                unresolved_md = self._unresolved_manual_deps(manual_deps, by_name)
                if unresolved_md:
                    continue
                # All manual_deps resolved; pick first as blocked_by for reporting
                blocker_name = manual_deps[0]
                blocker_entry = by_name.get(blocker_name)
                blocker_status = blocker_entry.get("status") if blocker_entry else "archived"
                source = "manual_deps"
            else:
                continue  # No blocker signal at all

            # Build reason
            if source == "manual_deps":
                reason = f"manual_deps {manual_deps} all resolved ({blocker_name} is {blocker_status})"
            else:
                reason = f"blocker '{blocker_name}' is {blocker_status}"

            recs.append(Recommendation(
                name=name,
                current_status=status,
                blocked_by=blocker_name,
                blocker_status=blocker_status,
                wave=wave,
                reason=reason,
                source=source,
            ))
        return recs
```

And add the helper method to the class (after `detect_unblocked`):

```python
    def _unresolved_manual_deps(self, manual_deps: list[str], by_name: dict[str, dict]) -> list[str]:
        """Return manual_deps entries not yet in _RESOLVED_STATUSES.

        A manual_dep is 'unresolved' if its entry is missing from by_name
        OR its status is not in _RESOLVED_STATUSES.
        """
        unresolved: list[str] = []
        for dep_name in manual_deps:
            dep_entry = by_name.get(dep_name)
            if dep_entry is None:
                unresolved.append(dep_name)
                continue
            if dep_entry.get("status") not in self._RESOLVED_STATUSES:
                unresolved.append(dep_name)
        return unresolved
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (all tests including TestDetectUnblockedManualDeps)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): support manual_deps multi-dependency detection"
```

---

### Task 5: 实现 check_on_archive (归档钩子)

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wave_scheduler.py`:

```python
import json
import os


class TestCheckOnArchive:
    """check_on_archive: filter recommendations to those blocked by archived_name."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """A fresh project root with .rddf/state/ pre-created."""
        (tmp_path / ".rddf" / "state").mkdir(parents=True)
        return str(tmp_path)

    def _write_iteration(self, project_root: str, data: dict) -> None:
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            json.dump(data, f)

    def test_returns_recs_for_dependents_of_archived(self, project_root):
        """Archive change-a; change-b (blocker=change-a, planned) -> returns [change-b]."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert len(recs) == 1
        assert recs[0].name == "change-b"
        assert recs[0].blocked_by == "change-a"

    def test_filters_out_recs_for_unrelated_blockers(self, project_root):
        """Archive change-a; change-c (blocker=change-b) -> no rec for change-c."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "change-b", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-b",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_returns_recs_for_manual_deps_dependents(self, project_root):
        """Archive A; D (manual_deps=[A,B]) with B also archived -> returns [D]."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "A")
        assert len(recs) == 1
        assert recs[0].name == "D"

    def test_missing_iteration_file_returns_empty(self, project_root):
        """No iteration.json -> return empty list, no exception."""
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_corrupt_iteration_file_returns_empty(self, project_root):
        """Corrupt iteration.json -> return empty list, no exception."""
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            f.write("{ not valid json")
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_no_matching_dependents_returns_empty(self, project_root):
        """Archive change-a but no change depends on it -> empty."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "change-x", "status": "planned", "added_at": "2026-01-01T00:00:00Z"},
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py::TestCheckOnArchive -v`
Expected: FAIL (`AttributeError: 'WaveScheduler' object has no attribute 'check_on_archive'`)

- [ ] **Step 3: Write minimal implementation**

Add to `WaveScheduler` class in `skills/_lib/wave_scheduler.py` (after `_unresolved_manual_deps`):

```python
    def check_on_archive(self, project_root: str, archived_name: str) -> list[Recommendation]:
        """Post-archive hook: return recs for changes unblocked by archiving archived_name.

        Loads iteration.json from <project_root>/.rddf/state/iteration.json,
        runs detect_unblocked, and filters to only those whose blocked_by
        or manual_deps includes archived_name.

        Tolerates missing or corrupt iteration.json (returns empty list).
        """
        from skills._lib import iteration as it_mod
        try:
            data = it_mod.load(project_root)
        except Exception:
            return []
        recs = self.detect_unblocked(data)
        # Filter: only recs where archived_name is in blocked_by or manual_deps
        out: list[Recommendation] = []
        for r in recs:
            if r.blocked_by == archived_name:
                out.append(r)
                continue
            # Check manual_deps - need to re-lookup the change entry
            for c in data.get("changes", []):
                if c.get("name") != r.name:
                    continue
                manual_deps = c.get("manual_deps") or []
                if archived_name in manual_deps:
                    out.append(r)
                break
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (all tests including TestCheckOnArchive)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): implement check_on_archive hook"
```

---

### Task 6: 实现 check_on_entry (入口钩子) + format_recommendations

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wave_scheduler.py`:

```python
class TestCheckOnEntry:
    """check_on_entry: scan all unblocked changes at skill entry."""

    @pytest.fixture
    def project_root(self, tmp_path):
        (tmp_path / ".rddf" / "state").mkdir(parents=True)
        return str(tmp_path)

    def _write_iteration(self, project_root: str, data: dict) -> None:
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            json.dump(data, f)

    def test_returns_all_unblocked_changes(self, project_root):
        """Entry check returns all unblocked (both fill and ship waves)."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "B", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                },
                {
                    "name": "C", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-plan")
        assert len(recs) == 2
        waves = {r.wave for r in recs}
        assert waves == {"fill", "ship"}

    def test_missing_iteration_returns_empty(self, project_root):
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-plan")
        assert recs == []

    def test_skill_name_accepted(self, project_root):
        """check_on_entry accepts any skill_name string (currently informational)."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [],
        })
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-ship")
        assert recs == []


class TestFormatRecommendations:
    """format_recommendations: render Recommendation list to human-readable string."""

    def test_empty_list_returns_empty_string(self):
        sched = WaveScheduler()
        assert sched.format_recommendations([]) == ""

    def test_fill_wave_format(self):
        """Fill wave rec renders with 'fill' wording."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="change-b", current_status="planned",
            blocked_by="change-a", blocker_status="archived",
            wave="fill", reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )]
        out = sched.format_recommendations(recs)
        assert "change-b" in out
        assert "fill" in out
        assert "change-a" in out

    def test_ship_wave_format(self):
        """Ship wave rec renders with 'ship' wording."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="change-c", current_status="proposed",
            blocked_by="change-a", blocker_status="archived",
            wave="ship", reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )]
        out = sched.format_recommendations(recs)
        assert "change-c" in out
        assert "ship" in out

    def test_multiple_recs_each_on_own_line(self):
        sched = WaveScheduler()
        recs = [
            Recommendation(
                name="B", current_status="planned", blocked_by="A",
                blocker_status="archived", wave="fill",
                reason="blocker 'A' is archived", source="iteration.blocker",
            ),
            Recommendation(
                name="C", current_status="proposed", blocked_by="A",
                blocker_status="archived", wave="ship",
                reason="blocker 'A' is archived", source="iteration.blocker",
            ),
        ]
        out = sched.format_recommendations(recs)
        lines = [l for l in out.split("\n") if l.strip()]
        # Each rec should produce at least one line mentioning its name
        assert any("B" in l for l in lines)
        assert any("C" in l for l in lines)

    def test_manual_deps_source_in_output(self):
        """manual_deps source rendered in output."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="D", current_status="planned", blocked_by="A",
            blocker_status="archived", wave="fill",
            reason="manual_deps ['A', 'B'] all resolved",
            source="manual_deps",
        )]
        out = sched.format_recommendations(recs)
        assert "D" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py::TestCheckOnEntry tests/unit/test_wave_scheduler.py::TestFormatRecommendations -v`
Expected: FAIL (`AttributeError: ... has no attribute 'check_on_entry' / 'format_recommendations'`)

- [ ] **Step 3: Write minimal implementation**

Add to `WaveScheduler` class in `skills/_lib/wave_scheduler.py` (after `check_on_archive`):

```python
    def check_on_entry(self, project_root: str, skill_name: str = "") -> list[Recommendation]:
        """Entry hook: scan all unblocked changes when entering a skill.

        Currently skill_name is informational (no per-skill filtering).
        Returns all unblocked recs regardless of wave.

        Tolerates missing or corrupt iteration.json (returns empty list).
        """
        from skills._lib import iteration as it_mod
        try:
            data = it_mod.load(project_root)
        except Exception:
            return []
        return self.detect_unblocked(data)

    def format_recommendations(self, recs: list[Recommendation]) -> str:
        """Render recommendations to a human-readable multi-line string.

        Returns empty string for empty input. Each recommendation includes:
          - change name
          - wave (fill/ship)
          - blocked_by + blocker_status
          - reason (already human-readable)
          - source (iteration.blocker / manual_deps)
        """
        if not recs:
            return ""
        lines: list[str] = []
        for r in recs:
            lines.append(f"  - {r.name}: {r.reason} (wave={r.wave}, source={r.source})")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler.py tests/unit/test_wave_scheduler.py
git commit -m "feat(auto-wave-scheduler): implement check_on_entry hook and format_recommendations"
```

---

### Task 7: bash wrapper - wave_scheduler_hooks.sh

**Files:**
- Create: `skills/_lib/wave_scheduler_hooks.sh`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [ ] **Step 1: Write the failing bats tests**

Create `tests/integration/test_wave_scheduler_hook.bats`:

```bash
#!/usr/bin/env bats
# Integration tests for skills/_lib/wave_scheduler_hooks.sh
# Verifies bash wrapper contract: post_archive + entry_check functions.

load test_helper

@test "wave_scheduler: hook file exists at skills/_lib/wave_scheduler_hooks.sh" {
    assert_file_exists "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
}

@test "wave_scheduler: wave_scheduler_post_archive function is defined" {
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    # Function should be defined after sourcing
    declare -F wave_scheduler_post_archive >/dev/null
}

@test "wave_scheduler: wave_scheduler_entry_check function is defined" {
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    declare -F wave_scheduler_entry_check >/dev/null
}

@test "wave_scheduler: post_archive prints suggestion when blocked change unblocked" {
    # Setup: create temp project root with iteration.json
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
    {"name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z", "blocker": "change-a"}
  ]
}
EOF
    # Add project root to PYTHONPATH so skills._lib imports resolve
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    # Output should contain wave suggestion
    [[ "$output" == *"change-b"* ]] || {
        echo "Expected output to mention change-b, got: $output"
        false
    }
    [[ "$output" == *"Wave suggestion"* ]] || {
        echo "Expected 'Wave suggestion' in output, got: $output"
        false
    }
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: post_archive no recs prints nothing or minimal" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"}
  ]
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    # Should not contain "Wave suggestion" since no recs
    [[ "$output" != *"Wave suggestion"* ]]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: post_archive missing iteration.json does not error" {
    TMP_ROOT=$(mktemp -d)
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: entry_check prints when unblocked changes exist" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
    {"name": "B", "status": "planned", "added_at": "2026-01-01T00:00:00Z", "blocker": "A"}
  ]
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_entry_check "$TMP_ROOT" "guide-plan"
    [ "$status" -eq 0 ]
    [[ "$output" == *"B"* ]]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: entry_check no recs does not error" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": []
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/skills/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_entry_check "$TMP_ROOT" "guide-plan"
    [ "$status" -eq 0 ]
    rm -rf "$TMP_ROOT"
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: FAIL (file does not exist)

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/wave_scheduler_hooks.sh`:

```bash
#!/usr/bin/env bash
# skills/_lib/wave_scheduler_hooks.sh - bash wrappers for WaveScheduler
# Exports:
#   - wave_scheduler_post_archive <project_root> <archived_name>
#   - wave_scheduler_entry_check <project_root> <skill_name>
#
# Oracle C1 safe: passes all parameters via env vars (no bash string
# interpolation into Python heredoc). The quoted 'PYEOF' delimiter
# prevents shell expansion inside the heredoc.

wave_scheduler_post_archive() {
  # Args: <project_root> <archived_name>
  local PROJECT_ROOT="${1:-${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  local ARCHIVED_NAME="${2:-}"
  export PROJECT_ROOT
  export ARCHIVED_NAME

  if [ -z "$ARCHIVED_NAME" ]; then
      return 0
  fi

  # Ensure skills._lib is importable
  local PARENT_DIR
  PARENT_DIR=$(dirname "$PROJECT_ROOT")
  export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

  local OUTPUT
  OUTPUT=$(WS_PROJECT_ROOT="$PROJECT_ROOT" WS_ARCHIVED_NAME="$ARCHIVED_NAME" python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["WS_PROJECT_ROOT"])
try:
    from skills._lib.wave_scheduler import WaveScheduler
    sched = WaveScheduler()
    recs = sched.check_on_archive(os.environ["WS_PROJECT_ROOT"], os.environ["WS_ARCHIVED_NAME"])
    if not recs:
        sys.exit(0)
    print("💡 Wave suggestion (post-archive):")
    for r in recs:
        print(f"  - {r.name}: {r.reason} (wave={r.wave}, source={r.source})")
    print("")
    print("   运行 'skill_use(\"guide-plan\")' 填充 (wave=fill) 或 'skill_use(\"guide-ship\")' 执行 (wave=ship)")
except Exception as e:
    print(f"⚠️ wave_scheduler_post_archive failed: {e}", file=sys.stderr)
    sys.exit(0)  # Never block archive on hook failure
PYEOF
)
  if [ -n "$OUTPUT" ]; then
      echo ""
      echo "$OUTPUT"
  fi
}

wave_scheduler_entry_check() {
  # Args: <project_root> <skill_name>
  local PROJECT_ROOT="${1:-${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  local SKILL_NAME="${2:-}"
  export PROJECT_ROOT
  export SKILL_NAME
  export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

  local OUTPUT
  OUTPUT=$(WS_PROJECT_ROOT="$PROJECT_ROOT" WS_SKILL_NAME="$SKILL_NAME" python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["WS_PROJECT_ROOT"])
try:
    from skills._lib.wave_scheduler import WaveScheduler
    sched = WaveScheduler()
    recs = sched.check_on_entry(os.environ["WS_PROJECT_ROOT"], os.environ["WS_SKILL_NAME"])
    if not recs:
        sys.exit(0)
    print("💡 Wave suggestion (entry):")
    for r in recs:
        print(f"  - {r.name}: {r.reason} (wave={r.wave}, source={r.source})")
    print("")
    print("   可推进的 changes 如上 (wave=fill -> guide-plan, wave=ship -> guide-ship)")
except Exception as e:
    print(f"⚠️ wave_scheduler_entry_check failed: {e}", file=sys.stderr)
    sys.exit(0)
PYEOF
)
  if [ -n "$OUTPUT" ]; then
      echo ""
      echo "$OUTPUT"
  fi
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: PASS (all 8 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wave_scheduler_hooks.sh tests/integration/test_wave_scheduler_hook.bats
git commit -m "feat(auto-wave-scheduler): add bash wrapper wave_scheduler_hooks.sh"
```

---

### Task 8: Hook 集成 - guide-ship Phase 3 post-archive

**Files:**
- Modify: `skills/guide-ship/SKILL.md`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [ ] **Step 1: Write the failing bats test**

Append to `tests/integration/test_wave_scheduler_hook.bats`:

```bash
@test "guide-ship: SKILL.md references wave_scheduler_hooks.sh in Phase 3" {
    # Phase 3 post-archive should source wave_scheduler_hooks.sh
    # (replacing or extending post_archive_fill.sh)
    grep -q "wave_scheduler_hooks.sh" "$REPO_ROOT/skills/guide-ship/SKILL.md" \
        || grep -q "wave_scheduler_post_archive" "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship: SKILL.md calls wave_scheduler_post_archive" {
    grep -q "wave_scheduler_post_archive" "$REPO_ROOT/skills/guide-ship/SKILL.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: FAIL on the two new tests

- [ ] **Step 3: Modify guide-ship SKILL.md**

In `skills/guide-ship/SKILL.md`, locate the Phase 3 post-archive hook section (around line 520-524):

```bash
# Phase 3 post-archive: fill suggestion hook - extracted to _lib/post_archive_fill.sh
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/post_archive_fill.sh"
run_post_archive_fill_suggestion
```

Replace with:

```bash
# Phase 3 post-archive: wave scheduler hook (v2.1) - supersedes post_archive_fill.sh
# WaveScheduler detects both planned (wave=fill) AND proposed (wave=ship) changes
# whose blockers have resolved. post_archive_fill.sh only handled planned.
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/wave_scheduler_hooks.sh"
wave_scheduler_post_archive "$PROJECT_ROOT" "$CHANGE_NAME"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/SKILL.md tests/integration/test_wave_scheduler_hook.bats
git commit -m "feat(auto-wave-scheduler): integrate wave_scheduler into guide-ship Phase 3"
```

---

### Task 9: Hook 集成 - guide-plan 和 guide-ship 入口

**Files:**
- Modify: `skills/guide-plan/SKILL.md`
- Modify: `skills/guide-ship/SKILL.md`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [ ] **Step 1: Write the failing bats tests**

Append to `tests/integration/test_wave_scheduler_hook.bats`:

```bash
@test "guide-plan: SKILL.md references wave_scheduler_entry_check" {
    grep -q "wave_scheduler_entry_check" "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide-ship: SKILL.md references wave_scheduler_entry_check" {
    grep -q "wave_scheduler_entry_check" "$REPO_ROOT/skills/guide-ship/SKILL.md"
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: FAIL on the two new tests

- [ ] **Step 3: Modify guide-plan and guide-ship SKILL.md**

In `skills/guide-plan/SKILL.md`, locate Phase 0 (intake) section. At the end of the Phase 0 (after `run_plan_intake` call or the intake summary), add:

```bash
# v2.1: wave scheduler entry check - suggest changes ready to advance
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/wave_scheduler_hooks.sh"
wave_scheduler_entry_check "$PROJECT_ROOT" "guide-plan"
```

In `skills/guide-ship/SKILL.md`, locate Phase 1 section. After the initial active changes display (after the table rendering), add:

```bash
# v2.1: wave scheduler entry check - suggest changes ready to advance
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/wave_scheduler_hooks.sh"
wave_scheduler_entry_check "$PROJECT_ROOT" "guide-ship"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/SKILL.md skills/guide-ship/SKILL.md tests/integration/test_wave_scheduler_hook.bats
git commit -m "feat(auto-wave-scheduler): integrate wave_scheduler entry check into guide-plan and guide-ship"
```

---

### Task 10: 全量验证 + smoke test 更新

**Files:**
- Test: `tests/unit/test_wave_scheduler.py`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [ ] **Step 1: Run unit tests**

Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run integration tests**

Run: `bats tests/integration/test_wave_scheduler_hook.bats`
Expected: All tests PASS

- [ ] **Step 3: Verify existing tests still pass**

Run: `python3 -m pytest tests/unit/test_iteration.py tests/unit/test_dependency_scheduler.py tests/unit/test_iteration_concurrency.py -v`
Expected: All existing tests PASS (no regression)

Run: `bats tests/integration/test_guide_ship_skill.bats tests/integration/test_guide_plan_skill.bats`
Expected: All existing skill tests PASS

- [ ] **Step 4: LSP diagnostics**

Run: `lsp_diagnostics` on `skills/_lib/wave_scheduler.py`
Expected: No errors

- [ ] **Step 5: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "test(auto-wave-scheduler): final verification pass" || echo "nothing to commit"
```
