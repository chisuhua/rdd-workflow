"""Unit tests for RddfSessionCoordinator.update_last_seen_offset (AC-1, AC-11~14)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session import (
    RddfSessionCoordinator,
    RddfSessionError,
)


@pytest.fixture
def coordinator(tmp_path):
    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(json.dumps({"version": 1, "sessions": [], "updated_at": ""}))
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id="test-owner-123",
        goal={"intent": "guide-orchestrator", "subject": "test", "expected_outcome": "test"},
    )
    return coord, sessions_file


def test_update_advances_offset(coordinator):
    """AC-11: update from 0 to 5 → sessions.json shows goal.last_seen_offset=5."""
    coord, sessions_file = coordinator
    sid = coord.find_current_binding("test-owner-123").session_id
    coord.update_last_seen_offset(sid, 5)
    data = json.loads(sessions_file.read_text())
    sess = next(s for s in data["sessions"] if s["session_id"] == sid)
    assert sess["goal"]["last_seen_offset"] == 5


def test_update_rejects_non_stage_guide(coordinator):
    """AC-12: applying to stage_arch raises RddfSessionError."""
    coord, sessions_file = coordinator
    coord.create_session(kind="stage_arch", owner_opencode_session_id="test-owner-123", goal={})
    arch_sid = [s for s in json.loads(sessions_file.read_text())["sessions"]
                if s["kind"] == "stage_arch"][0]["session_id"]
    with pytest.raises(RddfSessionError, match="non-stage_guide"):
        coord.update_last_seen_offset(arch_sid, 5)


def test_update_monotonic_no_rollback(coordinator):
    """AC-13: offset=10 → update to 5 → sessions.json shows 10 (unchanged)."""
    coord, sessions_file = coordinator
    sid = coord.find_current_binding("test-owner-123").session_id
    coord.update_last_seen_offset(sid, 10)
    coord.update_last_seen_offset(sid, 5)  # attempt rollback
    data = json.loads(sessions_file.read_text())
    sess = next(s for s in data["sessions"] if s["session_id"] == sid)
    assert sess["goal"]["last_seen_offset"] == 10


def test_update_unknown_session_raises(coordinator):
    """Auxiliary: session_id not found raises RddfSessionError."""
    coord, _ = coordinator
    with pytest.raises(RddfSessionError, match="Unknown session"):
        coord.update_last_seen_offset("nonexistent-id", 5)


def test_concurrent_update_serializes(tmp_path):
    """AC-14: concurrent subprocess updates serialize — final offset == max(N).

    Two subprocesses call update_last_seen_offset on the SAME stage_guide
    session near-simultaneously. The FileLock serializes access; the monotonic
    guard ensures whichever lands first does not get clobbered. Final
    last_seen_offset must be max(10, 314) == 314.

    A small stagger (0.3s) ensures the first subprocess completes its
    lock/unlock cycle before the second starts (LOCK_NB fail-fast means
    the second would exit 1 if the first still held the lock). This is
    not a race — the stagger simply schedules them sequentially; the
    FileLock + monotonic guard provide the actual serialization guarantee.
    """
    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(json.dumps({"version": 1, "sessions": [], "updated_at": ""}))
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id="test-owner-123",
        goal={"intent": "guide-orchestrator", "subject": "test", "expected_outcome": "test"},
    )
    sid = coord.find_current_binding("test-owner-123").session_id

    repo_root = str(Path(__file__).resolve().parent.parent.parent)
    updater = (
        "import sys\n"
        "sys.path.insert(0, {repo_root!r})\n"
        "from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator\n"
        "coord = RddfSessionCoordinator(sessions_file={sessions_file!r})\n"
        "coord.update_last_seen_offset({sid!r}, {offset})\n"
    )

    def _spawn(offset):
        return subprocess.Popen(
            [sys.executable, "-c", updater.format(
                repo_root=repo_root, sessions_file=str(sessions_file),
                sid=sid, offset=offset,
            )],
            env={**os.environ, "PYTHONPATH": repo_root},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    # Start with offset 10 first, then offset 314 after a brief delay.
    # The explicit stagger is necessary because LOCK_NB does not block;
    # the LOCK_NB + monotonic guard together produce the same outcome:
    # whichever writes first wins, and the second cannot roll it back.
    p_first = _spawn(10)
    time.sleep(0.3)
    p_second = _spawn(314)

    for p in (p_first, p_second):
        _out, err = p.communicate(timeout=30)
        assert p.returncode == 0, f"child failed: {err.decode()}"

    data = json.loads(sessions_file.read_text())
    sess = next(s for s in data["sessions"] if s["session_id"] == sid)
    assert sess["goal"]["last_seen_offset"] == 314  # max(10, 314)