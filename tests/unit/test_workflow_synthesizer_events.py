"""AC-G3 fixture: workflow_synthesizer consumes events.jsonl → child_progress field.

Per ADR-0056 decision 6 + improvement M2:
- AC-G3: synthesizer output 含 "X 完成 N/M" 格式
- M2: workflow_synthesizer.synthesize() 返回的 Recommendation 必须含 child_progress 字段
- W2.2 (complete-guide-orchestrator-flow): synthesizer 消费 events.jsonl

These tests lock down:
1. Zero-IO guard: no events.jsonl read when no active stage_X children
2. Aggregated progress: phase_started/phase_completed counts per session
3. Schema tolerance (MN1): .get() everywhere, no schema changes
4. Deterministic ordering: by kind then session_id
5. AC-G3 example pattern: 2 children + 5 events → "X 完成 N/M" in detail strings
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from _lib.workflow_synthesizer import (
    ChildProgress,
    WorkflowRecommendation,
    _active_stage_x_children,
    _read_events_for_children,
    synthesize,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh project_root + .rddf/state/ for AC-G3 fixture."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    yield tmp_path


def _run_hook(kind: str, intent: str, owner: str = "ac_g3_owner"):
    """Run the bash hook end-to-end (matches test_ac_g1_red_green style)."""
    cmd = [
        "bash", "-c",
        f'source "{HOOKS_SH}" && '
        f'rddf_session_hook_entry {kind} {intent} "ac-g3-subject" "ok"'
    ]
    import os as _os
    env = _os.environ.copy()
    env["OPENCODE_SESSION_ID"] = owner
    env["RDDF_OWNER"] = owner
    env["RDDF_OWNER_FROM"] = "shell-pid"
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
    )


def _append_phase_event(events_file: Path, session_id: str, kind: str,
                       event_type: str = "phase_started", ts: str = None):
    """Append a phase event directly to events.jsonl (no bash subprocess)."""
    from datetime import datetime, timezone
    row = {
        "event_id": f"evt_test_{ts or datetime.now(timezone.utc).isoformat()}",
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": "info",
        "message": f"test event for {kind}/{session_id}",
        "context": {
            "session_id": session_id,
            "kind": kind,
            "parent_session_id": None,
            "owner_opencode_session_id": "test_owner",
        },
    }
    with events_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- AC-G3 core: 2 children + 5 events → "X 完成 N/M" pattern ---

class TestAC_G3_Fixture:
    """The AC-G3 example from ADR-0056: 2 stage_X children + 5 events."""

    def test_two_children_five_events_renders_completed_over_total(self, tmp_project):
        """2 active stage_X children + 5 events (3 started, 2 completed)
        → synthesizer output contains "X 完成 N/M" detail strings."""
        # Create 2 sessions via real hook calls (end-to-end)
        proc_b = _run_hook("stage_builder", "rdd-builder", owner="owner_B")
        proc_v = _run_hook("stage_verify", "rdd-verifier", owner="owner_V")
        assert proc_b.returncode == 0
        assert proc_v.returncode == 0

        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        # Each hook entry already wrote 1 phase_started; add 4 more events
        # for a total of 5 events (3 started, 2 completed)
        sid_b = json.loads((tmp_project / ".rddf" / "state" / "sessions.json").read_text())["sessions"][0]["session_id"]
        sid_v = json.loads((tmp_project / ".rddf" / "state" / "sessions.json").read_text())["sessions"][1]["session_id"]
        # Append 2 more started + 2 completed across the 2 children
        _append_phase_event(events_file, sid_b, "stage_builder", "phase_started", "2026-09-24T01:00:00+00:00")
        _append_phase_event(events_file, sid_v, "stage_verify", "phase_started", "2026-09-24T01:01:00+00:00")
        _append_phase_event(events_file, sid_b, "stage_builder", "phase_completed", "2026-09-24T01:02:00+00:00")
        _append_phase_event(events_file, sid_v, "stage_verify", "phase_completed", "2026-09-24T01:03:00+00:00")

        rec = synthesize(str(tmp_project))
        # 2 children with events → 2 ChildProgress entries
        assert len(rec.child_progress) == 2, f"expected 2 entries; got {len(rec.child_progress)}"
        # AC-G3: each detail contains "X 完成 N/M"
        details = [cp.detail for cp in rec.child_progress]
        for d in details:
            assert "完成" in d, f"detail missing '完成' (AC-G3 pattern): {d}"
            # Match "X 完成 N/M" where N/M are integers
            import re
            assert re.search(r"\d+/\d+", d), f"detail missing N/M pattern: {d}"


# --- Zero-IO guard: no active children = no events read ---

class TestZeroIOGuard:
    """MN1: zero-IO when no active stage_X children exist."""

    def test_no_sessions_no_events_io(self, tmp_project):
        """No sessions.json + no events.jsonl → empty child_progress, no crash."""
        rec = synthesize(str(tmp_project))
        assert rec.child_progress == ()

    def test_sessions_exist_but_no_active_stage_x(self, tmp_project):
        """Sessions.json with completed sessions only → empty child_progress."""
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_old", "kind": "stage_builder",
                 "owner_opencode_session_id": "owner_X", "state": "completed",
                 "goal": {}, "started_at": "2026-09-24T00:00:00+00:00",
                 "last_heartbeat": "2026-09-24T00:00:00+00:00"},
            ],
        }))
        rec = synthesize(str(tmp_project))
        assert rec.child_progress == ()

    def test_no_events_file_with_active_children(self, tmp_project):
        """Active stage_X child exists but no events.jsonl → zero-progress entry
        with sentinel detail '尚未产生 events.jsonl', no crash."""
        # Create session manually (skip hook since hook auto-writes events)
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_manual", "kind": "stage_builder",
                 "owner_opencode_session_id": "manual_owner", "state": "active",
                 "goal": {"intent": "rdd-builder", "subject": "manual",
                          "expected_outcome": "ok"},
                 "started_at": "2026-09-24T01:00:00+00:00",
                 "last_heartbeat": "2026-09-24T01:00:00+00:00"},
            ],
        }))
        # No events.jsonl
        rec = synthesize(str(tmp_project))
        assert len(rec.child_progress) == 1
        assert rec.child_progress[0].started_count == 0
        assert rec.child_progress[0].completed_count == 0
        assert "尚未产生" in rec.child_progress[0].detail


# --- Schema tolerance (MN1): no schema changes ---

class TestSchemaTolerance:
    """MN1: events.jsonl reading uses .get() — malformed/missing fields OK."""

    def test_malformed_event_line_skipped(self, tmp_project):
        """Malformed JSONL lines should be skipped silently."""
        _run_hook("stage_builder", "rdd-builder")
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        # Append garbage line
        with events_file.open("a") as f:
            f.write("this is not json\n")
            f.write("{also not valid json\n")
        # Synthesizer must not crash; just skip
        rec = synthesize(str(tmp_project))
        assert len(rec.child_progress) == 1  # only the valid entry

    def test_event_without_context_skipped(self, tmp_project):
        """Events missing 'context' key should be skipped (not crash)."""
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        with events_file.open("w") as f:
            f.write(json.dumps({
                "event_id": "evt_broken", "ts": "2026-09-24T00:00:00+00:00",
                "event_type": "phase_started", "severity": "info",
                "message": "no context",  # no 'context' key
            }) + "\n")
        rec = synthesize(str(tmp_project))
        assert rec.child_progress == ()


# --- Deterministic ordering ---

class TestOrdering:
    """AC-G3: progress list is deterministically sorted (kind, session_id)."""

    def test_sorted_by_kind_then_session_id(self, tmp_project):
        """2 children in non-sorted order → output sorted by kind, then session_id."""
        _run_hook("stage_verify", "rdd-verifier", owner="owner_Z")
        _run_hook("stage_builder", "rdd-builder", owner="owner_A")
        rec = synthesize(str(tmp_project))
        kinds = [cp.kind for cp in rec.child_progress]
        assert kinds == sorted(kinds), f"not sorted by kind: {kinds}"


# --- AC-G3 explicit text match (per ADR-0056) ---

class TestAC_G3_TextPattern:
    """The AC-G3 example from the improvement file: detail must contain 'X 完成 N/M'."""

    def test_detail_text_matches_ac_g3_pattern(self, tmp_project):
        """Per AC-G3: synthesizer output 含 'X 完成 N/M' format."""
        # 1 child + 3 started + 2 completed = 5 events total
        proc = _run_hook("stage_builder", "rdd-builder")
        assert proc.returncode == 0

        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sid = json.loads(sessions_file.read_text())["sessions"][0]["session_id"]
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        # Total 3 phase_started, 2 phase_completed → started=3, completed=2
        for i in range(2):
            _append_phase_event(events_file, sid, "stage_builder", "phase_started",
                              ts=f"2026-09-24T00:0{i+1}:00+00:00")
        for i in range(2):
            _append_phase_event(events_file, sid, "stage_builder", "phase_completed",
                              ts=f"2026-09-24T00:1{i+1}:00+00:00")
        # Total = 5 events

        rec = synthesize(str(tmp_project))
        assert len(rec.child_progress) == 1
        cp = rec.child_progress[0]
        # AC-G3: "X 完成 N/M" where X is the kind, N=completed, M=started
        assert cp.detail == "stage_builder 完成 2/3", (
            f"AC-G3 pattern mismatch: got {cp.detail!r}"
        )


# --- Direct unit tests for helpers ---

class TestActiveStageXChildren:
    """Unit test for _active_stage_x_children helper."""

    def test_filters_to_active_stage_x(self):
        from _lib.workflow_synthesizer import _active_stage_x_children
        sessions = [
            {"session_id": "rds_1", "kind": "stage_builder", "state": "active"},
            {"session_id": "rds_2", "kind": "stage_arch", "state": "active"},
            {"session_id": "rds_3", "kind": "stage_builder", "state": "completed"},
            {"session_id": "rds_4", "kind": "rdd-builder", "state": "active"},  # alias, not stage_X
            {"session_id": "rds_5", "kind": "stage_verify", "state": "orphaned"},
        ]
        result = _active_stage_x_children(sessions)
        # rds_1 + rds_2 (both active + stage_X); rds_3 (completed), rds_4 (alias), rds_5 (orphaned) all filtered
        assert len(result) == 2
        assert {r["session_id"] for r in result} == {"rds_1", "rds_2"}
        kinds = {r["kind"] for r in result}
        assert kinds == {"stage_builder", "stage_arch"}

    def test_empty_sessions_returns_empty(self):
        from _lib.workflow_synthesizer import _active_stage_x_children
        assert _active_stage_x_children(None) == []
        assert _active_stage_x_children([]) == []


class TestReadEventsForChildren:
    """Unit test for _read_events_for_children helper."""

    def test_zero_io_guard_empty_children(self, tmp_project):
        """No active children → no read of events.jsonl (returns empty tuple)."""
        from _lib.workflow_synthesizer import _read_events_for_children
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        events_file.write_text("")  # empty events file
        result = _read_events_for_children(str(tmp_project), [])
        assert result == ()

    def test_missing_events_file_returns_zero_progress(self, tmp_project):
        """Active children but no events.jsonl → returns zero-progress entries."""
        from _lib.workflow_synthesizer import _read_events_for_children
        active = [{"kind": "stage_builder", "session_id": "rds_orphan"}]
        result = _read_events_for_children(str(tmp_project), active)
        assert len(result) == 1
        assert result[0].started_count == 0
        assert result[0].completed_count == 0


# --- Cross-owner visibility (multi-window correctness) ---

class TestCrossOwnerAggregation:
    """The aggregator must surface children from ALL owners — not filter by
    OPENCODE_SESSION_ID. Guide in window A needs to see window B's builders."""

    def test_aggregates_children_across_owners(self, tmp_project):
        """Window A (guide owner_A) + Window B (builder owner_B) both create sessions.
        Synthesizer from owner_A's view sees BOTH children in child_progress."""
        # Window B runs builder
        proc_b = _run_hook("stage_builder", "rdd-builder", owner="owner_B_window2")
        assert proc_b.returncode == 0
        # Window A (guide owner_A) — no active child itself, but wants to see B
        proc_a = _run_hook("stage_guide", "guide-orchestrator", owner="owner_A_window1")
        assert proc_a.returncode == 0

        rec = synthesize(str(tmp_project))
        # Both children visible (not filtered by owner)
        kinds = {cp.kind for cp in rec.child_progress}
        assert "stage_builder" in kinds
        assert "stage_guide" in kinds


# --- Writer/reader roundtrip (catches format drift) ---

class TestWriterReaderRoundtrip:
    """If EventsLog.append_event format changes, this catches it. Roundtrip
    through real append_event (not manual JSONL write)."""

    def test_append_event_then_synthesize_roundtrip(self, tmp_project):
        """Use EventsLog.append_event to write, then synthesize reads it back."""
        from skills.rddf_session.scripts.events_log import EventsLog

        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        # Pre-create session so _read_events_for_children picks it up
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_roundtrip", "kind": "stage_builder",
                 "owner_opencode_session_id": "rt_owner", "state": "active",
                 "goal": {"intent": "rdd-builder", "subject": "rt",
                          "expected_outcome": "ok"},
                 "started_at": "2026-09-24T01:00:00+00:00",
                 "last_heartbeat": "2026-09-24T01:00:00+00:00"},
            ],
        }))

        # Write via real EventsLog.append_event
        log = EventsLog(str(events_file))
        log.append_event(
            event_type="phase_started",
            severity="info",
            message="rt started",
            session_id="rds_roundtrip",
            kind="stage_builder",
            owner_opencode_session_id="rt_owner",
        )
        log.append_event(
            event_type="phase_completed",
            severity="info",
            message="rt completed",
            session_id="rds_roundtrip",
            kind="stage_builder",
            owner_opencode_session_id="rt_owner",
        )

        rec = synthesize(str(tmp_project))
        assert len(rec.child_progress) == 1
        cp = rec.child_progress[0]
        assert cp.kind == "stage_builder"
        assert cp.session_id == "rds_roundtrip"
        assert cp.started_count == 1
        assert cp.completed_count == 1
        assert cp.detail == "stage_builder 完成 1/1"


