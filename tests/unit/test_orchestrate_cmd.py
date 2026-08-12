"""Tests for rddf orchestrate subcommand (spec 2026-08-12)."""
import os
from pathlib import Path

import pytest

# Inject _lib/cli into sys.path so we can import orchestrate_cmd
# (worktree files don't propagate to ~/.agents/skills/_lib symlink yet)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "_lib" / "cli"
import sys

sys.path.insert(0, str(_SCRIPTS_DIR))

from orchestrate_cmd import (  # noqa: E402
    Trace,
    _append_event,
    _find_open_trace,
    _get_session_id,
    _get_trace_dir,
    _get_trace_path,
    _open_trace,
    _read_events,
)


def test_get_trace_path_includes_phase_pid_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    p = _get_trace_path(phase="guide-arch", session_id="ses_test123", pid=42, epoch=100)
    assert p.parent == tmp_path
    assert p.name.startswith("guide-arch-ses_test123-42-100-")
    assert p.suffix == ".jsonl"


def test_get_trace_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path / "custom_trace"))
    assert _get_trace_dir() == (tmp_path / "custom_trace").resolve()


def test_get_trace_dir_default(monkeypatch):
    monkeypatch.delenv("RDDF_TRACE_DIR", raising=False)
    d = _get_trace_dir()
    assert str(d).endswith(".rddf/state/trace")


def test_open_trace_creates_file_with_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace = _open_trace(phase="guide-arch", session_id="ses_test")
    assert trace.path.exists()
    assert trace.phase == "guide-arch"
    assert trace.session_id == "ses_test"
    trace.close()


def test_open_trace_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path / "nested" / "trace"))
    trace = _open_trace(phase="guide-arch", session_id="ses_x")
    assert trace.path.parent.is_dir()
    trace.close()


def test_append_event_writes_valid_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace = _open_trace(phase="guide-arch", session_id="ses_test")
    _append_event(trace, {"type": "checkpoint", "name": "start"})
    _append_event(trace, {"type": "subprocess", "cmd": ["echo"], "returncode": 0})
    trace.close()
    events = _read_events(trace.path)
    assert len(events) == 2
    assert events[0]["type"] == "checkpoint"
    assert events[1]["type"] == "subprocess"
    assert "ts" in events[0]


def test_read_events_skips_malformed_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    trace_path = tmp_path / "test.jsonl"
    trace_path.write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"checkpoint","name":"a"}\n'
        "not json\n"
        '{"ts":"2026-08-12T10:00:01Z","type":"finalize"}\n'
    )
    events = _read_events(trace_path)
    assert len(events) == 2
    assert events[0]["name"] == "a"
    assert events[1]["type"] == "finalize"


def test_find_open_trace_returns_none_when_all_finalized(tmp_path):
    (tmp_path / "guide-arch-1-1-100-aaaaaaaa.jsonl").write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","returncode":0}\n'
        '{"ts":"2026-08-12T10:00:01Z","type":"finalize"}\n'
    )
    assert _find_open_trace(tmp_path, "guide-arch") is None


def test_find_open_trace_returns_unfinalized(tmp_path):
    (tmp_path / "guide-arch-1-1-100-aaaaaaaa.jsonl").write_text(
        '{"ts":"2026-08-12T10:00:00Z","type":"subprocess","returncode":1}\n'
    )
    result = _find_open_trace(tmp_path, "guide-arch")
    assert result is not None
    assert result.name.startswith("guide-arch-")


def test_get_session_id_generates_uuid_when_no_state(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("RDDF_OPENCODE_SESSION_ID", raising=False)
    sid = _get_session_id()
    assert len(sid) == 32  # UUID hex


def test_get_session_id_reads_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("RDDF_OPENCODE_SESSION_ID", "ses_from_env")
    assert _get_session_id() == "ses_from_env"