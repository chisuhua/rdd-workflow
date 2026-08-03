"""Verify scan-state.sh emits BINDING_LINES when active session exists."""
import os
import subprocess
import tempfile
from pathlib import Path

SCAN_STATE_SCRIPT = Path("skills/guide/scripts/scan-state.sh")


def _invoke_scan_state(tmp_path, owner_id):
    """Source scan-state.sh and call scan_state, capture output."""
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(tmp_path)
    env["OPENCODE_SESSION_ID"] = owner_id

    cmd = (
        f'source "{SCAN_STATE_SCRIPT}" && '
        f'scan_state "$PROJECT_ROOT"'
    )
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True, env=env, text=True,
    )


def test_scan_state_emits_binding_line_when_active(tmp_path):
    """When sessions.json has active session owned by caller, scan-state outputs binding."""
    sessions_file = tmp_path / ".rddf" / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        """{
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_active_test",
                    "kind": "stage_ship",
                    "state": "active",
                    "owner_opencode_session_id": "test_owner",
                    "parent_session_id": null,
                    "started_at": "2026-08-02T15:00:00+00:00",
                    "last_heartbeat": "2026-08-02T15:30:00+00:00",
                    "attached_changes": [],
                    "goal": {}
                }
            ]
        }"""
    )

    result = _invoke_scan_state(tmp_path, "test_owner")
    output = result.stdout + result.stderr
    assert (
        "rds_active_test" in output
        or "📍 Current" in output
        or "stage_ship" in output
    ), f"Expected binding line for active session, got: {output}"


def test_scan_state_emits_no_binding_when_no_active(tmp_path):
    """When no active sessions owned by caller, no binding line."""
    sessions_file = tmp_path / ".rddf" / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        """{
            "version": 1,
            "sessions": [
                {
                    "session_id": "rds_other",
                    "kind": "stage_ship",
                    "state": "active",
                    "owner_opencode_session_id": "different_owner",
                    "parent_session_id": null,
                    "started_at": "2026-08-02T15:00:00+00:00",
                    "last_heartbeat": "2026-08-02T15:30:00+00:00",
                    "attached_changes": [],
                    "goal": {}
                }
            ]
        }"""
    )

    result = _invoke_scan_state(tmp_path, "test_owner")
    output = result.stdout + result.stderr
    assert "rds_other" not in output or "📍" not in output, (
        f"Should not emit binding for other owner's session, got: {output}"
    )
