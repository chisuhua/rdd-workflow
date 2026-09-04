"""Tests for resolved-revival semantics + reopened_count advisory.

Wave 4 Change 3:
- resolved entry + fingerprint match → status flips to open,
  reopened_count += 1, resolved_at/resolved_by preserved (audit trail)
- dismissed entry + fingerprint match → stays dismissed (asymmetric)
- reopened_count >= 3 → entry flagged with advisory_warning
- stale_only dead-code filter removed
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _seed_resolved_entry(tmp_path: Path, *, name: str = "feat-x", fingerprint: str = "fp-resolved-001") -> str:
    """Seed .planner-feedback.json with one resolved entry."""
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
        "planner_state_last_sync_at": "2026-09-04T09:00:00+00:00",
        "feedbacks": [
            {
                "feedback_id": "pf-20260904-001",
                "kind": "unmapped_proposal",
                "severity": "critical",
                "status": "resolved",
                "fingerprint": fingerprint,
                "proposal": name,
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
            }
        ],
        "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0,
                    "acknowledged": 0, "resolved": 1, "dismissed": 0},
    }
    (state_dir / ".planner-feedback.json").write_text(json.dumps(data))
    return project_root


def _seed_improvement(tmp_path: Path, name: str = "feat-x") -> None:
    improvements_dir = tmp_path / ".rddf" / "improvements"
    improvements_dir.mkdir(parents=True, exist_ok=True)
    (improvements_dir / f"{name}.md").write_text(f"---\nname: {name}\npriority: P1\n---\n")


def test_resolved_revival_flips_to_open_and_increments_count(tmp_path: Path):
    """Resolved + fingerprint match → status=open, reopened_count=1, resolved_at preserved."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
    project_root = _seed_resolved_entry(tmp_path, name="feat-x", fingerprint=fp)
    _seed_improvement(tmp_path, name="feat-x")  # same proposal → same fingerprint

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    revived = [e for e in result["feedbacks"] if e["fingerprint"] == fp]
    assert len(revived) == 1
    assert revived[0]["status"] == "open"
    assert revived[0]["reopened_count"] == 1
    assert revived[0]["resolved_at"] == "2026-09-04T09:30:00+00:00"
    assert revived[0]["resolved_by"] == "architect"


def test_dismissed_not_revival(tmp_path: Path):
    """Dismissed + fingerprint match → stays dismissed (asymmetric)."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
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
        "planner_state_last_sync_at": "2026-09-04T09:00:00+00:00",
        "feedbacks": [
            {
                "feedback_id": "pf-20260904-001",
                "kind": "unmapped_proposal",
                "severity": "critical",
                "status": "dismissed",
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
                "dismissed_at": "2026-09-04T09:30:00+00:00",
                "dismissed_by": "architect",
                "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
                "stale": False,
            }
        ],
        "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0,
                    "acknowledged": 0, "resolved": 0, "dismissed": 1},
    }
    (state_dir / ".planner-feedback.json").write_text(json.dumps(data))
    _seed_improvement(tmp_path, name="feat-x")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    matched = [e for e in result["feedbacks"] if e["fingerprint"] == fp]
    assert len(matched) == 1
    assert matched[0]["status"] == "dismissed"
    assert "reopened_count" not in matched[0] or matched[0].get("reopened_count") == 0


def test_reopened_count_persists_across_resolve_reive_cycles(tmp_path: Path):
    """Multiple resolve → revive cycles → reopened_count accumulates."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
    project_root = _seed_resolved_entry(tmp_path, name="feat-x", fingerprint=fp)
    _seed_improvement(tmp_path, name="feat-x")

    from _lib.planner_feedback import (
        compute_planner_feedback, write_planner_feedback, resolve_feedback,
    )
    first = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, first)
    assert first["feedbacks"][0]["status"] == "open"
    assert first["feedbacks"][0]["reopened_count"] == 1

    resolve_feedback(project_root, "pf-20260904-001")
    second = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, second)
    revived = [e for e in second["feedbacks"] if e["fingerprint"] == fp]
    assert revived[0]["status"] == "open"
    assert revived[0]["reopened_count"] == 2

    resolve_feedback(project_root, "pf-20260904-001")
    third = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, third)
    revived = [e for e in third["feedbacks"] if e["fingerprint"] == fp]
    assert revived[0]["reopened_count"] == 3
    assert revived[0].get("advisory_warning") == "high_reopen_count"


def test_open_entry_with_fingerprint_match_preserves_reopened_count(tmp_path: Path):
    """open (already revived) + fingerprint match → reopened_count preserved, no increment."""
    from _lib.planner_feedback import compute_fingerprint
    fp = compute_fingerprint(
        kind="unmapped_proposal",
        proposal="feat-x",
        theme="",
        related_adr_ids=[],
        reason="missing_theme_ref",
    )
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
        "planner_state_last_sync_at": "2026-09-04T09:00:00+00:00",
        "feedbacks": [
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
                "created_at": "2026-09-04T09:00:00+00:00",
                "last_seen_at": "2026-09-04T09:00:00+00:00",
                "acknowledged_at": None,
                "resolved_at": None,
                "resolved_by": None,
                "dismissed_at": None,
                "dismissed_by": None,
                "computed_from": {"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
                "stale": False,
                "reopened_count": 2,
            }
        ],
        "summary": {"open_critical": 1, "open_warning": 0, "open_info": 0,
                    "acknowledged": 0, "resolved": 0, "dismissed": 0},
    }
    (state_dir / ".planner-feedback.json").write_text(json.dumps(data))
    _seed_improvement(tmp_path, name="feat-x")

    from _lib.planner_feedback import compute_planner_feedback
    result = compute_planner_feedback(project_root)
    revived = [e for e in result["feedbacks"] if e["fingerprint"] == fp]
    assert revived[0]["status"] == "open"
    assert revived[0]["reopened_count"] == 2  # preserved, not incremented


def test_stale_only_dead_code_removed(tmp_path: Path):
    """compute_summary no longer filters status != stale_only (dead code removed)."""
    project_root = _setup_minimal(tmp_path)
    from _lib.planner_feedback import compute_summary, FeedbackEntry
    entries = [
        FeedbackEntry(
            feedback_id="pf-test-001",
            kind="unmapped_proposal",
            severity="critical",
            status="open",
            fingerprint="fp-001",
            proposal="feat-x",
            theme="",
            related_adr_ids=[],
            message="...",
            suggested_action="...",
            created_at="2026-09-04T09:00:00+00:00",
            last_seen_at="2026-09-04T09:00:00+00:00",
            acknowledged_at=None,
            resolved_at=None,
            resolved_by=None,
            dismissed_at=None,
            dismissed_by=None,
            computed_from={"state_revision": 0, "arch_handoff_revision": 0, "codebase_commit": ""},
            stale=False,
        ),
    ]
    summary = compute_summary(entries)
    assert summary["open_critical"] == 1


def _setup_minimal(tmp_path: Path) -> str:
    project_root = str(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True, exist_ok=True)
    return project_root