"""Unit tests for the unified ship-change discovery read-model."""

import json
import subprocess
from pathlib import Path

import pytest

# Skip if the module isn't built yet
pytest.importorskip("skills._lib.discover_ship_changes")


def _make_change(tmp_path: Path, name: str, *, tasks: int = 0, done: int = 0) -> Path:
    change_dir = tmp_path / "openspec" / "changes" / name
    change_dir.mkdir(parents=True)
    tasks_md = change_dir / "tasks.md"
    lines = ["# Tasks\n"]
    for i in range(tasks):
        prefix = "- [x]" if i < done else "- [ ]"
        lines.append(f"{prefix} Task {i}\n")
    tasks_md.write_text("".join(lines))
    return change_dir


def test_disk_only_candidate_marked_needs_reconciliation(tmp_path: Path, monkeypatch):
    _make_change(tmp_path, "alpha", tasks=3, done=1)
    monkeypatch.chdir(tmp_path)
    from skills._lib.discover_ship_changes import discover

    result = discover(tmp_path)
    names = {c.name for c in result}
    assert "alpha" in names
    candidate = next(c for c in result if c.name == "alpha")
    assert candidate.filesystem_present is True
    assert candidate.iteration_status is None
    assert "needs_reconciliation" in candidate.flags


def test_executable_priority_order(tmp_path: Path, monkeypatch):
    """Disk + branch should outrank disk-only."""
    _make_change(tmp_path, "a", tasks=3, done=1)
    _make_change(tmp_path, "b", tasks=3, done=0)
    monkeypatch.chdir(tmp_path)
    # Fake branch for `a` only
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    # Need at least one commit so branches are visible
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "openspec/a"], cwd=tmp_path, check=True)

    from skills._lib.discover_ship_changes import discover

    result = discover(tmp_path)
    names = [c.name for c in result]
    assert names.index("a") < names.index("b")
    candidate_a = next(c for c in result if c.name == "a")
    assert candidate_a.filesystem_present is True
    assert candidate_a.branch == "openspec/a"