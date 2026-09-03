# rdd-planner Stage 2.5 Wave 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `planner advance-sprint` 显式冲刺推进与生命周期闭环，支持持久化历史记录（`.rddf/state/.planner-history.jsonl`），实现 `planner history` 过滤/prune，并修复并发状态更新与 H1 权威源冲突告警。

**Architecture:** 包含 4 个独立 Change。Change 0 在 `_lib/planner_state.py` 中引入 `update_state`（锁内 read-modify-write）防止 lost-update，并在 `_lib/planner_attach.py` 中增加 skeleton Theme 优先与 fragment 主题冲突警告。Change 1 新建 `_lib/planner_history.py` 作为独立的追加式 jsonl 存储层（支持坏行跳过、行级版本、格式校验与显式 prune）。Change 2 实现 `advance-sprint`（严格前进约束、无基线拒绝、同步快照写入、sprint_started_at 重置、更新 roadmap）。Change 3 接入 CLI `rddf planner history`（支持 `--last N` / `--since` / `--json` / `prune`），并落地 ADR-0041 与 ADR 索引更新。

**Tech Stack:** Python 3.11+, jsonl, PyYAML, jsonschema, pytest, bats-core, `_lib.core.atomic_write` + `FileLock`.

**Builds on:** Wave 1 & Wave 2 commits (P0-1 ~ P0-3, diff, audit, warn, adr-gate).
**Contract Policy:** Schema version remains `1`. No touch to 226 `.rddf/improvements/*.md` files. Single writer `_lib/roadmap_sprint.py` preserved.

---

## File Map

- **Change 0** (Concurrency & Authority Hardening):
  - Modify: `_lib/planner_state.py` (add `update_state(project_root, mutator)`)
  - Modify: `_lib/planner_attach.py` (warn on fragment theme conflict)
  - Test: `tests/unit/test_planner_state.py`
  - Test: `tests/unit/test_planner_attach.py`
- **Change 1** (History Storage Layer):
  - Create: `_lib/planner_history.py` (append_history_entry, read_history, prune_history)
  - Test: `tests/unit/test_planner_history.py`
- **Change 2** (advance-sprint Lifecycle):
  - Modify: `_lib/planner_sync.py` (advance_sprint logic, validate forward-only, snapshot write)
  - Modify: `_lib/cli/planner_cmd.py` (register `advance-sprint [--to-sprint] [--dry-run] [--force]`)
  - Test: `tests/unit/test_planner_sync.py`
  - Test: `tests/integration/test_planner_cmd.bats`
- **Change 3** (History CLI & ADR-0041):
  - Modify: `_lib/cli/planner_cmd.py` (register `history [--last N] [--since S] [--json]` and `history prune`)
  - Create: `docs/adr/ADR-0041-planner-sprint-lifecycle-and-history.md`
  - Modify: `docs/adr/README.md` (sync index)
  - Test: `tests/unit/test_planner_cli.py`
  - Test: `tests/integration/test_planner_cmd.bats`
  - Test: `tests/unit/test_adr_index_gate.py`

---

## Task 0: Concurrency `update_state` & H1 Conflict Warning

**Files:**
- Modify: `_lib/planner_state.py`
- Modify: `_lib/planner_attach.py`
- Test: `tests/unit/test_planner_state.py`
- Test: `tests/unit/test_planner_attach.py`

- [ ] **Step 1: Write failing tests for `update_state`**

In `tests/unit/test_planner_state.py`:

```python
def test_update_state_modifies_under_lock(tmp_path):
    from _lib.planner_state import write_state, read_state, update_state
    initial = read_state(tmp_path)
    write_state(tmp_path, initial)

    def mutator(state):
        state["current_sprint"] = "sprint-2026-10"
        return state

    res = update_state(tmp_path, mutator)
    assert res["current_sprint"] == "sprint-2026-10"
    loaded = read_state(tmp_path)
    assert loaded["current_sprint"] == "sprint-2026-10"


def test_update_state_fails_if_no_state_file(tmp_path):
    from _lib.planner_state import update_state, PlannerStateError
    with pytest.raises(PlannerStateError, match="No state file found"):
        update_state(tmp_path, lambda s: s)
```

In `tests/unit/test_planner_attach.py`:

```python
def test_attach_logs_warning_when_fragment_theme_conflicts(tmp_path, caplog):
    import logging
    _setup_roadmap(tmp_path, themes=["skeleton theme"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\n主题: fragment fallback\n---\n"
    )
    _setup_improvement(tmp_path, "imp1")
    with caplog.at_level(logging.WARNING, logger="_lib.planner_attach"):
        attach_proposal(project_root=tmp_path, proposal="imp1",
                        project_id="fragment fallback", phase="phase-2")
    assert any("Theme conflict" in r.message or "fallback" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/unit/test_planner_state.py tests/unit/test_planner_attach.py -q -k "update_state or fragment_theme_conflicts"
```
Expected: FAIL (`update_state` not defined; warning not logged).

- [ ] **Step 3: Implement `update_state` in `_lib/planner_state.py`**

Add `update_state` in `_lib/planner_state.py`:

```python
def update_state(
    project_root: Path,
    mutator: Any,
    *,
    validate: bool = True,
) -> Dict[str, Any]:
    """Read state under lock, mutate it in-place, and write atomically.

    Prevents lost-update races in concurrent advance-sprint and sync calls.
    Raises PlannerStateError if state file does not exist.
    """
    path = _state_path(project_root)
    if not path.exists():
        raise PlannerStateError(f"No state file found at {path} to update.")

    lock_path = path.with_suffix(path.suffix + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)

    with FileLock(str(lock_path), timeout=10.0):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != SCHEMA_VERSION:
            raise SchemaMismatchError(f"State version mismatch: {data.get('version')}")

        new_data = mutator(data) or data

        if validate:
            schema = json.loads(STATE_SCHEMA_PATH.read_text())
            try:
                jsonschema.validate(new_data, schema)
            except jsonschema.ValidationError as exc:
                raise PlannerStateError(f"State validation failed: {exc.message}") from exc

        atomic_write_json(path, new_data)
        return new_data
```
Also expose `update_state` in `__all__`.

- [ ] **Step 4: Add fragment theme conflict warning in `_lib/planner_attach.py`**

In `attach_proposal` of `_lib/planner_attach.py`:

```python
    rm = _roadmap_path(project_root)
    skeleton_themes = set()
    if rm.exists():
        s_themes, _ = _parse_skeleton(rm.read_text(encoding="utf-8"))
        skeleton_themes = {t for t in s_themes if t and t != "Theme"}

    if project_id not in skeleton_themes and project_id in valid_projects:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "Theme conflict: project_id %r matched fragment 主题 fallback, but not skeleton Theme column.",
            project_id
        )
```

- [ ] **Step 5: Run tests and verify pass**

```bash
python3 -m pytest tests/unit/test_planner_state.py tests/unit/test_planner_attach.py -q -k "update_state or fragment_theme_conflicts"
```
Expected: PASS.

- [ ] **Step 6: Commit Change 0**

```bash
git add _lib/planner_state.py _lib/planner_attach.py tests/unit/test_planner_state.py tests/unit/test_planner_attach.py
git commit -m "fix(planner): add update_state read-modify-write and attach fallback warning"
```

---

## Task 1: History Storage Layer `_lib/planner_history.py`

**Files:**
- Create: `_lib/planner_history.py`
- Test: `tests/unit/test_planner_history.py`

- [ ] **Step 1: Write failing tests for history storage**

Create `tests/unit/test_planner_history.py`:

