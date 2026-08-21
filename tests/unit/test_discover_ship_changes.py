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


def test_archived_change_excluded_from_handoff(tmp_path: Path, monkeypatch):
    """An entry in archived_changes must not appear as a candidate."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".plan-handoff.json").write_text(json.dumps({
        "current_change": "alpha",
        "committed_changes": ["alpha", "beta"],
        "archived_changes": ["alpha"],
    }))
    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    names = {c.name for c in result}
    assert "alpha" not in names
    assert "beta" in names


def test_branch_only_archived_is_filtered(tmp_path: Path, monkeypatch):
    """A residual openspec/<name> branch whose name is in archived_changes
    must not surface as a candidate."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".plan-handoff.json").write_text(json.dumps({
        "archived_changes": ["stale-branch"],
    }))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-q", "-m", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "openspec/stale-branch"], cwd=tmp_path, check=True)

    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    assert all(c.name != "stale-branch" for c in result)


def test_malformed_iteration_entry_skipped(tmp_path: Path, monkeypatch):
    """iteration.json entries missing 'name' must not crash discover."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / "iteration.json").write_text(json.dumps({
        "changes": [{"status": "proposed"}, {"name": "good", "status": "proposed"}],
    }))
    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    assert any(c.name == "good" for c in result)


def test_empty_repo_returns_empty_list(tmp_path: Path, monkeypatch):
    """A repo with no changes at all must return [] without raising."""
    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    assert result == []


def test_malformed_state_json_is_tolerated(tmp_path: Path, monkeypatch):
    """Malformed .plan-handoff.json / iteration.json must be ignored, not crash."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".plan-handoff.json").write_text("{not json")
    (state / "iteration.json").write_text("not json at all")
    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    assert result == []


def test_invalid_change_name_filtered(tmp_path: Path, monkeypatch):
    """Directories with names that could cause option-injection are filtered."""
    bad = tmp_path / "openspec" / "changes" / "--evil"
    bad.mkdir(parents=True)
    (bad / "tasks.md").write_text("- [x] x\n")
    good = tmp_path / "openspec" / "changes" / "alpha"
    good.mkdir(parents=True)
    (good / "tasks.md").write_text("- [x] x\n")
    from skills._lib.discover_ship_changes import discover
    result = discover(tmp_path)
    names = {c.name for c in result}
    assert "alpha" in names
    assert "--evil" not in names


def test_is_valid_change_name_accepts_typical_names():
    from skills._lib.discover_ship_changes import is_valid_change_name
    assert is_valid_change_name("alpha")
    assert is_valid_change_name("fix-rddf-init")
    assert is_valid_change_name("v2.0.1")
    assert not is_valid_change_name("")
    assert not is_valid_change_name("--evil")
    assert not is_valid_change_name("../../etc")
    assert not is_valid_change_name("-leading-dash")


# --- fix-discover-ship-changes-needs-planning-fallback: _classify regression ---

def test_classify_approved_missing_disk_only():
    """approved + filesystem_present=False → only missing_disk (NOT needs_planning).

    Regression: pre-fix bug appended needs_planning to flags for any
    filesystem_present=False + non-worktree/branch candidate. This caused
    ship menu to surface already-implemented proposals as actionable work.
    """
    from skills._lib.discover_ship_changes import Candidate, _classify
    cand = Candidate(name="x", filesystem_present=False, iteration_status="approved")
    _classify(cand)
    assert cand.flags == ["missing_disk"], (
        f"approved candidate should only carry missing_disk, got {cand.flags}"
    )


def test_classify_archived_missing_disk_only():
    """archived + filesystem_present=False → only missing_disk (NOT needs_planning).

    Most common post-archive case: openspec/changes/<name>/ deleted by
    'openspec archive', iteration.json updated to status="archived".
    Should not re-surface in ship menu.
    """
    from skills._lib.discover_ship_changes import Candidate, _classify
    cand = Candidate(name="x", filesystem_present=False, iteration_status="archived")
    _classify(cand)
    assert cand.flags == ["missing_disk"], (
        f"archived candidate should only carry missing_disk, got {cand.flags}"
    )


def test_classify_proposed_needs_planning():
    """proposed + filesystem_present=False → needs_planning preserved.

    Existing behavior must NOT regress: a proposed change without disk
    artifacts is a real "needs planning" candidate.
    """
    from skills._lib.discover_ship_changes import Candidate, _classify
    cand = Candidate(name="x", filesystem_present=False, iteration_status="proposed")
    _classify(cand)
    assert "missing_disk" in cand.flags, (
        f"missing_disk should be present, got {cand.flags}"
    )
    assert "needs_planning" in cand.flags, (
        f"needs_planning should be present, got {cand.flags}"
    )


def test_classify_planned_needs_planning():
    """planned + filesystem_present=False → needs_planning preserved.

    Same regression check for "planned" iteration_status (Path A pre-created
    changes via guide-design approve stay in "planned" until fill).
    """
    from skills._lib.discover_ship_changes import Candidate, _classify
    cand = Candidate(name="x", filesystem_present=False, iteration_status="planned")
    _classify(cand)
    assert "needs_planning" in cand.flags, (
        f"needs_planning should be present, got {cand.flags}"
    )