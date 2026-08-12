"""Tests for ADR-0027 close hook (``_lib/close_issues.py``).

Change-b sub-task 2: close_issues_for_change + can_close_in_repo + prune_old_issues.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from close_issues import (  # type: ignore[import-not-found]
    close_issues_for_change,
    prune_old_issues,
    can_close_in_repo,
    CloseResult,
)


# ── Helpers ───────────────────────────────────────────────────────────────


def _write_roadmap_meta(project_root: str, issue_refs, gh_repo="chisuhua/rdd-workflow") -> Path:
    change_dir = Path(project_root) / "openspec" / "changes" / "my-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    meta = change_dir / "roadmap-meta.yaml"
    refs_yaml = "[" + ", ".join(str(r) for r in issue_refs) + "]"
    meta.write_text(f"issue_refs: {refs_yaml}\ngh_repo: {gh_repo}\n", encoding="utf-8")
    return meta


def _make_issue_file(project_root: str, dedup_hash: str, category="doctor-critical", closed_at: str | None = None) -> Path:
    issues_dir = Path(project_root) / ".rddf" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    path = issues_dir / f"{category}-{dedup_hash}.md"
    closed_line = f'closed_at: "{closed_at}"\n' if closed_at else ""
    path.write_text(
        f'---\ncategory: "{category}"\ndedup_hash: "{dedup_hash}"\nsubmitted_url: null\n{closed_line}---\n\nbody\n',
        encoding="utf-8",
    )
    return path


# ── TDD 2.1: can_close_in_repo (already covered in issue_reporter tests, smoke here) ──


def test_can_close_in_repo_returns_true_for_writable_repo():
    fake_proc = mock.Mock(returncode=0, stdout="true", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc):
        assert can_close_in_repo("owner/repo") is True


def test_can_close_in_repo_returns_false_for_readonly_repo():
    fake_proc = mock.Mock(returncode=0, stdout="false", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc):
        assert can_close_in_repo("owner/repo") is False


# ── TDD 2.2-2.3: close_issues_for_change with refs ──────────────────────


def test_close_issues_for_change_with_no_meta_file_is_noop(tmp_path, monkeypatch):
    """No roadmap-meta.yaml → empty result, no gh calls."""
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)
    result = close_issues_for_change("nonexistent-change", project_root=str(tmp_path))
    assert result.closed == []
    assert result.skipped == []
    assert result.manual_links == []
    assert result.errors == []


def test_close_issues_for_change_with_empty_refs_is_noop(tmp_path, monkeypatch):
    _write_roadmap_meta(str(tmp_path), issue_refs=[])
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)
    result = close_issues_for_change("my-change", project_root=str(tmp_path))
    assert result.closed == []


def test_close_issues_for_change_disabled_by_env(tmp_path, monkeypatch):
    """RDDF_REPORT_CLOSE_ON_ARCHIVE=no short-circuits the hook."""
    _write_roadmap_meta(str(tmp_path), issue_refs=[123])
    monkeypatch.setenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", "no")
    with mock.patch("subprocess.run") as m:
        result = close_issues_for_change("my-change", project_root=str(tmp_path))
    assert result.closed == []
    assert m.call_count == 0


def test_close_issues_for_change_degrades_when_no_push_permission(tmp_path, monkeypatch):
    """can_close_in_repo returns False → manual_links populated, no gh close calls."""
    _write_roadmap_meta(str(tmp_path), issue_refs=[123, 456])
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)
    monkeypatch.setenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", "yes")
    monkeypatch.setattr("close_issues.can_close_in_repo", lambda _repo: False)
    with mock.patch("subprocess.run") as m:
        result = close_issues_for_change("my-change", project_root=str(tmp_path))
    assert result.closed == []
    assert sorted(ref for ref, _ in result.manual_links) == [123, 456]
    assert all("github.com/chisuhua/rdd-workflow" in url for _, url in result.manual_links)
    assert m.call_count == 0  # no close attempts when no push permission


# ── TDD 2.4: skip already-closed issues ──────────────────────────────────


def test_close_issues_for_change_skips_already_closed_issue(tmp_path, monkeypatch):
    _write_roadmap_meta(str(tmp_path), issue_refs=[123])
    monkeypatch.setattr("close_issues.can_close_in_repo", lambda _repo: True)
    monkeypatch.setattr("subprocess.run", mock.Mock(
        side_effect=[
            mock.Mock(returncode=0, stdout="abc1234", stderr=""),  # git rev-parse --short HEAD
            mock.Mock(returncode=0, stdout="CLOSED", stderr=""),  # gh issue view state check
        ]
    ))
    result = close_issues_for_change("my-change", project_root=str(tmp_path))
    assert result.closed == []
    assert result.skipped == [123]


# ── TDD 2.6: prune_old_issues (TDD 2.6) ─────────────────────────────────


def test_prune_old_issues_removes_only_old_closed_files(tmp_path):
    """Files with old closed_at are removed; recent ones are kept; unsubmitted are kept."""
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    _make_issue_file(str(tmp_path), "old11111", closed_at=old)
    _make_issue_file(str(tmp_path), "recent22", closed_at=recent)
    _make_issue_file(str(tmp_path), "nosub33")  # no closed_at

    removed = prune_old_issues(project_root=str(tmp_path), retention_days=30)
    assert removed == 1

    issues_dir = Path(tmp_path) / ".rddf" / "issues"
    remaining = {p.name for p in issues_dir.glob("*.md")}
    assert "doctor-critical-old11111.md" not in remaining
    assert "doctor-critical-recent22.md" in remaining
    assert "doctor-critical-nosub33.md" in remaining


def test_prune_old_issues_returns_zero_when_dir_missing(tmp_path):
    removed = prune_old_issues(project_root=str(tmp_path))
    assert removed == 0


# ── TDD 2.7: unsubmitted files are NEVER pruned (regression) ───────────


def test_prune_old_issues_never_deletes_unsubmitted_files(tmp_path):
    """Even with a 1-day retention, unsubmitted files survive (closed_at missing)."""
    _make_issue_file(str(tmp_path), "nosub44")
    removed = prune_old_issues(project_root=str(tmp_path), retention_days=1)
    assert removed == 0
    issues_dir = Path(tmp_path) / ".rddf" / "issues"
    assert (issues_dir / "doctor-critical-nosub44.md").exists()


# ── TDD 2.5: graceful failure handling ──────────────────────────────────


def test_close_issues_for_change_records_error_on_state_check_failure(tmp_path, monkeypatch):
    _write_roadmap_meta(str(tmp_path), issue_refs=[123])
    monkeypatch.setattr("close_issues.can_close_in_repo", lambda _repo: True)
    with mock.patch("subprocess.run", side_effect=FileNotFoundError("gh missing")):
        result = close_issues_for_change("my-change", project_root=str(tmp_path))
    assert result.closed == []
    assert any("state check #123" in e for e in result.errors)
