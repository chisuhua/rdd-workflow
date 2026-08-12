"""Tests for ADR-0027 CLI handlers: ``rddf report-issue`` + ``rddf issue {submit,list,show}``.

Agent-plane manual entry point (per ADR-0027 §1.0). Bypasses the
post-flow-analysis classifier — the user has already classified.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))


def test_report_issue_writes_local_file(tmp_path, monkeypatch, capsys):
    """``rddf report-issue 'foo'`` creates a local issue file with default manual category."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="")))

    from cli.report_issue_cmd import cmd_report_issue
    rc = cmd_report_issue(["doc typo on line 42", "--no-submit"])
    assert rc == 0

    issues_dir = tmp_path / ".rddf" / "issues"
    files = list(issues_dir.glob("manual-*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "doc typo on line 42" in content


def test_report_issue_with_explicit_category(tmp_path, monkeypatch):
    """``--category flow-bug`` sets the issue category in the filename."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="")))

    from cli.report_issue_cmd import cmd_report_issue
    rc = cmd_report_issue(["schema drift", "--category", "flow-bug", "--no-submit"])
    assert rc == 0

    issues_dir = tmp_path / ".rddf" / "issues"
    files = list(issues_dir.glob("flow-bug-*.md"))
    assert len(files) == 1


def test_report_issue_with_phase_metadata(tmp_path, monkeypatch):
    """``--phase <name>`` adds phase to the issue metadata (filename reflects category only)."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="")))

    from cli.report_issue_cmd import cmd_report_issue
    rc = cmd_report_issue(["bug X", "--phase", "guide-plan", "--no-submit"])
    assert rc == 0

    issues_dir = tmp_path / ".rddf" / "issues"
    files = list(issues_dir.glob("manual-*.md"))
    assert len(files) == 1
    # Phase is in detect_issue payload metadata (used for dedup hash) but not in rendered body
    # — body is intentionally compact per ADR-0027 §3.1.


def test_issue_list_shows_local_files(tmp_path, monkeypatch, capsys):
    """``rddf issue list`` enumerates .rddf/issues/*.md."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="")))

    from cli.report_issue_cmd import cmd_report_issue
    from cli.issue_cmd import cmd_issue

    cmd_report_issue(["issue A", "--no-submit"])
    cmd_report_issue(["issue B", "--no-submit"])

    rc = cmd_issue(["list"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "issue A" in captured.out or "issue B" in captured.out
    assert "manual-" in captured.out


def test_issue_show_displays_body(tmp_path, monkeypatch, capsys):
    """``rddf issue show <hash>`` prints the issue body."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=mock.Mock(returncode=1, stdout="", stderr="")))

    from cli.report_issue_cmd import cmd_report_issue
    from cli.issue_cmd import cmd_issue

    cmd_report_issue(["test description unique", "--no-submit"])

    issues_dir = tmp_path / ".rddf" / "issues"
    hash_file = list(issues_dir.glob("manual-*.md"))[0]
    dedup_hash = hash_file.name.split("-")[1].split(".")[0]

    rc = cmd_issue(["show", dedup_hash])
    assert rc == 0
    captured = capsys.readouterr()
    assert "test description unique" in captured.out


def test_issue_submit_uses_filename_category(tmp_path, monkeypatch):
    """``rddf issue submit <file>`` infers category from filename ``<category>-<hash>.md``."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    fake_proc = mock.Mock(returncode=0, stdout="https://github.com/x/y/issues/1", stderr="")
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=fake_proc))

    issue = tmp_path / "flow-bug-abcdef12.md"
    issue.write_text("---\ncategory: \"flow-bug\"\n---\nbody\n")

    from cli.issue_cmd import cmd_issue
    rc = cmd_issue(["submit", str(issue)])
    assert rc == 0


def test_routes_table_registers_new_commands():
    """_ROUTES in _lib/cli/__init__.py must include 'report-issue' and 'issue'."""
    sys.path.insert(0, str(_PROJECT_ROOT))
    from cli import _ROUTES
    assert "report-issue" in _ROUTES
    assert "issue" in _ROUTES
    assert _ROUTES["report-issue"].endswith(":cmd_report_issue")
    assert _ROUTES["issue"].endswith(":cmd_issue")
