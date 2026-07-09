"""Integration tests for rddf-session — full lifecycle, cross-opencode-session recovery, worktree-decoupling."""
import json
import subprocess
from pathlib import Path

import pytest

from skills._lib.rddf_session import RddfSessionCoordinator, ConflictError


@pytest.fixture
def project_root(tmp_path):
    """Create a minimal git repo with .rddf/state/ directory."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_full_lifecycle(project_root):
    """Create -> heartbeat refresh -> completion -> cross-opencode-session read."""
    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    # 1. Create
    sid = coord.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_owner1",
        goal={"intent": "guide-plan", "subject": "change-x"},
    )
    assert sessions_file.exists()

    # 2. Heartbeat refresh
    coord.refresh_heartbeat(sid)
    found = coord.find_session(sid)
    assert found is not None
    assert found.state == "active"

    # 3. Complete
    coord.update_session_status(sid, "completed", end_reason="plan-done")

    # 4. Read from different opencode session
    coord2 = RddfSessionCoordinator(sessions_file=str(sessions_file))
    found = coord2.find_session(sid)
    assert found is not None
    assert found.state == "completed"
    assert found.end_reason == "plan-done"


def test_cross_opencode_session_conflict_soft_prompt(project_root):
    """Two opencode sessions creating same kind MUST trigger 4-option soft prompt logic."""
    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord_a = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid_a = coord_a.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_session_a",
        goal={"intent": "guide-plan"},
    )

    # Session B attempts to create
    coord_b = RddfSessionCoordinator(sessions_file=str(sessions_file))
    with pytest.raises(ConflictError):
        coord_b.create_session(
            kind="stage_plan",
            owner_opencode_session_id="ses_session_b",
            goal={"intent": "guide-plan"},
        )

    # User selects "transfer ownership" (option 2)
    coord_b.transfer_ownership(sid_a, "ses_session_b")

    # Session B retries — should succeed (same owner now)
    sid_b_retry = coord_b.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_session_b",
        goal={"intent": "guide-plan"},
    )
    assert sid_b_retry == sid_a  # same session id


def test_worktree_decoupling(project_root):
    """rddf-session MUST NOT contain worktree_path field, even after worktree creation."""
    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sid = coord.create_session(
        kind="stage_ship",
        owner_opencode_session_id="ses_x",
        goal={"intent": "guide-ship", "subject": "change-y"},
    )

    # Simulate worktree creation (no rddf-session impact)
    wt_path = project_root / ".rddf" / "wt" / "change-y"
    wt_path.mkdir(parents=True)

    # rddf-session MUST NOT have worktree_path
    found = coord.find_session(sid)
    assert not hasattr(found, "worktree_path")
    data = json.loads(sessions_file.read_text())
    assert "worktree_path" not in data["sessions"][0]


def test_orphaned_recovery(project_root):
    """orphaned session MUST be resumable via resume subcommand."""
    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sid = coord.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_old",
        goal={"intent": "guide-plan"},
    )

    # Simulate timeout (backdate)
    data = json.loads(sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    sessions_file.write_text(json.dumps(data))

    coord.check_heartbeat_timeouts()
    found = coord.find_session(sid)
    assert found is not None
    assert found.state == "orphaned"

    # Resume
    coord.update_session_status(sid, "active")
    coord.transfer_ownership(sid, "ses_new")

    found = coord.find_session(sid)
    assert found is not None
    assert found.state == "active"
    assert found.owner_opencode_session_id == "ses_new"


def test_history_archive(project_root):
    """archive_history MUST move old terminal sessions to .archive.json."""
    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sids = []
    for i in range(5):
        sid = coord.create_session(
            kind="stage_arch",
            owner_opencode_session_id=f"ses_{i}",
            goal={"intent": "guide-arch", "subject": f"c-{i}"},
        )
        sids.append(sid)
        # Complete first 4 immediately so next create does not conflict
        if i < 4:
            coord.update_session_status(sid, "completed", end_reason="x")

    archived = coord.archive_history(keep=2)
    assert archived == 2

    main_count = len(coord.list_sessions())
    assert main_count == 3  # 2 recent completed + 1 active

    archive_file = sessions_file.with_suffix(".archive.json")
    assert archive_file.exists()
    archive_data = json.loads(archive_file.read_text())
    assert len(archive_data["sessions"]) == 2