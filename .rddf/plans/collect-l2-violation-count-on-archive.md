# collect-l2-violation-count-on-archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the L2 violation count collection feature by wiring `collect_l2_count()` into the archive flow, rendering the count in `rddf status --iteration`, adding a `rddf l2-trend` subcommand, and covering it with tests.

**Architecture:** A small new module `skills/_lib/iteration/l2.py` (already drafted) runs a configurable shell command, parses the integer result, and writes `l2_violation_count_after` + `l2_violation_kind` into the archived change's iteration.json entry. `archive.sh` calls it after `mark_iteration_archived`. `iteration/render.py` prints the L2 count next to archived changes. A new CLI module `l2_trend_cmd.py` registers `rddf l2-trend` and prints a sorted trend table.

**Tech Stack:** Python 3.11, bash, pytest, bats, jsonschema, subprocess.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/iteration/l2.py` | Collect L2 count via shell command, update iteration.json (already drafted) |
| `skills/_lib/archive.sh` | Call `collect_l2_count()` after `mark_iteration_archived` |
| `skills/_lib/iteration/render.py` | Print `L2: <n>` for archived changes in iteration view |
| `skills/_lib/cli/l2_trend_cmd.py` | New CLI handler for `rddf l2-trend` |
| `skills/_lib/cli/__init__.py` | Register `l2-trend` subcommand |
| `skills/_lib/cli/__main__.py` | Update help text to list `l2-trend` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_iteration_l2.py` | Unit tests for `collect_l2_count`: default cmd, custom cmd via env var, failure modes, missing change |
| `tests/unit/test_iteration_render_l2.py` | Verify `print_view` renders `L2: <n>` for archived changes with recorded count |
| `tests/unit/test_cli_routing.py` | Verify `l2-trend` is registered and routed |
| `tests/unit/test_archive_l2_hook.py` | Verify archive shell integration calls `collect_l2_count` (optional if bats covers it) |

---

## Task 1: Wire `collect_l2_count` into `archive.sh`

**Files:**
- Modify: `skills/_lib/archive.sh:346-367` (after `mark_iteration_archived`)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_archive_l2_hook.py`:

```python
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def test_archive_change_calls_collect_l2_count():
    """archive.sh should run collect_l2_count after mark_iteration_archived."""
    # This is an integration-level assertion; we will verify via bats later.
    # For the unit test, assert that the helper function exists and can be sourced.
    archive_sh = Path(__file__).parents[2] / "skills" / "_lib" / "archive.sh"
    assert archive_sh.is_file()
    result = subprocess.run(
        ["bash", "-c", f"source '{archive_sh}' && type collect_l2_count_wrapper"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_archive_l2_hook.py::test_archive_change_calls_collect_l2_count -v`
Expected: FAIL with `collect_l2_count_wrapper: not found`

- [ ] **Step 3: Write minimal implementation**

Add a `collect_l2_count_wrapper()` function in `archive.sh` and call it in `archive_change()` after `mark_iteration_archived`:

```bash
# collect_l2_count_wrapper <name> <main_root>
#   Best-effort L2 count collection. Never propagates failure.
collect_l2_count_wrapper() {
  local name="${1:-}" main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  local skills_parent
  skills_parent="$(cd "$main_root/skills/../" 2>/dev/null && pwd)"
  [[ -z "$skills_parent" ]] && return 0

  SKILLS_PARENT="$skills_parent" \
    MAIN_ROOT="$main_root" \
    CHANGE_NAME="$name" \
    python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.l2 import collect_l2_count
    warning = collect_l2_count(os.environ["MAIN_ROOT"], os.environ["CHANGE_NAME"])
    if warning:
        print(f"⚠️  {warning}", file=sys.stderr)
except Exception as e:
    print(f"⚠️  collect_l2_count failed (archive continues): {e}", file=sys.stderr)
' 2>/dev/null || true
  return 0
}
```

Then in `archive_change()` after line 349 (`mark_iteration_archived ...`) insert:

```bash
  # 8.6 Collect L2 violation count (collect-l2-violation-count-on-archive)
  collect_l2_count_wrapper "$name" "$main_root"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_archive_l2_hook.py::test_archive_change_calls_collect_l2_count -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 2: Render L2 count in `rddf status --iteration`

**Files:**
- Modify: `skills/_lib/iteration/render.py:99-106`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_iteration_render_l2.py`:

```python
import re
from pathlib import Path

from skills._lib.iteration.render import print_view


def test_render_archived_change_with_l2_count(capsys, tmp_path):
    """Archived change with recorded L2 count should display it."""
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "remove-sim-include",
                "status": "archived",
                "archived_at": "2026-08-06T00:00:00+00:00",
                "l2_violation_count_after": 3,
                "l2_violation_kind": "sim_include_drv",
            }
        ],
    }
    from skills._lib.iteration.store import save

    save(str(tmp_path), iter_data)
    print_view(str(tmp_path))
    out = capsys.readouterr().out
    assert "L2: 3" in out
    assert "sim_include_drv" in out


def test_render_archived_change_without_l2_count(capsys, tmp_path):
    """Archived change without L2 count should display 'L2: not recorded'."""
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "old-change",
                "status": "archived",
                "archived_at": "2026-08-06T00:00:00+00:00",
                "l2_violation_count_after": None,
                "l2_violation_kind": None,
            }
        ],
    }
    from skills._lib.iteration.store import save

    save(str(tmp_path), iter_data)
    print_view(str(tmp_path))
    out = capsys.readouterr().out
    assert "L2: not recorded" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_iteration_render_l2.py -v`
Expected: FAIL with `AssertionError` because `L2: 3` is not rendered yet.

- [ ] **Step 3: Write minimal implementation**

Modify `skills/_lib/iteration/render.py` archived section (lines 99-106):

```python
    archived = list_archived(data)
    if archived:
        print("🗄️  最近归档 (top 5):")
        for c in archived[:5]:
            l2_count = c.get("l2_violation_count_after")
            l2_kind = c.get("l2_violation_kind")
            if l2_count is not None:
                l2_disp = f"L2: {l2_count} ({l2_kind or 'unknown'})"
            else:
                l2_disp = "L2: not recorded"
            print(f"   ✅ {c['name']}  ({c.get('archived_at', '')}) — {l2_disp}")
        if len(archived) > 5:
            print(f"   ... (共 {len(archived)} 个归档)")
        print()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_iteration_render_l2.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 3: Add `rddf l2-trend` subcommand

**Files:**
- Create: `skills/_lib/cli/l2_trend_cmd.py`
- Modify: `skills/_lib/cli/__init__.py:78-94`
- Modify: `skills/_lib/cli/__main__.py:163-183`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_cli_l2_trend.py`:

```python
import pytest

from skills._lib.cli import list_commands, route


def test_l2_trend_registered():
    assert "l2-trend" in list_commands()


def test_l2_trend_no_iteration_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    code = route("l2-trend", [])
    out = capsys.readouterr().out
    assert code == 0
    assert "no archived changes" in out.lower()


def test_l2_trend_prints_sorted_table(tmp_path, monkeypatch, capsys):
    from skills._lib.iteration.store import save

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [
            {
                "name": "c2",
                "status": "archived",
                "archived_at": "2026-08-06T02:00:00+00:00",
                "l2_violation_count_after": 5,
            },
            {
                "name": "c1",
                "status": "archived",
                "archived_at": "2026-08-06T01:00:00+00:00",
                "l2_violation_count_after": 8,
            },
        ],
    }
    save(str(tmp_path), iter_data)
    code = route("l2-trend", [])
    out = capsys.readouterr().out
    assert code == 0
    assert "c1" in out and "c2" in out
    assert out.index("c1") < out.index("c2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_cli_l2_trend.py -v`
Expected: FAIL with `KeyError: 'l2-trend'` (not registered)

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/cli/l2_trend_cmd.py`:

```python
"""``rddf l2-trend`` subcommand handler.

Created: collect-l2-violation-count-on-archive (P2, 2026-08-05).
Prints a chronological table of archived changes with their recorded
L2 violation count after archive.
"""
from __future__ import annotations

import os
import sys


def cmd_l2_trend(args: list[str]) -> int:
    """Handle ``rddf l2-trend``.

    Args:
        args: Ignored (no flags yet).

    Returns:
        0 always.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    iter_path = os.path.join(project_root, ".rddf", "state", "iteration.json")

    if not os.path.isfile(iter_path):
        print("📭 iteration.json not found — no L2 trend data available")
        return 0

    try:
        from skills._lib.iteration.store import list_archived, load

        data = load(project_root)
    except Exception as e:
        print(f"❌ l2-trend: failed to load iteration.json: {e}", file=sys.stderr)
        return 1

    archived = list_archived(data)
    if not archived:
        print("(no archived changes)")
        return 0

    archived = sorted(
        archived,
        key=lambda c: (c.get("archived_at") or "")
    )

    print("📉 L2 violation count trend")
    print()
    print(f"{'Change':<40} {'L2 count':<10} {'Archived at':<24}")
    print(f"{'-' * 40} {'-' * 10} {'-' * 24}")
    for c in archived:
        name = c.get("name", "?")[:40]
        count = c.get("l2_violation_count_after")
        count_disp = str(count) if count is not None else "not recorded"
        archived_at = c.get("archived_at") or "-"
        print(f"{name:<40} {count_disp:<10} {archived_at:<24}")

    return 0


__all__ = ["cmd_l2_trend"]
```

Register in `skills/_lib/cli/__init__.py` by adding to `_ROUTES`:

```python
    "l2-trend": "skills._lib.cli.l2_trend_cmd:cmd_l2_trend",
```

Update `skills/_lib/cli/__main__.py` `_print_help()` help text to include:

```python
    print("  l2-trend     L2 violation count trend for archived changes")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_cli_l2_trend.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 4: Add unit tests for `collect_l2_count`

**Files:**
- Create: `tests/unit/test_iteration_l2.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_iteration_l2.py`:

```python
import os
from pathlib import Path

import pytest

from skills._lib.iteration.l2 import collect_l2_count
from skills._lib.iteration.store import load, save


def test_collect_l2_count_default_command(tmp_path, monkeypatch):
    """Default command output is parsed and written to iteration.json."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo 7")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert warning is None
    data = load(str(tmp_path))
    assert data["changes"][0]["l2_violation_count_after"] == 7
    assert data["changes"][0]["l2_violation_kind"] == "sim_include_drv"


