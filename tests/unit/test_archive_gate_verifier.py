"""Tests for archive gate verifier contract (Tasks 11-14).

Per fix-rdd-verifier-lifecycle-dashboard:
- Archive readiness requires verification.state=passed (or audited bypassed)
- verdict_sha must match current implementation branch tip
- Cache must have no failed AC
- Direct ac-verifier fallback writes structured verdict to cache
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.archive_gate import (
    check_archive_readiness,
    write_structured_cache_fallback,
    load_iteration_doc,
)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "x"], check=True)


def _commit_branch(tmp_path: Path, name: str) -> str:
    _init_repo(tmp_path)
    (tmp_path / "f").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "f"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    sha = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                                   text=True).strip()
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", "-b", f"openspec/{name}"], check=True)
    return sha


def _setup_state_with_verification(tmp_path: Path, change: dict) -> None:
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    doc = {"version": 7, "updated_at": "2026-08-26T00:00:00Z",
           "current_phase": "v2.1", "changes": [change]}
    (state_dir / "iteration.json").write_text(json.dumps(doc))


def test_archive_ready_when_passed_and_sha_matches(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": sha,
                         "archive_ready": True, "checked_at": "2026-08-26T00:00:00Z"}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is True
    assert result["verification_state"] == "passed"


def test_archive_blocked_when_verification_missing(tmp_path):
    _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False
    assert "missing" in result["reason"].lower()


def test_archive_blocked_when_state_failed(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "failed", "verdict_sha": sha,
                         "archive_ready": False, "failed_acs": ["AC-1"]}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False
    assert "failed" in result["reason"]


def test_archive_blocked_when_verdict_sha_stale(tmp_path):
    _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": "old_sha",
                         "archive_ready": True}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False
    assert "stale" in result["reason"].lower() or "moved" in result["reason"].lower()


def test_archive_blocked_when_branch_missing(tmp_path):
    _init_repo(tmp_path)
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": "abc",
                         "archive_ready": True}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False
    assert "branch" in result["reason"].lower()


def test_archive_ready_when_bypassed_with_reason(tmp_path):
    _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "bypassed", "archive_ready": True,
                         "bypass_reason": "emergency", "bypass_source": "SKIP_RDD_VERIFIER"}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is True


def test_archive_blocked_when_bypassed_without_reason(tmp_path):
    _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "bypassed", "archive_ready": True}
    })
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False


def test_archive_blocked_when_cache_has_failed_ac(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": sha,
                         "archive_ready": True}
    })
    from _lib.verifier.cache import verdict_cache
    verdict_cache(tmp_path, "ch-x", sha,
                  [{"ac_id": "AC-1", "status": "fail"}],
                  ran_by="rdd-verifier",
                  verification_state="failed",
                  failed_acs=["AC-1"])
    result = check_archive_readiness(tmp_path, "ch-x")
    assert result["ready"] is False
    assert result["cache_failed"] is True


def test_feature_archive_gate_hard_blocks(tmp_path):
    _commit_branch(tmp_path, "ch-x")
    _setup_state_with_verification(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": "abc",
                         "archive_ready": True}
    })
    result = check_archive_readiness(tmp_path, "ch-x",
                                       feature_archive_gate="hard")
    assert result["ready"] is False


def test_write_structured_cache_fallback_writes_v2(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    verdict_doc = {"codebase_commit": sha,
                   "verdict": [{"ac_id": "AC-1", "status": "pass"}]}
    write_structured_cache_fallback(tmp_path, "ch-x", verdict_doc,
                                      implementation_ref="openspec/ch-x")
    cache_path = tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json"
    cached = json.loads(cache_path.read_text())
    assert cached["schema_version"] == 2
    assert cached["ran_by"] == "archive_gate_check"
    assert cached["verification_state"] == "passed"
    assert cached["failed_acs"] == []
    assert cached["implementation_ref"] == "openspec/ch-x"


def test_write_structured_cache_fallback_writes_failed(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    verdict_doc = {"codebase_commit": sha,
                   "verdict": [{"ac_id": "AC-1", "status": "fail"}]}
    write_structured_cache_fallback(tmp_path, "ch-x", verdict_doc)
    cache_path = tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json"
    cached = json.loads(cache_path.read_text())
    assert cached["verification_state"] == "failed"
    assert cached["failed_acs"] == ["AC-1"]
