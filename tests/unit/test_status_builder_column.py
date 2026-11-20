"""Tests for the ``BUILDER`` column in ``rddf status``.

The overview table used to omit the builder stage entirely, so an agent
had to read ``.rddf/state/builder/<name>.json`` by hand for every change
to find out whether P3 had been reached.

Column contract:
  - named ``BUILDER`` (NOT ``PHASE`` — the table already prints an
    iteration/roadmap ``Phase`` above it, with a different meaning)
  - value is the builder ``current_phase`` (``phase-0`` … ``phase-3``)
  - archived changes show ``-`` (their builder state lingers as phase-3)
  - missing or corrupt builder state shows ``-`` and never raises
"""
from __future__ import annotations

import json
from pathlib import Path

from skills._lib.cli.status_cmd import _builder_phase, cmd_status


def _write_iteration(project_root: Path, changes: list) -> None:
    state = project_root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "iteration.json").write_text(
        json.dumps({
            "version": 6,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": changes,
        }),
        encoding="utf-8",
    )


def _write_builder_state(project_root: Path, change_name: str, payload) -> None:
    d = project_root / ".rddf" / "state" / "builder"
    d.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        (d / f"{change_name}.json").write_text(payload, encoding="utf-8")
    else:
        (d / f"{change_name}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_builder_phase_reads_current_phase(tmp_path):
    _write_builder_state(tmp_path, "add-x", {"current_phase": "phase-2"})
    assert _builder_phase(str(tmp_path), "add-x", "in_worktree") == "phase-2"


def test_builder_phase_missing_state_is_dash(tmp_path):
    assert _builder_phase(str(tmp_path), "add-x", "in_worktree") == "-"


def test_builder_phase_corrupt_state_is_dash(tmp_path):
    _write_builder_state(tmp_path, "add-x", "{ not json")
    assert _builder_phase(str(tmp_path), "add-x", "in_worktree") == "-"


def test_builder_phase_archived_is_dash(tmp_path):
    """Archived changes keep their builder state (phase-3) on disk —
    showing it would read as "still in P3"."""
    _write_builder_state(tmp_path, "old-x", {"current_phase": "phase-3"})
    assert _builder_phase(str(tmp_path), "old-x", "archived") == "-"


def test_status_overview_renders_builder_column(tmp_path, capsys, monkeypatch):
    """Mode A's active-changes table is derived from disk, not iteration.json.

    (rddf-status-based-on-improvements: `rddf status` no longer reads
    iteration.json; the active-changes table comes from openspec/changes/.)
    """
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    active = tmp_path / "openspec" / "changes" / "add-x"
    active.mkdir(parents=True)
    (active / "tasks.md").write_text("- [x] t1\n- [ ] t2\n", encoding="utf-8")
    archived = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-old-x"
    archived.mkdir(parents=True)
    _write_builder_state(tmp_path, "add-x", {"current_phase": "phase-2"})
    _write_builder_state(tmp_path, "old-x", {"current_phase": "phase-3"})

    rc = cmd_status([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "BUILDER" in out
    assert "phase-2" in out
    # the tasks counter comes from tasks.md on disk
    assert "1/2" in out
    # archived changes are not part of the active-changes table at all
    assert "old-x" not in out
    assert "phase-3" not in out
