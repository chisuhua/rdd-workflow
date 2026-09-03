"""Tests for rdd_arch_status — arch-handoff + planner-feedback aggregator.

Stage 3 Change 4: rdd-arch Phase 1 reads .planner-feedback.json (planner-owned)
and surfaces stale indicator + open counts. Aggregates with .arch-handoff.json.
"""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


class TestRddArchStatus:
    def test_status_includes_planner_summary_when_feedback_exists(self, tmp_repo):
        """status() returns planner open counts + total when .planner-feedback.json present."""
        from _lib.rdd_arch_status import build_arch_status
        feedback_path = Path(tmp_repo) / ".rddf" / "state" / ".planner-feedback.json"
        feedback_path.write_text(json.dumps({
            "schema": "planner-feedback-v1",
            "version": 1,
            "feedbacks": [
                {"feedback_id": "pf-1", "kind": "coverage_gap", "severity": "critical",
                 "status": "open", "fingerprint": "a", "proposal": "p1", "theme": "",
                 "related_adr_ids": [], "message": "", "suggested_action": "",
                 "created_at": "2026-09-03T00:00:00Z",
                 "last_seen_at": "2026-09-03T00:00:00Z",
                 "acknowledged_at": None, "resolved_at": None, "resolved_by": None,
                 "dismissed_at": None, "dismissed_by": None, "computed_from": {},
                 "stale": False},
            ],
            "summary": {"open_critical": 1, "open_warning": 0, "open_info": 0,
                        "acknowledged": 0, "resolved": 0, "dismissed": 0},
            "codebase_commit": "abc123",
            "branch": "master",
        }))
        status = build_arch_status(tmp_repo)
        assert status["planner"]["open_critical"] == 1
        assert status["planner"]["open_total"] == 1

    def test_status_works_when_no_planner_feedback(self, tmp_repo):
        """status() returns planner=None when no .planner-feedback.json."""
        from _lib.rdd_arch_status import build_arch_status
        status = build_arch_status(tmp_repo)
        assert status["planner"] is None

    def test_status_one_line_summary_includes_planner_counts(self, tmp_repo):
        """format_status_line() shows 'N critical, M warning, K stale' when feedback present."""
        from _lib.rdd_arch_status import build_arch_status, format_status_line
        feedback_path = Path(tmp_repo) / ".rddf" / "state" / ".planner-feedback.json"
        feedback_path.write_text(json.dumps({
            "schema": "planner-feedback-v1",
            "version": 1,
            "feedbacks": [
                {"feedback_id": "pf-1", "kind": "coverage_gap", "severity": "critical",
                 "status": "open", "fingerprint": "a", "proposal": "p1", "theme": "",
                 "related_adr_ids": [], "message": "", "suggested_action": "",
                 "created_at": "2026-09-03T00:00:00Z",
                 "last_seen_at": "2026-09-03T00:00:00Z",
                 "acknowledged_at": None, "resolved_at": None, "resolved_by": None,
                 "dismissed_at": None, "dismissed_by": None, "computed_from": {},
                 "stale": True},
            ],
            "summary": {"open_critical": 1, "open_warning": 0, "open_info": 0,
                        "acknowledged": 0, "resolved": 0, "dismissed": 0},
            "codebase_commit": "abc123",
            "branch": "master",
        }))
        status = build_arch_status(tmp_repo)
        line = format_status_line(status)
        assert "1 critical" in line
        assert "0 warning" in line
        assert "stale" in line.lower() or "1 stale" in line

    def test_status_one_line_summary_clean_when_no_feedback(self, tmp_repo):
        """format_status_line() shows 'No planner feedback' when file absent."""
        from _lib.rdd_arch_status import build_arch_status, format_status_line
        status = build_arch_status(tmp_repo)
        line = format_status_line(status)
        assert "No planner feedback" in line or "0 open" in line

    def test_branch_isolation_status_reads_only_current_branch_feedback(self, tmp_repo):
        """build_arch_status annotates which branch's feedback is being shown."""
        from _lib.rdd_arch_status import build_arch_status
        feedback_path = Path(tmp_repo) / ".rddf" / "state" / ".planner-feedback.json"
        feedback_path.write_text(json.dumps({
            "schema": "planner-feedback-v1",
            "version": 1,
            "branch": "feature-x",
            "feedbacks": [],
            "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0,
                        "acknowledged": 0, "resolved": 0, "dismissed": 0},
        }))
        status = build_arch_status(tmp_repo)
        assert status["planner_branch"] == "feature-x"