"""Tests for _lib/builder_feedback_router.py."""
import json
import sys

import pytest

sys.path.insert(0, "/workspace/project/rdd-workflow")

from _lib.builder_feedback_router import route_feedback


@pytest.fixture
def project_root(tmp_path):
    rddf_dir = tmp_path / ".rddf" / "state"
    rddf_dir.mkdir(parents=True)
    return tmp_path


class TestRouteFeedback:
    def test_route_ac_fail_promotes(self, project_root):
        entry = {"feedback_id": "fb-1", "kind": "ac-fail", "ref_change": "change-A"}
        result = route_feedback(entry, project_root, accept_builder_source=True)
        assert result["routed_to_planner_feedback"] is True
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert feedback_file.exists()
        data = json.loads(feedback_file.read_text())
        assert data["schema"] == "planner-feedback-v1"
        assert data["version"] == 1
        assert data["owner"] == "rdd-planner"
        assert len(data["feedbacks"]) == 1
        assert data["feedbacks"][0]["feedback_id"] == "fb-1"
        assert data["feedbacks"][0]["from_builder"] is True

    def test_route_non_ac_fail_does_not_promote(self, project_root):
        entry = {"feedback_id": "fb-2", "kind": "rejected", "ref_change": "change-A"}
        result = route_feedback(entry, project_root, accept_builder_source=True)
        assert result["routed_to_planner_feedback"] is False
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert not feedback_file.exists()

    def test_route_ac_fail_accept_false(self, project_root):
        entry = {"feedback_id": "fb-3", "kind": "ac-fail", "ref_change": "change-A"}
        result = route_feedback(entry, project_root, accept_builder_source=False)
        assert result["routed_to_planner_feedback"] is False
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert not feedback_file.exists()

    def test_route_ref_change_mismatch(self, project_root):
        entry = {"feedback_id": "fb-4", "kind": "ac-fail", "ref_change": "change-B"}
        result = route_feedback(entry, project_root, accept_builder_source=True, current_change="change-A")
        assert result["routed_to_planner_feedback"] is False
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert not feedback_file.exists()

    def test_route_ref_change_match(self, project_root):
        entry = {"feedback_id": "fb-5", "kind": "ac-fail", "ref_change": "change-A"}
        result = route_feedback(entry, project_root, accept_builder_source=True, current_change="change-A")
        assert result["routed_to_planner_feedback"] is True
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert feedback_file.exists()

    def test_route_appends_multiple_entries(self, project_root):
        entry1 = {"feedback_id": "fb-6", "kind": "ac-fail", "ref_change": "change-A"}
        entry2 = {"feedback_id": "fb-7", "kind": "ac-fail", "ref_change": "change-A"}
        route_feedback(entry1, project_root, accept_builder_source=True)
        route_feedback(entry2, project_root, accept_builder_source=True)
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        data = json.loads(feedback_file.read_text())
        assert len(data["feedbacks"]) == 2
        assert data["feedbacks"][0]["feedback_id"] == "fb-6"
        assert data["feedbacks"][1]["feedback_id"] == "fb-7"

    def test_route_appends_to_existing_file(self, project_root):
        existing = {
            "schema": "planner-feedback-v1",
            "version": 1,
            "owner": "rdd-planner",
            "feedbacks": [{"feedback_id": "existing-fb", "kind": "info", "from_builder": False}],
            "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0},
        }
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        feedback_file.write_text(json.dumps(existing))
        entry = {"feedback_id": "fb-8", "kind": "ac-fail", "ref_change": "change-A"}
        route_feedback(entry, project_root, accept_builder_source=True)
        data = json.loads(feedback_file.read_text())
        assert len(data["feedbacks"]) == 2
        assert data["feedbacks"][0]["feedback_id"] == "existing-fb"
        assert data["feedbacks"][1]["feedback_id"] == "fb-8"
        assert data["feedbacks"][1]["from_builder"] is True

    def test_route_preserves_schema(self, project_root):
        entry = {"feedback_id": "fb-9", "kind": "ac-fail", "ref_change": "change-A"}
        route_feedback(entry, project_root, accept_builder_source=True)
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        data = json.loads(feedback_file.read_text())
        assert data["schema"] == "planner-feedback-v1"
        assert data["version"] == 1
        assert data["owner"] == "rdd-planner"
        assert "feedbacks" in data
        assert "summary" in data
        assert data["summary"]["open_critical"] == 0
        assert data["summary"]["open_warning"] == 0

    def test_route_marks_from_builder(self, project_root):
        entry = {"feedback_id": "fb-10", "kind": "ac-fail", "ref_change": "change-A"}
        route_feedback(entry, project_root, accept_builder_source=True)
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        data = json.loads(feedback_file.read_text())
        assert data["feedbacks"][0]["from_builder"] is True

    def test_route_no_current_change_means_promote(self, project_root):
        entry = {"feedback_id": "fb-11", "kind": "ac-fail", "ref_change": "anything"}
        result = route_feedback(entry, project_root, accept_builder_source=True, current_change=None)
        assert result["routed_to_planner_feedback"] is True
        feedback_file = project_root / ".rddf" / "state" / ".planner-feedback.json"
        assert feedback_file.exists()
