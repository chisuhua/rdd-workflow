"""Unit tests for skills/_lib/workflow_synthesizer.py.

Covers:
- Dataclass shape (frozen, fields)
- All 14 decision paths (parametrized + individual)
- Phase status summary (4 phases with correct detail strings)
- unblocked_changes filtering and sorting
- rddf-session active_session / orphaned_sessions
- Never-raises contract (corrupt JSON, missing state dir, exceptions)
- Determinism (sorted outputs)
"""
import dataclasses
import json
from pathlib import Path

import pytest

from skills._lib.workflow_synthesizer import (
    PhaseStatus,
    WorkflowRecommendation,
    synthesize,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path):
    """Empty project root with .rddf/state/ + openspec/changes/ created."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Handoff file helpers
# ---------------------------------------------------------------------------


def _write_arch_handoff(project_root, *, adr_count=5, roadmap_exists=True):
    """Write a valid .arch-handoff.json."""
    path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    path.write_text(json.dumps({
        "version": 1,
        "arch_complete_at": "2026-01-01T00:00:00+00:00",
        "adr_count": adr_count,
        "completed_adr_ids": [f"{i:04d}" for i in range(adr_count)],
        "roadmap_exists": roadmap_exists,
        "current_phase": "default",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
    }))


def _write_design_handoff(project_root, *, proposals_reviewed=1):
    """Write a valid .design-handoff.json."""
    path = Path(project_root) / ".rddf" / "state" / ".design-handoff.json"
    path.write_text(json.dumps({
        "version": 1,
        "design_complete_at": "2026-01-01T12:00:00+00:00",
        "proposals_reviewed": proposals_reviewed,
        "all_proposals_have_decision": True,
    }))


def _write_plan_handoff(project_root, *, active_changes=1):
    """Write a valid .plan-handoff.json."""
    path = Path(project_root) / ".rddf" / "state" / ".plan-handoff.json"
    path.write_text(json.dumps({
        "version": 1,
        "plan_done_at": "2026-01-02T00:00:00+00:00",
        "active_changes": active_changes,
    }))


def _write_iteration(project_root, changes):
    """Write a valid iteration.json with the given changes list."""
    path = Path(project_root) / ".rddf" / "state" / "iteration.json"
    path.write_text(json.dumps({
        "version": 4,
        "updated_at": "2026-01-01T00:00:00+00:00",
        "current_phase": "default",
        "changes": changes,
    }))


def _write_sessions(project_root, sessions):
    """Write a valid sessions.json."""
    path = Path(project_root) / ".rddf" / "state" / "sessions.json"
    path.write_text(json.dumps({"version": 1, "sessions": sessions}))


# ---------------------------------------------------------------------------
# Dataclass shape tests
# ---------------------------------------------------------------------------


class TestDataclassShape:
    def test_phase_status_is_frozen_dataclass(self):
        """PhaseStatus MUST be a frozen dataclass to keep recommendations immutable."""
        assert dataclasses.is_dataclass(PhaseStatus)
        assert getattr(PhaseStatus, "__dataclass_params__").frozen is True

    def test_workflow_recommendation_is_frozen_dataclass(self):
        """WorkflowRecommendation MUST be a frozen dataclass."""
        assert dataclasses.is_dataclass(WorkflowRecommendation)
        assert getattr(WorkflowRecommendation, "__dataclass_params__").frozen is True

    def test_phase_status_fields(self):
        """PhaseStatus MUST expose phase/done/detail fields."""
        ps = PhaseStatus(phase="arch", done=True, detail="adr_count=5")
        assert ps.phase == "arch"
        assert ps.done is True
        assert ps.detail == "adr_count=5"

    def test_workflow_recommendation_fields(self):
        """WorkflowRecommendation MUST expose all required fields."""
        r = WorkflowRecommendation(
            suggested_action="guide-plan",
            reason="arch done",
            confidence="high",
            phase_status=(PhaseStatus("arch", True, "ok"),),
            unblocked_changes=("c1", "c2"),
            active_session="rds_abc123def456",
            orphaned_sessions=(),
            all_options=(),
            wt_issues=(),
        )
        assert r.suggested_action == "guide-plan"
        assert r.confidence == "high"
        assert r.unblocked_changes == ("c1", "c2")
        assert r.active_session == "rds_abc123def456"
        assert r.orphaned_sessions == ()
        assert r.all_options == ()
        assert r.wt_issues == ()

    def test_frozen_dataclass_mutation_raises(self):
        """Frozen dataclass MUST raise FrozenInstanceError on mutation."""
        ps = PhaseStatus("arch", True, "ok")
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(ps, "done", False)


# ---------------------------------------------------------------------------
# Path 1: arch-handoff missing -> guide-arch
# ---------------------------------------------------------------------------


class TestPathArchMissing:
    def test_arch_missing_recommends_guide_arch(self, project_root):
        """Path 1: no .arch-handoff.json -> guide-arch, confidence=high."""
        r = synthesize(project_root)
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"
        assert "arch" in r.reason.lower() or "架构" in r.reason

    def test_arch_missing_when_state_dir_empty(self, tmp_path):
        """Path 1 also fires when .rddf/state/ exists but is empty."""
        (tmp_path / ".rddf" / "state").mkdir(parents=True)
        r = synthesize(str(tmp_path))
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Path 2: arch-handoff exists, adr_count < 1 -> guide-arch (recover)
# ---------------------------------------------------------------------------


class TestPathArchIncomplete:
    def test_adr_count_zero_recommends_guide_arch(self, project_root):
        """Path 2: arch-handoff exists but adr_count=0 -> guide-arch."""
        _write_arch_handoff(project_root, adr_count=0)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"

    def test_adr_count_missing_recommends_guide_arch(self, project_root):
        """Path 2: arch-handoff exists but adr_count field missing -> guide-arch."""
        path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
        path.write_text(json.dumps({"version": 1, "arch_complete_at": "x"}))
        r = synthesize(project_root)
        assert r.suggested_action == "guide-arch"


# ---------------------------------------------------------------------------
# Path 3: arch done, design-handoff missing -> guide-design
# ---------------------------------------------------------------------------


class TestPathArchDoneDesignMissing:
    def test_arch_done_design_missing_recommends_guide_design(self, project_root):
        """Path 3: arch-handoff ok, no design-handoff -> guide-design."""
        _write_arch_handoff(project_root, adr_count=5)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-design"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Path 4: arch done, design done, plan-handoff missing -> guide-plan
# ---------------------------------------------------------------------------


class TestPathArchDoneDesignDonePlanMissing:
    def test_arch_done_plan_missing_recommends_guide_plan(self, project_root):
        """Path 4: arch-handoff + design-handoff ok, no plan-handoff -> guide-plan."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-plan"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Path 5: plan-handoff exists, active_changes=0 -> guide-ship (cleanup)
