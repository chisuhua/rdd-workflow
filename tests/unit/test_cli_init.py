"""Unit tests for ``skills._lib.cli.init_cmd``."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills._lib.cli import init_cmd


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Build a fake rdd-workflow repo at tmp_path/repo with required source files.

    Layout:
        tmp_path/repo/
            package.json
            skills/
                INSTALL.md
                guide/SKILL.md
            skills/cli/rddf.sh
            _lib/
                state.sh
    """
    repo = tmp_path / "repo"
    (repo / "skills").mkdir(parents=True)
    (repo / "skills" / "INSTALL.md").write_text("# INSTALL\n")
    (repo / "skills" / "guide").mkdir()
    (repo / "skills" / "guide" / "SKILL.md").write_text("# guide\n")
    (repo / "skills" / "cli").mkdir()
    (repo / "skills" / "cli" / "rddf.sh").write_text("#!/usr/bin/env bash\necho ok\n")
    (repo / "_lib").mkdir()
    (repo / "_lib" / "state.sh").write_text("# state\n")
    (repo / "package.json").write_text(json.dumps({"version": "2.0.7"}))

    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(repo))
    return repo, target


def test_cmd_init_copies_to_target_dir(fake_repo, capsys):
    """cmd_init copies skills/, _lib/, package.json, skills/cli/rddf.sh to <target>/.opencode/skills/rdd-workflow/."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([str(target)])
    assert rc == 0
    dest = target / ".opencode" / "skills" / "rdd-workflow"
    assert (dest / "package.json").is_file()
    assert (dest / "skills" / "INSTALL.md").is_file()
    assert (dest / "skills" / "guide" / "SKILL.md").is_file()
    assert (dest / "skills" / "cli" / "rddf.sh").is_file()
    assert (dest / "_lib" / "state.sh").is_file()


def test_cmd_init_creates_parent_dirs(fake_repo, capsys):
    """cmd_init creates .opencode/skills/rdd-workflow/ if it does not exist."""
    repo, target = fake_repo
    dest = target / ".opencode" / "skills" / "rdd-workflow"
    assert not dest.exists()
    rc = init_cmd.cmd_init([str(target)])
    assert rc == 0
    assert dest.is_dir()


def test_cmd_init_default_target_is_project_root(fake_repo, monkeypatch, capsys):
    """Without an explicit target arg, cmd_init installs to RDDF_PROJECT_ROOT/."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([])
    assert rc == 0
    dest = repo / ".opencode" / "skills" / "rdd-workflow"
    assert (dest / "skills" / "INSTALL.md").is_file()


def test_cmd_init_missing_source_exits_one(tmp_path, monkeypatch, capsys):
    """When source layout is missing, cmd_init prints a clear error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = init_cmd.cmd_init([str(tmp_path / "target")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "找不到" in captured.err or "skills" in captured.err


def test_cmd_init_prints_summary(fake_repo, capsys):
    """cmd_init prints an install summary with file counts."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init([str(target)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "安装完成" in captured.out or "installed" in captured.out.lower()


def test_cmd_init_help_flag(fake_repo, capsys):
    """cmd_init --help prints usage and returns 0 without writing any files."""
    repo, target = fake_repo
    rc = init_cmd.cmd_init(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "usage" in captured.out.lower() or "用法" in captured.out
    assert not (target / ".opencode").exists()