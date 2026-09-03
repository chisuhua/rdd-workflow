"""Tests for planner_feedback.FeedbackEntry model and fingerprint.

Stage 3 Change 2: persistent review-task model. feedback_id/status/severity/
fingerprint/computed_from lifecycle contract per plan v2 §2.2.
"""
import hashlib
from datetime import datetime, timezone

import pytest


class TestFeedbackEntryModel:
    def test_feedback_id_format_pf_dash_dash_dot_underscore(self):
        """Feedback ID follows pf-YYYYMMDD-NNN format."""
        from _lib.planner_feedback import FeedbackEntry
        e = FeedbackEntry(
            feedback_id="pf-20260903-001",
            kind="coverage_gap",
            severity="critical",
            status="open",
            fingerprint="abc123",
            proposal="feat-x",
            theme="t1",
            related_adr_ids=[],
            message="x",
            suggested_action="y",
            created_at="2026-09-03T10:00:00Z",
            last_seen_at="2026-09-03T10:00:00Z",
            acknowledged_at=None,
            resolved_at=None,
            resolved_by=None,
            dismissed_at=None,
            dismissed_by=None,
            computed_from={"planner_state_revision": 1, "arch_handoff_revision": 1, "codebase_commit": "abc"},
        )
        assert e.feedback_id.startswith("pf-")
        parts = e.feedback_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert parts[2].isdigit()

    def test_fingerprint_is_deterministic_for_same_input(self):
        """Same proposal+theme+reason+kind produces same fingerprint."""
        from _lib.planner_feedback import compute_fingerprint
        f1 = compute_fingerprint(
            kind="coverage_gap",
            proposal="feat-foo",
            theme="cross-repo-protocol",
            related_adr_ids=["0030"],
            reason="unmapped",
        )
        f2 = compute_fingerprint(
            kind="coverage_gap",
            proposal="feat-foo",
            theme="cross-repo-protocol",
            related_adr_ids=["0030"],
            reason="unmapped",
        )
        assert f1 == f2
        assert len(f1) == 16  # sha256 truncated to 16 chars

    def test_fingerprint_changes_when_input_changes(self):
        """Different input produces different fingerprint (collision-resistant)."""
        from _lib.planner_feedback import compute_fingerprint
        f1 = compute_fingerprint("coverage_gap", "feat-foo", "t1", ["0030"], "x")
        f2 = compute_fingerprint("coverage_gap", "feat-foo", "t2", ["0030"], "x")
        assert f1 != f2
        f3 = compute_fingerprint("coverage_gap", "feat-bar", "t1", ["0030"], "x")
        assert f1 != f3

    def test_summary_counts_status_groups_correctly(self):
        """Summary reflects current status distribution across feedbacks."""
        from _lib.planner_feedback import FeedbackEntry, compute_summary

        entries = [
            FeedbackEntry("pf-1", "coverage_gap", "critical", "open", "fp1", "p1", "t1", [], "", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", None, None, None, None, None, {}),
            FeedbackEntry("pf-2", "unmapped_proposal", "warning", "open", "fp2", "p2", "t2", [], "", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", None, None, None, None, None, {}),
            FeedbackEntry("pf-3", "adr_drift", "info", "acknowledged", "fp3", "p3", "t3", [], "", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", None, None, None, None, {}),
            FeedbackEntry("pf-4", "coverage_gap", "warning", "resolved", "fp4", "p4", "t4", [], "", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", None, "2026-01-03T00:00:00Z", "architect", None, None, {}),
            FeedbackEntry("pf-5", "coverage_gap", "critical", "dismissed", "fp5", "p5", "t5", [], "", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", None, None, None, "2026-01-04T00:00:00Z", "architect", {}),
        ]
        summary = compute_summary(entries)
        assert summary["open_critical"] == 1
        assert summary["open_warning"] == 1
        assert summary["open_info"] == 0
        assert summary["acknowledged"] == 1
        assert summary["resolved"] == 1
        assert summary["dismissed"] == 1

    def test_severity_must_be_critical_warning_or_info(self):
        """Severity enum locked at v1."""
        from _lib.planner_feedback import FeedbackEntry
        with pytest.raises(ValueError, match="severity"):
            FeedbackEntry(
                feedback_id="pf-bad-001",
                kind="coverage_gap",
                severity="BLOCKER",
                status="open",
                fingerprint="x", proposal="", theme="", related_adr_ids=[],
                message="", suggested_action="",
                created_at="2026-01-01T00:00:00Z", last_seen_at="2026-01-01T00:00:00Z",
                acknowledged_at=None, resolved_at=None, resolved_by=None,
                dismissed_at=None, dismissed_by=None, computed_from={},
            )

    def test_status_must_be_in_lifecycle_enum(self):
        """Status enum: open / acknowledged / resolved / dismissed."""
        from _lib.planner_feedback import FeedbackEntry
        with pytest.raises(ValueError, match="status"):
            FeedbackEntry(
                feedback_id="pf-bad-002",
                kind="coverage_gap",
                severity="info",
                status="WONT_FIX",
                fingerprint="x", proposal="", theme="", related_adr_ids=[],
                message="", suggested_action="",
                created_at="2026-01-01T00:00:00Z", last_seen_at="2026-01-01T00:00:00Z",
                acknowledged_at=None, resolved_at=None, resolved_by=None,
                dismissed_at=None, dismissed_by=None, computed_from={},
            )