def test_collect_l2_count_missing_change(tmp_path, monkeypatch):
    """Missing change returns a warning but does not raise."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo 7")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "missing")

    assert "missing" in warning


def test_collect_l2_count_invalid_output(tmp_path, monkeypatch):
    """Non-numeric command output returns a warning and does not touch file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "echo not-a-number")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert "invalid result" in warning
    data = load(str(tmp_path))
    assert "l2_violation_count_after" not in data["changes"][0]


def test_collect_l2_count_command_failure(tmp_path, monkeypatch):
    """Command failure returns a warning and does not raise."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RDDF_L2_COUNT_CMD", "exit 1")
    iter_data = {
        "version": 5,
        "updated_at": "2026-08-06T00:00:00+00:00",
        "current_phase": "ship",
        "changes": [{"name": "c1", "status": "archived"}],
    }
    save(str(tmp_path), iter_data)

    warning = collect_l2_count(str(tmp_path), "c1")

    assert warning is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_iteration_l2.py -v`
Expected: FAIL if l2.py is not yet importable or behavior differs.

- [ ] **Step 3: Write minimal implementation**

`skills/_lib/iteration/l2.py` is already drafted. Verify it satisfies the tests; adjust if needed. No new production code should be needed for this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_iteration_l2.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 5: Run regression tests

**Files:**
- (no files modified)

- [ ] **Step 1: Write the failing test**

No new test; this task verifies existing tests still pass.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/ -q --tb=short`
Expected: may fail if schema migration or new fields break existing assumptions.

- [ ] **Step 3: Write minimal implementation**

Fix any failures discovered. Likely candidates:
- Tests asserting iteration.json `version` == 4 need updating to 5.
- Tests enumerating per-change fields may need `l2_violation_count_after` and `l2_violation_kind` added.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/unit/ -q --tb=short
bats tests/smoke.bats
```
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

## Task 6: Update `tasks.md` checkboxes and commit

**Files:**
- Modify: `openspec/changes/collect-l2-violation-count-on-archive/tasks.md`

- [ ] **Step 1: Mark tasks complete**

Update `openspec/changes/collect-l2-violation-count-on-archive/tasks.md`:
- 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 → `[x]`
- 2.1 → `[x]`

- [ ] **Step 2: Verify tasks.md**

Run: `grep -c '^- \[x\]' openspec/changes/collect-l2-violation-count-on-archive/tasks.md`
Expected: 7

- [ ] **Step 3: Commit working tree**

In the current branch `openspec/collect-l2-violation-count-on-archive`:

```bash
git add -A
git commit -m "feat(iteration): collect L2 violation count on archive

- Add l2_violation_count_after / l2_violation_kind to iteration.json (schema v5)
- Wire collect_l2_count into archive.sh after mark_iteration_archived
- Render L2 count in rddf status --iteration
- Add rddf l2-trend subcommand
- Unit tests for collect_l2_count, render, and CLI routing

Refs: collect-l2-violation-count-on-archive"
```

- [ ] **Step 4: Verify commit**

Run: `git log -1 --oneline`
Expected: shows the new commit

- [ ] **Step 5: Defer archive**

Do NOT run `archive` here; guide-ship Phase 3 will handle merge → archive → cleanup.
