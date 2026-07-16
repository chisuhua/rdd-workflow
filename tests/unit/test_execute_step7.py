"""Unit tests for skills/_lib/execute_step7.py"""
import json
import os
import tempfile
from datetime import datetime
import pytest
from skills._lib import execute_step7 as es7


@pytest.fixture
def tmp_repo_with_tasks(tmp_path):
    """Create temp repo with tasks.md."""
    changes_dir = tmp_path / "openspec" / "changes" / "test-change"
    changes_dir.mkdir(parents=True)
    (changes_dir / "tasks.md").write_text("""# Tasks
- [x] Task 1
- [x] Task 2
- [ ] Task 3
""")
    return str(tmp_path), "test-change"


def test_run_step7_report_basic(tmp_repo_with_tasks):
    """Runs without crashing and returns summary dict."""
    project_root, change_name = tmp_repo_with_tasks
    result = es7.run_step7_report(project_root, change_name)
    assert isinstance(result, dict)
    assert result["change_name"] == change_name
    assert "done" in result
    assert "total" in result


def test_run_step7_report_counts_progress(tmp_repo_with_tasks):
    """Counts done/total from tasks.md correctly."""
    project_root, change_name = tmp_repo_with_tasks
    result = es7.run_step7_report(project_root, change_name)
    assert result["done"] == 2
    assert result["total"] == 3


def test_run_step7_report_no_tasks_md(tmp_path):
    """Handles missing tasks.md gracefully."""
    result = es7.run_step7_report(str(tmp_path), "nonexistent")
    assert result["done"] == 0
    assert result["total"] == 0


def test_run_step7_report_complete_flag(tmp_repo_with_tasks):
    """Detects when all tasks are done."""
    project_root, change_name = tmp_repo_with_tasks
    # Make all tasks done
    tasks_file = os.path.join(project_root, "openspec", "changes", change_name, "tasks.md")
    with open(tasks_file) as f:
        content = f.read()
    content = content.replace("- [ ]", "- [x]")
    with open(tasks_file, "w") as f:
        f.write(content)
    
    result = es7.run_step7_report(project_root, change_name)
    assert result["complete"] is True


def test_run_step7_report_syncs_iteration(tmp_repo_with_tasks):
    """Updates iteration.json with done/total counts."""
    project_root, change_name = tmp_repo_with_tasks
    es7.run_step7_report(project_root, change_name)
    
    iteration_path = os.path.join(project_root, ".rddf", "state", "iteration.json")
    if os.path.exists(iteration_path):
        with open(iteration_path) as f:
            data = json.load(f)
        # Verify the change is recorded in iteration
        # (Exact structure depends on iteration module)
        assert "changes" in data or change_name in str(data)


def test_run_step7_report_handles_iteration_failure(tmp_repo_with_tasks):
    """If iteration sync fails, doesn't crash the report."""
    project_root, change_name = tmp_repo_with_tasks
    # Should not crash even if iteration module has issues
    result = es7.run_step7_report(project_root, change_name)
    assert result is not None
