"""Unit tests for archive_history archive_orphans semantics.

Covers the proposal scenarios:
- --archive-orphans archives every orphaned session regardless of keep budget
- without --archive-orphans, orphaned sessions stay when total terminal is below keep
"""
import json
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator


def _terminal_session(index: int, state: str) -> dict:
    """Return a minimal valid session dict for the given terminal state."""
    return {
        "session_id": f"rds_{index:012x}",
        "kind": "stage_arch",
        "owner_opencode_session_id": "prev_owner",
        "state": state,
        "started_at": f"2026-07-{index + 1:02d}T00:00:00",
        "last_heartbeat": f"2026-07-{index + 1:02d}T01:00:00",
        "ended_at": f"2026-07-{index + 1:02d}T02:00:00",
        "end_reason": "heartbeat-timeout" if state == "orphaned" else "arch-done",
        "goal": {"intent": "guide-arch"},
        "attached_changes": [],
        "context_pointer": None,
    }


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_archive_orphans_archives_all_orphaned_sessions_regardless_of_keep(coordinator, sessions_file):
    """archive_history(archive_orphans=True) MUST archive every orphaned session even when keep exceeds terminal count."""
    sessions_file.write_text(json.dumps({
        "version": 1,
        "sessions": [_terminal_session(i, "orphaned") for i in range(5)],
    }))
    active_sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_active",
        goal={},
    )

    archived = coordinator.archive_history(keep=20, archive_orphans=True)

    assert archived == 5
    remaining = coordinator.list_sessions()
    assert [s.session_id for s in remaining] == [active_sid]
    assert all(s.state != "orphaned" for s in remaining)


def test_archive_orphans_false_keeps_orphaned_within_keep_budget(coordinator, sessions_file):
    """archive_history(archive_orphans=False) MUST keep orphaned sessions when total terminal count is below keep."""
    sessions_file.write_text(json.dumps({
        "version": 1,
        "sessions": [_terminal_session(i, "orphaned") for i in range(5)],
    }))
    active_sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_active",
        goal={},
    )

    archived = coordinator.archive_history(keep=20, archive_orphans=False)

    assert archived == 0
    remaining = coordinator.list_sessions()
    assert len(remaining) == 6  # 5 orphaned + 1 active
    assert active_sid in {s.session_id for s in remaining}
