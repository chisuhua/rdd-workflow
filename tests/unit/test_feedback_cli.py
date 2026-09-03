"""Tests for feedback CLI dispatcher."""
from __future__ import annotations

import json
import pytest

from _lib.cli.feedback_cmd import cmd_feedback


def _make_project(tmp_path):
    """Create .rddf/improvements/ subdir and return it as project root."""
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True)
    return imp_dir


def test_cli_add_minimal(tmp_path, capsys):
    """rddf feedback add <name> --from X --kind Y --body Z succeeds."""
    _make_project(tmp_path)
    improvement = tmp_path / ".rddf" / "improvements" / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    rc = cmd_feedback([
        "add", "improve",
        "--from", "guide-design",
        "--kind", "needs-revision",
        "--body", "missing AC",
        "--project-root", str(tmp_path),
    ])
    captured = capsys.readouterr()
    assert rc == 0, f"stderr={captured.err}"
    assert "feedback-" in captured.out
    assert "improve.md" in captured.out


def test_cli_add_with_ref_change(tmp_path, capsys):
    """--ref-change is passed through to resolver."""
    _make_project(tmp_path)
    improvement = tmp_path / ".rddf" / "improvements" / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    rc = cmd_feedback([
        "add", "improve",
        "--from", "guide-design",
        "--kind", "needs-revision",
        "--body", "test",
        "--ref-change", "my-change",
        "--project-root", str(tmp_path),
    ])
    assert rc == 0
    text = improvement.read_text()
    assert "**ref_change**: my-change" in text


def test_cli_add_invalid_source(tmp_path):
    """Invalid --from returns non-zero exit code (argparse validates at parse time)."""
    _make_project(tmp_path)
    improvement = tmp_path / ".rddf" / "improvements" / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    try:
        rc = cmd_feedback([
            "add", "improve",
            "--from", "invalid",
            "--kind", "noted",
            "--body", "x",
            "--project-root", str(tmp_path),
        ])
        assert rc != 0
    except SystemExit as e:
        # argparse exits with 2 on invalid choice
        assert e.code != 0


def test_cli_add_missing_proposal(tmp_path):
    """Non-existent improvement file returns exit code 1."""
    _make_project(tmp_path)
    rc = cmd_feedback([
        "add", "ghost",
        "--from", "human",
        "--kind", "noted",
        "--body", "x",
        "--project-root", str(tmp_path),
    ])
    assert rc == 1


def test_cli_add_dry_run(tmp_path):
    """--dry-run does not modify file."""
    _make_project(tmp_path)
    improvement = tmp_path / ".rddf" / "improvements" / "improve.md"
    original = "---\nname: improve\n---\n"
    improvement.write_text(original)
    rc = cmd_feedback([
        "add", "improve",
        "--from", "human",
        "--kind", "noted",
        "--body", "would write",
        "--dry-run",
        "--project-root", str(tmp_path),
    ])
    assert rc == 0
    assert improvement.read_text() == original