# ---------------------------------------------------------------------------


class TestPathPlanHandoffZeroActive:
    def test_plan_handoff_zero_active_recommends_guide_ship_cleanup(
        self, project_root
    ):
        """Path 5: plan-handoff exists, active_changes=0 -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=0)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Path 6: plan-handoff exists, active_changes>0 -> guide-ship
# ---------------------------------------------------------------------------


class TestPathPlanHandoffActiveChanges:
    def test_plan_handoff_active_changes_recommends_guide_ship(
        self, project_root, monkeypatch
    ):
        """Path 6: plan-handoff exists, active_changes>0, no worktree -> guide-ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=3)
        # Mock no worktrees, no committed change -> path 6 default
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [])
        monkeypatch.setattr(ws, "_committed_change_in_head", lambda pr: False)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Path 7: worktree with incomplete tasks -> guide-ship
# ---------------------------------------------------------------------------


class TestPathWorktreeInProgress:
    def test_worktree_incomplete_tasks_recommends_guide_ship(
        self, project_root, monkeypatch
    ):
        """Path 7: worktree has incomplete tasks -> guide-ship (medium)."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [
            {
                "path": "/fake/wt",
                "branch": "refs/heads/openspec/c1",
                "is_openspec": True,
            }
        ])
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt: True)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"


# ---------------------------------------------------------------------------
# Path 8: detached openspec worktrees -> guide-ship
# ---------------------------------------------------------------------------


class TestPathDetachedWorktrees:
    def test_detached_worktrees_recommends_guide_ship(
        self, project_root, monkeypatch
    ):
        """Path 8: detached openspec worktrees -> guide-ship (medium)."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [
            {
                "path": "/fake/wt1",
                "branch": "refs/heads/openspec/c1",
                "is_openspec": True,
            }
        ])
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt: False)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"
        assert "worktree" in r.reason or "分离" in r.reason

    def test_multiple_detached_worktrees_count_in_reason(
        self, project_root, monkeypatch
    ):
        """Path 8: reason string MUST include the worktree count."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [
            {"path": "/wt1", "branch": "refs/heads/openspec/a", "is_openspec": True},
            {"path": "/wt2", "branch": "refs/heads/openspec/b", "is_openspec": True},
            {"path": "/wt3", "branch": "refs/heads/openspec/c", "is_openspec": True},
        ])
        monkeypatch.setattr(ws, "_worktree_has_incomplete_tasks", lambda wt: False)
        r = synthesize(project_root)
        assert "3" in r.reason


# ---------------------------------------------------------------------------
# Path 10: committed change in HEAD, no worktree -> guide-ship
# ---------------------------------------------------------------------------


class TestPathCommittedChangeInHead:
    def test_committed_change_recommends_guide_ship(
        self, project_root, monkeypatch
    ):
        """Path 10: committed change in HEAD, no worktree -> guide-ship (medium)."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=1)
        from skills._lib import workflow_synthesizer as ws
        monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [])
        monkeypatch.setattr(ws, "_committed_change_in_head", lambda pr: True)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "medium"


# ---------------------------------------------------------------------------
# Phase status summary (4 phases)
# ---------------------------------------------------------------------------


class TestPhaseStatusSummary:
    def test_phase_status_has_4_entries(self, project_root):
        """phase_status MUST be a tuple of 4 entries: arch, design, plan, ship."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=2)
        r = synthesize(project_root)
        assert len(r.phase_status) == 4
        phases = [ps.phase for ps in r.phase_status]
        assert phases == ["arch", "design", "plan", "ship"]

    def test_phase_status_arch_done_detail(self, project_root):
        """phase_status arch entry MUST show adr_count in detail when done."""
        _write_arch_handoff(project_root, adr_count=7)
        r = synthesize(project_root)
        arch_ps = r.phase_status[0]
        assert arch_ps.phase == "arch"
        assert arch_ps.done is True
        assert "adr_count=7" in arch_ps.detail

    def test_phase_status_arch_missing_detail(self, project_root):
        """phase_status arch entry MUST show 'no handoff' when missing."""
        r = synthesize(project_root)
        arch_ps = r.phase_status[0]
        assert arch_ps.done is False
        assert "no handoff" in arch_ps.detail

    def test_phase_status_design_done_detail(self, project_root):
        """phase_status design entry MUST show proposals_reviewed in detail when done."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        r = synthesize(project_root)
        design_ps = r.phase_status[1]
        assert design_ps.phase == "design"
        assert design_ps.done is True
        assert "proposals_reviewed=3" in design_ps.detail

    def test_phase_status_design_missing_detail(self, project_root):
        """phase_status design entry MUST show 'no handoff' when missing."""
        _write_arch_handoff(project_root, adr_count=5)
        r = synthesize(project_root)
        design_ps = r.phase_status[1]
        assert design_ps.phase == "design"
        assert design_ps.done is False
        assert "no handoff" in design_ps.detail

    def test_phase_status_plan_done_detail(self, project_root):
        """phase_status plan entry MUST show active_changes in detail when done."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_design_handoff(project_root, proposals_reviewed=3)
        _write_plan_handoff(project_root, active_changes=4)
        r = synthesize(project_root)
        plan_ps = r.phase_status[2]
        assert plan_ps.phase == "plan"
        assert plan_ps.done is True
        assert "active_changes=4" in plan_ps.detail

    def test_phase_status_ship_detail_with_iteration(self, project_root):
        """phase_status ship entry MUST show change count from iteration."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "c1", "status": "archived", "added_at": "x"},
            {"name": "c2", "status": "proposed", "added_at": "x"},
        ])
        r = synthesize(project_root)
        ship_ps = r.phase_status[3]
        assert ship_ps.phase == "ship"
        assert "changes=2" in ship_ps.detail
        assert "archived=1" in ship_ps.detail

    def test_phase_status_ship_default_no_iteration(self, project_root):
        """phase_status ship entry defaults to 'no worktree' when no iteration."""
        _write_arch_handoff(project_root, adr_count=5)
        r = synthesize(project_root)
        ship_ps = r.phase_status[3]
        assert "no worktree" in ship_ps.detail


