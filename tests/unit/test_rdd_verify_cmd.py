"""Tests for rddf rdd-verify CLI batch orchestration.

Per fix-rdd-verifier-lifecycle-dashboard Tasks 7-10.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


# ============================================================================
# M2 Task 2.1 (complete-project-yaml-config-gaps M2):
# _detect_verification_provider reads .rddf/project.yaml verification.provider
# ============================================================================


def test_detect_verification_provider_default_llm_no_project_yaml(tmp_path):
    """No .rddf/project.yaml → provider defaults to 'llm' (existing ac-verifier behavior)."""
    from _lib.cli.rdd_verify_cmd import _detect_verification_provider
    # tmp_path has no .rddf/project.yaml
    assert _detect_verification_provider(tmp_path) == "llm"


def test_detect_verification_provider_hook_when_yaml_sets_hook(tmp_path):
    """.rddf/project.yaml verification.provider: hook → return 'hook'."""
    from _lib.cli.rdd_verify_cmd import _detect_verification_provider
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"verification": {"provider": "hook"}})
    )
    assert _detect_verification_provider(tmp_path) == "hook"


def test_detect_verification_provider_explicit_llm(tmp_path):
    """.rddf/project.yaml verification.provider: llm → return 'llm' (explicit)."""
    from _lib.cli.rdd_verify_cmd import _detect_verification_provider
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"verification": {"provider": "llm"}})
    )
    assert _detect_verification_provider(tmp_path) == "llm"


def test_detect_verification_provider_falls_back_on_corrupt_yaml(tmp_path):
    """Corrupt project.yaml → fall back to 'llm' (graceful, never crash)."""
    from _lib.cli.rdd_verify_cmd import _detect_verification_provider
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text("invalid: : : yaml: : :")
    # Should not raise; should fall back to default
    assert _detect_verification_provider(tmp_path) == "llm"


# ============================================================================
# M2 Task 2.2 (complete-project-yaml-config-gaps M2):
# _hook_runner maps hook verdict → _default_runner return format
# ============================================================================


def test_hook_runner_exit_0_maps_to_passed(tmp_path, monkeypatch):
    """Hook script exit 0 → _hook_runner returns passed verdict dict."""
    from _lib.cli.rdd_verify_cmd import _hook_runner
    # Create mock tools/verify_change.sh that exits 0
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    hook = tools_dir / "verify_change.sh"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    result = _hook_runner("ch-test", tmp_path)
    assert result["exit_code"] == 0
    assert result["verdict"][0]["status"] == "pass"
    assert result["failed_acs"] == []
    assert result["provider"] == "hook"


def test_hook_runner_exit_1_maps_to_failed(tmp_path):
    """Hook script exit 1 → _hook_runner returns failed verdict dict."""
    from _lib.cli.rdd_verify_cmd import _hook_runner
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    hook = tools_dir / "verify_change.sh"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    result = _hook_runner("ch-test", tmp_path)
    assert result["exit_code"] == 1
    assert result["verdict"][0]["status"] == "fail"
    assert "hook-ch-test" in result["failed_acs"]
    assert result["provider"] == "hook"


def test_hook_runner_exit_2_maps_to_error(tmp_path):
    """Hook script exit 2+ → _hook_runner returns error verdict dict."""
    from _lib.cli.rdd_verify_cmd import _hook_runner
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    hook = tools_dir / "verify_change.sh"
    hook.write_text("#!/bin/sh\nexit 2\n")
    hook.chmod(0o755)
    result = _hook_runner("ch-test", tmp_path)
    assert result["exit_code"] == 3
    assert "error" in result
    assert result["provider"] == "hook"


def test_hook_runner_missing_script_returns_skipped(tmp_path):
    """tools/verify_change.sh missing → _hook_runner returns skipped (passed exit 0)."""
    from _lib.cli.rdd_verify_cmd import _hook_runner
    # tmp_path has no tools/ subdirectory
    result = _hook_runner("ch-test", tmp_path)
    assert result["exit_code"] == 0
    assert "skipped" in result.get("note", "")
    assert result["provider"] == "hook"


def test_hook_runner_path_outside_tools_raises(tmp_path):
    """Hook path outside tools/ must raise HookPathError (security whitelist)."""
    import pytest
    from _lib.cli.rdd_verify_cmd import _hook_runner
    from _lib.verifier.hook_runner import HookPathError
    # Create a hook in tmp_path root (not in tools/)
    bad_hook = tmp_path / "evil_verify.sh"
    bad_hook.write_text("#!/bin/sh\nexit 0\n")
    bad_hook.chmod(0o755)
    with pytest.raises(HookPathError):
        _hook_runner("ch-test", tmp_path, hook_path=bad_hook)


# ============================================================================
# M2 Task 2.3 + 2.6 (complete-project-yaml-config-gaps M2):
# cmd_rdd_verify selects runner based on project.yaml + explicit override
# ============================================================================


def test_cmd_rdd_verify_uses_hook_runner_when_provider_hook(tmp_path, monkeypatch):
    """cmd_rdd_verify detects verification.provider=hook → uses _hook_runner.

    Per design.md: runner=None → provider detection; provider=hook → _hook_runner.
    """
    import yaml
    # Setup: project.yaml with provider=hook
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"verification": {"provider": "hook"}})
    )
    # Setup: hook script that exits 0
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "verify_change.sh").write_text("#!/bin/sh\nexit 0\n")
    (tools_dir / "verify_change.sh").chmod(0o755)
    # Setup: git repo + openspec branch (use _commit_branch helper)
    _commit_branch(tmp_path, "ch-x")
    # Setup: iteration.json with eligible change (tasks_done == tasks_total)
    _setup_state(tmp_path, [
        {"name": "ch-x", "phase": "v2.1", "status": "in_worktree",
         "implementation_ref": "openspec/ch-x", "tasks_done": 1, "tasks_total": 1},
    ])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = cmd_rdd_verify([])
    # hook returns exit 0 → rdd-verify aggregate passed → rc 0
    assert rc == 0, f"hook provider exit 0 should yield rc 0, got {rc}"


def test_cmd_rdd_verify_default_runner_when_no_provider(tmp_path, monkeypatch):
    """cmd_rdd_verify without provider override → uses _default_runner (LLM)."""
    import yaml
    # Setup: project.yaml WITHOUT verification.provider
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({"git": {"openspec_tracked": True}}))
    # Setup: git branch + eligible change
    _commit_branch(tmp_path, "ch-y")
    _setup_state(tmp_path, [
        {"name": "ch-y", "phase": "v2.1", "status": "in_worktree",
         "implementation_ref": "openspec/ch-y", "tasks_done": 1, "tasks_total": 1},
    ])
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # Inject a runner to capture which one is selected
    captured = {}
    def spy_runner(change_name, project_root):
        captured["name"] = change_name
        captured["provider"] = "spy_default"
        return {"exit_code": 0, "verdict": [{"ac_id": "spy", "status": "pass"}],
                "failed_acs": [], "verdict_json": None, "provider": "spy_default"}
    rc = cmd_rdd_verify([], runner=spy_runner)
    assert rc == 0
    # Explicit runner wins over provider detection (Metis Decision 8)
    assert captured.get("provider") == "spy_default"


def test_explicit_runner_overrides_provider_hook(tmp_path, monkeypatch):
    """Explicit runner argument beats project.yaml provider detection (Metis Decision 8)."""
    import yaml
    # Setup: project.yaml with provider=hook
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"verification": {"provider": "hook"}})
    )
    # Setup: git branch + eligible change
    _commit_branch(tmp_path, "ch-z")
    _setup_state(tmp_path, [
        {"name": "ch-z", "phase": "v2.1", "status": "in_worktree",
         "implementation_ref": "openspec/ch-z", "tasks_done": 1, "tasks_total": 1},
    ])
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    # Pass explicit mock runner — should win over hook detection
    mock_calls = []
    def mock_runner(change_name, project_root):
        mock_calls.append((change_name, project_root))
        return {"exit_code": 0, "verdict": [{"ac_id": "mock", "status": "pass"}],
                "failed_acs": [], "verdict_json": None, "provider": "mock"}
    rc = cmd_rdd_verify([], runner=mock_runner)
    assert rc == 0
    # mock_runner was invoked; _hook_runner was NOT
    assert len(mock_calls) == 1
    assert mock_calls[0][0] == "ch-z"
