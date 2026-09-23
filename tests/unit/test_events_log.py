"""Tests for events_log.py — events.jsonl append/read/archive + anti-pattern guard.

Per feat-guide-orchestrator-session-event-bus (ADR-0055 v3, Oracle + Metis revised).
"""
from __future__ import annotations

import json

import pytest

from skills.rddf_session.scripts.events_log import (
    ARCHIVE_KEEP_DEFAULT,
    DEFAULT_MAX_SIZE_MB,
    EventsLog,
    EventsLogError,
    archive_events,
)


def test_append_event_writes_correct_format(tmp_path):
    """AC-5: append_event produces valid JSONL row with all fields."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    row = log.append_event(
        event_type="phase_started",
        severity="info",
        message="rddf-session: rds_xxx (stage_arch)",
        session_id="rds_xxx",
        kind="stage_arch",
        parent_session_id="rds_yyy",
        owner_opencode_session_id="ses_xxx",
    )
    lines = (tmp_path / "events.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["event_id"] == row["event_id"]
    assert parsed["event_type"] == "phase_started"
    assert parsed["severity"] == "info"
    assert parsed["message"].startswith("rddf-session")
    assert parsed["context"]["session_id"] == "rds_xxx"
    assert parsed["context"]["kind"] == "stage_arch"
    assert parsed["context"]["parent_session_id"] == "rds_yyy"
    assert parsed["context"]["owner_opencode_session_id"] == "ses_xxx"


def test_read_since_filters_by_offset(tmp_path):
    """AC-5: read_since(offset=N) skips first N lines, returns rest."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    for i in range(5):
        log.append_event(
            event_type="test",
            severity="info",
            message=f"event-{i}",
            session_id=f"rds_{i}",
            kind="stage_arch",
            parent_session_id=None,
            owner_opencode_session_id="ses",
        )
    # offset=2 skips lines 0,1; returns lines 2,3,4 (3 events)
    rows = log.read_since(offset=2)
    assert len(rows) == 3
    assert rows[0]["message"] == "event-2"
    assert rows[-1]["message"] == "event-4"
    # offset=0 returns all 5 events
    all_rows = log.read_since(offset=0)
    assert len(all_rows) == 5


def test_read_since_returns_empty_when_file_missing(tmp_path):
    """read_since on missing file returns [] (graceful fallback)."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    assert log.read_since(offset=0) == []


def test_archive_events_moves_old(tmp_path):
    """AC-5: archive_events(keep=N) moves oldest rows beyond N to .archive.jsonl."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    for i in range(10):
        log.append_event(
            event_type="test",
            severity="info",
            message=f"e-{i}",
            session_id=f"rds_{i}",
            kind="stage_arch",
            parent_session_id=None,
            owner_opencode_session_id="ses",
        )
    archived = archive_events(str(tmp_path / "events.jsonl"), keep=3)
    assert archived == 7
    main = (tmp_path / "events.jsonl").read_text().strip().split("\n")
    archive = (tmp_path / "events.archive.jsonl").read_text().strip().split("\n")
    assert len(main) == 3
    assert len(archive) == 7
    # Verify archive has oldest 7, main has newest 3
    assert any('"e-0"' in line for line in archive)
    assert any('"e-9"' in line for line in main)


def test_no_event_log_jsonl_alias(tmp_path):
    """AC-4 anti-pattern guard: events_log.py never creates event-log.jsonl (with hyphen)."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    log.append_event(
        event_type="test",
        severity="info",
        message="x",
        session_id="r1",
        kind="stage_arch",
        parent_session_id=None,
        owner_opencode_session_id="ses",
    )
    # Must NOT have event-log.jsonl — only events.jsonl
    assert not (tmp_path / "event-log.jsonl").exists()
    assert (tmp_path / "events.jsonl").exists()


def test_unknown_event_type_rejected(tmp_path):
    """Unknown event_type raises EventsLogError (validation guard)."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    with pytest.raises(EventsLogError, match="Unknown event_type"):
        log.append_event(
            event_type="bogus_event_type",
            severity="info",
            message="x",
            session_id="r1",
            kind="stage_arch",
            parent_session_id=None,
            owner_opencode_session_id="ses",
        )


def test_default_max_size_constant():
    """50MB cap (configurable, not just config)."""
    assert DEFAULT_MAX_SIZE_MB == 50


def test_archive_keep_default():
    """archive_events default keep=1000."""
    assert ARCHIVE_KEEP_DEFAULT == 1000