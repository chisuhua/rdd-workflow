"""Tests for rddf rdd-verify CLI batch orchestration.

Per fix-rdd-verifier-lifecycle-dashboard Tasks 7-10.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.cli.rdd_verify_cmd import (
    cmd_rdd_verify,
    run_one_change,
    aggregate_exit,
    update_iteration_summary,
    _load_iteration_doc,
    _save_iteration_doc,
)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "x"], check=True)


def _setup_state(tmp_path: Path, changes: list) -> None:
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    doc = {"version": 7, "updated_at": "2026-08-26T00:00:00Z",
           "current_phase": "v2.1", "changes": changes}
    (state_dir / "iteration.json").write_text(json.dumps(doc))


def _commit_branch(tmp_path: Path, name: str) -> str:
    _init_repo(tmp_path)
    (tmp_path / "f").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "f"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    sha = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                                   text=True).strip()
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", "-b", f"openspec/{name}"], check=True)
    return sha


def test_aggregate_exit_picks_highest():
    assert aggregate_exit(["passed", "passed"]) == 0
    assert aggregate_exit(["failed", "passed"]) == 1
    assert aggregate_exit(["failed", "error"]) == 3
    assert aggregate_exit(["halted", "passed"]) == 4
    assert aggregate_exit(["halted", "failed", "error"]) == 4
    assert aggregate_exit(["bypassed", "passed"]) == 0


def test_empty_queue_returns_zero(tmp_path, monkeypatch, capsys):
    _setup_state(tmp_path, [])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RDDF_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("SKIP_RDD_VERIFIER", raising=False)
    monkeypatch.delenv("RDDF_VERIFIER_BYPASS_REASON", raising=False)
    rc = cmd_rdd_verify([])
    out = capsys.readouterr().out
    assert rc == 0
    assert ("empty" in out.lower() or "0 changes" in out.lower()
            or "no eligible" in out.lower() or "no changes" in out.lower())


def test_skip_without_reason_fails_closed(tmp_path, monkeypatch):
    _setup_state(tmp_path, [])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RDDF_PROJECT_ROOT", raising=False)
    monkeypatch.setenv("SKIP_RDD_VERIFIER", "yes")
    monkeypatch.delenv("RDDF_VERIFIER_BYPASS_REASON", raising=False)
    rc = cmd_rdd_verify([])
    assert rc == 3


def test_skip_with_reason_writes_bypassed_state(tmp_path, monkeypatch):
    change = {"name": "ch-x", "status": "in_worktree",
              "tasks_done": 2, "tasks_total": 2}
    _setup_state(tmp_path, [change])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RDDF_PROJECT_ROOT", raising=False)
    monkeypatch.setenv("SKIP_RDD_VERIFIER", "yes")
    monkeypatch.setenv("RDDF_VERIFIER_BYPASS_REASON", "emergency hotfix")
    rc = cmd_rdd_verify([])
    assert rc == 0
    doc = _load_iteration_doc(tmp_path)
    ch = next(c for c in doc["changes"] if c["name"] == "ch-x")
    assert ch["verification"]["state"] == "bypassed"
    assert ch["verification"]["bypass_source"] == "SKIP_RDD_VERIFIER"
    assert ch["verification"]["bypass_reason"] == "emergency hotfix"


def test_run_one_change_passed_writes_cache_and_state(tmp_path):
    sha = _commit_branch(tmp_path, "ch-x")
    _setup_state(tmp_path, [{"name": "ch-x", "status": "in_worktree",
                              "tasks_done": 1, "tasks_total": 1}])
    def fake_runner(change_name, project_root):
        return {"exit_code": 0, "verdict": [], "verdict_json": None,
                "failed_acs": []}
    result = run_one_change(tmp_path, "ch-x", fake_runner)
    assert result["state"] == "passed"
    assert result["verdict_sha"] == sha
    assert result["archive_ready"] is True

    cache_file = tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json"
    assert cache_file.is_file()
    cached = json.loads(cache_file.read_text())
    assert cached["verification_state"] == "passed"
    assert cached["codebase_commit"] == sha


def test_run_one_change_failed_writes_failed_state(tmp_path):
    sha = _commit_branch(tmp_path, "ch-y")
    _setup_state(tmp_path, [{"name": "ch-y", "status": "completed",
                              "tasks_done": 3, "tasks_total": 3}])
    def fake_runner(change_name, project_root):
        return {"exit_code": 1, "verdict": [{"ac_id": "AC-1", "status": "fail"}],
                "verdict_json": None, "failed_acs": ["AC-1"]}
    result = run_one_change(tmp_path, "ch-y", fake_runner)
    assert result["state"] == "failed"
    assert result["archive_ready"] is False
    assert result["failed_acs"] == ["AC-1"]
    assert result["route"] in ("guide-ship", "guide-plan")


def test_run_one_change_error_returns_error_state(tmp_path):
    _commit_branch(tmp_path, "ch-z")
    _setup_state(tmp_path, [{"name": "ch-z", "status": "in_worktree",
                              "tasks_done": 1, "tasks_total": 1}])
    def fake_runner(change_name, project_root):
        return {"exit_code": 3, "verdict": [], "verdict_json": None,
                "failed_acs": []}
    result = run_one_change(tmp_path, "ch-z", fake_runner)
    assert result["state"] == "error"


def test_run_one_change_uses_cache_when_fresh(tmp_path):
    sha = _commit_branch(tmp_path, "ch-c")
    from _lib.verifier.cache import verdict_cache
    verdict_cache(tmp_path, "ch-c", sha, [{"ac_id": "AC-1", "status": "pass"}],
                  ran_by="rdd-verifier", verification_state="passed", failed_acs=[])
    _setup_state(tmp_path, [{"name": "ch-c", "status": "completed",
                              "tasks_done": 1, "tasks_total": 1}])
    called = []
    def fake_runner(change_name, project_root):
        called.append(change_name)
        return {"exit_code": 99, "verdict": [], "verdict_json": None, "failed_acs": []}
    result = run_one_change(tmp_path, "ch-c", fake_runner)
    assert called == []
    assert result["state"] == "passed"


def test_run_one_change_branch_missing_returns_halted(tmp_path):
    _init_repo(tmp_path)
    _setup_state(tmp_path, [{"name": "ch-missing", "status": "in_worktree",
                              "tasks_done": 1, "tasks_total": 1}])
    def fake_runner(change_name, project_root):
        return {"exit_code": 0, "verdict": [], "verdict_json": None, "failed_acs": []}
    result = run_one_change(tmp_path, "ch-missing", fake_runner)
    assert result["state"] == "halted"
    assert "branch" in (result.get("halt_reason") or "").lower()


def test_update_iteration_summary_writes_verification(tmp_path):
    _setup_state(tmp_path, [{"name": "ch-z", "status": "in_worktree",
                              "tasks_done": 1, "tasks_total": 1}])
    update_iteration_summary(tmp_path, "ch-z", {
        "state": "passed",
        "verdict_sha": "abc123",
        "checked_at": "2026-08-26T12:00:00Z",
        "route": "archive-ready",
        "loop_count": 0,
        "failed_acs": [],
        "archive_ready": True,
    })
    doc = _load_iteration_doc(tmp_path)
    ch = next(c for c in doc["changes"] if c["name"] == "ch-z")
    assert ch["verification"]["state"] == "passed"
    assert ch["verification"]["verdict_sha"] == "abc123"
    assert ch["verification"]["archive_ready"] is True
