"""Unit tests for dispatch_quick_review field (per ADR-0049 §Decision 5).

Covers:
- write_builder_handoff accepts dispatch_quick_review kwarg
- _validate_dispatch_quick_review validates complexity_confirmed + suggested_action
- _validate_dispatch_quick_review auto-fills reviewed_at
- read/write roundtrip preserves dispatch_quick_review
- update_builder_handoff partial preserves dispatch_quick_review
- schema validation: missing complexity_confirmed raises
- schema validation: invalid enum values raise
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from _lib.builder_handoff import (
    write_builder_handoff,
    read_builder_handoff,
    update_builder_handoff,
)


@pytest.fixture
def tmp_project_root():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def _valid_review(**overrides):
    """Return a valid dispatch_quick_review dict; allow overrides."""
    base = {
        "complexity_confirmed": "simple",
        "concerns": [],
        "suggested_action": "proceed",
        "data_source": "/abs/path/.rddf/improvements/foo.md",
    }
    base.update(overrides)
    return base


class TestDispatchQuickReviewWrite:
    def test_dispatch_quick_review_none_omits_field(self, tmp_project_root):
        """Backward compat: None means don't write the field (per ADR-0049)."""
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-x",
            current_phase="phase-0",
            approval_status="dispatched_to_quick",
            dispatch_quick_at="2026-09-10T10:00:00Z",
        )
        assert "dispatch_quick_review" not in handoff

    def test_dispatch_quick_review_dict_writes_field(self, tmp_project_root):
        """Dict input writes the field."""
        review = _valid_review()
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-y",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
        )
        assert "dispatch_quick_review" in handoff
        assert handoff["dispatch_quick_review"]["complexity_confirmed"] == "simple"
        assert handoff["dispatch_quick_review"]["suggested_action"] == "proceed"

    def test_dispatch_quick_review_complex_with_concerns(self, tmp_project_root):
        """complex complexity_confirmed with concerns list is preserved."""
        review = _valid_review(
            complexity_confirmed="complex",
            concerns=["touches _lib/core/", "cross-module side effects"],
            suggested_action="escalate",
        )
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-z",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
        )
        r = handoff["dispatch_quick_review"]
        assert r["complexity_confirmed"] == "complex"
        assert len(r["concerns"]) == 2
        assert "_lib/core/" in r["concerns"][0]
        assert r["suggested_action"] == "escalate"

    def test_dispatch_quick_review_auto_fills_reviewed_at(self, tmp_project_root):
        """reviewed_at is auto-filled when absent (per validation helper)."""
        review = _valid_review()  # no reviewed_at
        assert "reviewed_at" not in review
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-a",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
        )
        r = handoff["dispatch_quick_review"]
        assert "reviewed_at" in r
        # ISO format
        assert "T" in r["reviewed_at"]


class TestDispatchQuickReviewValidation:
    def test_missing_complexity_confirmed_raises(self, tmp_project_root):
        review = {
            "concerns": [],
            "suggested_action": "proceed",
            "data_source": "/abs/foo.md",
        }
        with pytest.raises(ValueError, match="complexity_confirmed"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-b",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_missing_suggested_action_raises(self, tmp_project_root):
        review = {
            "complexity_confirmed": "simple",
            "concerns": [],
            "data_source": "/abs/foo.md",
        }
        with pytest.raises(ValueError, match="suggested_action"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-c",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_invalid_complexity_confirmed_raises(self, tmp_project_root):
        review = _valid_review(complexity_confirmed="definitely-complex")
        with pytest.raises(ValueError, match="complexity_confirmed must be one of"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-d",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_invalid_suggested_action_raises(self, tmp_project_root):
        review = _valid_review(suggested_action="abort")
        with pytest.raises(ValueError, match="suggested_action must be one of"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-e",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_concerns_must_be_list(self, tmp_project_root):
        review = _valid_review(concerns="not a list")
        with pytest.raises(ValueError, match="concerns must be list"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-f",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_concerns_items_must_be_str(self, tmp_project_root):
        review = _valid_review(concerns=["ok", 42, "also-ok"])
        with pytest.raises(ValueError, match=r"concerns\[1\] must be str"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-g",
                approval_status="dispatched_to_quick",
                dispatch_quick_review=review,
            )

    def test_non_dict_raises(self, tmp_project_root):
        with pytest.raises(ValueError, match="must be dict"):
            write_builder_handoff(
                project_root=tmp_project_root,
                change_name="change-h",
                approval_status="dispatched_to_quick",
                dispatch_quick_review="not a dict",
            )


class TestDispatchQuickReviewRoundTrip:
    def test_write_then_read_preserves_review(self, tmp_project_root):
        review = _valid_review(
            complexity_confirmed="complex",
            concerns=["data migration"],
            suggested_action="escalate",
            data_source="/abs/path/.rddf/improvements/migrate.md",
        )
        write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-i",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
        )
        data = read_builder_handoff(tmp_project_root, "change-i")
        assert "dispatch_quick_review" in data
        assert data["dispatch_quick_review"]["complexity_confirmed"] == "complex"
        assert data["dispatch_quick_review"]["concerns"] == ["data migration"]
        assert data["dispatch_quick_review"]["suggested_action"] == "escalate"

    def test_update_builder_handoff_preserves_review(self, tmp_project_root):
        """update_builder_handoff partial merge preserves dispatch_quick_review (per ADR-0049)."""
        review = _valid_review(complexity_confirmed="complex")
        write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-j",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
            dispatch_quick_at="2026-09-10T10:00:00Z",
        )
        # Update only execution_status; review should be preserved
        merged = update_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-j",
            execution_status="running",
        )
        assert merged["dispatch_quick_review"]["complexity_confirmed"] == "complex"
        assert merged["dispatch_quick_at"] == "2026-09-10T10:00:00Z"
        assert merged["execution_status"] == "running"

    def test_forced_by_user_field_preserved(self, tmp_project_root):
        """forced_by_user optional field roundtrips."""
        review = _valid_review(
            complexity_confirmed="complex",
            forced_by_user=True,
        )
        write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-k",
            approval_status="dispatched_to_quick",
            dispatch_quick_review=review,
        )
        data = read_builder_handoff(tmp_project_root, "change-k")
        assert data["dispatch_quick_review"]["forced_by_user"] is True


class TestDispatchQuickReviewRegression:
    """Backward-compat: existing builder_handoff behavior unchanged."""

    def test_no_review_field_means_legacy_handoff(self, tmp_project_root):
        """Handoff written without dispatch_quick_review works exactly as before."""
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="legacy-change",
            approval_status="approved",
        )
        assert "dispatch_quick_review" not in handoff
        # Core fields still present
        assert handoff["approval_status"] == "approved"
        assert handoff["schema"] == "builder-handoff-v1"

    def test_dispatch_quick_at_unchanged(self, tmp_project_root):
        """dispatch_quick_at (per ADR-0048) still works alongside dispatch_quick_review."""
        handoff = write_builder_handoff(
            project_root=tmp_project_root,
            change_name="change-l",
            approval_status="dispatched_to_quick",
            dispatch_quick_at="2026-09-10T11:00:00Z",
            dispatch_quick_review=_valid_review(),
        )
        assert handoff["dispatch_quick_at"] == "2026-09-10T11:00:00Z"
        assert handoff["dispatch_quick_review"]["complexity_confirmed"] == "simple"