# --- Heartbeat task-level progress (AC-P2-2-2) ---

class TestHeartbeatTaskProgress:
    """AC-P2-2-2: workflow_synthesizer renders heartbeat task progress
    (N/M real task counts) instead of phase-ratio 0/1."""

    def test_heartbeat_preferred_over_phase_ratio(self, tmp_project):
        """phase_started + phase_completed (1/1 ratio) + phase_heartbeat
        (3/5 tasks) → detail shows 3/5 (heartbeat wins)."""
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_hb1", "kind": "stage_builder",
                 "owner_opencode_session_id": "hb_owner", "state": "active",
                 "goal": {"intent": "rdd-builder", "subject": "hb1",
                          "expected_outcome": "ok"},
                 "started_at": "2026-09-24T01:00:00+00:00",
                 "last_heartbeat": "2026-09-24T01:10:00+00:00"},
            ],
        }))
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        _append_phase_event(events_file, "rds_hb1", "stage_builder",
                            "phase_started", "2026-09-24T01:00:00+00:00")
        _append_phase_event(events_file, "rds_hb1", "stage_builder",
                            "phase_completed", "2026-09-24T01:01:00+00:00")
        # Heartbeat with real task counts
        hb_row = {
            "event_id": "evt_hb_1",
            "ts": "2026-09-24T01:05:00+00:00",
            "event_type": "phase_heartbeat",
            "severity": "info",
            "message": "heartbeat",
            "context": {"session_id": "rds_hb1", "kind": "stage_builder",
                        "tasks_total": 5, "tasks_completed": 3,
                        "owner_opencode_session_id": "hb_owner"},
        }
        with events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(hb_row, ensure_ascii=False) + "\n")

        rec = synthesize(str(tmp_project))
        assert len(rec.child_progress) == 1
        cp = rec.child_progress[0]
        # AC-P2-2-2: heartbeat renders 3/5, not phase ratio 1/1
        assert cp.detail == "stage_builder 完成 3/5", f"got: {cp.detail}"

    def test_latest_heartbeat_wins(self, tmp_project):
        """Two heartbeats (2/5 then 4/5) → latest (4/5) renders."""
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_hb2", "kind": "stage_builder",
                 "owner_opencode_session_id": "hb_owner2", "state": "active",
                 "goal": {"intent": "rdd-builder", "subject": "hb2",
                          "expected_outcome": "ok"},
                 "started_at": "2026-09-24T01:00:00+00:00",
                 "last_heartbeat": "2026-09-24T01:10:00+00:00"},
            ],
        }))
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        for ts, done in [("2026-09-24T01:02:00+00:00", 2),
                         ("2026-09-24T01:08:00+00:00", 4)]:
            hb_row = {
                "event_id": f"evt_hb_{done}",
                "ts": ts,
                "event_type": "phase_heartbeat",
                "severity": "info",
                "message": "heartbeat",
                "context": {"session_id": "rds_hb2", "kind": "stage_builder",
                            "tasks_total": 5, "tasks_completed": done,
                            "owner_opencode_session_id": "hb_owner2"},
            }
            with events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(hb_row, ensure_ascii=False) + "\n")

        rec = synthesize(str(tmp_project))
        cp = rec.child_progress[0]
        assert cp.detail == "stage_builder 完成 4/5", f"got: {cp.detail}"

    def test_heartbeat_without_tasks_falls_back_to_ratio(self, tmp_project):
        """heartbeat without tasks_total/tasks_completed → phase ratio (MN-HB4)."""
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        sessions_file.write_text(json.dumps({
            "version": 1,
            "sessions": [
                {"session_id": "rds_hb3", "kind": "stage_builder",
                 "owner_opencode_session_id": "hb_owner3", "state": "active",
                 "goal": {"intent": "rdd-builder", "subject": "hb3",
                          "expected_outcome": "ok"},
                 "started_at": "2026-09-24T01:00:00+00:00",
                 "last_heartbeat": "2026-09-24T01:10:00+00:00"},
            ],
        }))
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        _append_phase_event(events_file, "rds_hb3", "stage_builder",
                            "phase_started", "2026-09-24T01:00:00+00:00")
        _append_phase_event(events_file, "rds_hb3", "stage_builder",
                            "phase_completed", "2026-09-24T01:01:00+00:00")
        # Heartbeat WITHOUT tasks fields
        hb_row = {
            "event_id": "evt_hb_no_tasks",
            "ts": "2026-09-24T01:05:00+00:00",
            "event_type": "phase_heartbeat",
            "severity": "info",
            "message": "heartbeat",
            "context": {"session_id": "rds_hb3", "kind": "stage_builder",
                        "owner_opencode_session_id": "hb_owner3"},
        }
        with events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(hb_row, ensure_ascii=False) + "\n")

        rec = synthesize(str(tmp_project))
        cp = rec.child_progress[0]
        # Falls back to phase ratio 1/1 (original Wave 2 behavior)
        assert cp.detail == "stage_builder 完成 1/1", f"got: {cp.detail}"