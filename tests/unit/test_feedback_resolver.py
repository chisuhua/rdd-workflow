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