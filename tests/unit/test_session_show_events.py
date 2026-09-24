"""Unit tests for session_show_cmd: filter combinators + format variants.

Covers AC-P2-4-1~6:
- AC-P2-4-1: --owner filters events
- AC-P2-4-2: --session filters events
- AC-P2-4-3: --kind filters events
- AC-P2-4-4: --since/--until ISO 8601 range
- AC-P2-4-5: default table sorted by ts ascending
- AC-P2-4-6: missing events.jsonl => "(no events)" (no crash)
"""
from __future__ import annotations

import json

import pytest

from _lib.cli.session_show_cmd import (
    build_event_query,
    format_events_json,
    format_events_raw,
    format_events_table,
    handle_show_events_cmd,
)

SAMPLE_EVENTS = [
    {"event_id": "evt_001", "ts": "2026-09-24T01:00:00+00:00", "event_type": "phase_started",
     "severity": "info", "kind": "stage_builder", "owner_opencode_session_id": "owner_a",
     "message": "started",
     "context": {"session_id": "rds_001", "kind": "stage_builder",
                 "owner_opencode_session_id": "owner_a"}},
    {"event_id": "evt_002", "ts": "2026-09-24T01:05:00+00:00", "event_type": "phase_completed",
     "severity": "info", "kind": "stage_builder", "owner_opencode_session_id": "owner_a",
     "message": "completed",
     "context": {"session_id": "rds_001", "kind": "stage_builder",
                 "owner_opencode_session_id": "owner_a"}},
    {"event_id": "evt_003", "ts": "2026-09-24T02:00:00+00:00", "event_type": "phase_started",
     "severity": "info", "kind": "stage_guide", "owner_opencode_session_id": "owner_b",
     "message": "guide started",
     "context": {"session_id": "rds_002", "kind": "stage_guide",
                 "owner_opencode_session_id": "owner_b"}},
]


def test_filter_by_owner():
    """AC-P2-4-1: --owner filters by owner_opencode_session_id."""
    query = build_event_query(owner="owner_a")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 2
    assert all(e["owner_opencode_session_id"] == "owner_a" for e in filtered)


def test_filter_by_session():
    """AC-P2-4-2: --session filters by context.session_id."""
    query = build_event_query(session_id="rds_002")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["context"]["session_id"] == "rds_002"


def test_filter_by_kind():
    """AC-P2-4-3: --kind filters by kind."""
    query = build_event_query(kind="stage_guide")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["kind"] == "stage_guide"


def test_filter_combined_and():
    """M-SE6: filters compose with AND."""
    query = build_event_query(owner="owner_a", kind="stage_builder")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 2


def test_filter_since_until():
    """AC-P2-4-4: --since/--until ISO 8601 range."""
    query = build_event_query(since="2026-09-24T01:05:00", until="2026-09-24T01:10:00")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["event_id"] == "evt_002"


def test_format_table_sorted_ascending():
    """AC-P2-4-5: table format sorted by ts ascending (latest at bottom)."""
    result = format_events_table(SAMPLE_EVENTS)
    lines = [ln for ln in result.strip().split("\n") if ln.strip()]
    assert "TIME" in lines[0]
    assert lines[-1].endswith("guide started")


def test_format_json():
    """M-SE3: JSON output is a parseable array."""
    result = format_events_json(SAMPLE_EVENTS)
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 3


def test_format_raw():
    """M-SE4: raw output = one JSONL per line."""
    result = format_events_raw(SAMPLE_EVENTS)
    lines = [ln for ln in result.strip().split("\n") if ln.strip()]
    assert len(lines) == 3
    for line in lines:
        assert "event_id" in json.loads(line)


def test_empty_events_table():
    """AC-P2-4-6: no events => '(no events)'."""
    assert "(no events)" in format_events_table([])


def test_empty_events_json():
    """AC-P2-4-6: no events => '[]' in json format."""
    assert format_events_json([]) == "[]"


def test_empty_events_raw():
    """AC-P2-4-6: no events => empty string in raw format."""
    assert format_events_raw([]).strip() == ""


def test_handle_missing_events_file(tmp_path, capsys):
    """AC-P2-4-6: events.jsonl missing => '(no events)', exit 0."""
    missing = tmp_path / "nonexistent.jsonl"
    rc = handle_show_events_cmd(events_path=str(missing), format="table")
    out = capsys.readouterr().out
    assert rc == 0
    assert "(no events)" in out


def test_handle_events_file_with_filters(tmp_path, capsys):
    """End-to-end handler: read JSONL, apply filter, emit table."""
    events_file = tmp_path / "events.jsonl"
    with events_file.open("w", encoding="utf-8") as f:
        for ev in SAMPLE_EVENTS:
            f.write(json.dumps(ev) + "\n")
    rc = handle_show_events_cmd(
        events_path=str(events_file), owner="owner_b", format="table"
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "rds_002" in out
    assert "rds_001" not in out


def test_cmd_sessions_show_events_dispatches(tmp_path, monkeypatch, capsys):
    """AC-P2-4-1~6 wiring: cmd_sessions(['show', '--events', ...]) routes
    to handle_show_events_cmd (events.jsonl under project root)."""
    project_root = tmp_path
    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    events_file = state_dir / "events.jsonl"
    with events_file.open("w", encoding="utf-8") as f:
        for ev in SAMPLE_EVENTS:
            f.write(json.dumps(ev) + "\n")

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(project_root))
    from _lib.cli.sessions_cmd import cmd_sessions
    rc = cmd_sessions(["show", "--events", "--owner", "owner_b", "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["context"]["session_id"] == "rds_002"


def test_cmd_sessions_show_events_missing_file(tmp_path, monkeypatch, capsys):
    """AC-P2-4-6: sessions show --events with no events.jsonl => '(no events)'."""
    project_root = tmp_path
    (project_root / ".rddf" / "state").mkdir(parents=True)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(project_root))
    from _lib.cli.sessions_cmd import cmd_sessions
    rc = cmd_sessions(["show", "--events"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(no events)" in out