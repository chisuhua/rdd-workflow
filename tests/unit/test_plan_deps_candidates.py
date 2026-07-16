"""Unit tests for skills/_lib/plan_deps_candidates.py"""
import json
import os
import subprocess
import tempfile
from unittest import mock

import pytest
from skills._lib import plan_deps_candidates as pdc


@pytest.fixture
def tmp_repo_with_changes(tmp_path):
    """Create temp repo with git init + 2 committed changes."""
    import subprocess
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

    # Create 2 changes
    changes_dir = tmp_path / "openspec" / "changes"
    for name in ["change-a", "change-b"]:
        change_dir = changes_dir / name
        change_dir.mkdir(parents=True)
        (change_dir / ".openspec.yaml").write_text(f"name: {name}\n")

    # Commit
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    return str(tmp_path)


def test_generate_deps_candidates_basic(tmp_repo_with_changes):
    """Generates valid JSON with 'candidates' key."""
    result = pdc.generate_deps_candidates(tmp_repo_with_changes)
    assert "candidates" in result
    assert isinstance(result["candidates"], list)
    assert "change-a" in result["candidates"]
    assert "change-b" in result["candidates"]


def test_generate_deps_candidates_writes_file(tmp_repo_with_changes):
    """Writes .deps-candidates.json to .rddf/state/."""
    pdc.generate_deps_candidates(tmp_repo_with_changes)
    handoff_path = os.path.join(tmp_repo_with_changes, ".rddf", "state", ".deps-candidates.json")
    assert os.path.exists(handoff_path)
    with open(handoff_path) as f:
        data = json.load(f)
    assert "candidates" in data


def test_generate_deps_candidates_only_committed(tmp_path):
    """Only includes changes committed to HEAD (git show HEAD:)."""
    # Set up git repo
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

    # Create 1 committed change + 1 uncommitted change
    changes_dir = tmp_path / "openspec" / "changes"
    (changes_dir / "committed").mkdir(parents=True)
    (changes_dir / "committed" / ".openspec.yaml").write_text("name: committed\n")
    (changes_dir / "uncommitted").mkdir(parents=True)
    (changes_dir / "uncommitted" / ".openspec.yaml").write_text("name: uncommitted\n")

    # Commit only 'committed'
    subprocess.run(["git", "add", "openspec/changes/committed"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    result = pdc.generate_deps_candidates(str(tmp_path))
    assert "committed" in result["candidates"]
    assert "uncommitted" not in result["candidates"]


def test_generate_deps_candidates_empty_no_changes(tmp_path):
    """Handles empty changes directory."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    result = pdc.generate_deps_candidates(str(tmp_path))
    assert result["candidates"] == []


def test_generate_deps_candidates_no_openspec_dir(tmp_path):
    """Handles missing openspec/changes directory."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    result = pdc.generate_deps_candidates(str(tmp_path))
    assert result["candidates"] == []


def test_generate_deps_candidates_no_git_show_failure_no_crash(tmp_path):
    """If git show fails for a particular change, skip it (don't crash)."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    # No openspec dir at all
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    result = pdc.generate_deps_candidates(str(tmp_path))
    assert isinstance(result["candidates"], list)
