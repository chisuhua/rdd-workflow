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
