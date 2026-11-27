"""The builder handoff must not claim more than what happened.

Background (fix-builder-handoff-p2-lifecycle-truth): ``phase2_execute.sh``
wrote ``execution_status="completed"`` when the **setup** finished (worktree
created) — before a single task was implemented. Measured 2026-11-26: 5 files
changed, 0 tasks checked, handoff said "completed" ⇒ every reader (a resumed
session, a board, any consumer) misread the state.

The truth now comes from disk (the task counter); the handoff only carries a
*claim*, and the P2.5 review (the merge decision point) shows both.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
REPO_ROOT = Path(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _lib.builder_handoff import implementation_state  # noqa: E402


def _write_tasks(root: Path, name: str, done: int, total: int) -> None:
    d = root / "openspec" / "changes" / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"- [{'x' if i < done else ' '}] t{i}\n" for i in range(total)]
    (d / "tasks.md").write_text("".join(lines), encoding="utf-8")


def _write_handoff(root: Path, name: str, execution_status: str) -> None:
    d = root / ".rddf" / "state" / "builder"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(
        json.dumps({
            "schema": "builder-handoff-v1",
            "version": 1,
            "owner": "rdd-builder",
            "change_name": name,
            "current_phase": "phase-2",
            "execution_status": execution_status,
        }, ensure_ascii=False),
        encoding="utf-8",
    )


# --- AC1 / AC2: truth from disk, handoff only claims -------------------------


def test_setup_only_handoff_does_not_claim_completion(tmp_path):
    """P2 setup wrote `completed` with zero tasks done — the lie."""
    _write_tasks(tmp_path, "c1", 0, 3)
    _write_handoff(tmp_path, "c1", "completed")
    state = implementation_state(str(tmp_path), "c1")
    assert state.claimed_complete is True
    assert state.actually_complete is False
    assert state.inconsistent is True


def test_legacy_handoff_is_readable_and_interpreted_as_setup(tmp_path):
    """Legacy value: readable, never crashing, and NOT taken as "done"."""
    _write_tasks(tmp_path, "c1", 1, 3)
    _write_handoff(tmp_path, "c1", "completed")
    state = implementation_state(str(tmp_path), "c1")
    assert state.handoff_status == "completed"
    assert state.actually_complete is False
    assert state.inconsistent is True


def test_consistent_handoff_is_not_inconsistent(tmp_path):
    _write_tasks(tmp_path, "c1", 3, 3)
    _write_handoff(tmp_path, "c1", "completed")
    state = implementation_state(str(tmp_path), "c1")
    assert state.actually_complete is True
    assert state.inconsistent is False


def test_running_handoff_with_all_tasks_done_is_not_inconsistent(tmp_path):
    _write_tasks(tmp_path, "c1", 3, 3)
    _write_handoff(tmp_path, "c1", "running")
    state = implementation_state(str(tmp_path), "c1")
    assert state.actually_complete is True
    assert state.inconsistent is False


def test_missing_files_do_not_crash(tmp_path):
    state = implementation_state(str(tmp_path), "nope")
    assert state.tasks_total == 0
    assert state.handoff_status == ""
    assert state.actually_complete is False
    assert state.inconsistent is False


def test_zero_total_tasks_is_not_complete(tmp_path):
    _write_tasks(tmp_path, "c1", 0, 0)
    _write_handoff(tmp_path, "c1", "completed")
    state = implementation_state(str(tmp_path), "c1")
    assert state.actually_complete is False
    assert state.inconsistent is True


# --- AC1: the write side must not write the lie ------------------------------


def test_phase2_setup_does_not_write_completed():
    script = (REPO_ROOT / "skills/rdd-builder/scripts/phase2_execute.sh").read_text(
        encoding="utf-8")
    assert 'execution_status="completed"' not in script, (
        "P2 setup must not claim the implementation is completed"
    )
    assert 'execution_status="running"' in script


def test_phase3_archive_writes_completed():
    script = (REPO_ROOT / "skills/rdd-builder/scripts/phase3_archive.sh").read_text(
        encoding="utf-8")
    assert 'execution_status="completed"' in script


# --- AC3: the enum converges -------------------------------------------------


def test_execution_status_enum_has_no_wild_values():
    schema = json.loads(
        (REPO_ROOT / "_lib/schemas/builder_handoff_schema.json").read_text(encoding="utf-8")
    )
    enum = schema["properties"]["execution_status"]["enum"]
    assert enum == ["pending", "running", "failed", "completed"]
    assert "in-progress" not in enum


def test_no_wild_in_progress_value_is_written_anywhere():
    """The enum has no `in-progress` ⇒ no writer may use it (this file excepted:
    it names the value on purpose, to pin the enum)."""
    this_file = Path(__file__).resolve()
    candidates = (
        list((REPO_ROOT / "tests").rglob("*.py"))
        + list((REPO_ROOT / "_lib").rglob("*.py"))
        + list((REPO_ROOT / "skills").rglob("*.py"))
    )
    for path in candidates:
        if path.resolve() == this_file:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert '"in-progress"' not in text, path


# --- AC4: the consumer (P2.5 review) shows the truth ------------------------


def test_phase25_review_uses_the_shared_state_helper():
    script = (REPO_ROOT / "skills/rdd-builder/scripts/phase2_5_review.sh").read_text(
        encoding="utf-8")
    assert "implementation_state" in script, (
        "P2.5 review is the only consumer of the handoff before the merge "
        "decision — it must read the real state"
    )


def test_phase25_review_reports_inconsistency(tmp_path):
    script = (REPO_ROOT / "skills/rdd-builder/scripts/phase2_5_review.sh").read_text(
        encoding="utf-8")
    assert "inconsistent" in script and "不一致" in script
