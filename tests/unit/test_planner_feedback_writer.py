"""Tests for planner_feedback compute/write/lifecycle operations.

Stage 3 Change 2: persistent review-task storage layer at
.rddf/state/.planner-feedback.json (planner owns).
"""
import json
import os
import subprocess

import pytest


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a minimal project with .rddf/state dir."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


class TestPlannerFeedbackWriter:
    def test_write_uses_filelock_and_atomic(self, tmp_repo):
        """write_planner_feedback uses FileLock + atomic_write_json."""
        from _lib.planner_feedback import write_planner_feedback, read_planner_feedback
        data = {
            "schema": "planner-feedback-v1",
            "version": 1,
            "owner": "rdd-planner",
            "branch": "master",
            "worktree_root": tmp_repo,
            "codebase_commit": "abc123",
            "arch_handoff_revision": 0,
            "planner_state_last_sync_at": "2026-09-03T10:00:00Z",
            "feedbacks": [],
            "summary": {
                "open_critical": 0, "open_warning": 0, "open_info": 0,
                "acknowledged": 0, "resolved": 0, "dismissed": 0,
            },
        }
        write_planner_feedback(tmp_repo, data)
        lock = os.path.join(tmp_repo, ".rddf", "state", ".planner-feedback.json.lock")
        assert os.path.exists(lock), "FileLock file must be created"
        loaded = read_planner_feedback(tmp_repo)
        assert loaded["version"] == 1
        assert loaded["owner"] == "rdd-planner"

    def test_compute_planner_feedback_creates_entry_for_unmapped(self, tmp_repo):
        """compute_planner_feedback scans improvements + ADR + roadmap → emits coverage_gap."""
        from _lib.planner_feedback import compute_planner_feedback, read_planner_feedback
        improvements = tmp_repo + "/.rddf/improvements"
        os.makedirs(improvements)
        with open(os.path.join(improvements, "feat-foo.md"), "w") as f:
            f.write("---\nname: feat-foo\npriority: P1\n---\n# feat-foo\n")
        result = compute_planner_feedback(tmp_repo)
        assert result["feedbacks"], "compute must emit feedback for unmapped P1 proposal"
        kinds = {f["kind"] for f in result["feedbacks"]}
        assert "unmapped_proposal" in kinds or "coverage_gap" in kinds

    def test_compute_planner_feedback_idempotent_on_same_input(self, tmp_repo):
        """Two compute calls with same input produce same fingerprint (no duplicate entries)."""
        from _lib.planner_feedback import compute_planner_feedback
        improvements = tmp_repo + "/.rddf/improvements"
        os.makedirs(improvements)
        with open(os.path.join(improvements, "feat-foo.md"), "w") as f:
            f.write("---\nname: feat-foo\npriority: P1\n---\n# feat-foo\n")
        r1 = compute_planner_feedback(tmp_repo)
        r2 = compute_planner_feedback(tmp_repo)
        assert len(r1["feedbacks"]) == len(r2["feedbacks"])
        fps1 = sorted(f["fingerprint"] for f in r1["feedbacks"])
        fps2 = sorted(f["fingerprint"] for f in r2["feedbacks"])
        assert fps1 == fps2

    def test_compute_planner_feedback_handles_missing_handoff(self, tmp_repo):
        """If .arch-handoff.json absent, compute still runs (computed_from reflects it)."""
        from _lib.planner_feedback import compute_planner_feedback
        result = compute_planner_feedback(tmp_repo)
        assert result["feedbacks"] == []
        assert result["arch_handoff_revision"] == 0

    def test_compute_planner_feedback_does_not_mark_stale_on_commit_mismatch_only(self, tmp_repo):
        """codebase_commit change alone (revisions unchanged) does NOT trigger stale.

        stale = arch_handoff_revision OR state_revision mismatch.
        codebase_commit is informational metadata only (Wave 4 redesign;
        eliminates Stage 3 doc-only-commit noise).
        """
        from _lib.planner_feedback import (
            compute_planner_feedback, write_planner_feedback,
        )
        improvements = tmp_repo + "/.rddf/improvements"
        os.makedirs(improvements)
        with open(os.path.join(improvements, "feat-foo.md"), "w") as f:
            f.write("---\nname: feat-foo\npriority: P1\n---\n# feat-foo\n")

        r1 = compute_planner_feedback(tmp_repo, codebase_commit="abc123")
        write_planner_feedback(tmp_repo, r1)

        r2 = compute_planner_feedback(tmp_repo, codebase_commit="def456")
        stale = [f for f in r2["feedbacks"] if f.get("stale")]
        assert not stale, (
            "codebase_commit change alone (revisions unchanged) must NOT "
            "trigger stale — Wave 4 2-revision redesign"
        )

    def test_compute_planner_feedback_handles_corrupted_feedback_file(self, tmp_repo):
        """If .planner-feedback.json exists but is corrupted, compute rebuilds from scratch."""
        from _lib.planner_feedback import compute_planner_feedback
        feedback_path = os.path.join(tmp_repo, ".rddf", "state", ".planner-feedback.json")
        with open(feedback_path, "w") as f:
            f.write("{ this is not valid json")
        result = compute_planner_feedback(tmp_repo)
        assert "feedbacks" in result
        assert "summary" in result