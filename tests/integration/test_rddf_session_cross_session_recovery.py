#!/usr/bin/env python3
"""Cross-session recovery tests for rddf-session.

Tests the session timeout → orphaned session → recovery chain:
1. Session times out (heartbeat expired)
2. Session becomes orphaned (owner_opencode_session_id gone)
3. find_next_recommendation identifies recoverable session
4. transfer_ownership allows new owner to take over
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session import (
    RddfSessionCoordinator,
    HeartbeatConfig,
    RddfSessionError,
)


class TestRddfSessionCrossSessionRecovery:
    """Test session recovery across OpenCode sessions."""

    def test_timeout_makes_session_orphaned(self, tmp_path: Path, monkeypatch):
        """A session with expired heartbeat should be marked as orphaned.

        Steps:
        1. Create session with short heartbeat timeout
        2. Wait for timeout
        3. Verify session status is 'orphaned'
        """
        sessions_file = str(tmp_path / "sessions.json")
        config = HeartbeatConfig(
            timeout_seconds=0.3,
            refresh_threshold_seconds=0.15,
        )

        # Test creates both stage_plan and stage_arch sessions; the
        # stage-level singleton check would otherwise block the second
        # creation. Opt into cross-stage parallelism for this test.
        monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
        coord = RddfSessionCoordinator(sessions_file, config)

        # Create session
        session_id = coord.create_session(
            kind="stage_plan",
            owner_opencode_session_id="owner_A",
            goal={"intent": "guide-plan", "subject": "test"},
        )

        session = coord.find_session(session_id)
        assert session is not None
        assert session.state == "active"

        # Wait for timeout
        time.sleep(0.6)

        # Trigger timeout check
        newly_orphaned = coord.check_heartbeat_timeouts()
        assert session_id in newly_orphaned

        # Verify session status is now orphaned
        session = coord.find_session(session_id)
        assert session is not None
        assert session.state == "orphaned"

    def test_find_next_recommendation_returns_orphaned(self, tmp_path: Path, monkeypatch):
        """find_next_recommendation should return orphaned sessions.

        Steps:
        1. Create multiple sessions
        2. Let some timeout
        3. Call find_next_recommendation
        4. Verify it returns the orphaned session
        """
        sessions_file = str(tmp_path / "sessions.json")
        config = HeartbeatConfig(
            timeout_seconds=0.3,
            refresh_threshold_seconds=0.15,
        )

        coord = RddfSessionCoordinator(sessions_file, config)

        # Create two sessions; opt into cross-stage parallelism for stage_arch
        monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
        session1_id = coord.create_session(
            kind="stage_plan",
            owner_opencode_session_id="owner_A",
            goal={"intent": "guide-plan", "subject": "test1"},
        )
        session2_id = coord.create_session(
            kind="stage_arch",
            owner_opencode_session_id="owner_B",
            goal={"intent": "guide-arch", "subject": "test2"},
        )

        # Refresh session2 to keep it active
        time.sleep(0.2)
        coord.refresh_heartbeat(session2_id)

        # Wait for session1 to timeout
        time.sleep(0.2)

        # Trigger timeout check
        coord.check_heartbeat_timeouts()

        # find_next_recommendation should return session1 (orphaned)
        recommendation = coord.find_next_recommendation()

        assert recommendation is not None
        # Should recommend recovering the timed-out session
        assert recommendation.state == "orphaned"

    def test_transfer_ownership_to_new_session(self, tmp_path: Path):
        """transfer_ownership allows new owner to take over orphaned session.

        Steps:
        1. Create session with owner A
        2. Let it timeout (become orphaned)
        3. Call transfer_ownership with owner B
        4. Verify owner B now owns the session
        """
        sessions_file = str(tmp_path / "sessions.json")
        config = HeartbeatConfig(
            timeout_seconds=0.3,
            refresh_threshold_seconds=0.15,
        )

        coord = RddfSessionCoordinator(sessions_file, config)

        # Create session with owner A
        session_id = coord.create_session(
            kind="stage_plan",
            owner_opencode_session_id="owner_A",
            goal={"intent": "guide-plan", "subject": "test"},
        )

        session = coord.find_session(session_id)
        assert session is not None
        assert session.owner_opencode_session_id == "owner_A"

        # Wait for timeout
        time.sleep(0.4)

        # Trigger timeout check
        coord.check_heartbeat_timeouts()

        # Verify orphaned
        session = coord.find_session(session_id)
        assert session is not None
        assert session.state == "orphaned"

        # Update status back to active before transfer
        coord.update_session_status(session_id, "active")
        coord.refresh_heartbeat(session_id)

        # Transfer to owner B
        coord.transfer_ownership(session_id, "owner_B")

        # Verify owner B now owns the session
        session = coord.find_session(session_id)
        assert session is not None
        assert session.owner_opencode_session_id == "owner_B"
        assert session.state == "active"

    def test_cross_session_recovery_workflow(self, tmp_path: Path):
        """End-to-end cross-session recovery workflow.

        Simulates:
        1. Session created in OpenCode session A
        2. OpenCode session A crashes/times out
        3. User opens new OpenCode session B
        4. Session B discovers orphaned session via find_next_recommendation
        5. Session B takes ownership via transfer_ownership
        """
        sessions_file = str(tmp_path / "sessions.json")
        config = HeartbeatConfig(
            timeout_seconds=0.3,
            refresh_threshold_seconds=0.15,
        )

        coord = RddfSessionCoordinator(sessions_file, config)

        # Step 1: Session created in OpenCode session A
        session_a_id = coord.create_session(
            kind="stage_plan",
            owner_opencode_session_id="opencode_session_A",
            goal={"intent": "guide-plan", "subject": "workflow-recovery"},
        )

        # Step 2: OpenCode session A crashes (simulated by timeout)
        time.sleep(0.4)

        # Trigger timeout check
        newly_orphaned = coord.check_heartbeat_timeouts()
        assert session_a_id in newly_orphaned

        # Step 3: User opens new OpenCode session B
        # Step 4: Session B discovers orphaned session
        recommendation = coord.find_next_recommendation()

        assert recommendation is not None
        assert recommendation.session_id == session_a_id
        assert recommendation.state == "orphaned"

        # Step 5: Session B takes ownership
        # First need to reactivate the orphaned session
        coord.update_session_status(session_a_id, "active")
        coord.refresh_heartbeat(session_a_id)
        coord.transfer_ownership(session_a_id, "opencode_session_B")

        # Verify owner changed
        session = coord.find_session(session_a_id)
        assert session is not None
        assert session.owner_opencode_session_id == "opencode_session_B"
        assert session.state == "active"

        # Step 6: Session B continues work with heartbeat
        coord.refresh_heartbeat(session_a_id)

        # Verify session is healthy
        sessions = coord.list_sessions()
        active = [s for s in sessions if s.state == "active"]

        assert len(active) == 1
        assert active[0].session_id == session_a_id
        assert active[0].owner_opencode_session_id == "opencode_session_B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
