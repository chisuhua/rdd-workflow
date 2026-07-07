"""Tests for the v2-loop-engine actions module.

Covers: ActionResult dataclass, run_subprocess wrapper (success / failure /
timeout), 7 built-in actions registered, plugin loading with empty dir.
"""
import pytest
from skills._lib.actions import Action, ActionResult, run_subprocess


def test_action_result_dataclass():
    """ActionResult(success, data, error=None) defaults error to None."""
    r = ActionResult(success=True, data={"x": 1})
    assert r.success is True
    assert r.data == {"x": 1}
    assert r.error is None


def test_action_result_with_error():
    """ActionResult carries an error string on failure."""
    r = ActionResult(success=False, data={"k": "v"}, error="boom")
    assert r.success is False
    assert r.data == {"k": "v"}
    assert r.error == "boom"


def test_run_subprocess_success():
    """run_subprocess returns success=True on exit 0 and captures stdout."""
    result = run_subprocess(["echo", "hello"], timeout_seconds=5)
    assert result.success is True
    assert "hello" in result.data.get("stdout", "")
    assert result.data.get("returncode") == 0


def test_run_subprocess_failure_returns_error():
    """run_subprocess returns success=False on non-zero exit and surfaces error."""
    result = run_subprocess(["false"], timeout_seconds=5)
    assert result.success is False
    assert result.error is not None
    assert result.data.get("returncode") != 0


def test_run_subprocess_timeout_terminates():
    """run_subprocess kills process exceeding timeout and reports timeout."""
    result = run_subprocess(["sleep", "10"], timeout_seconds=1)
    assert result.success is False
    # Either explicit timeout flag, or the word "timeout" in the error message.
    is_timeout = result.data.get("timed_out") is True or "timeout" in (result.error or "").lower()
    assert is_timeout, f"expected timeout signal, got data={result.data!r} error={result.error!r}"


def test_seven_builtin_actions_registered():
    """All 7 built-in actions present in BUILTIN_ACTIONS."""
    from skills._lib.actions import BUILTIN_ACTIONS

    expected = {
        "action_create_worktree", "action_generate_plan", "action_execute_worktree",
        "action_archive_change", "action_cleanup_stale", "action_update_roadmap",
        "action_create_adr",
    }
    actual = {a.__name__ for a in BUILTIN_ACTIONS}
    assert expected == actual


def test_load_plugin_actions_empty_when_dir_missing(tmp_path, monkeypatch):
    """No error when .rddf/actions/ doesn't exist."""
    monkeypatch.chdir(tmp_path)
    from skills._lib.actions import load_plugin_actions

    assert load_plugin_actions() == []
