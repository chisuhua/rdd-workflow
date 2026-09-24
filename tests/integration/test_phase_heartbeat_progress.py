"""Integration test: phase_heartbeat write-end roundtrip.

Covers AC-P2-2-1: rddf_session_hook_heartbeat writes phase_heartbeat to events.jsonl
with context.tasks_total and context.tasks_completed.
AC-P2-2-3: append → read_since roundtrip preserves tasks_total/tasks_completed.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

from skills.rddf_session.scripts.events_log import EventsLog


def test_heartbeat_append_event_extra_context(tmp_path):
    """AC-P2-2-1: append_event with extra_context merges tasks_total/tasks_completed.

    Currently EventsLog.append_event does NOT accept extra_context parameter,
    so this test MUST FAIL at call time (TypeError).  Once implemented, the
    call succeeds and the written event contains the extra fields in context.
    """
    log = EventsLog(str(tmp_path / "events.jsonl"))
    row = log.append_event(
        event_type="phase_heartbeat",
        severity="info",
        message="rddf-session: rds_xxx heartbeat",
        session_id="rds_heartbeat_test",
        kind="stage_builder",
        extra_context={"tasks_total": 5, "tasks_completed": 3},
    )
    assert row["context"]["tasks_total"] == 5
    assert row["context"]["tasks_completed"] == 3

    # Verify durable write
    lines = (tmp_path / "events.jsonl").read_text().strip().split("\n")
    parsed = json.loads(lines[0])
    assert parsed["context"]["tasks_total"] == 5
    assert parsed["context"]["tasks_completed"] == 3


def test_heartbeat_append_read_roundtrip(tmp_path):
    """AC-P2-2-3: phase_heartbeat event written via append_event is read back
    verbatim via read_since with tasks_total/tasks_completed intact."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    log.append_event(
        event_type="phase_heartbeat",
        severity="info",
        message="heartbeat roundtrip",
        session_id="rds_roundtrip_hb",
        kind="stage_builder",
        extra_context={"tasks_total": 5, "tasks_completed": 2},
    )
    log.append_event(
        event_type="phase_heartbeat",
        severity="info",
        message="heartbeat roundtrip 2",
        session_id="rds_roundtrip_hb",
        kind="stage_builder",
        extra_context={"tasks_total": 5, "tasks_completed": 4},
    )

    events = log.read_since(offset=0)
    heartbeats = [e for e in events if e["event_type"] == "phase_heartbeat"]
    assert len(heartbeats) == 2
    assert heartbeats[0]["context"]["tasks_completed"] == 2
    assert heartbeats[1]["context"]["tasks_completed"] == 4
    assert heartbeats[1]["context"]["tasks_total"] == 5
    assert heartbeats[1]["context"]["kind"] == "stage_builder"


def test_heartbeat_interval_default_300(monkeypatch):
    """AC-P2-2-4: default heartbeat interval is 300s (5 min)."""
    from skills.rddf_session.scripts.events_log import get_heartbeat_interval_sec
    monkeypatch.delenv("RDDF_HEARTBEAT_INTERVAL_SEC", raising=False)
    assert get_heartbeat_interval_sec() == 300


def test_heartbeat_interval_env_override(monkeypatch):
    """AC-P2-2-4 / M-HB5: RDDF_HEARTBEAT_INTERVAL_SEC overrides the default."""
    from skills.rddf_session.scripts.events_log import get_heartbeat_interval_sec
    monkeypatch.setenv("RDDF_HEARTBEAT_INTERVAL_SEC", "120")
    assert get_heartbeat_interval_sec() == 120


def test_heartbeat_interval_invalid_falls_back(monkeypatch):
    """M-HB5: non-integer env value falls back to default (no crash)."""
    from skills.rddf_session.scripts.events_log import get_heartbeat_interval_sec
    monkeypatch.setenv("RDDF_HEARTBEAT_INTERVAL_SEC", "not-a-number")
    assert get_heartbeat_interval_sec() == 300