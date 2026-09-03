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