```python
"""Tests for planner_history append-only jsonl storage."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from _lib.planner_history import (
    HISTORY_FILENAME,
    HistoryEntry,
    append_history_entry,
    read_history,
    prune_history,
    HistoryError,
)


def test_append_and_read_history(tmp_path):
    entry = HistoryEntry(
        version=1,
        sprint="sprint-2026-09",
        closed_at="2026-09-30T23:59:59Z",
        started_at="2026-09-01T00:00:00Z",
        snapshot={"active_projects": [{"project_id": "p1"}]},
    )
    append_history_entry(tmp_path, entry)
    entries, corrupt_count = read_history(tmp_path)
    assert corrupt_count == 0
    assert len(entries) == 1
    assert entries[0].sprint == "sprint-2026-09"
    assert entries[0].snapshot["active_projects"][0]["project_id"] == "p1"


def test_read_history_skips_corrupted_lines(tmp_path, caplog):
    h_file = tmp_path / ".rddf" / "state" / HISTORY_FILENAME
    h_file.parent.mkdir(parents=True, exist_ok=True)
    valid_line = json.dumps({
        "version": 1,
        "sprint": "sprint-2026-08",
        "closed_at": "2026-08-31T23:59:59Z",
        "started_at": "2026-08-01T00:00:00Z",
        "snapshot": {},
    })
    h_file.write_text(valid_line + "\n{bad json line\n" + valid_line + "\n")

    entries, corrupt_count = read_history(tmp_path)
    assert corrupt_count == 1
    assert len(entries) == 2


def test_prune_history_dry_run_does_not_modify(tmp_path):
    for i in range(5):
        entry = HistoryEntry(
            version=1,
            sprint=f"sprint-2026-0{i+1}",
            closed_at="2026-09-30T23:59:59Z",
            started_at="2026-09-01T00:00:00Z",
            snapshot={},
        )
        append_history_entry(tmp_path, entry)

    rem = prune_history(tmp_path, keep=2, dry_run=True)
    assert rem == 3
    entries, _ = read_history(tmp_path)
    assert len(entries) == 5


def test_prune_history_apply_truncates_oldest(tmp_path):
    for i in range(5):
        entry = HistoryEntry(
            version=1,
            sprint=f"sprint-2026-0{i+1}",
            closed_at="2026-09-30T23:59:59Z",
            started_at="2026-09-01T00:00:00Z",
            snapshot={},
        )
        append_history_entry(tmp_path, entry)

    rem = prune_history(tmp_path, keep=2, dry_run=False)
    assert rem == 3
    entries, _ = read_history(tmp_path)
    assert len(entries) == 2
    assert entries[0].sprint == "sprint-2026-04"
    assert entries[1].sprint == "sprint-2026-05"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/unit/test_planner_history.py -q
```
Expected: FAIL (`ModuleNotFoundError: No module named '_lib.planner_history'`).

- [ ] **Step 3: Implement `_lib/planner_history.py`**

Create `_lib/planner_history.py`:

```python
"""Append-only JSONL history storage for planner sprints.

Maintains `.rddf/state/.planner-history.jsonl`.
Provides safe append under FileLock, line-by-line parsing with corruption tolerance,
and explicit pruning.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

logger = logging.getLogger(__name__)

HISTORY_FILENAME = ".planner-history.jsonl"


class HistoryError(Exception):
    """Base error for planner_history."""


@dataclass
class HistoryEntry:
    version: int
    sprint: str
    closed_at: str
    started_at: str
    snapshot: Dict[str, Any]


def _history_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / HISTORY_FILENAME


def append_history_entry(project_root: Path, entry: HistoryEntry) -> None:
    """Append a HistoryEntry line to .planner-history.jsonl under lock."""
    path = _history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")

    line = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
    with FileLock(str(lock_path), timeout=10.0):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


def read_history(
    project_root: Path,
) -> Tuple[List[HistoryEntry], int]:
    """Read all entries from history.

    Returns (entries, corrupt_line_count).
    Corrupted lines log a warning and are skipped.
    """
    path = _history_path(project_root)
    if not path.exists():
        return [], 0

    entries: List[HistoryEntry] = []
    corrupt_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                entries.append(HistoryEntry(
                    version=data.get("version", 1),
                    sprint=data["sprint"],
                    closed_at=data["closed_at"],
                    started_at=data["started_at"],
                    snapshot=data.get("snapshot", {}),
                ))
            except Exception as exc:
                corrupt_count += 1
                logger.warning("Corrupted line %d in %s: %s", idx, path, exc)

    return entries, corrupt_count


def prune_history(
    project_root: Path,
    *,
    keep: int,
    dry_run: bool = True,
) -> int:
    """Retain only the latest `keep` entries. Returns number of pruned entries."""
    if keep < 0:
        raise HistoryError("keep must be non-negative")

    path = _history_path(project_root)
    if not path.exists():
        return 0

    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        entries, corrupt = read_history(project_root)
        if len(entries) <= keep:
            return 0

        prune_count = len(entries) - keep
        if not dry_run:
            retained = entries[prune_count:]
            content = "".join(json.dumps(asdict(e), ensure_ascii=False) + "\n" for e in retained)
            atomic_write_text(path, content)

        return prune_count
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m pytest tests/unit/test_planner_history.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit Change 1**

```bash
git add _lib/planner_history.py tests/unit/test_planner_history.py
git commit -m "feat(planner): append-only JSONL history storage layer"
```

---

## Task 2: `advance-sprint` Lifecycle & CLI

**Files:**
- Modify: `_lib/planner_sync.py`
- Modify: `_lib/cli/planner_cmd.py`
- Test: `tests/unit/test_planner_sync.py`
- Test: `tests/integration/test_planner_cmd.bats`

- [ ] **Step 1: Write failing tests for advance-sprint**

In `tests/unit/test_planner_sync.py`:

```python
def test_advance_sprint_enforces_forward_only(tmp_path):
    from _lib.planner_state import write_state
    from _lib.planner_sync import advance_sprint, SyncError
    write_state(tmp_path, {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:00:00Z",
        "sprint_started_at": "2026-09-01T00:00:00Z",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    })
    with pytest.raises(SyncError, match="must move forward"):
        advance_sprint(tmp_path, to_sprint="sprint-2026-08")


