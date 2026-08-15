"""Tests for from_issue.py scaffold writer.

Covers:
1. Happy path: writes .rddf/improvements/<slug>-i<N>.md with required fields.
2. Slug collision: appends -i<N> suffix when same slug already exists.
3. Dedup against .rddf/improvements/<existing>.md frontmatter issue_ref.
4. Dedup against openspec/changes/<other>/roadmap-meta.yaml issue_refs.
5. Body truncation at 4000 chars with reference URL preserved.
6. HARD-GATE: never writes proposal-suggestions.md.
"""
import os
import subprocess
import types
from pathlib import Path

import sys
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Dash-bridge: map skills.add_improve → skills/add-improve (matching conftest.py pattern)
_mod_name = "skills.add_improve"
if _mod_name not in sys.modules:
    _mod = types.ModuleType(_mod_name)
    _mod.__path__ = [os.path.join(str(_PROJECT_ROOT), "skills", "add-improve")]
    sys.modules[_mod_name] = _mod

# Also bridge scripts sub-module
_scripts_name = "skills.add_improve.scripts"
if _scripts_name not in sys.modules:
    _scripts_mod = types.ModuleType(_scripts_name)
    _scripts_mod.__path__ = [os.path.join(str(_PROJECT_ROOT), "skills", "add-improve", "scripts")]
    sys.modules[_scripts_name] = _scripts_mod

from skills.add_improve.scripts.from_issue import (  # noqa: E402
    write_scaffold,
    check_dedup,
    truncate_body,
    slugify,
    DedupHit,
)


def _setup_tmp_project(tmp_path: Path, *, improvements: list = None, changes: list = None) -> Path:
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True, exist_ok=True)
    (tmp_path / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    for imp in improvements or []:
        (tmp_path / ".rddf" / "improvements" / f"{imp['name']}.md").write_text(imp["content"])
    for change in changes or []:
        change_dir = tmp_path / "openspec" / "changes" / change["name"]
        change_dir.mkdir(parents=True, exist_ok=True)
        (change_dir / "roadmap-meta.yaml").write_text(change["meta"])
    return tmp_path


# === Test Group 1: slugify ===

def test_slugify_basic():
    assert slugify("Fix Race Condition") == "fix-race-condition"


def test_slugify_special_chars():
    assert slugify("Fix: 50% off!") == "fix-50-off"


def test_slugify_unicode():
    assert slugify("修复竞态条件") == "修复竞态条件"


def test_slugify_multiple_spaces():
    assert slugify("foo   bar  baz") == "foo-bar-baz"


# === Test Group 2: truncate_body ===

def test_truncate_body_short():
    """Body <= 4000 chars is returned unchanged."""
    body = "x" * 1000
    out = truncate_body(body, "https://github.com/foo/bar/issues/42")
    assert out == body


def test_truncate_body_oversize():
    """Body > 4000 chars is truncated with reference URL preserved."""
    body = "x" * 5000
    out = truncate_body(body, "https://github.com/foo/bar/issues/42")
    assert len(out) <= 4000
    assert "https://github.com/foo/bar/issues/42" in out
    assert "..." in out


# === Test Group 3: check_dedup ===

def test_dedup_no_match(tmp_path):
    """No existing proposal → no dedup hit."""
    _setup_tmp_project(tmp_path)
    assert check_dedup(42, tmp_path) == []


def test_dedup_in_improvements(tmp_path):
    """Existing improvement with issue_ref: 42 triggers dedup hit."""
    _setup_tmp_project(tmp_path, improvements=[
        {"name": "fix-foo", "content": "---\nissue_ref: 42\n---\n"},
    ])
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 1
    assert hits[0].path == ".rddf/improvements/fix-foo.md"


def test_dedup_in_roadmap_meta(tmp_path):
    """Existing change with issue_refs in roadmap-meta.yaml triggers dedup hit."""
    _setup_tmp_project(tmp_path, changes=[
        {"name": "fix-bar", "meta": "issue_refs: [42]\n"},
    ])
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 1
    assert "openspec/changes/fix-bar/roadmap-meta.yaml" in hits[0].path


def test_dedup_in_both_locations(tmp_path):
    """Both locations dedup hits are returned."""
    _setup_tmp_project(
        tmp_path,
        improvements=[
            {"name": "fix-foo", "content": "---\nissue_ref: 42\n---\n"},
        ],
        changes=[
            {"name": "fix-bar", "meta": "issue_refs: [42]\n"},
        ],
    )
    hits = check_dedup(42, tmp_path)
    assert len(hits) == 2


# === Test Group 4: write_scaffold happy path ===

def test_write_scaffold_happy_path(tmp_path):
    """Happy path writes file with required fields."""
    _setup_tmp_project(tmp_path)
    out = write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix race condition",
        body="Steps to reproduce...",
    )
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "**issue_ref**: 42" in content
    assert "**gh_repo**: foo/bar" in content
    assert "Fix race condition" in content
    assert "Steps to reproduce" in content


def test_write_scaffold_slug_collision(tmp_path):
    """When slug already exists, append -i<N> suffix."""
    _setup_tmp_project(
        tmp_path,
        improvements=[
            {"name": "fix-race-condition", "content": "---\nissue_ref: 99\n---\n"},
        ],
    )
    out = write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix race condition",
        body="...",
    )
    # New file should be fix-race-condition-i42.md
    assert out.name == "fix-race-condition-i42.md"
    assert out.exists()


def test_write_scaffold_never_touches_proposal_suggestions(tmp_path):
    """HARD-GATE: write_scaffold does not create proposal-suggestions.md."""
    _setup_tmp_project(tmp_path)
    write_scaffold(
        project_root=tmp_path,
        issue_num=42,
        gh_repo="foo/bar",
        title="Fix",
        body="...",
    )
    assert not (tmp_path / "proposal-suggestions.md").exists()
