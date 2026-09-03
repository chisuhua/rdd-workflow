"""Tests for planner CLI dispatcher."""
from __future__ import annotations

import json
import pytest

from _lib.cli.planner_cmd import cmd_planner


def test_cli_status_prints_sprint_info(tmp_path, capsys):
    """rddf planner status prints sprint id."""
    rc = cmd_planner(["status", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "sprint-" in captured.out


def test_cli_sync_default_is_dry_run(tmp_path, capsys):
    """rddf planner sync without --apply does NOT write state file."""
    rc = cmd_planner(["sync", "--project-root", str(tmp_path)])
    assert rc == 0
    state_path = tmp_path / ".rddf" / "state" / ".planner-state.json"
    assert not state_path.exists()


def test_cli_sync_apply_writes_state(tmp_path, capsys):
    """rddf planner sync --apply writes state file."""
    rc = cmd_planner(["sync", "--apply", "--project-root", str(tmp_path)])
    assert rc == 0
    state_path = tmp_path / ".rddf" / "state" / ".planner-state.json"
    assert state_path.exists()


def test_cli_status_with_stored_state(tmp_path, capsys):
    """status reads stored state if it exists."""
    from _lib.planner_state import write_state
    sample = {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+08:00",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }
    write_state(tmp_path, sample)
    rc = cmd_planner(["status", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "stored" in captured.out
    assert "sprint-2026-09" in captured.out


def test_cli_no_subcommand_exits_nonzero(capsys):
    """argparse exits 2 when no subcommand given."""
    try:
        rc = cmd_planner([])
        assert rc != 0
    except SystemExit as e:
        assert e.code != 0