def test_advance_sprint_success_records_history_and_updates_state(tmp_path):
    from _lib.planner_state import write_state, read_state
    from _lib.planner_history import read_history
    from _lib.planner_sync import advance_sprint
    (tmp_path / ".rddf" / "roadmap.md").write_text("# Roadmap\n## Phase Skeleton\n<!-- AUTO-INDEX -->\n")
    write_state(tmp_path, {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:00:00Z",
        "sprint_started_at": "2026-09-01T00:00:00Z",
        "active_projects": [{"project_id": "p1", "phase": "p", "priority": "P1", "status": "active", "proposal": "pr1"}],
        "unmapped_proposals": [],
        "synced_proposals": ["pr1"],
    })

    res = advance_sprint(tmp_path, to_sprint="sprint-2026-10")
    assert res["old_sprint"] == "sprint-2026-09"
    assert res["new_sprint"] == "sprint-2026-10"

    # History written
    entries, _ = read_history(tmp_path)
    assert len(entries) == 1
    assert entries[0].sprint == "sprint-2026-09"

    # State updated
    st = read_state(tmp_path)
    assert st["current_sprint"] == "sprint-2026-10"
    assert st["sprint_started_at"] != "2026-09-01T00:00:00Z"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/unit/test_planner_sync.py -q -k "advance_sprint"
```
Expected: FAIL (`ImportError: cannot import name 'advance_sprint'`).

- [ ] **Step 3: Implement `advance_sprint` in `_lib/planner_sync.py`**

Add to `_lib/planner_sync.py`:

```python
_SPRINT_PATTERN = re.compile(r"^sprint-(\d{4})-(0[1-9]|1[0-2])$")


def _next_sprint_id(current: str) -> str:
    m = _SPRINT_PATTERN.match(current)
    if not m:
        return f"sprint-{_dt.datetime.now().strftime('%Y-%m')}"
    year, month = int(m.group(1)), int(m.group(2))
    if month == 12:
        return f"sprint-{year + 1:04d}-01"
    return f"sprint-{year:04d}-{month + 1:02d}"


