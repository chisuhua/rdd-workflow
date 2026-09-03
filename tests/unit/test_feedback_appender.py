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


def test_append_uses_lock_file(tmp_path):
    """Lock file .lock is created next to target during write."""
    import _lib.feedback_appender as appender_mod
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    called = []
    original = appender_mod.FileLock
    def spy(*args, **kw):
        called.append((args, kw))
        return original(*args, **kw)
    appender_mod.FileLock = spy
    try:
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body="just noting",
            ref_change=None,
        )
    finally:
        appender_mod.FileLock = original
    expected_lock = str(target) + ".lock"
    assert any(expected_lock in str(call_args) for call_args, _ in called)


def test_append_loop_guard_blocks_after_3(tmp_path):
    """3rd needs-revision succeeds; 4th raises LoopExceededError."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    for i in range(3):
        append_feedback(
            target_path=str(target),
            source="guide-design",
            kind="needs-revision",
            body=f"feedback {i}",
            ref_change=None,
        )
    with pytest.raises(LoopExceededError, match="Loop exceeded"):
        append_feedback(
            target_path=str(target),
            source="guide-design",
            kind="needs-revision",
            body="4th attempt",
            ref_change=None,
        )


def test_append_rejected_kind_does_not_count_toward_loop(tmp_path):
    """rejected kind does not bump revision_count."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="rejected",
        body="just rejecting",
        ref_change=None,
    )
    text = target.read_text()
    assert "revision_count: 1" not in text  # not bumped
    assert "revision_count: 0" in text


def test_append_invalid_source_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Invalid source"):
        append_feedback(
            target_path=str(target),
            source="not-a-source",
            kind="noted",
            body="x",
            ref_change=None,
        )


def test_append_invalid_kind_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Invalid kind"):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="bogus",
            body="x",
            ref_change=None,
        )


def test_append_empty_body_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Body length"):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body="",
            ref_change=None,
        )


def test_append_appends_in_chronological_order(tmp_path):
    """Multiple appends result in oldest-first order in file."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    for i in range(3):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body=f"entry {i}",
            ref_change=None,
        )
    text = target.read_text()
    pos0 = text.index("entry 0")
    pos1 = text.index("entry 1")
    pos2 = text.index("entry 2")
    assert pos0 < pos1 < pos2


def test_append_preserves_existing_body(tmp_path):
    """Existing ## Acceptance section is not overwritten."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n# Improve\n\n## Acceptance\n- [ ] do thing\n")
    append_feedback(
        target_path=str(target),
        source="human",
        kind="noted",
        body="review note",
        ref_change=None,
    )
    text = target.read_text()
    assert "## Acceptance\n- [ ] do thing" in text
    assert "## Feedback" in text
    assert "review note" in text