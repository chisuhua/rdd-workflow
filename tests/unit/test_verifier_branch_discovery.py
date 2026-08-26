"""Tests for implementation commit resolver + eligible-change discovery.

Per fix-rdd-verifier-lifecycle-dashboard Tasks 5 + 6:
- Resolves openspec/<change> branch tip; fails closed when missing/detached
- Discovers eligible changes from iteration.json (in_worktree/completed with tasks_done == tasks_total)
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.branch import resolve_implementation_commit
from _lib.verifier.discovery import discover_eligible, _is_eligible


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "x"], check=True)


def _commit(path: Path, filename: str, content: str = "x") -> str:
    (path / filename).write_text(content)
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "add " + filename], check=True)
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"],
                                  text=True).strip()


def test_resolve_branch_tip(tmp_path):
    _init_repo(tmp_path)
    _commit(tmp_path, "f1.txt")
    _commit(tmp_path, "f2.txt")
    tip_sha = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                                       text=True).strip()
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", "-b", "openspec/ch-x"], check=True)
    assert resolve_implementation_commit(tmp_path, "ch-x") == tip_sha


def test_resolve_branch_missing_returns_none(tmp_path):
    _init_repo(tmp_path)
    assert resolve_implementation_commit(tmp_path, "ch-x") is None


def test_resolve_detached_head_returns_none(tmp_path):
    _init_repo(tmp_path)
    sha = _commit(tmp_path, "f.txt")
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", sha], check=True)
    assert resolve_implementation_commit(tmp_path, "ch-x") is None


def test_resolve_non_git_dir_returns_none(tmp_path):
    assert resolve_implementation_commit(tmp_path, "ch-x") is None


def test_is_eligible_in_worktree_complete():
    change = {"status": "in_worktree", "tasks_done": 3, "tasks_total": 3}
    assert _is_eligible(change) is True


def test_is_eligible_completed():
    change = {"status": "completed", "tasks_done": 5, "tasks_total": 5}
    assert _is_eligible(change) is True


def test_is_eligible_incomplete_tasks():
    change = {"status": "in_worktree", "tasks_done": 1, "tasks_total": 3}
    assert _is_eligible(change) is False


def test_is_eligible_archived():
    change = {"status": "archived", "tasks_done": 5, "tasks_total": 5}
    assert _is_eligible(change) is False


def test_is_eligible_archived_partial():
    change = {"status": "archived_partial", "tasks_done": 5, "tasks_total": 5}
    assert _is_eligible(change) is False


def test_is_eligible_zero_tasks():
    change = {"status": "in_worktree", "tasks_done": 0, "tasks_total": 0}
    assert _is_eligible(change) is False


def test_is_eligible_proposed():
    change = {"status": "proposed", "tasks_done": 5, "tasks_total": 5}
    assert _is_eligible(change) is False


def test_discover_from_iteration(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    state = {
        "version": 7,
        "changes": [
            {"name": "a", "status": "in_worktree", "tasks_done": 3, "tasks_total": 3},
            {"name": "b", "status": "in_worktree", "tasks_done": 1, "tasks_total": 3},
            {"name": "c", "status": "completed", "tasks_done": 2, "tasks_total": 2},
            {"name": "d", "status": "archived", "tasks_done": 1, "tasks_total": 1},
            {"name": "e", "status": "proposed", "tasks_done": 0, "tasks_total": 0},
        ],
    }
    (state_dir / "iteration.json").write_text(json.dumps(state))
    assert discover_eligible(tmp_path) == ["a", "c"]


def test_discover_empty_when_no_iteration(tmp_path):
    assert discover_eligible(tmp_path) == []


def test_discover_empty_when_no_eligible(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "iteration.json").write_text(json.dumps({
        "version": 7, "changes": [
            {"name": "x", "status": "proposed", "tasks_done": 0, "tasks_total": 0},
        ],
    }))
    assert discover_eligible(tmp_path) == []
