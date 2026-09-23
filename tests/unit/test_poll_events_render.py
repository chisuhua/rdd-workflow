"""Behavior tests for rddf_session_hook_poll_events (AC-3, AC-4, AC-5).

Exercises the real bash function via subprocess against a fake project root
whose skills/ tree is symlinked to the real repo. The function's internal
PYTHONPATH="$project_root" python3 calls resolve imports through the symlink.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"
POLL_CMD = (
    f"source '{HOOKS_SH}'; "
    "rddf_session_hook_poll_events"
)


@pytest.fixture
def fake_project(tmp_path):
    """Fake project root with importable skills/ symlink and empty state dir.

    The skills/ tree is symlinked to the real repo so that
    PYTHONPATH="$project_root" python3 calls (used inside the hook function)
    can resolve ``from skills.rddf_session.scripts...`` imports.
    """
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / "skills").symlink_to(REPO_ROOT / "skills", target_is_directory=True)
    return tmp_path


def _make_guide_session(fake_project, owner="test-owner"):
    """Create an active stage_guide session at last_seen_offset=0."""
    from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
    sessions_file = fake_project / ".rddf" / "state" / "sessions.json"
    sessions_file.write_text(json.dumps({"version": 1, "sessions": [], "updated_at": ""}))
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid = coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id=owner,
        goal={
            "intent": "guide-orchestrator",
            "subject": "test",
            "expected_outcome": "test",
            "last_seen_offset": 0,
        },
    )
    return sessions_file, sid


def _write_events(fake_project, count=3, owner="test-owner", sid="rds_test"):
    """Write N events to events.jsonl using EventsLog (matches real schema)."""
    from skills.rddf_session.scripts.events_log import EventsLog
    events_file = fake_project / ".rddf" / "state" / "events.jsonl"
    el = EventsLog(str(events_file))
    for i in range(count):
        el.append_event(
            event_type="phase_started",
            severity="info",
            message=f"child progress message {i}",
            session_id=sid,
            kind="stage_arch",
            owner_opencode_session_id=owner,
        )
    return events_file


def _run_poll(fake_project, owner="test-owner"):
    """Run rddf_session_hook_poll_events as a subprocess and return CompletedProcess."""
    env = {**os.environ, "PROJECT_ROOT": str(fake_project), "OPENCODE_SESSION_ID": owner}
    return subprocess.run(
        ["bash", "-c", POLL_CMD],
        capture_output=True, text=True, env=env,
    )


def _offset_from_file(sessions_file) -> int:
    data = json.loads(sessions_file.read_text())
    sess = data["sessions"][0]
    return sess["goal"].get("last_seen_offset", -1)


class TestPollEventsRender:
    """Real behavior tests (replaces the old fixture-only smoke test)."""

    def test_poll_reads_events_since_offset(self, fake_project):
        """AC-3: reads events from offset 0 and renders child progress to stdout."""
        sessions_file, sid = _make_guide_session(fake_project)
        _write_events(fake_project, count=3, sid=sid)

        res = _run_poll(fake_project)

        assert res.returncode == 0, f"poll_events failed: {res.stderr}"
        assert "📊 Child Sessions:" in res.stdout
        assert "child progress message 0" in res.stdout
        assert "child progress message 2" in res.stdout

    def test_poll_advances_offset(self, fake_project):
        """AC-5: after reading 3 events from offset 0, last_seen_offset == 3."""
        sessions_file, sid = _make_guide_session(fake_project)
        _write_events(fake_project, count=3, sid=sid)

        res = _run_poll(fake_project)
        assert res.returncode == 0, f"poll_events failed: {res.stderr}"

        assert _offset_from_file(sessions_file) == 3

    def test_poll_no_events_skips(self, fake_project):
        """Best-effort: missing events.jsonl -> silent success, no output, offset unchanged."""
        sessions_file, _ = _make_guide_session(fake_project)

        res = _run_poll(fake_project)

        assert res.returncode == 0
        assert "📊 Child Sessions:" not in res.stdout
        assert _offset_from_file(sessions_file) == 0