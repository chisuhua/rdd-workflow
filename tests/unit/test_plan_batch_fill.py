"""Unit tests for the plan batch-fill helper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills.guide_plan.scripts import plan_batch_fill as batch_fill


def _make_repo(tmp_path: Path, names: list[str], *, acceptance: str = "- [ ] Implement it") -> Path:
    for name in names:
        change_dir = tmp_path / "openspec" / "changes" / name
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text(
            f"""# {name}

## Why
The reason for {name}.

## What Changes
- Add the feature.

## Capabilities
- MUST support the feature.

## Impact
- No schema changes.

## Acceptance
{acceptance}
""",
            encoding="utf-8",
        )
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "iteration.json").write_text(
        json.dumps({
            "version": 6,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {"name": name, "status": "planned"} for name in names
            ],
        }),
        encoding="utf-8",
    )
    return tmp_path


def test_single_change_fill_updates_status(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, ["one"])
    result = batch_fill.fill_changes(repo, ["one"])
    assert result.filled == ["one"]
    assert (repo / "openspec/changes/one/design.md").exists()
    assert "## Context" in (repo / "openspec/changes/one/design.md").read_text()
    state = json.loads((repo / ".rddf/state/iteration.json").read_text())
    assert state["changes"][0]["status"] == "proposed"


def test_multiple_changes_fill_in_one_call(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, ["one", "two"])
    result = batch_fill.fill_changes(repo, ["one", "two"])
    assert result.filled == ["one", "two"]
    assert all((repo / "openspec/changes" / name / "tasks.md").exists() for name in ["one", "two"])


def test_missing_acceptance_creates_empty_tasks(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, ["one"], acceptance="")
    batch_fill.fill_changes(repo, ["one"])
    assert (repo / "openspec/changes/one/tasks.md").read_text() == (
        "# Tasks: one\n\n## Implementation Tasks\n"
    )


def test_iteration_write_failure_preserves_original(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path, ["one"])
    state_path = repo / ".rddf/state/iteration.json"
    original = state_path.read_bytes()
    monkeypatch.setattr(batch_fill, "atomic_write_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        batch_fill.fill_changes(repo, ["one"])
    assert state_path.read_bytes() == original


def test_existing_design_is_skipped_idempotently(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, ["one"])
    design = repo / "openspec/changes/one/design.md"
    design.write_text("existing\n", encoding="utf-8")
    result = batch_fill.fill_changes(repo, ["one"])
    assert result.skipped == ["one"]
    assert design.read_text() == "existing\n"
    state = json.loads((repo / ".rddf/state/iteration.json").read_text())
    assert state["changes"][0]["status"] == "planned"


def test_invalid_or_missing_change_fails(tmp_path: Path) -> None:
    """fill_changes accumulates invalid names into result.failed (no raise).

    Per design contract: one bad entry doesn't block the other 8 in batch.
    """
    repo = _make_repo(tmp_path, ["one"])

    # Invalid name (path traversal) — only bad entry
    result = batch_fill.fill_changes(repo, ["../escape"])
    assert result.failed == ["../escape"]
    assert result.filled == []
    assert result.skipped == []

    # Missing proposal.md — only bad entry
    result2 = batch_fill.fill_changes(repo, ["missing"])
    assert result2.failed == ["missing"]
    assert result2.filled == []
