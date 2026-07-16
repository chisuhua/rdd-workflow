"""Unit tests for skills/_lib/update_roadmap_progress.py"""
import os
import json
import tempfile
import pytest
from skills._lib import update_roadmap_progress as urmp


@pytest.fixture
def tmp_repo(tmp_path):
    """Create temp repo with roadmap-state.json and roadmap-meta.yaml."""
    # Create .rddf/state/roadmap-state.json
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "roadmap-state.json"
    state_file.write_text(json.dumps({
        "phases": {
            "phase-1": {
                "categories": {
                    "general": {
                        "changes": ["test-change", "other-change"],
                        "completed_changes": []
                    }
                },
                "gate_status": {"all_changes_complete": False}
            }
        }
    }))

    # Create openspec/changes/test-change/roadmap-meta.yaml
    change_dir = tmp_path / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    meta_file = change_dir / "roadmap-meta.yaml"
    meta_file.write_text("""roadmap:
  phase: "phase-1"
  category: "general"
  priority: "P1"
  gate_checklist: []
  cross_phase_deps: []
  category_validation:
    valid: true
    reason: ""
""")

    return str(tmp_path)


def test_update_roadmap_progress_basic(tmp_repo):
    """Updates roadmap-state.json with completed change."""
    result = urmp.update_roadmap_progress(tmp_repo, "test-change")
    assert result["change_name"] == "test-change"
    assert result["phase"] == "phase-1"
    assert result["category"] == "general"
    assert "test-change" in result["completed_changes"]


def test_update_roadmap_progress_writes_state_file(tmp_repo):
    """Writes updated roadmap-state.json."""
    urmp.update_roadmap_progress(tmp_repo, "test-change")

    state_path = os.path.join(tmp_repo, ".rddf", "state", "roadmap-state.json")
    with open(state_path) as f:
        state = json.load(f)
    cat_data = state["phases"]["phase-1"]["categories"]["general"]
    assert "test-change" in cat_data["completed_changes"]


def test_update_roadmap_progress_idempotent(tmp_repo):
    """Calling twice does not duplicate the entry."""
    urmp.update_roadmap_progress(tmp_repo, "test-change")
    urmp.update_roadmap_progress(tmp_repo, "test-change")

    state_path = os.path.join(tmp_repo, ".rddf", "state", "roadmap-state.json")
    with open(state_path) as f:
        state = json.load(f)
    cat_data = state["phases"]["phase-1"]["categories"]["general"]
    assert cat_data["completed_changes"].count("test-change") == 1


def test_update_roadmap_progress_all_complete_detection(tmp_repo):
    """Detects when all changes in a phase are complete."""
    # Add other-change to completed first, then complete test-change
    state_path = os.path.join(tmp_repo, ".rddf", "state", "roadmap-state.json")
    with open(state_path) as f:
        state = json.load(f)
    state["phases"]["phase-1"]["categories"]["general"]["completed_changes"] = ["other-change"]
    with open(state_path, "w") as f:
        json.dump(state, f)

    result = urmp.update_roadmap_progress(tmp_repo, "test-change")
    assert result["all_changes_complete"] is True  # both done


def test_update_roadmap_progress_not_all_complete(tmp_repo):
    """Returns all_changes_complete=False when other changes remain."""
    result = urmp.update_roadmap_progress(tmp_repo, "test-change")
    assert result["all_changes_complete"] is False  # other-change still pending


def test_update_roadmap_progress_missing_state_file(tmp_path):
    """Gracefully handles missing roadmap-state.json (returns error)."""
    # Create roadmap-meta.yaml (required) but NOT roadmap-state.json
    change_dir = tmp_path / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "roadmap-meta.yaml").write_text("""roadmap:
  phase: "phase-1"
  category: "general"
""")
    result = urmp.update_roadmap_progress(str(tmp_path), "test-change")
    assert "error" in result
    assert "roadmap-state.json" in result["error"]


def test_update_roadmap_progress_missing_meta_file(tmp_repo):
    """Gracefully handles missing roadmap-meta.yaml (returns error)."""
    # Remove the meta file
    os.remove(os.path.join(tmp_repo, "openspec", "changes", "test-change", "roadmap-meta.yaml"))
    result = urmp.update_roadmap_progress(tmp_repo, "test-change")
    assert "error" in result
    assert "roadmap-meta" in result["error"]