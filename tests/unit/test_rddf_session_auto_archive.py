"""Verify _rddf_should_auto_archive threshold helper.

Contract (from .rddf/improvements/add-rddf-session-auto-archive-on-entry.md):
  threshold = keep + 5 (default)
  RDDF_AUTO_ARCHIVE_THRESHOLD env var overrides threshold (0 = disabled)
  RDDF_AUTO_ARCHIVE_KEEP env var overrides keep (0 = disabled)

Returns: True if total_count >= threshold AND keep > 0 AND threshold > 0
"""
import json
import os
import subprocess
from pathlib import Path

HOOKS_SCRIPT = Path("skills/rddf-session/scripts/rddf_session_hooks.sh")


def _invoke_helper(total_count: int, keep: int, threshold: int | None) -> bool:
    """Invoke _rddf_should_auto_archive with given args via bash subprocess.

    Helper signature: _rddf_should_auto_archive <total_count> <keep> <threshold>
    Returns 0 (true) if should archive, 1 (false) otherwise.
    """
    args = f"{total_count} {keep} {threshold if threshold is not None else ''}"
    env = os.environ.copy()
    env.pop("RDDF_AUTO_ARCHIVE_KEEP", None)
    env.pop("RDDF_AUTO_ARCHIVE_THRESHOLD", None)
    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_should_auto_archive {args}'],
        capture_output=True, env=env,
    )
    return result.returncode == 0


def test_default_threshold_triggers_at_keep_plus_5():
    """Default threshold = keep + 5. So 14 < 15, 15 = 15 (trigger)."""
    assert _invoke_helper(total_count=14, keep=10, threshold=None) is False
    assert _invoke_helper(total_count=15, keep=10, threshold=None) is True
    assert _invoke_helper(total_count=20, keep=10, threshold=None) is True


def test_keep_zero_disables_archive():
    """RDDF_AUTO_ARCHIVE_KEEP=0 -> never archive regardless of count."""
    # Helper accepts keep=0 directly
    assert _invoke_helper(total_count=100, keep=0, threshold=None) is False
    assert _invoke_helper(total_count=0, keep=0, threshold=None) is False


def test_threshold_zero_disables_archive():
    """RDDF_AUTO_ARCHIVE_THRESHOLD=0 -> never archive regardless of count."""
    assert _invoke_helper(total_count=100, keep=10, threshold=0) is False
    assert _invoke_helper(total_count=15, keep=10, threshold=0) is False


def test_threshold_override_respected():
    """Custom threshold = 20, so 19 < 20, 20 >= 20 triggers."""
    assert _invoke_helper(total_count=19, keep=10, threshold=20) is False
    assert _invoke_helper(total_count=20, keep=10, threshold=20) is True


def test_negative_values_treated_as_disabled():
    """Defensive: negative keep or threshold treated as 0 (disabled)."""
    # Note: bash arithmetic handles negative naturally, but contract is
    # "0 means disabled". Helper should clamp negatives to 0.
    assert _invoke_helper(total_count=100, keep=-5, threshold=None) is False
    assert _invoke_helper(total_count=100, keep=10, threshold=-3) is False


def test_below_keep_count_never_triggers():
    """When total count is below keep (no archive possible), never trigger."""
    # If only 5 sessions and keep=10, archive would be empty -> no-op anyway.
    # Helper should not trigger.
    assert _invoke_helper(total_count=5, keep=10, threshold=None) is False
    assert _invoke_helper(total_count=10, keep=10, threshold=None) is False


def _terminal_session(index: int):
    return {
        "session_id": f"rds_{index:012x}",
        "kind": "stage_arch",
        "owner_opencode_session_id": "prev_owner",
        "state": "completed",
        "started_at": "2026-07-01T00:00:00",
        "last_heartbeat": "2026-07-01T01:00:00",
        "ended_at": "2026-07-01T02:00:00",
        "goal": {"intent": "guide-arch"},
        "attached_changes": [],
        "context_pointer": None,
        "end_reason": "arch-done",
    }


def test_auto_archive_invokes_archive_history_when_triggered(tmp_path, monkeypatch):
    """When threshold met, helper invokes coord.archive_history(keep)."""
    # Setup: fake sessions.json with 20 terminal sessions (>= keep+5=15 threshold)
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        json.dumps({"version": 1, "sessions": [_terminal_session(i) for i in range(20)]})
    )

    # Patch env so hook can locate sessions.json
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("RDDF_AUTO_ARCHIVE_KEEP", raising=False)
    monkeypatch.delenv("RDDF_AUTO_ARCHIVE_THRESHOLD", raising=False)

    # Invoke helper via bash
    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    # Should succeed (exit 0) — best-effort, swallows errors but success path is 0
    assert result.returncode == 0, f"stderr: {result.stderr.decode()}"
    # sessions.json should have been updated (archive-history wrote new state)
    data_after = json.loads(sessions_file.read_text())
    # After archive_history(keep=10): terminal sessions kept = min(20, 10) = 10
    assert len(data_after["sessions"]) <= 10, (
        f"Expected <=10 sessions after archive, got {len(data_after['sessions'])}"
    )


def test_auto_archive_silent_when_below_threshold(tmp_path, monkeypatch):
    """When below threshold, helper does not touch sessions.json."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    original_data = {"version": 1, "sessions": [_terminal_session(i) for i in range(8)]}
    sessions_file.write_text(json.dumps(original_data))

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    assert result.returncode == 0
    # sessions.json unchanged
    data_after = json.loads(sessions_file.read_text())
    assert len(data_after["sessions"]) == 8


def test_auto_archive_swallows_errors(tmp_path, monkeypatch):
    """When archive fails (corrupt file), helper exits 0 and stderr prints warning."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    # Corrupt JSON to force archive_history to fail
    sessions_file.write_text("{this is not valid json")

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    # best-effort: even on failure, exit 0
    assert result.returncode == 0
    # stderr should contain a warning
    err = result.stderr.decode()
    assert "auto-archive" in err.lower() or "skip" in err.lower(), (
        f"Expected warning in stderr, got: {err}"
    )
