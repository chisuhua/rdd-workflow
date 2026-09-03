"""Tests for feedback_appender (atomic append-only writer)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from _lib.feedback_appender import (
    append_feedback,
    FeedbackError,
    LoopExceededError,
    generate_feedback_id,
)


def test_generate_feedback_id_format():
    """ID matches pattern feedback-YYYYMMDD-NNN."""
    fid = generate_feedback_id(seq=1)
    assert re.match(r"^feedback-\d{8}-001$", fid)


def test_generate_feedback_id_pads_seq():
    """Seq < 100 is zero-padded to 3 digits."""
    fid = generate_feedback_id(seq=42)
    assert fid.endswith("-042")


def test_append_creates_feedback_section_if_missing(tmp_path):
    """If file has no ## Feedback section, append_feedback creates one."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n# Improve\n\n## Acceptance\n- [ ] x\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="needs-revision",
        body="missing AC",
        ref_change=None,
    )
    text = target.read_text()
    assert "## Feedback" in text
    assert "### feedback-" in text
    assert "missing AC" in text


def test_append_increments_revision_count(tmp_path):
    """Each needs-revision call increments frontmatter revision_count."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="needs-revision",
        body="first feedback",
        ref_change=None,
    )
    text = target.read_text()
    assert "revision_count: 1" in text