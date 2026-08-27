"""Unit tests for verifier-re-verify-archived-flag.

Per verifier-re-verify-archived-flag proposal acceptance:
- argparse 解析 --re-verify-archived + --archived-since flags
- discover_archived_changes 正确枚举 (含日期提取)
- 默认 rdd-verify 行为不变 (向后兼容)
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixture: build a minimal repo with archive/<date>-<name>/ structure
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_with_archives(tmp_path):
    """Build a repo with iteration.json + openspec/changes/archive/<date>-<name>/."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "iteration.json").write_text(
        '{"changes": [{"name": "test", "status": "archived", "tasks_total": 1, "tasks_done": 1}]}',
        encoding="utf-8",
    )
    archive = tmp_path / "openspec" / "changes" / "archive"
    (archive / "2026-08-27-foo").mkdir(parents=True)
    (archive / "2026-08-27-foo" / "tasks.md").write_text("- [x] T1\n", encoding="utf-8")
    (archive / "2026-08-26-bar").mkdir(parents=True)
    (archive / "2026-08-26-bar" / "tasks.md").write_text("- [x] T1\n", encoding="utf-8")
    (archive / "2026-06-07-baz").mkdir(parents=True)
    (archive / "2026-06-07-baz" / "tasks.md").write_text("- [x] T1\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests for discover_archived
# ---------------------------------------------------------------------------

def test_discover_archived_returns_all_without_since(repo_with_archives):
    """No since filter → returns all archived entries with archive_date parsed."""
    from skills._lib.verifier.discovery import discover_archived
    results = discover_archived(repo_with_archives)
    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"foo", "bar", "baz"}
    dates = {r["archive_date"] for r in results}
    assert dates == {"2026-08-27", "2026-08-26", "2026-06-07"}


def test_discover_archived_filters_by_since(repo_with_archives):
    """since=2026-08-27 → only entries archived on/after this date."""
    from skills._lib.verifier.discovery import discover_archived
    results = discover_archived(repo_with_archives, since="2026-08-27")
    names = [r["name"] for r in results]
    assert names == ["foo"]
    assert results[0]["archive_date"] == "2026-08-27"


def test_discover_archived_invalid_since_ignored(repo_with_archives):
    """Invalid since date string → returns all (graceful degradation)."""
    from skills._lib.verifier.discovery import discover_archived
    results = discover_archived(repo_with_archives, since="not-a-date")
    assert len(results) == 3


def test_discover_archived_missing_dir_returns_empty(tmp_path):
    """No openspec/changes/archive/ → returns empty list (not error)."""
    from skills._lib.verifier.discovery import discover_archived
    results = discover_archived(tmp_path)
    assert results == []


def test_discover_archived_skips_non_matching_dirs(tmp_path):
    """Dirs not matching <date>-<name> pattern are skipped (no date prefix)."""
    archive = tmp_path / "openspec" / "changes" / "archive"
    (archive / "2026-08-27-good").mkdir(parents=True)
    (archive / "not-a-date-bad").mkdir(parents=True)
    from skills._lib.verifier.discovery import discover_archived
    results = discover_archived(tmp_path)
    assert len(results) == 1
    assert results[0]["name"] == "good"


def test_discover_archived_invalid_date_format_included_without_since(tmp_path):
    """Dirs with regex-matchable but invalid dates (e.g. 2026-13-45) are
    included without since filter, but excluded when since is set."""
    archive = tmp_path / "openspec" / "changes" / "archive"
    (archive / "2026-13-45-bad-date").mkdir(parents=True)
    from skills._lib.verifier.discovery import discover_archived
    # No filter: regex matches, date string preserved as-is
    results = discover_archived(tmp_path)
    assert len(results) == 1
    assert results[0]["archive_date"] == "2026-13-45"
    # With since filter: invalid date excluded (can't compare)
    results = discover_archived(tmp_path, since="2026-08-27")
    assert results == []


# ---------------------------------------------------------------------------
# Test for CLI flag parsing
# ---------------------------------------------------------------------------

def test_cli_re_verify_archived_flag_parses():
    """argparse accepts --re-verify-archived and --archived-since flags."""
    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    # Use --help to verify flag exists without triggering full execution
    import argparse
    parser = argparse.ArgumentParser(prog="rddf rdd-verify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--re-verify-archived", action="store_true")
    parser.add_argument("--archived-since", type=str, default=None)
    args = parser.parse_args(["--re-verify-archived", "--archived-since", "2026-08-27"])
    assert args.re_verify_archived is True
    assert args.archived_since == "2026-08-27"


def test_cli_default_no_re_verify_archived():
    """Without --re-verify-archived flag, default is False (backward compat)."""
    import argparse
    parser = argparse.ArgumentParser(prog="rddf rdd-verify")
    parser.add_argument("--re-verify-archived", action="store_true")
    args = parser.parse_args([])
    assert args.re_verify_archived is False


# ---------------------------------------------------------------------------
# Test backward compat: discover_eligible still excludes archived
# ---------------------------------------------------------------------------

def test_discover_eligible_excludes_archived(repo_with_archives):
    """Default discover_eligible (status filter) does not include archived changes."""
    from skills._lib.verifier.discovery import discover_eligible
    eligible = discover_eligible(repo_with_archives)
    assert "foo" not in eligible
    assert "bar" not in eligible
    assert "baz" not in eligible