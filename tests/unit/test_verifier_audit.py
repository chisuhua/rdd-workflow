"""Tests for verifier audit log (JSONL).

Per fix-rdd-verifier-lifecycle-dashboard Task 4:
- Append-only JSONL events at .rddf/state/verifier/<change>.audit.jsonl
- Events: running, failed, halted, bypassed, archive-ready
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.audit import (
    write_event, read_events, _audit_path, VALID_EVENTS,
)


def test_audit_path():
    p = _audit_path(Path("/tmp/proj"), "ch-x")
    assert p == Path("/tmp/proj/.rddf/state/verifier/ch-x.audit.jsonl")


def test_audit_appends_event(tmp_path):
    write_event(tmp_path, "ch-x", "running", commit="abc123")
    write_event(tmp_path, "ch-x", "archive-ready", commit="abc123")
    events = read_events(tmp_path, "ch-x")
    assert [e["event"] for e in events] == ["running", "archive-ready"]


def test_audit_preserves_optional_fields(tmp_path):
    write_event(tmp_path, "ch-y", "halted", commit="deadbeef",
                halt_reason="max_loops exceeded", loop_count=3)
    events = read_events(tmp_path, "ch-y")
    assert len(events) == 1
    assert events[0]["halt_reason"] == "max_loops exceeded"
    assert events[0]["loop_count"] == 3


def test_audit_bypass_event(tmp_path):
    write_event(tmp_path, "ch-z", "bypassed", commit="cafe0000",
                bypass_reason="emergency hotfix",
                bypass_source="SKIP_RDD_VERIFIER")
    events = read_events(tmp_path, "ch-z")
    assert events[0]["event"] == "bypassed"
    assert events[0]["bypass_source"] == "SKIP_RDD_VERIFIER"


def test_audit_invalid_event_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        write_event(tmp_path, "ch-x", "unknown-event-type")


def test_audit_read_empty(tmp_path):
    assert read_events(tmp_path, "nope") == []


def test_audit_archive_ready_event(tmp_path):
    write_event(tmp_path, "ch-w", "archive-ready", commit="1234")
    events = read_events(tmp_path, "ch-w")
    assert events[0]["event"] == "archive-ready"


def test_audit_event_has_timestamp(tmp_path):
    write_event(tmp_path, "ch-a", "running")
    events = read_events(tmp_path, "ch-a")
    assert "ts" in events[0]
    assert events[0]["change"] == "ch-a"
