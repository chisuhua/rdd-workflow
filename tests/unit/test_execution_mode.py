"""Unit tests for execution mode analysis (ADR-0023)."""

import os
import tempfile
from pathlib import Path

from skills.deps.scripts.deps_output import (
    analyze_execution_mode,
    compute_execution_mode_recommendations,
)


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


def test_analyze_execution_mode_small():
    """Small change (≤2 files, ≤3 tasks) → lightweight."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "small-change", design_files=2, tasks=3)
        rec = analyze_execution_mode("small-change", tmpdir)
        
        assert rec["mode"] == "lightweight"
        assert rec["details"]["change_size"] == "small"
        assert rec["details"]["file_count"] == 2
        assert rec["details"]["task_count"] == 3


def test_analyze_execution_mode_medium():
    """Medium change (3-5 files or 4-6 tasks) → lightweight (per ADR-0023 design)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "medium-change", design_files=4, tasks=5)
        rec = analyze_execution_mode("medium-change", tmpdir)
        
        assert rec["mode"] == "lightweight"  # medium prefers lightweight per proposal
        assert rec["details"]["change_size"] == "medium"


def test_analyze_execution_mode_large():
    """Large change (≥6 files or ≥7 tasks) → worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "large-change", design_files=8, tasks=10)
        rec = analyze_execution_mode("large-change", tmpdir)
        
        assert rec["mode"] == "worktree"
        assert rec["details"]["change_size"] == "large"


def test_analyze_execution_mode_risky_keyword():
    """Risky keywords (refactor, migration, etc.) force worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "risky-change", design_files=1, tasks=1, has_risky_keyword=True)
        rec = analyze_execution_mode("risky-change", tmpdir)
        
        assert rec["mode"] == "worktree"
        assert rec["details"]["is_risky"] is True


def test_compute_execution_mode_recommendations_multiple():
    """Compute recommendations for multiple changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_change(tmpdir, "small-1", design_files=1, tasks=2)
        _create_change(tmpdir, "medium-1", design_files=4, tasks=5)
        
        changes = [
            {"name": "small-1", "phase": "v2.1", "category": "improvement", "status": "ready"},
            {"name": "medium-1", "phase": "v2.1", "category": "improvement", "status": "ready"},
        ]
        
        recs = compute_execution_mode_recommendations(changes, tmpdir)
        
        assert "small-1" in recs
        assert "medium-1" in recs
        assert recs["small-1"]["mode"] == "lightweight"
        assert recs["medium-1"]["mode"] == "lightweight"  # medium prefers lightweight per ADR-0023


def test_compute_execution_mode_recommendations_empty():
    """Empty changes list returns empty dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        recs = compute_execution_mode_recommendations([], tmpdir)
        assert recs == {}
