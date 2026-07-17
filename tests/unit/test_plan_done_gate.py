"""Unit tests for skills/_lib/plan_done_gate.py"""
import json
import os
import tempfile
from datetime import datetime
import pytest
from skills.guide_plan.scripts import plan_done_gate as pdg


@pytest.fixture
def tmp_repo():
    """Create temporary repo with state dir + active changes."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, ".rddf", "state"))
        # Create 2 active changes, each with the 3 artifacts committed to git
        os.makedirs(os.path.join(tmp, "openspec", "changes", "change-1"))
        os.makedirs(os.path.join(tmp, "openspec", "changes", "change-2"))
        yield tmp


def test_write_plan_handoff_basic(tmp_repo):
    """Writes valid JSON."""
    result = pdg.write_plan_handoff(
        project_root=tmp_repo,
        change_count=2,
        current_change="change-1",
    )
    assert isinstance(result, dict)
    assert result["active_changes"] == 2
    assert result["current_change"] == "change-1"
    assert result["all_artifacts_committed"] is True
    assert result["ship_started_at"] is None
    assert "plan_complete_at" in result
    # File on disk
    path = os.path.join(tmp_repo, ".rddf/state/.plan-handoff.json")
    assert os.path.exists(path)


def test_plan_handoff_change_count(tmp_repo):
    """Sets active_changes to provided count."""
    result = pdg.write_plan_handoff(project_root=tmp_repo, change_count=5, current_change="")
    assert result["active_changes"] == 5


def test_plan_handoff_current_change(tmp_repo):
    """Sets current_change to provided string."""
    result = pdg.write_plan_handoff(
        project_root=tmp_repo, change_count=1, current_change="specific-change"
    )
    assert result["current_change"] == "specific-change"


def test_plan_handoff_empty_changes(tmp_repo):
    """Handles 0 changes (current_change=')."""
    result = pdg.write_plan_handoff(project_root=tmp_repo, change_count=0, current_change="")
    assert result["active_changes"] == 0
    assert result["current_change"] == ""


def test_plan_handoff_complete_at(tmp_repo):
    """Sets plan_complete_at to ISO timestamp."""
    result = pdg.write_plan_handoff(project_root=tmp_repo, change_count=1, current_change="x")
    assert "plan_complete_at" in result
    assert "T" in result["plan_complete_at"]
    assert len(result["plan_complete_at"]) >= 19


def test_plan_handoff_ship_started_at_null(tmp_repo):
    """Initial ship_started_at is null."""
    result = pdg.write_plan_handoff(project_root=tmp_repo, change_count=1, current_change="x")
    assert result["ship_started_at"] is None


def test_plan_handoff_all_artifacts_committed(tmp_repo):
    """all_artifacts_committed is hardcoded True (gating is upstream)."""
    result = pdg.write_plan_handoff(project_root=tmp_repo, change_count=1, current_change="x")
    assert result["all_artifacts_committed"] is True


def test_plan_handoff_file_written(tmp_repo):
    """File is created on disk with valid JSON content."""
    pdg.write_plan_handoff(project_root=tmp_repo, change_count=3, current_change="name")
    path = os.path.join(tmp_repo, ".rddf/state/.plan-handoff.json")
    with open(path) as f:
        content = json.load(f)
    assert content["active_changes"] == 3
    assert content["current_change"] == "name"
