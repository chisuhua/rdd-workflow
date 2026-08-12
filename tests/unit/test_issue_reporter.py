"""Tests for ADR-0027 issue reporter core (``_lib/issue_reporter.py``).

Change-b of the 3-change split. Covers the 5 public functions:
- detect_issue: sanitize payload via _lib/loop/sanitizer
- write_issue_file: persist local issue under .rddf/issues/<cat>-<hash>.md
- submit_issue_via_gh: L2 (gh CLI) submission with dedup pre-check
- can_close_in_repo: probe gh permissions.push
- is_ci_environment: detect 6 CI markers
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from issue_reporter import (  # type: ignore[import-not-found]
    detect_issue,
    write_issue_file,
    submit_issue_via_gh,
    can_close_in_repo,
    is_ci_environment,
    IssueResult,
)


# ── detect_issue (TDD 1.1) ────────────────────────────────────────────────


def test_detect_issue_sanitizes_home_paths():
    """``detect_issue`` routes payload through _lib/loop/sanitizer."""
    payload = {
        "description": "Error in /home/alice/myproj/src/main.py:42",
        "stack": ["/home/alice/myproj/lib.py:13 in helper"],
    }
    result = detect_issue("manual", payload)
    assert result.category == "manual"
    assert "alice" not in result.sanitized_description
    assert "myproj" not in result.sanitized_description
    assert "main.py" in result.sanitized_description
    assert result.had_sensitive_data is True


def test_detect_issue_no_sensitive_data():
    """Plain payload passes through cleanly."""
    payload = {"description": "doc typo on line 5", "stack": []}
    result = detect_issue("manual", payload)
    assert result.sanitized_description == "doc typo on line 5"
    assert result.had_sensitive_data is False


# ── write_issue_file (TDD 1.2) ─────────────────────────────────────────────


def test_write_issue_file_creates_file_with_frontmatter(tmp_path, monkeypatch):
    """write_issue_file persists a complete Markdown file with dedup_hash in name."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf").mkdir()
    payload = {"description": "schema drift detected", "stack": ["/home/x/y.py:1"]}
    result = detect_issue("flow-bug", payload)
    file_path = write_issue_file(result, project_root=str(tmp_path))
    assert file_path.exists()
    assert file_path.name.startswith("flow-bug-")
    assert file_path.name.endswith(".md")
    content = file_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert ('category: "flow-bug"' in content
            or "category: flow-bug" in content)
    assert "submitted: false" in content
    assert "schema drift" in content


def test_write_issue_file_dedup_identical_inputs(tmp_path):
    """Same payload on two writes produces the same filename (idempotent)."""
    (tmp_path / ".rddf").mkdir()
    payload = {"description": "schema drift", "stack": ["/home/x/y.py:1"]}
    r1 = detect_issue("flow-bug", payload)
    r2 = detect_issue("flow-bug", payload)
    p1 = write_issue_file(r1, project_root=str(tmp_path))
    p2 = write_issue_file(r2, project_root=str(tmp_path))
    assert p1.name == p2.name


def test_write_issue_file_creates_rddf_issues_dir(tmp_path):
    """write_issue_file creates .rddf/issues/ if it doesn't exist."""
    payload = {"description": "x", "stack": []}
    result = detect_issue("manual", payload)
    file_path = write_issue_file(result, project_root=str(tmp_path))
    assert (tmp_path / ".rddf" / "issues").is_dir()
    assert file_path.exists()


# ── submit_issue_via_gh (TDD 1.3) ──────────────────────────────────────────


def test_submit_issue_via_gh_success(monkeypatch, tmp_path):
    """Successful gh issue create returns submitted_url."""
    issue_file = tmp_path / "manual-aabbccdd.md"
    issue_file.write_text("test body")
    fake_proc = mock.Mock(returncode=0, stdout="https://github.com/chisuhua/rdd-workflow/issues/42", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc) as m:
        result = submit_issue_via_gh(issue_file, "manual", "chisuhua/rdd-workflow")
    assert result.success is True
    assert result.submitted_url == "https://github.com/chisuhua/rdd-workflow/issues/42"
    assert any("--label" in str(call) for call in m.call_args_list)


def test_submit_issue_via_gh_failure(monkeypatch, tmp_path):
    """gh issue create failure returns success=False with error message."""
    issue_file = tmp_path / "manual-aabbccdd.md"
    issue_file.write_text("test body")
    fake_proc = mock.Mock(returncode=1, stdout="", stderr="gh: not authed")
    with mock.patch("subprocess.run", return_value=fake_proc):
        result = submit_issue_via_gh(issue_file, "manual", "chisuhua/rdd-workflow")
    assert result.success is False
    assert "not authed" in result.error


# ── is_ci_environment (TDD 1.4, 1.5) ─────────────────────────────────────


def test_is_ci_environment_detects_ci_true(monkeypatch):
    monkeypatch.setenv("CI", "true")
    assert is_ci_environment() is True


def test_is_ci_environment_detects_github_actions(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert is_ci_environment() is True


def test_is_ci_environment_detects_jenkins(monkeypatch):
    monkeypatch.setenv("JENKINS_URL", "https://jenkins.example.com")
    assert is_ci_environment() is True


def test_is_ci_environment_detects_gitlab_ci(monkeypatch):
    monkeypatch.setenv("GITLAB_CI", "true")
    assert is_ci_environment() is True


def test_is_ci_environment_detects_circleci(monkeypatch):
    monkeypatch.setenv("CIRCLECI", "true")
    assert is_ci_environment() is True


def test_is_ci_environment_detects_buildkite(monkeypatch):
    monkeypatch.setenv("BUILDKITE", "true")
    assert is_ci_environment() is True


def test_is_ci_environment_false_when_no_markers(monkeypatch):
    for k in ("CI", "GITHUB_ACTIONS", "JENKINS_URL", "BUILDKITE", "CIRCLECI", "GITLAB_CI"):
        monkeypatch.delenv(k, raising=False)
    assert is_ci_environment() is False


# ── can_close_in_repo (TDD 2.1, 2.2) ─────────────────────────────────────


def test_can_close_in_repo_returns_true_when_push_true():
    fake_proc = mock.Mock(returncode=0, stdout="true", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc):
        assert can_close_in_repo("chisuhua/rdd-workflow") is True


def test_can_close_in_repo_returns_false_when_push_false():
    fake_proc = mock.Mock(returncode=0, stdout="false", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc):
        assert can_close_in_repo("chisuhua/rdd-workflow") is False


def test_can_close_in_repo_returns_false_when_gh_missing():
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        assert can_close_in_repo("chisuhua/rdd-workflow") is False


def test_can_close_in_repo_returns_false_on_timeout():
    with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=10)):
        assert can_close_in_repo("chisuhua/rdd-workflow") is False


# ── End-to-end (TDD 1.1-1.5) ────────────────────────────────────────────


def test_end_to_end_detect_write_submit(tmp_path, monkeypatch):
    """Full pipeline: detect → write → submit (mocked) roundtrip."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf").mkdir()
    payload = {
        "description": "Failed at /home/alice/myproj/src/main.py:42",
        "stack": ["/home/alice/myproj/lib.py:13 in helper"],
    }
    result = detect_issue("flow-bug", payload)
    file_path = write_issue_file(result, project_root=str(tmp_path))
    assert file_path.exists()

    fake_proc = mock.Mock(returncode=0, stdout="https://github.com/x/y/issues/1", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc):
        submit_result = submit_issue_via_gh(file_path, "flow-bug", "x/y")
    assert submit_result.success is True
    assert submit_result.submitted_url == "https://github.com/x/y/issues/1"
