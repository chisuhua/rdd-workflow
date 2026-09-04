"""Tests for recompute_planner_feedback + safe_recompute_planner_feedback helpers.

Wave 4 Change 2: hooks (planner sync --apply + arch-done) call these
helpers to close the bidirectional loop. safe_recompute wraps the
strict helper with try/except to avoid blocking parent flows.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _setup_improvements_only(tmp_path: Path) -> str:
    """Create .rddf/improvements/feat-x.md with no theme_ref → triggers feedback emit."""
    project_root = str(tmp_path)
    improvements_dir = tmp_path / ".rddf" / "improvements"
    improvements_dir.mkdir(parents=True)
    (improvements_dir / "feat-x.md").write_text(
        "---\nname: feat-x\npriority: P1\n---\n# feat-x\n"
    )
    return project_root


def test_recompute_planner_feedback_writes_feedback_file(tmp_path: Path):
    """recompute_planner_feedback creates .planner-feedback.json with the unmapped entry."""
    project_root = _setup_improvements_only(tmp_path)

    from _lib.planner_feedback import recompute_planner_feedback
    recompute_planner_feedback(project_root)

    path = tmp_path / ".rddf" / "state" / ".planner-feedback.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data["feedbacks"]) == 1
    assert data["feedbacks"][0]["proposal"] == "feat-x"
    assert data["feedbacks"][0]["kind"] == "unmapped_proposal"


def test_safe_recompute_swallows_exceptions(tmp_path: Path):
    """safe_recompute catches exceptions, logs warning, returns None without re-raise."""
    project_root = _setup_improvements_only(tmp_path)

    from unittest.mock import patch
    from _lib.planner_feedback import safe_recompute_planner_feedback

    with patch(
        "_lib.planner_feedback.compute_planner_feedback",
        side_effect=RuntimeError("simulated compute failure"),
    ):
        result = safe_recompute_planner_feedback(project_root)

    assert result is None


def test_safe_recompute_returns_state_on_success(tmp_path: Path):
    """safe_recompute returns the new state dict on success (no exception)."""
    project_root = _setup_improvements_only(tmp_path)

    from _lib.planner_feedback import safe_recompute_planner_feedback
    result = safe_recompute_planner_feedback(project_root)

    assert result is not None
    assert "feedbacks" in result
    assert len(result["feedbacks"]) == 1


def test_recompute_idempotent_on_same_input(tmp_path: Path):
    """Two consecutive recomputes → second call returns same feedbacks (R15 true idempotency)."""
    project_root = _setup_improvements_only(tmp_path)

    from _lib.planner_feedback import recompute_planner_feedback
    first = recompute_planner_feedback(project_root)
    second = recompute_planner_feedback(project_root)

    assert len(first["feedbacks"]) == len(second["feedbacks"]) == 1
    assert first["feedbacks"][0]["feedback_id"] == second["feedbacks"][0]["feedback_id"]
    # last_seen_at preserved on fingerprint match (R15)
    assert first["feedbacks"][0]["last_seen_at"] == second["feedbacks"][0]["last_seen_at"]


def test_recompute_uses_single_file_lock(tmp_path: Path):
    """recompute_planner_feedback reads prior + computes + writes inside one FileLock."""
    project_root = _setup_improvements_only(tmp_path)

    from _lib import planner_feedback as pf
    from _lib.core.lock import FileLock

    lock_acquire_count = 0
    real_FileLock = pf.FileLock

    class CountingLock(real_FileLock):
        def __init__(self, *args, **kwargs):
            nonlocal lock_acquire_count
            lock_acquire_count += 1
            super().__init__(*args, **kwargs)

    pf.FileLock = CountingLock
    try:
        pf.recompute_planner_feedback(project_root)
    finally:
        pf.FileLock = real_FileLock

    assert lock_acquire_count == 1, (
        f"recompute should acquire lock exactly once, got {lock_acquire_count}"
    )