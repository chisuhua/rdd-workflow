"""Unit tests for ``skills._lib.cli.guide_cmd`` priority ladder."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skills._lib.cli import guide_cmd


def _run_git(cwd: str, *args: str) -> str:
    """Run a git command and return stdout (stripped)."""
    r = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Build a tmp git repo with .rddf/state/ and an empty openspec/changes/."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(str(repo), "init")
    _run_git(str(repo), "config", "user.email", "test@example.com")
    _run_git(str(repo), "config", "user.name", "Test")
    # Empty initial commit so the repo is valid.
    (repo / "README.md").write_text("# test\n")
    _run_git(str(repo), "add", "README.md")
    _run_git(str(repo), "commit", "-m", "init")

    (repo / ".rddf" / "state").mkdir(parents=True)
    (repo / "openspec" / "changes").mkdir(parents=True)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(repo))
    return repo


def test_priority_1_arch_done_plan_undone_recommends_guide_plan(git_repo, capsys):
    """arch-handoff present, plan-handoff absent → 'guide-plan'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out
    assert "进入变更生成" in captured.out


def test_priority_2_arch_done_zero_adrs_recommends_guide_arch_recover(git_repo, capsys):
    """arch-handoff present but ADR < 1 → 'guide-arch (recover)'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-arch" in captured.out
    assert "未完成" in captured.out or "回到" in captured.out


def test_priority_3_plan_done_recommends_guide_ship(git_repo, capsys):
    """plan-handoff present (with active changes & filesystem match) → 'guide-ship'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    (git_repo / ".rddf" / "state" / ".plan-handoff.json").write_text(
        json.dumps({"active_changes": 2})
    )
    # Need active change dirs for cross-validation
    (git_repo / "openspec" / "changes" / "my-change").mkdir(parents=True)
    (git_repo / "openspec" / "changes" / "my-change" / "proposal.md").write_text("x")
    (git_repo / "openspec" / "changes" / "other-change").mkdir(parents=True)
    (git_repo / "openspec" / "changes" / "other-change" / "proposal.md").write_text("x")
    _run_git(str(git_repo), "add", "openspec/changes")
    _run_git(str(git_repo), "commit", "-m", "add changes")

    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "变更执行" in captured.out


def test_priority_4_plan_done_zero_active_recommends_guide_ship_cleanup(git_repo, capsys):
    """plan-handoff present but active_changes = 0 → 'guide-ship (cleanup)'."""
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 3})
    )
    (git_repo / ".rddf" / "state" / ".plan-handoff.json").write_text(
        json.dumps({"active_changes": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "残留" in captured.out or "清理" in captured.out


def test_stale_workflow_state_warning_emitted(git_repo, capsys):
    """When workflow-state.md exists, a stale-warning line is printed alongside the recommendation."""
    (git_repo / "workflow-state.md").write_text("stale content")
    # No handoffs → should recommend based on priority 6 (no roadmap → guide-arch)
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "stale" in captured.out.lower() or "workflow-state" in captured.out


def test_priority_6_no_roadmap_recommends_guide_arch(git_repo, capsys):
    """No roadmap.md → 'guide-arch'."""
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-arch" in captured.out
    assert "roadmap" in captured.out.lower() or "架构" in captured.out


def test_priority_7_no_changes_dir_recommends_guide_plan(git_repo, capsys):
    """roadmap.md exists, but no openspec/changes/ → 'guide-plan'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    # Remove openspec/changes entirely
    import shutil
    shutil.rmtree(git_repo / "openspec" / "changes")
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out


def test_priority_8_pending_proposal_recommends_guide_plan(git_repo, capsys):
    """roadmap + changes dir + unapproved improvement in improvements/ → 'guide-plan'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    # Create improvements/ directory with an unapproved proposal
    (git_repo / "improvements").mkdir()
    (git_repo / "improvements" / "test-prop.md").write_text(
        "# test-prop\n\n**优先级**: P0 | **来源**: test\n"
    )
    # proposal-approved.md is empty (no approved proposals)
    (git_repo / "proposal-approved.md").write_text(
        "# 已批准提案\n\n| 提案 | 优先级 | 批准时间 | 批准者 |\n|------|--------|----------|--------|\n"
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-plan" in captured.out
    assert "未审查提案" in captured.out or "propose" in captured.out.lower()


def test_priority_9_no_pending_proposal_recommends_guide_ship(git_repo, capsys):
    """All prior checks pass and all improvements are approved → default 'guide-ship'."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    # Create improvements/ with an already-approved proposal
    (git_repo / "improvements").mkdir()
    (git_repo / "improvements" / "test-prop.md").write_text(
        "# test-prop\n\n**优先级**: P0 | **来源**: test\n"
    )
    # proposal-approved.md contains the proposal (already approved)
    (git_repo / "proposal-approved.md").write_text(
        "# 已批准提案\n\n| 提案 | 优先级 | 批准时间 | 批准者 |\n|------|--------|----------|--------|\n| [test-prop](improvements/test-prop.md) | P0 | 2026-07-24 | test |\n"
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "guide-ship" in captured.out
    assert "准备 ship" in captured.out or "ship" in captured.out.lower()


def test_cmd_guide_prints_state_summary(git_repo, capsys):
    """cmd_guide prints a state summary including roadmap and handoff presence."""
    (git_repo / "roadmap.md").write_text("# Roadmap\n")
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"adr_count": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "🔍" in captured.out or "项目状态" in captured.out
    assert "roadmap.md" in captured.out


def test_cmd_guide_uses_roadmap_path_from_handoff(git_repo, capsys):
    """When .arch-handoff.json has roadmap_path, that path is checked (not default 'roadmap.md')."""
    (git_repo / "docs" / "my-roadmap.md").parent.mkdir(parents=True, exist_ok=True)
    (git_repo / "docs" / "my-roadmap.md").write_text("# Custom\n")
    (git_repo / ".rddf" / "state" / ".arch-handoff.json").write_text(
        json.dumps({"roadmap_path": "docs/my-roadmap.md", "adr_count": 0})
    )
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    # Should NOT recommend guide-arch because custom roadmap exists (falls through to default guide-ship)
    assert "进入架构定义" not in captured.out


def test_cmd_guide_works_outside_git_repo(tmp_path, monkeypatch, capsys):
    """When cwd is not a git repo, cmd_guide still emits a recommendation (falls back to pwd)."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # No .rddf/state, no openspec, no roadmap
    rc = guide_cmd.cmd_guide([])
    captured = capsys.readouterr()
    assert rc == 0
    # Should recommend guide-arch (no roadmap)
    assert "guide-arch" in captured.out