"""Tests for fix-adr-0027-close-hook-dead-code: archive path fallback + submitted_url matching."""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))


def test_load_issue_refs_archive_fallback(tmp_path: Path) -> None:
    """After openspec archive, the change dir is moved to archive/<date>-<name>/.

    The hook must find the roadmap-meta.yaml in either the active path
    OR the post-archive path. This test simulates the post-archive layout
    (only archive/<date>-<name>/roadmap-meta.yaml exists).
    """
    from close_issues import _load_issue_refs  # type: ignore[import-not-found]

    archive_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-08-24-add-foo"
    archive_dir.mkdir(parents=True)
    (archive_dir / "roadmap-meta.yaml").write_text(dedent("""\
        name: add-foo
        issue_refs:
          - 42
          - 123
        gh_repo: my-org/my-repo
    """), encoding="utf-8")

    refs, gh_repo = _load_issue_refs("add-foo", str(tmp_path))
    assert refs == [42, 123], f"expected [42, 123], got {refs}"
    assert gh_repo == "my-org/my-repo", f"expected my-org/my-repo, got {gh_repo}"


def test_update_local_issue_files_matches_by_submitted_url(tmp_path: Path) -> None:
    """closed_at must be written when local issue file's submitted_url contains /issues/<n>.

    Pre-fix bug: code matched on dedup_hash (always 8-hex from stack
    normalization) against issue_number (always integer) — never
    matched. Fix matches on submitted_url like 'github.com/.../issues/42'.
    """
    from close_issues import _update_local_issue_files, CloseResult  # type: ignore[import-not-found]

    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    issue_file = issues_dir / "flow-bug-aabbccdd.md"
    issue_file.write_text(dedent("""\
        ---
        category: "flow-bug"
        submitted: true
        submitted_url: "https://github.com/chisuhua/rdd-workflow/issues/42"
        dedup_hash: "aabbccdd"
        ---
        ## Description

        some bug
    """), encoding="utf-8")

    result = CloseResult(closed=[42], skipped=[], manual_links=[], errors=[])
    _update_local_issue_files([42], str(tmp_path), result)

    text = issue_file.read_text(encoding="utf-8")
    assert "closed_at:" in text, f"closed_at not written: {text}"
    assert "closed_ref: 42" in text, f"closed_ref not written: {text}"


def test_close_issues_early_return_when_no_refs(tmp_path) -> None:
    """When issue_refs is empty, hook must early-return without touching local files."""
    from close_issues import close_issues_for_change, _load_issue_refs  # type: ignore[import-not-found]

    # Arrange: change with empty issue_refs (active path)
    change_dir = tmp_path / "openspec" / "changes" / "empty-refs"
    change_dir.mkdir(parents=True)
    (change_dir / "roadmap-meta.yaml").write_text(
        "name: empty-refs\nissue_refs: []\n", encoding="utf-8"
    )

    # Arrange: local issue file that must NOT be modified
    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    issue_file = issues_dir / "flow-bug-deadbeef.md"
    original_text = 'submitted: true\nsubmitted_url: "https://github.com/x/y/issues/7"\n'
    issue_file.write_text(original_text, encoding="utf-8")

    # Act
    refs, _ = _load_issue_refs("empty-refs", str(tmp_path))
    assert refs == [], f"_load_issue_refs should return [], got {refs}"

    result = close_issues_for_change("empty-refs", str(tmp_path))
    assert result.closed == []
    assert result.skipped == []
    assert result.errors == []
    assert result.manual_links == []

    # Local file untouched
    assert issue_file.read_text(encoding="utf-8") == original_text