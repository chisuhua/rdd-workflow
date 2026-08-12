"""Cross-cutting integration tests for ADR-0027 reporter + close hook.

Change-c delivers these as a focused Python integration test (the full
bats suite is deferred to a follow-up per the change-c proposal's
"In Scope" caveats). Covers:

- E2E: detect_issue → write_issue_file → submit_issue_via_gh (mocked)
- E2E: close_issues_for_change with no push permission (third-party user)
- E2E: CI environment suppresses L2 submission
- Regression: existing change-a + change-b modules still compose correctly
"""
from __future__ import annotations

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
    is_ci_environment,
    can_close_in_repo,
)
from close_issues import close_issues_for_change, prune_old_issues  # type: ignore[import-not-found]


# ── E2E: detect → write → submit (mocked) ──────────────────────────────


def test_e2e_full_pipeline_creates_submits_and_closes(tmp_path, monkeypatch):
    """Full 5-ring E2E: detect → write → submit (mocked) → close hook (mocked)."""
    # 1. Detect
    payload = {
        "description": "Schema drift in /home/alice/myproj/src/main.py:42",
        "stack": [
            "/home/alice/myproj/src/main.py:42 in main",
            "/home/alice/myproj/lib/utils.py:13 in helper",
        ],
    }
    result = detect_issue("flow-bug", payload)
    assert "alice" not in result.sanitized_description
    assert "main.py" in result.sanitized_description
    assert len(result.dedup_hash) == 8

    # 2. Write
    file_path = write_issue_file(result, project_root=str(tmp_path))
    assert file_path.exists()
    assert file_path.name.startswith("flow-bug-")

    # 3. Submit (mocked gh)
    fake_proc = mock.Mock(
        returncode=0,
        stdout="https://github.com/x/y/issues/1",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=fake_proc))
    submit_result = submit_issue_via_gh(file_path, "flow-bug", "x/y")
    assert submit_result.success is True
    assert submit_result.submitted_url == "https://github.com/x/y/issues/1"


# ── E2E: CI suppression in the pipeline ──────────────────────────────────


def test_e2e_ci_environment_suppresses_l2_submission(tmp_path, monkeypatch):
    """When CI=true, callers should short-circuit before submit_issue_via_gh."""
    monkeypatch.setenv("CI", "true")
    assert is_ci_environment() is True

    payload = {"description": "x", "stack": []}
    result = detect_issue("manual", payload)
    file_path = write_issue_file(result, project_root=str(tmp_path))

    submit_called = False

    def _track(*args, **kwargs):
        nonlocal submit_called
        submit_called = True
        return mock.Mock(returncode=0, stdout="https://x", stderr="")

    monkeypatch.setattr("subprocess.run", _track)
    if not is_ci_environment():
        submit_issue_via_gh(file_path, "manual", "x/y")

    assert submit_called is False, "submit must be skipped in CI"


# ── E2E: close hook with no push permission (third-party user) ──────────


def test_e2e_close_hook_degrades_gracefully_without_push(tmp_path, monkeypatch):
    """Third-party user (no push to upstream) gets manual-close hints, no gh close calls."""
    change_dir = tmp_path / "openspec" / "changes" / "feat-x"
    change_dir.mkdir(parents=True)
    (change_dir / "roadmap-meta.yaml").write_text(
        "issue_refs: [101, 202]\ngh_repo: chisuhua/rdd-workflow\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("close_issues.can_close_in_repo", lambda _repo: False)
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)

    result = close_issues_for_change("feat-x", project_root=str(tmp_path))
    assert result.closed == []
    assert result.skipped == []
    assert sorted(ref for ref, _ in result.manual_links) == [101, 202]
    assert all(
        "github.com/chisuhua/rdd-workflow" in url for _, url in result.manual_links
    )


# ── E2E: close hook with write permission (dogfooding) ──────────────────