# ---------------------------------------------------------------------------
# unblocked_changes
# ---------------------------------------------------------------------------


class TestUnblockedChanges:
    def test_unblocked_changes_filters_blocked(self, project_root):
        """unblocked_changes MUST exclude changes with non-null blocker."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "c-ready-1", "status": "proposed", "added_at": "x", "blocker": None},
            {"name": "c-blocked", "status": "proposed", "added_at": "x", "blocker": "c-ready-1"},
            {"name": "c-ready-2", "status": "in_worktree", "added_at": "x", "blocker": None},
            {"name": "c-archived", "status": "archived", "added_at": "x", "blocker": None},
            {"name": "c-planned", "status": "planned", "added_at": "x", "blocker": None},
            {"name": "c-completed", "status": "completed", "added_at": "x", "blocker": None},
        ])
        r = synthesize(project_root)
        assert r.unblocked_changes == ("c-ready-1", "c-ready-2")

    def test_unblocked_changes_empty_iteration(self, project_root):
        """unblocked_changes MUST be () when iteration is missing."""
        _write_arch_handoff(project_root, adr_count=5)
        r = synthesize(project_root)
        assert r.unblocked_changes == ()

    def test_unblocked_changes_sorted_alphabetically(self, project_root):
        """unblocked_changes MUST be sorted alphabetically for determinism."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "zeta", "status": "proposed", "added_at": "x"},
            {"name": "alpha", "status": "proposed", "added_at": "x"},
            {"name": "middle", "status": "in_worktree", "added_at": "x"},
        ])
        r = synthesize(project_root)
        assert r.unblocked_changes == ("alpha", "middle", "zeta")

    def test_unblocked_changes_empty_string_blocker_treated_as_unblocked(
        self, project_root
    ):
        """unblocked_changes MUST treat empty-string blocker as unblocked."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "c1", "status": "proposed", "added_at": "x", "blocker": ""},
        ])
        r = synthesize(project_root)
        assert r.unblocked_changes == ("c1",)


# ---------------------------------------------------------------------------
# rddf-session: active_session
# ---------------------------------------------------------------------------


class TestActiveSession:
    def test_active_session_bound_when_env_set(self, project_root, monkeypatch):
        """active_session MUST return rds_id when OPENCODE_SESSION_ID matches."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [
            {
                "session_id": "rds_abc123def456",
                "kind": "stage_plan",
                "owner_opencode_session_id": "ses_mine",
                "state": "active",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
            {
                "session_id": "rds_other99999999",
                "kind": "stage_arch",
                "owner_opencode_session_id": "ses_other",
                "state": "active",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
        ])
        monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_mine")
        r = synthesize(project_root)
        assert r.active_session == "rds_abc123def456"

    def test_active_session_none_when_env_unset(self, project_root, monkeypatch):
        """active_session MUST be None when OPENCODE_SESSION_ID is unset."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [])
        monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
        r = synthesize(project_root)
        assert r.active_session is None

    def test_active_session_none_when_no_match(self, project_root, monkeypatch):
        """active_session MUST be None when no session matches the env var."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [
            {
                "session_id": "rds_abc123def456",
                "kind": "stage_plan",
                "owner_opencode_session_id": "ses_other",
                "state": "active",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
        ])
        monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_mine")
        r = synthesize(project_root)
        assert r.active_session is None

    def test_active_session_ignores_orphaned(self, project_root, monkeypatch):
        """active_session MUST NOT match orphaned sessions even if owner matches."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [
            {
                "session_id": "rds_orphaned1234",
                "kind": "stage_plan",
                "owner_opencode_session_id": "ses_mine",
                "state": "orphaned",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
        ])
        monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_mine")
        r = synthesize(project_root)
        assert r.active_session is None


# ---------------------------------------------------------------------------
# rddf-session: orphaned_sessions
# ---------------------------------------------------------------------------


class TestOrphanedSessions:
    def test_orphaned_sessions_listed_sorted_by_started_at_desc(self, project_root):
        """orphaned_sessions MUST list orphaned rds_ids sorted newest-first."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [
            {
                "session_id": "rds_older000001",
                "kind": "stage_arch",
                "owner_opencode_session_id": None,
                "state": "orphaned",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
            {
                "session_id": "rds_newer000002",
                "kind": "stage_plan",
                "owner_opencode_session_id": None,
                "state": "orphaned",
                "started_at": "2026-02-01T00:00:00+00:00",
                "last_heartbeat": "2026-02-01T00:00:00+00:00",
            },
        ])
        r = synthesize(project_root)
        assert r.orphaned_sessions == ("rds_newer000002", "rds_older000001")

    def test_orphaned_sessions_empty_when_no_orphans(self, project_root):
        """orphaned_sessions MUST be () when no orphaned sessions exist."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_sessions(project_root, [
            {
                "session_id": "rds_active123456",
                "kind": "stage_arch",
                "owner_opencode_session_id": "ses_x",
                "state": "active",
                "started_at": "2026-01-01T00:00:00+00:00",
                "last_heartbeat": "2026-01-01T00:00:00+00:00",
            },
        ])
        r = synthesize(project_root)
        assert r.orphaned_sessions == ()

    def test_orphaned_sessions_empty_when_no_sessions_file(self, project_root):
        """orphaned_sessions MUST be () when sessions.json is missing."""
        _write_arch_handoff(project_root, adr_count=5)
        r = synthesize(project_root)
        assert r.orphaned_sessions == ()


# ---------------------------------------------------------------------------
# Never-raises contract + corrupt state resilience
# ---------------------------------------------------------------------------


class TestNeverRaises:
    def test_corrupt_sessions_json_does_not_raise(self, project_root):
        """synthesize MUST NOT raise on corrupt sessions.json."""
        _write_arch_handoff(project_root, adr_count=5)
        sessions_path = (
            Path(project_root) / ".rddf" / "state" / "sessions.json"
        )
        sessions_path.write_text("{not valid json")
        r = synthesize(project_root)
        # state_reader returns None for corrupt JSON, so synthesizer proceeds
        assert r.suggested_action in ("guide-plan", "guide-ship", "guide-arch", "guide-design")

    def test_corrupt_iteration_json_does_not_raise(self, project_root):
        """synthesize MUST NOT raise on corrupt iteration.json."""
        _write_arch_handoff(project_root, adr_count=5)
        iteration_path = (
            Path(project_root) / ".rddf" / "state" / "iteration.json"
        )
        iteration_path.write_text("{broken json")
        r = synthesize(project_root)
        assert r.suggested_action in ("guide-plan", "guide-ship", "guide-arch", "guide-design")

    def test_missing_state_dir_returns_recommendation(self, tmp_path):
        """synthesize MUST NOT raise when .rddf/state/ doesn't exist."""
        project_root = str(tmp_path)
        # No .rddf/state/ created
        r = synthesize(project_root)
        # All reads return None -> path 1 fires -> guide-arch
        assert r.suggested_action == "guide-arch"
        assert r.confidence == "high"

    def test_exception_returns_fallback_recommendation(
        self, project_root, monkeypatch
    ):
        """synthesize MUST return fallback on unexpected exception."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer as ws

        def boom(_):
            raise RuntimeError("forced")

        monkeypatch.setattr(ws.state_reader, "read_arch_handoff", boom)
        r = synthesize(project_root)
        assert r.suggested_action == "guide-ship"
        assert r.confidence == "low"
        assert "fallback" in r.reason.lower()

    def test_fallback_recommendation_has_4_phase_status_entries(
        self, project_root, monkeypatch
    ):
        """Fallback recommendation MUST include 4 phase_status entries."""
        _write_arch_handoff(project_root, adr_count=5)
        from skills._lib import workflow_synthesizer as ws

        def boom(_):
            raise RuntimeError("forced")

        monkeypatch.setattr(ws.state_reader, "read_arch_handoff", boom)
        r = synthesize(project_root)
        assert len(r.phase_status) == 4
        phases = [ps.phase for ps in r.phase_status]
        assert phases == ["arch", "design", "plan", "ship"]


# ---------------------------------------------------------------------------
# Worktree helper: _worktree_has_incomplete_tasks
# ---------------------------------------------------------------------------


class TestWorktreeHasIncompleteTasks:
    def test_incomplete_tasks_detected(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST return True when tasks.md has `- [ ]`."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        changes_dir = wt / "openspec" / "changes" / "c1"
        changes_dir.mkdir(parents=True)
        (changes_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] done task\n- [ ] incomplete task\n"
        )
        assert _worktree_has_incomplete_tasks(str(wt)) is True

    def test_all_complete_tasks_returns_false(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST return False when all tasks done."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        changes_dir = wt / "openspec" / "changes" / "c1"
        changes_dir.mkdir(parents=True)
        (changes_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] done task\n- [x] another done\n"
        )
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_no_tasks_md_returns_false(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST return False when no tasks.md."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        changes_dir = wt / "openspec" / "changes" / "c1"
        changes_dir.mkdir(parents=True)
        # No tasks.md created
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_no_changes_dir_returns_false(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST return False when no changes dir."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        # No openspec/changes/ dir created
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_incomplete_task_at_file_start(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST detect `- [ ]` at file start."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        changes_dir = wt / "openspec" / "changes" / "c1"
        changes_dir.mkdir(parents=True)
        (changes_dir / "tasks.md").write_text("- [ ] first task incomplete\n")
        assert _worktree_has_incomplete_tasks(str(wt)) is True

    def test_skips_archive_dir(self, tmp_path):
        """_worktree_has_incomplete_tasks MUST skip archive/ subdirectory."""
        from skills._lib.workflow_synthesizer import _worktree_has_incomplete_tasks
        wt = tmp_path / "wt"
        archive_dir = wt / "openspec" / "changes" / "archive" / "old-change"
        archive_dir.mkdir(parents=True)
        (archive_dir / "tasks.md").write_text("- [ ] incomplete in archive\n")
        assert _worktree_has_incomplete_tasks(str(wt)) is False


# ---------------------------------------------------------------------------
# Parametrized decision tree coverage (all 13 paths)
# ---------------------------------------------------------------------------


class TestDecisionTreeAllPaths:
    """Parametrized coverage of all decision paths."""

    @pytest.mark.parametrize(
        "scenario,arch_adr_count,has_design_handoff,has_plan_handoff,"
        "plan_active_changes,has_worktree,worktree_incomplete,"
        "has_committed_change,expected_action,expected_confidence",
        [
            # Path 1: no arch-handoff
            ("p1-no-arch", None, False, False, 0, False, False, False, "guide-arch", "high"),
            # Path 2: arch-handoff exists, adr_count < 1
            ("p2-adr-zero", 0, False, False, 0, False, False, False, "guide-arch", "high"),
            # Path 3: arch done, no design-handoff
            ("p3-no-design", 5, False, False, 0, False, False, False, "guide-design", "high"),
            # Path 4: arch + design done, no plan-handoff
            ("p4-no-plan", 5, True, False, 0, False, False, False, "guide-plan", "high"),
            # Path 5: plan-handoff exists, 0 active
            ("p5-plan-zero", 5, True, True, 0, False, False, False, "guide-ship", "high"),
            # Path 6: plan-handoff, active>0, no worktree
            ("p6-plan-active", 5, True, True, 1, False, False, False, "guide-ship", "high"),
            # Path 7: worktree with incomplete tasks
            ("p7-wt-incomplete", 5, True, True, 1, True, True, False, "guide-ship", "medium"),
            # Path 8: detached worktrees (no incomplete)
            ("p8-detached-wt", 5, True, True, 1, True, False, False, "guide-ship", "medium"),
            # Path 10: committed change, no worktree
            ("p10-committed", 5, True, True, 1, False, False, True, "guide-ship", "medium"),
        ],
    )
    def test_decision_path(
        self, project_root, monkeypatch, scenario, arch_adr_count,
        has_design_handoff, has_plan_handoff, plan_active_changes,
        has_worktree, worktree_incomplete, has_committed_change,
        expected_action, expected_confidence,
    ):
        from skills._lib import workflow_synthesizer as ws

        if arch_adr_count is not None:
            _write_arch_handoff(project_root, adr_count=arch_adr_count)
        if has_design_handoff:
            _write_design_handoff(project_root, proposals_reviewed=3)
        if has_plan_handoff:
            _write_plan_handoff(
                project_root, active_changes=plan_active_changes
            )

        if has_worktree:
            monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [
                {
                    "path": "/fake/wt",
                    "branch": "refs/heads/openspec/c1",
                    "is_openspec": True,
                }
            ])
        else:
            monkeypatch.setattr(ws, "_list_worktrees", lambda pr: [])
        monkeypatch.setattr(
            ws, "_worktree_has_incomplete_tasks", lambda wt: worktree_incomplete
        )
        monkeypatch.setattr(
            ws, "_committed_change_in_head", lambda pr: has_committed_change
        )

        r = synthesize(project_root)
        assert r.suggested_action == expected_action, (
            f"scenario={scenario}: expected {expected_action}, "
            f"got {r.suggested_action} (reason={r.reason})"
        )
        assert r.confidence == expected_confidence, (
            f"scenario={scenario}: expected confidence {expected_confidence}, "
            f"got {r.confidence}"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self, project_root):
        """synthesize MUST return identical recommendations for identical inputs."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "b", "status": "proposed", "added_at": "x"},
            {"name": "a", "status": "proposed", "added_at": "x"},
        ])
        r1 = synthesize(project_root)
        r2 = synthesize(project_root)
        assert r1 == r2

    def test_unblocked_changes_deterministic_order(self, project_root):
        """unblocked_changes MUST be sorted deterministically."""
        _write_arch_handoff(project_root, adr_count=5)
        _write_iteration(project_root, [
            {"name": "z", "status": "proposed", "added_at": "x"},
            {"name": "a", "status": "proposed", "added_at": "x"},
            {"name": "m", "status": "proposed", "added_at": "x"},
        ])
        r = synthesize(project_root)
        assert r.unblocked_changes == ("a", "m", "z")