def advance_sprint(
    project_root: Path,
    *,
    to_sprint: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Advance current sprint, record previous sprint snapshot to history, and refresh roadmap.

    Enforces forward-only advancement unless force=True.
    Raises SyncError if no baseline state exists or format is invalid.
    """
    from _lib.planner_state import _state_path, read_state, update_state
    from _lib.planner_history import HistoryEntry, append_history_entry

    state_file = _state_path(project_root)
    if not state_file.exists():
        raise SyncError("No baseline state exists. Run `rddf planner sync --apply` first.")

    stored = read_state(project_root)
    old_sprint = stored["current_sprint"]

    if to_sprint:
        if not _SPRINT_PATTERN.match(to_sprint):
            raise SyncError(f"Invalid sprint format: {to_sprint!r}, expected sprint-YYYY-MM")
        new_sprint = to_sprint
    else:
        new_sprint = _next_sprint_id(old_sprint)

    if not force and new_sprint <= old_sprint:
        raise SyncError(f"Target sprint {new_sprint!r} must move forward from {old_sprint!r}. Use --force to override.")

    if dry_run:
        return {"old_sprint": old_sprint, "new_sprint": new_sprint, "dry_run": True}

    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    # 1. Write history snapshot first
    history_entry = HistoryEntry(
        version=1,
        sprint=old_sprint,
        closed_at=now_iso,
        started_at=stored.get("sprint_started_at", now_iso),
        snapshot=dict(stored),
    )
    append_history_entry(project_root, history_entry)

    # 2. Mutate state under lock
    def _advance_mutator(state: Dict[str, Any]) -> Dict[str, Any]:
        state["current_sprint"] = new_sprint
        state["sprint_started_at"] = now_iso
        state["last_sync_at"] = now_iso
        return state

    updated_state = update_state(project_root, _advance_mutator)

    # 3. Update roadmap AUTO-SPRINT section
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if roadmap_path.exists():
        from _lib.roadmap_sprint import update_roadmap
        update_roadmap(str(roadmap_path), updated_state, table="project")

    return {"old_sprint": old_sprint, "new_sprint": new_sprint, "dry_run": False}
```

- [ ] **Step 4: Register `advance-sprint` in `_lib/cli/planner_cmd.py`**

In `_build_parser()`:

```python
    p_adv = sub.add_parser("advance-sprint", help="Close current sprint and advance to next", parents=[common])
    p_adv.add_argument("--to-sprint", default=None, help="Target sprint ID (default: next month)")
    p_adv.add_argument("--force", action="store_true", help="Allow backward/same sprint advancement")
    p_adv.add_argument("--dry-run", action="store_true", help="Preview advancement without writing")
```

In `cmd_planner()`:

```python
        if ns.subcommand == "advance-sprint":
            from _lib.planner_sync import advance_sprint, SyncError
            try:
                res = advance_sprint(
                    project_root,
                    to_sprint=ns.to_sprint,
                    force=ns.force,
                    dry_run=ns.dry_run,
                )
            except SyncError as exc:
                sys.stderr.write(f"ERROR: {exc}\n")
                return 1

            if res.get("dry_run"):
                sys.stdout.write(f"DRY-RUN: would advance {res['old_sprint']} -> {res['new_sprint']}\n")
            else:
                sys.stdout.write(f"✓ Sprint advanced: {res['old_sprint']} -> {res['new_sprint']}\n")
            return 0
```

- [ ] **Step 5: Add bats integration test**

In `tests/integration/test_planner_cmd.bats`:

```bash
@test "planner: advance-sprint advances sprint and updates history" {
    mkdir -p .rddf/improvements
    printf -- '---\nname: p1\npriority: P2\n---\n# p1\n' > .rddf/improvements/p1.md
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"

    run python3 -m _lib.cli planner advance-sprint --to-sprint sprint-2026-12 --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Sprint advanced" ]]
    [ -f .rddf/state/.planner-history.jsonl ]
}
```

- [ ] **Step 6: Run tests and verify pass**

```bash
python3 -m pytest tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py -q
bats tests/integration/test_planner_cmd.bats
```
Expected: PASS.

- [ ] **Step 7: Commit Change 2**

```bash
git add _lib/planner_sync.py _lib/cli/planner_cmd.py tests/unit/test_planner_sync.py tests/integration/test_planner_cmd.bats
git commit -m "feat(planner): implement advance-sprint command with forward-only validation"
```

---

## Task 3: `planner history` CLI, ADR-0041, and Index Gate

**Files:**
- Modify: `_lib/cli/planner_cmd.py`
- Create: `docs/adr/ADR-0041-planner-sprint-lifecycle-and-history.md`
- Modify: `docs/adr/README.md`
- Test: `tests/unit/test_planner_cli.py`
- Test: `tests/integration/test_planner_cmd.bats`
- Test: `tests/unit/test_adr_index_gate.py`

- [ ] **Step 1: Write failing tests for `history` and `history prune` CLI**

In `tests/unit/test_planner_cli.py`:

```python
def test_cli_history_prints_empty_notice_when_no_history(tmp_path, capsys):
    from _lib.cli.planner_cmd import cmd_planner
    rc = cmd_planner(["history", "--project-root", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "No sprint history" in captured.out


def test_cli_history_lists_entries_and_supports_json(tmp_path, capsys):
    from _lib.cli.planner_cmd import cmd_planner
    from _lib.planner_history import HistoryEntry, append_history_entry
    entry = HistoryEntry(1, "sprint-2026-08", "2026-08-31T00:00:00Z", "2026-08-01T00:00:00Z", {"active_projects": []})
    append_history_entry(tmp_path, entry)

    rc = cmd_planner(["history", "--json", "--project-root", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "sprint-2026-08" in captured.out
```

In `tests/integration/test_planner_cmd.bats`:

```bash
@test "planner: history displays closed sprints" {
    mkdir -p .rddf/improvements
    printf -- '---\nname: p1\npriority: P2\n---\n# p1\n' > .rddf/improvements/p1.md
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"
    python3 -m _lib.cli planner advance-sprint --to-sprint sprint-2026-11 --project-root "$TEST_TMP"

    run python3 -m _lib.cli planner history --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "sprint-" ]]
}
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/unit/test_planner_cli.py -q -k "history"
```
Expected: FAIL (`invalid choice: 'history'`).

- [ ] **Step 3: Implement `history` in `_lib/cli/planner_cmd.py`**

Add `history` parser:

```python
    p_hist = sub.add_parser("history", help="Show or prune sprint history", parents=[common])
    p_hist.add_argument("--last", type=int, default=None, help="Show last N sprints")
    p_hist.add_argument("--since", default=None, help="Show sprints since YYYY-MM")
    p_hist.add_argument("--json", action="store_true", help="Output JSON format")
    p_hist.add_argument("--prune-keep", type=int, default=None, help="Prune older sprints keeping N latest")
    p_hist.add_argument("--apply", action="store_true", help="Apply prune modification (default dry-run)")
```

In `cmd_planner`:

```python
        if ns.subcommand == "history":
            from _lib.planner_history import read_history, prune_history
            from dataclasses import asdict

            if ns.prune_keep is not None:
                dry_run = not ns.apply
                count = prune_history(project_root, keep=ns.prune_keep, dry_run=dry_run)
                if dry_run:
                    sys.stdout.write(f"DRY-RUN: would prune {count} historical sprint(s) (keeping {ns.prune_keep})\n")
                else:
                    sys.stdout.write(f"✓ Pruned {count} historical sprint(s)\n")
                return 0

            entries, corrupt_count = read_history(project_root)
            if corrupt_count > 0:
                sys.stderr.write(f"WARNING: skipped {corrupt_count} corrupted history record(s)\n")

            if ns.since:
                entries = [e for e in entries if e.sprint >= ns.since]
            if ns.last is not None and ns.last >= 0:
                entries = entries[-ns.last:]

            if not entries:
                sys.stdout.write("No sprint history recorded.\n")
                return 0

            if ns.json:
                import json as _json
                sys.stdout.write(_json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write("| Sprint | Started | Closed | Active Projects |\n")
                sys.stdout.write("|--------|---------|--------|-----------------|\n")
                for e in entries:
                    active_count = len(e.snapshot.get("active_projects") or [])
                    sys.stdout.write(f"| {e.sprint} | {e.started_at[:10]} | {e.closed_at[:10]} | {active_count} |\n")
            return 0
```

- [ ] **Step 4: Create `docs/adr/ADR-0041-planner-sprint-lifecycle-and-history.md`**

```markdown
# ADR-0041: Planner Sprint Lifecycle and History Storage

> **状态**: 已采纳 (2026-09-03)
> **日期**: 2026-09-03
> **决策者**: sisyphus

## Context

Stage 2.5 introduced sprint tracking, proposal attach, and diff capabilities. However:
1. `current_sprint` had no explicit lifecycle transition mechanism.
2. Sprint closure risk lost history without persistent snapshot storage.
3. Concurrent sprint advance operations faced lost-update risks.

## Decision

1. **Sprint Advancement (`advance-sprint`)**:
   - Enforce forward-only progression (`new_sprint > old_sprint`) by default.
   - Atomic state transitions via `update_state` read-modify-write under `FileLock`.
   - On advance, write pre-closure snapshot to history before mutating state.
   - Reset `sprint_started_at` to the advancement timestamp.
   - Automatically refresh roadmap AUTO-SPRINT section via canonical writer.

2. **History Storage (`planner history`)**:
   - Store historical sprint records in `.rddf/state/.planner-history.jsonl` (gitignored).
   - Append-only write under FileLock.
   - Line-by-line parsing with corruption tolerance (skip & warn on corrupt records).
   - Unlimited retention by default; explicit pruning via `--prune-keep N [--apply]`.

3. **Authority Hierarchy**:
   - `## Phase Skeleton` Theme column remains primary.
   - Phase fragment `主题` serves as fallback, emitting a warning upon conflict.

## Consequences

- ✅ Full audit trail for past sprint performance and project allocations.
- ✅ Zero state corruption from concurrent advance or sync operations.
- ✅ Preserves schema version 1 backward compatibility.
- ⚠️ Adds `.planner-history.jsonl` file management.
```

- [ ] **Step 5: Synchronize ADR index in `docs/adr/README.md`**

Update `docs/adr/README.md` using `_lib.adr_index_generator`:

```bash
python3 <<'PYEOF'
from pathlib import Path
import re
from _lib.adr_index_generator import render_table, scan_adrs

adrs = scan_adrs(Path('docs/adr'))
seen = {}
for a in adrs:
    seen.setdefault(a["number"], a)
deduped = sorted(seen.values(), key=lambda a: a["number"])
table = render_table(deduped).rstrip()

readme = Path('docs/adr/README.md').read_text(encoding='utf-8')
pattern = re.compile(r'<!-- ADR_INDEX_START -->\n.*?<!-- ADR_INDEX_END -->', re.DOTALL)
new_readme = pattern.sub(f'<!-- ADR_INDEX_START -->\n{table}\n<!-- ADR_INDEX_END -->', readme)
Path('docs/adr/README.md').write_text(new_readme, encoding='utf-8')
PYEOF
```

- [ ] **Step 6: Run tests and verify pass**

```bash
python3 -m pytest tests/unit/test_planner_cli.py tests/unit/test_adr_index_gate.py -q
bats tests/integration/test_planner_cmd.bats
```
Expected: PASS.

- [ ] **Step 7: Commit Change 3**

```bash
git add _lib/cli/planner_cmd.py docs/adr/ADR-0041-planner-sprint-lifecycle-and-history.md docs/adr/README.md tests/unit/test_planner_cli.py tests/integration/test_planner_cmd.bats
git commit -m "feat(planner): add history CLI and ADR-0041 sprint lifecycle contract"
```

---

## Task 4: Full Wave 3 Regression Gate

- [ ] **Step 1: Run focused unit suites**

```bash
python3 -m pytest tests/unit/test_roadmap_sprint.py tests/unit/test_planner_state.py tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py tests/unit/test_planner_attach.py tests/unit/test_planner_audit.py tests/unit/test_planner_history.py tests/unit/test_feedback_appender.py tests/unit/test_feedback_cli.py tests/unit/test_adr_index_gate.py -q
```
Expected: All pass (~150 tests).

- [ ] **Step 2: Run integration suites**

```bash
bats tests/integration/test_planner_cmd.bats tests/integration/test_feedback_cmd.bats
```
Expected: All pass.

- [ ] **Step 3: Run quick regression & python regression**

```bash
./test.sh --quick
```
Expected: All green.

- [ ] **Step 4: Verify invariants**

```bash
git status --short .rddf/improvements/
```
Expected: Empty (0 files touched).

---

## Self-Review Checklist
1. **Concurrency**: `update_state` read-modify-write under lock implemented in Change 0.
2. **Forward-only**: `advance_sprint` rejects backward move without `--force`.
3. **No history loss**: History snapshot written before state mutation.
4. **Pruning safety**: `prune_history` defaults to dry-run.
5. **Single writer intact**: `update_roadmap(table="project")` still the only writer.
6. **No bulk edits**: Improvements directory untouched.