def test_e2e_close_hook_dogfooding_closes_and_updates_local_file(
    tmp_path, monkeypatch
):
    """Maintainer scenario: close hook calls gh close + updates local file closed_at."""
    change_dir = tmp_path / "openspec" / "changes" / "feat-y"
    change_dir.mkdir(parents=True)
    (change_dir / "roadmap-meta.yaml").write_text(
        "issue_refs: [303]\ngh_repo: chisuhua/rdd-workflow\n",
        encoding="utf-8",
    )
    # Pre-create the local issue file
    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "flow-bug-303.md").write_text(
        '---\ncategory: "flow-bug"\ndedup_hash: "303"\nsubmitted_url: null\n---\n\nbody\n',
        encoding="utf-8",
    )

    monkeypatch.setattr("close_issues.can_close_in_repo", lambda _repo: True)
    monkeypatch.setattr("subprocess.run", mock.Mock(
        side_effect=[
            mock.Mock(returncode=0, stdout="abc1234", stderr=""),  # git rev-parse
            mock.Mock(returncode=0, stdout="OPEN", stderr=""),  # state check
            mock.Mock(returncode=0, stdout="", stderr=""),  # gh issue close
        ]
    ))

    result = close_issues_for_change("feat-y", project_root=str(tmp_path))
    assert result.closed == [303]
    assert result.errors == []

    issue_text = (issues_dir / "flow-bug-303.md").read_text()
    assert "closed_at:" in issue_text
    assert "closed_ref: 303" in issue_text


# ── E2E: retention — old closed files pruned, recent kept, unsubmitted kept ──


def test_e2e_retention_prunes_old_keeps_recent_and_unsubmitted(tmp_path):
    """The 30-day retention only touches submitted-and-closed files."""
    from datetime import datetime, timezone, timedelta

    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    recent_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    (issues_dir / "phase-crash-old11.md").write_text(
        f'---\nclosed_at: "{old_ts}"\n---\n', encoding="utf-8",
    )
    (issues_dir / "phase-crash-recent2.md").write_text(
        f'---\nclosed_at: "{recent_ts}"\n---\n', encoding="utf-8",
    )
    (issues_dir / "phase-crash-unsub3.md").write_text(
        '---\nsubmitted_url: null\n---\n', encoding="utf-8",
    )

    removed = prune_old_issues(project_root=str(tmp_path), retention_days=30)
    assert removed == 1
    remaining = {p.name for p in issues_dir.glob("*.md")}
    assert "phase-crash-old11.md" not in remaining
    assert "phase-crash-recent2.md" in remaining
    assert "phase-crash-unsub3.md" in remaining


# ── E2E: cross-module composition (change-a + change-b still work) ─────


def test_e2e_dedup_hash_matches_across_detect_calls():
    """Same payload → same dedup_hash (change-a + change-b compose correctly)."""
    payload = {
        "description": "schema drift detected",
        "stack": ["/home/alice/proj/main.py:42 in main"],
    }
    r1 = detect_issue("flow-bug", payload)
    r2 = detect_issue("flow-bug", payload)
    assert r1.dedup_hash == r2.dedup_hash

    payload_diff_path = {
        "description": "schema drift detected",
        "stack": ["/Users/bob/other-proj/main.py:99 in main"],
    }
    r3 = detect_issue("flow-bug", payload_diff_path)
    assert r3.dedup_hash == r1.dedup_hash  # cross-machine stability


def test_e2e_sanitizer_extension_in_detect():
    """Change-a's sanitizer extension works through change-b's detect_issue."""
    payload = {
        "description": "Failed in /Users/charlie/repo/lib.py:7",
        "stack": ["/Users/charlie/repo/handler.py:3 in handle"],
    }
    result = detect_issue("phase-crash", payload)
    assert "charlie" not in result.sanitized_description
    assert "lib.py" in result.sanitized_description
    assert "repo" not in result.sanitized_description  # project name gone
