"""Unit tests for skills/_lib/wave_scheduler.py - auto wave transition detector.

TDD contract: locks the behavior of WaveScheduler which consumes
iteration.json + deps-analysis.json and returns Recommendation list
for changes whose blockers have resolved.
"""
import json
import os
import pytest

from skills._lib.wave_scheduler import Recommendation, WaveScheduler


class TestRecommendationDataclass:
    def test_required_fields_present(self):
        """Recommendation must have: name, current_status, blocked_by,
        blocker_status, wave, reason, source."""
        rec = Recommendation(
            name="change-b",
            current_status="planned",
            blocked_by="change-a",
            blocker_status="archived",
            wave="fill",
            reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )
        assert rec.name == "change-b"
        assert rec.current_status == "planned"
        assert rec.blocked_by == "change-a"
        assert rec.blocker_status == "archived"
        assert rec.wave == "fill"
        assert rec.reason.startswith("blocker")
        assert rec.source == "iteration.blocker"

    def test_wave_must_be_fill_or_ship(self):
        """wave field semantic: 'fill' for planned->propose, 'ship' for proposed->guide-ship."""
        rec = Recommendation(
            name="c", current_status="proposed", blocked_by="a",
            blocker_status="archived", wave="ship",
            reason="r", source="iteration.blocker",
        )
        assert rec.wave == "ship"


class TestWaveSchedulerSkeleton:
    def test_can_instantiate(self):
        """WaveScheduler can be instantiated without args."""
        sched = WaveScheduler()
        assert sched is not None

    def test_detect_unblocked_returns_list(self):
        """detect_unblocked returns a list (empty for empty input)."""
        sched = WaveScheduler()
        result = sched.detect_unblocked({"changes": []})
        assert isinstance(result, list)
        assert result == []


class TestDetectUnblockedPlanned:
    """detect_unblocked for planned status with iteration.blocker field."""

    def test_planned_with_archived_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=archived -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "change-b"
        assert r.current_status == "planned"
        assert r.blocked_by == "change-a"
        assert r.blocker_status == "archived"
        assert r.wave == "fill"
        assert r.source == "iteration.blocker"

    def test_planned_with_completed_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=completed -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].blocker_status == "completed"
        assert recs[0].wave == "fill"

    def test_planned_with_in_worktree_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=in_worktree -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_proposed_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=proposed -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "proposed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_no_blocker_returns_nothing(self):
        """planned + blocker=None -> 0 recs (covered by list_ready_for_fill elsewhere)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z"},
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_missing_blocker_entry_returns_nothing(self):
        """planned + blocker=X but X not in changes -> 0 recs (blocker not yet tracked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "ghost-change",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []
