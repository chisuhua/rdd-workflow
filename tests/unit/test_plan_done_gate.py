"""Unit tests for _lib/plan_done_gate.py"""
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


def _write_deps_analysis(project_root, recommendations):
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "deps-analysis.json"), "w") as f:
        json.dump({"execution_mode_recommendations": recommendations}, f)


def test_filters_archived_changes(tmp_path):
    """Only active (non-archive) changes remain in execution_mode_decisions."""
    # Active change dir + archived change dir
    (tmp_path / "openspec" / "changes" / "fix-active").mkdir(parents=True)
    (tmp_path / "openspec" / "changes" / "archive" / "2026-07-31-old-archived").mkdir(parents=True)

    _write_deps_analysis(tmp_path, {
        "fix-active": {"mode": "lightweight", "reason": "ok"},
        "old-archived": {"mode": "worktree", "reason": "stale"},
    })

    decisions = pdg._load_execution_mode_decisions(str(tmp_path))

    assert "fix-active" in decisions
    assert "old-archived" not in decisions


def test_missing_deps_file_returns_empty(tmp_path):
    """Missing deps-analysis.json yields empty dict (unchanged behavior)."""
    assert pdg._load_execution_mode_decisions(str(tmp_path)) == {}


def _write_change_meta(project_root, name, added_at):
    change_dir = os.path.join(project_root, "openspec", "changes", name)
    os.makedirs(change_dir, exist_ok=True)
    with open(os.path.join(change_dir, "proposal.md"), "w") as f:
        f.write("# P")
    with open(os.path.join(change_dir, "design.md"), "w") as f:
        f.write("# D")
    with open(os.path.join(change_dir, "tasks.md"), "w") as f:
        f.write("- [ ] a")


def test_freshness_warning_when_deps_stale(tmp_path, capsys):
    """Plan-done emits a stderr warning when deps-analysis is older than the change."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "deps-analysis.json").write_text(json.dumps({
        "updated_at": "2026-07-01T00:00:00+00:00",
        "execution_mode_recommendations": {},
    }))
    _write_change_meta(str(tmp_path), "alpha", "2026-08-04T00:00:00+00:00")
    # Add roadmap-meta.yaml with newer added_at so the freshness warning fires.
    meta_path = tmp_path / "openspec" / "changes" / "alpha" / "roadmap-meta.yaml"
    meta_path.write_text('added_at: "2026-08-04T00:00:00+00:00"\n')

    pdg._load_execution_mode_decisions(str(tmp_path))
    err = capsys.readouterr().err
    assert "deps-analysis" in err or "stale" in err or "older" in err


def test_no_warning_when_deps_fresh(tmp_path, capsys):
    """Plan-done stays silent when deps-analysis is newer than the change."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "deps-analysis.json").write_text(json.dumps({
        "updated_at": "2026-08-05T00:00:00+00:00",
        "execution_mode_recommendations": {},
    }))
    _write_change_meta(str(tmp_path), "alpha", "2026-08-04T00:00:00+00:00")
    meta_path = tmp_path / "openspec" / "changes" / "alpha" / "roadmap-meta.yaml"
    meta_path.write_text('added_at: "2026-08-04T00:00:00+00:00"\n')

    pdg._load_execution_mode_decisions(str(tmp_path))
    err = capsys.readouterr().err
    assert err == ""
