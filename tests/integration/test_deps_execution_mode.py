"""Integration test for deps-driven execution mode decision (ADR-0024).

Tests the complete data flow:
  deps analysis → deps-analysis.json
  → plan-done gate → .plan-handoff.json
  → guide-ship → detect_execution_mode()
"""

import json
import os
import tempfile
from pathlib import Path

from skills.deps.scripts import deps_output as do
from skills.guide_plan.scripts import plan_done_gate as pg


def _create_change(
    project_root: str,
    name: str,
    design_files: int = 0,
    tasks: int = 0,
    has_risky_keyword: bool = False,
):
    """Helper to create a test change directory with artifacts."""
    change_dir = Path(project_root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    
    (change_dir / "proposal.md").write_text(f"# {name}\n\nDescription.\n")
    (change_dir / ".openspec.yaml").write_text("kind: improvement\n")
    
    if design_files > 0:
        design_content = "# Design\n\n"
        for i in range(design_files):
            design_content += f"- Create: file{i}.py\n"
        (change_dir / "design.md").write_text(design_content)
    
    if tasks > 0:
        tasks_content = "# Tasks\n\n"
        for i in range(tasks):
            tasks_content += f"- [ ] Task {i}\n"
        (change_dir / "tasks.md").write_text(tasks_content)
    
    if has_risky_keyword:
        (change_dir / "proposal.md").write_text(
            "# Proposal\n\nThis is a refactor of the system.\n"
        )


def test_full_pipeline_deps_to_ship():
    """Test complete data flow: deps → plan-handoff → ship reads decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "small-change", design_files=1, tasks=2)
        _create_change(tmpdir, "large-change", design_files=8, tasks=10)
        
        changes = [
            {
                "name": "small-change",
                "phase": "v2.1",
                "category": "improvement",
                "status": "ready",
                "parallel_group": 0,
            },
            {
                "name": "large-change",
                "phase": "v2.1",
                "category": "improvement",
                "status": "ready",
                "parallel_group": 1,
            },
        ]
        
        analysis = do.build_analysis(changes, fallback=True, project_root=tmpdir)
        
        assert "execution_mode_recommendations" in analysis
        assert "small-change" in analysis["execution_mode_recommendations"]
        assert "large-change" in analysis["execution_mode_recommendations"]
        assert analysis["execution_mode_recommendations"]["small-change"]["mode"] == "lightweight"
        assert analysis["execution_mode_recommendations"]["large-change"]["mode"] == "worktree"
        
        do.write_analysis(tmpdir, analysis)
        
        handoff = pg.write_plan_handoff(
            project_root=tmpdir,
            change_count=2,
            current_change="small-change",
        )
        
        assert "execution_mode_decisions" in handoff
        assert "small-change" in handoff["execution_mode_decisions"]
        assert "large-change" in handoff["execution_mode_decisions"]
        
        handoff_path = Path(tmpdir) / ".rddf" / "state" / ".plan-handoff.json"
        assert handoff_path.exists()
        
        with open(handoff_path) as f:
            handoff_data = json.load(f)
        
        assert "execution_mode_decisions" in handoff_data
        assert handoff_data["execution_mode_decisions"]["small-change"]["mode"] == "lightweight"


def test_plan_handoff_loads_from_deps_analysis():
    """Test that plan_done_gate reads execution_mode_recommendations from deps-analysis.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "test-change", design_files=1, tasks=2)
        
        changes = [{"name": "test-change", "phase": "v2.1", "status": "ready"}]
        analysis = do.build_analysis(changes, fallback=True, project_root=tmpdir)
        do.write_analysis(tmpdir, analysis)
        
        handoff = pg.write_plan_handoff(
            project_root=tmpdir,
            change_count=1,
            current_change="test-change",
        )
        
        assert handoff["execution_mode_decisions"]["test-change"]["mode"] == "lightweight"


def test_ship_reads_handoff_decision():
    """Test that ship_plan.sh can read execution_mode_decisions from handoff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir) / ".rddf" / "state"
        state_dir.mkdir(parents=True)
        
        handoff_data = {
            "plan_complete_at": "2026-07-24T10:00:00Z",
            "active_changes": 1,
            "all_artifacts_committed": True,
            "ship_started_at": None,
            "current_change": "test-change",
            "execution_mode_decisions": {
                "test-change": {
                    "mode": "lightweight",
                    "reason": "小改动 + 低复杂度",
                    "confidence": "high",
                }
            },
        }
        
        handoff_path = state_dir / ".plan-handoff.json"
        with open(handoff_path, "w") as f:
            json.dump(handoff_data, f)
        
        assert handoff_path.exists()
        
        with open(handoff_path) as f:
            loaded = json.load(f)
        
        assert loaded["execution_mode_decisions"]["test-change"]["mode"] == "lightweight"
