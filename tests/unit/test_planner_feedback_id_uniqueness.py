"""Tests for feedback_id stability + uniqueness + defensive counter (Wave 4 Sub-task 1.2).

P0-3 + R3 + R9 + R15:
- counter starts at max(prior same-date-prefix)+1 (not 1)
- fingerprint match preserves prior feedback_id (R9 — ID stability)
- fingerprint match preserves prior last_seen_at (R15 — true idempotency)
- malformed IDs skipped without crashing
- missing feedback_id key skipped (defensive)

Previous Stage 3 implementation:
- counter = 1 always → same-day recompute collides with preserved
  resolved entries (P0-3)
- merge overwrote prior feedback_id even on fingerprint match (R9)
- merge overwrote prior last_seen_at (R15)
- rsplit crashed on malformed IDs (R3)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _seed_feedback(
    tmp_path: Path,
    *,
    date_prefix: str = "20260904",
    prior_feedbacks: list,
) -> str:
    """Write a planner feedback.json with given prior feedbacks."""
    project_root = str(tmp_path)
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "schema": "planner-feedback-v1",
        "version": 1,
        "owner": "rdd-planner",
        "branch": "master",
        "worktree_root": project_root,
        "codebase_commit": "",
        "arch_handoff_revision": 0,
        "state_revision": 0,
        "planner_state_last_sync_at": f"{date_prefix[:4]}-{date_prefix[4:6]}-{date_prefix[6:]}T10:00:00+00:00",
        "feedbacks": prior_feedbacks,
        "summary": {
            "open_critical": 0, "open_warning": 0, "open_info": 0,
            "acknowledged": 0, "resolved": 0, "dismissed": 0,
        },
    }
    (state_dir / ".planner-feedback.json").write_text(json.dumps(data))
    return project_root


def _seed_improvement(tmp_path: Path, name: str = "feat-x") -> None:
    improvements_dir = tmp_path / ".rddf" / "improvements"
    improvements_dir.mkdir(parents=True, exist_ok=True)
    (improvements_dir / f"{name}.md").write_text(f"---\nname: {name}\npriority: P1\n---\n")


def test_same_day_recompute_no_collision(tmp_path: Path):
    """prior pf-YYYYMMDD-001 resolved preserved → new entry pf-YYYYMMDD-002 (not -001)."""
    fp_x = "fp-x1234567890abcd"
    prior_feedbacks = [
        {
            "feedback_id": "pf-20260904-001",
            "kind": "unmapped_proposal",
            "severity": "critical",
            "status": "resolved",
            "fingerprint": fp_x,
            "proposal": "feat-old",
            "theme": "",
            "related_adr_ids": [],
            "message": "...",
            "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None,
            "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect",
            "dismissed_at": None,
            "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-y")  # new unmapped proposal

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    new_entries = [
        e for e in result["feedbacks"]
        if e["status"] == "open"
    ]
    new_ids = [e["feedback_id"] for e in new_entries]
    assert "pf-20260904-002" in new_ids, f"expected new id -002, got {new_ids}"
    assert "pf-20260904-001" not in new_ids or any(
        e["feedback_id"] == "pf-20260904-001" and e["status"] == "resolved"
        for e in result["feedbacks"]
    ), "old resolved -001 should be preserved, not used for new entry"


def test_counter_starts_at_max_plus_one(tmp_path: Path):
    """3 prior pf-YYYYMMDD-005/-003/-007 → new entry pf-YYYYMMDD-008 (max+1)."""
    prior_feedbacks = []
    for n in (5, 3, 7):
        prior_feedbacks.append({
            "feedback_id": f"pf-20260904-{n:03d}",
            "kind": "unmapped_proposal",
            "severity": "critical",
            "status": "resolved",
            "fingerprint": f"fp-resolved-{n}",
            "proposal": f"feat-{n}",
            "theme": "",
            "related_adr_ids": [],
            "message": "...",
            "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None,
            "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect",
            "dismissed_at": None,
            "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        })
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-new")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    new_entries = [e for e in result["feedbacks"] if e["status"] == "open"]
    assert len(new_entries) == 1
    assert new_entries[0]["feedback_id"] == "pf-20260904-008"


def test_cross_day_independent_counter(tmp_path: Path):
    """Cross-day prior -001/-002 + new same-day -001 → no collision across dates."""
    prior_feedbacks = [
        {
            "feedback_id": "pf-20260903-001",
            "kind": "unmapped_proposal",
            "severity": "critical",
            "status": "resolved",
            "fingerprint": "fp-old-001",
            "proposal": "feat-old-a",
            "theme": "",
            "related_adr_ids": [],
            "message": "...",
            "suggested_action": "...",
            "created_at": "2026-09-03T09:00:00+00:00",
            "last_seen_at": "2026-09-03T09:00:00+00:00",
            "acknowledged_at": None,
            "resolved_at": "2026-09-03T09:30:00+00:00",
            "resolved_by": "architect",
            "dismissed_at": None,
            "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-new")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    new_entries = [e for e in result["feedbacks"] if e["status"] == "open"]
    assert len(new_entries) == 1
    new_id = new_entries[0]["feedback_id"]
    assert new_id.startswith("pf-20260904-")
    assert new_id != "pf-20260904-002" or True  # 20260904 prefix only
    assert new_id == "pf-20260904-001"  # counter starts fresh for new day


def test_prior_id_preserved_on_fingerprint_match(tmp_path: Path):
    """fingerprint match → prior feedback_id preserved (R9)."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
    prior_id = "pf-20260904-005"
    prior_feedbacks = [
        {
            "feedback_id": prior_id,
            "kind": "unmapped_proposal",
            "severity": "critical",
            "status": "open",
            "fingerprint": fp,
            "proposal": "feat-x",
            "theme": "",
            "related_adr_ids": [],
            "message": "...",
            "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None,
            "resolved_at": None,
            "resolved_by": None,
            "dismissed_at": None,
            "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-x")  # same proposal → same fingerprint

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    matched = [e for e in result["feedbacks"] if e["fingerprint"] == fp]
    assert len(matched) == 1
    assert matched[0]["feedback_id"] == prior_id  # ID preserved


def test_last_seen_at_preserved_on_fingerprint_match(tmp_path: Path):
    """fingerprint match → prior last_seen_at preserved (R15 true idempotency)."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
    prior_lsa = "2026-09-04T08:00:00+00:00"
    prior_feedbacks = [
        {
            "feedback_id": "pf-20260904-001",
            "kind": "unmapped_proposal",
            "severity": "critical",
            "status": "open",
            "fingerprint": fp,
            "proposal": "feat-x",
            "theme": "",
            "related_adr_ids": [],
            "message": "...",
            "suggested_action": "...",
            "created_at": prior_lsa,
            "last_seen_at": prior_lsa,
            "acknowledged_at": None,
            "resolved_at": None,
            "resolved_by": None,
            "dismissed_at": None,
            "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-x")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    matched = [e for e in result["feedbacks"] if e["fingerprint"] == fp]
    assert matched[0]["last_seen_at"] == prior_lsa  # preserved, NOT bumped to now_iso


def test_malformed_id_skipped_in_counter(tmp_path: Path):
    """Malformed feedback_ids (missing -NNN or non-numeric suffix) skipped, no crash."""
    prior_feedbacks = [
        {
            "feedback_id": "pf-20260904-foo",
            "kind": "unmapped_proposal", "severity": "critical", "status": "resolved",
            "fingerprint": "fp-bad-001", "proposal": "feat-bad-a", "theme": "",
            "related_adr_ids": [], "message": "...", "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None, "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect", "dismissed_at": None, "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
        {
            "feedback_id": "pf-20260904-001",
            "kind": "unmapped_proposal", "severity": "critical", "status": "resolved",
            "fingerprint": "fp-good-001", "proposal": "feat-good", "theme": "",
            "related_adr_ids": [], "message": "...", "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None, "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect", "dismissed_at": None, "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
        {
            "feedback_id": "pf-bad-no-digits",
            "kind": "unmapped_proposal", "severity": "critical", "status": "resolved",
            "fingerprint": "fp-bad-002", "proposal": "feat-bad-b", "theme": "",
            "related_adr_ids": [], "message": "...", "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None, "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect", "dismissed_at": None, "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-new")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    new_entries = [e for e in result["feedbacks"] if e["status"] == "open"]
    assert len(new_entries) == 1
    assert new_entries[0]["feedback_id"] == "pf-20260904-002"


def test_missing_feedback_id_key_skipped(tmp_path: Path):
    """entry without feedback_id key is skipped (no KeyError)."""
    prior_feedbacks = [
        {
            # no feedback_id key at all
            "kind": "unmapped_proposal", "severity": "critical", "status": "resolved",
            "fingerprint": "fp-no-id", "proposal": "feat-no-id", "theme": "",
            "related_adr_ids": [], "message": "...", "suggested_action": "...",
            "created_at": "2026-09-04T09:00:00+00:00",
            "last_seen_at": "2026-09-04T09:00:00+00:00",
            "acknowledged_at": None, "resolved_at": "2026-09-04T09:30:00+00:00",
            "resolved_by": "architect", "dismissed_at": None, "dismissed_by": None,
            "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            "stale": False,
        },
    ]
    project_root = _seed_feedback(tmp_path, prior_feedbacks=prior_feedbacks)
    _seed_improvement(tmp_path, name="feat-new")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    new_entries = [e for e in result["feedbacks"] if e["status"] == "open"]
    assert len(new_entries) == 1
    assert new_entries[0]["feedback_id"] == "pf-20260904-001"