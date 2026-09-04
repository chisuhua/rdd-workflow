"""Tests for _current_branch helper (Wave 4 Sub-task 1.3).

Replaces hardcoded 'branch': 'main' in _empty_schema and
compute_planner_feedback's return with git rev-parse --abbrev-ref HEAD.

Handles:
- normal git repo → branch name
- detached HEAD → 'detached'
- non-git / subprocess failure → 'unknown'
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest


def test_branch_uses_git_head(tmp_path: Path):
    """In a git repo → _current_branch returns 'git rev-parse --abbrev-ref HEAD' output."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "checkout", "-b", "feat-branch-helper"],
                   cwd=tmp_path, capture_output=True, check=True)

    from _lib.planner_feedback import _current_branch
    assert _current_branch(str(tmp_path)) == "feat-branch-helper"


def test_branch_fallback_non_git(tmp_path: Path):
    """Non-git dir → _current_branch returns 'unknown' (no crash)."""
    from _lib.planner_feedback import _current_branch
    assert _current_branch(str(tmp_path)) == "unknown"


def test_branch_detached_head_returns_detached(tmp_path: Path):
    """git rev-parse --abbrev-ref HEAD on detached HEAD → 'HEAD' literal → mapped to 'detached'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=tmp_path, capture_output=True, check=True)
    # Detach HEAD
    subprocess.run(["git", "checkout", "--detach"],
                   cwd=tmp_path, capture_output=True, check=True)

    from _lib.planner_feedback import _current_branch
    assert _current_branch(str(tmp_path)) == "detached"


def test_branch_subprocess_timeout_returns_unknown(tmp_path: Path):
    """subprocess.run timeout / FileNotFoundError → 'unknown'."""
    from _lib import planner_feedback
    import _lib.planner_feedback as pf_mod

    real_run = pf_mod.subprocess.run

    def _timeout_run(*args, **kwargs):
        if args and args[0] and args[0][0] == "git":
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=5)
        return real_run(*args, **kwargs)

    with mock.patch.object(pf_mod.subprocess, "run", side_effect=_timeout_run):
        result = pf_mod._current_branch(str(tmp_path))
    assert result == "unknown"


def test_empty_schema_branch_uses_helper_not_hardcoded(tmp_path: Path):
    """_empty_schema('branch' field) reflects current git branch, not 'main'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "checkout", "-b", "current-branch-name"],
                   cwd=tmp_path, capture_output=True, check=True)

    from _lib.planner_feedback import _empty_schema
    schema = _empty_schema(str(tmp_path))
    assert schema["branch"] == "current-branch-name"


def test_compute_planner_feedback_return_uses_branch_helper(tmp_path: Path):
    """compute_planner_feedback return dict uses _current_branch value."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "checkout", "-b", "my-feature"],
                   cwd=tmp_path, capture_output=True, check=True)
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True)
    (tmp_path / ".rddf" / "improvements" / "feat-x.md").write_text(
        "---\nname: feat-x\npriority: P1\n---\n"
    )

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(str(tmp_path))
    assert result["branch"] == "my-feature"