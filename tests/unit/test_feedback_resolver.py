"""Tests for feedback_resolver (read-only proposal→change resolution)."""
from __future__ import annotations

import pytest

from _lib.feedback_resolver import resolve_change_id, ResolutionError


def test_resolver_explicit_ref_change(tmp_path):
    """--ref-change takes precedence over everything else."""
    improvement = tmp_path / "improve-foo.md"
    improvement.write_text("---\nname: improve-foo\n---\n")
    # Even if frontmatter says change=other, explicit wins
    result = resolve_change_id(
        proposal="improve-foo",
        improvement_path=str(improvement),
        explicit_ref="my-change"
    )
    assert result == "my-change"


def test_resolver_frontmatter_change_field(tmp_path):
    """If no explicit ref, read frontmatter 'change:' field."""
    improvement = tmp_path / "improve-bar.md"
    improvement.write_text("---\nname: improve-bar\nchange: bar-change\n---\n")
    result = resolve_change_id(
        proposal="improve-bar",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "bar-change"


def test_resolver_basename_fallback(tmp_path):
    """If neither explicit nor frontmatter, fall back to proposal name == change name."""
    improvement = tmp_path / "improve-baz.md"
    improvement.write_text("---\nname: improve-baz\n---\n")
    result = resolve_change_id(
        proposal="improve-baz",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "improve-baz"


def test_resolver_missing_file_falls_back_to_basename(tmp_path):
    """If improvement file does not exist, return proposal name."""
    result = resolve_change_id(
        proposal="ghost",
        improvement_path=str(tmp_path / "does-not-exist.md"),
        explicit_ref=None
    )
    assert result == "ghost"


def test_resolver_missing_frontmatter_falls_back_to_basename(tmp_path):
    """If file exists but has no frontmatter, return proposal name."""
    improvement = tmp_path / "no-front.md"
    improvement.write_text("# Just a body, no frontmatter\n")
    result = resolve_change_id(
        proposal="no-front",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "no-front"


def test_resolver_empty_change_field_falls_back(tmp_path):
    """If frontmatter 'change:' is empty string, fall back to basename."""
    improvement = tmp_path / "empty-change.md"
    improvement.write_text("---\nname: empty-change\nchange: ''\n---\n")
    result = resolve_change_id(
        proposal="empty-change",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "empty-change"


def test_resolver_malformed_frontmatter_raises(tmp_path):
    """If frontmatter has opening --- but no closing, raise ResolutionError."""
    improvement = tmp_path / "bad-fm.md"
    improvement.write_text("---\nname: bad\nno closing")
    with pytest.raises(ResolutionError, match="Malformed frontmatter"):
        resolve_change_id(
            proposal="bad-fm",
            improvement_path=str(improvement),
            explicit_ref=None
        )


def test_resolver_invalid_yaml_raises(tmp_path):
    """If frontmatter YAML is malformed, raise ResolutionError."""
    improvement = tmp_path / "bad-yaml.md"
    improvement.write_text("---\nname: [unclosed bracket\n---\n")
    with pytest.raises(ResolutionError, match="YAML parse error"):
        resolve_change_id(
            proposal="bad-yaml",
            improvement_path=str(improvement),
            explicit_ref=None
        )