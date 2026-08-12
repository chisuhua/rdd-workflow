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
    _classify_interrupted_phase,
    _find_open_trace,
    _get_session_id,
    _get_trace_dir,
    _get_trace_path,
    _handle_checkpoint,
    _handle_finalize,
    _handle_subprocess,
    _handle_sweep,
    _open_trace,
    _read_events,
    _tail_file,
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


def test_tail_file_returns_whole_file_when_small(tmp_path):
    p = tmp_path / "small.txt"
    p.write_text("hello world")
    assert _tail_file(p, n=4096) == "hello world"


def test_tail_file_truncates_large_file(tmp_path):
    p = tmp_path / "large.txt"
    p.write_text("x" * 10000)
    result = _tail_file(p, n=100)
    assert len(result.encode("utf-8")) == 100


def test_handle_subprocess_runs_command_and_records(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "int-test")
    rc = _handle_subprocess(["echo", "hello"], trace_dir=tmp_path)
    assert rc == 0
    traces = list(tmp_path.glob("*.jsonl"))
    assert len(traces) == 1
    events = _read_events(traces[0])
    assert len(events) == 1
    assert events[0]["type"] == "subprocess"
    assert events[0]["cmd"] == ["echo", "hello"]
    assert events[0]["returncode"] == 0
    assert "hello" in events[0]["stdout_tail"]


def test_handle_subprocess_swallows_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "int-test")
    rc = _handle_subprocess(["sleep", "10"], trace_dir=tmp_path, timeout=1)
    assert rc == 124
    events = _read_events(list(tmp_path.glob("*.jsonl"))[0])
    assert events[0]["timeout"] is True


def test_handle_subprocess_sanitizes_output(monkeypatch, tmp_path):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "int-test")
    rc = _handle_subprocess(
        ["sh", "-c", "echo AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE"],
        trace_dir=tmp_path,
    )
    assert rc == 0
    events = _read_events(list(tmp_path.glob("*.jsonl"))[0])
    assert "AKIAIOSFODNN7EXAMPLE" not in events[0]["stdout_tail"]


def test_handle_checkpoint_appends_event(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-plan")
    rc = _handle_checkpoint(
        name="after-setup",
        state_marker="phase_started",
        trace_dir=tmp_path,
    )
    assert rc == 0
    traces = list(tmp_path.glob("*.jsonl"))
    assert len(traces) == 1
    events = _read_events(traces[0])
    assert events[0]["type"] == "checkpoint"
    assert events[0]["name"] == "after-setup"
    assert events[0]["state_marker"] == "phase_started"


def test_handle_finalize_writes_finalize_event(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    _handle_subprocess(["true"], trace_dir=tmp_path)
    rc = _handle_finalize(trace_dir=tmp_path)
    assert rc == 0
    traces = list(tmp_path.glob("*.jsonl"))
    events = _read_events(traces[0])
    last = events[-1]
    assert last["type"] == "finalize"
    assert last["subprocess_failures"] == 0
    assert last["checkpoints"] == 0


def test_handle_finalize_counts_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    _handle_subprocess(["false"], trace_dir=tmp_path)
    _handle_checkpoint("mid", "", trace_dir=tmp_path)
    _handle_finalize(trace_dir=tmp_path)
    events = _read_events(list(tmp_path.glob("*.jsonl"))[0])
    last = events[-1]
    assert last["subprocess_failures"] == 1
    assert last["checkpoints"] == 1


def test_sweep_classifies_unfinalized_old_trace_as_interrupted(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    trace = tmp_path / "guide-arch-ses_x-1-1000000-aaaaaaaa.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0,"stderr_tail":"","stdout_tail":""}\n'
    )
    import os
    os.utime(trace, (1000000, 1000000))
    monkeypatch.setenv("RDDF_TRACE_STALE_MINUTES", "0")
    rc = _handle_sweep(trace_dir=tmp_path)
    assert rc == 0
    assert not trace.exists()


def test_sweep_skips_finalized_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    import os
    import time
    trace = tmp_path / "guide-arch-ses_x-1-1000000-bbbbbbbb.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"finalize","subprocess_failures":0}\n'
    )
    recent = time.time() - 60
    os.utime(trace, (recent, recent))
    _handle_sweep(trace_dir=tmp_path)
    assert trace.exists()


def test_sweep_skips_recent_unfinalized_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("RDDF_PHASE", "guide-arch")
    trace = tmp_path / "guide-arch-ses_x-1-1000000-cccccccc.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0}\n'
    )
    rc = _handle_sweep(trace_dir=tmp_path)
    assert rc == 0
    assert trace.exists()


def test_classify_interrupted_phase_with_no_subprocess(monkeypatch):
    monkeypatch.setenv("RDDF_PHASE", "guide-test")
    cls = _classify_interrupted_phase([])
    assert cls is not None
    assert cls.matched_rule == "INTERRUPTED-NO-SUBPROCESS"
    assert cls.should_report is True


def test_classify_interrupted_phase_with_subprocess(monkeypatch):
    monkeypatch.setenv("RDDF_PHASE", "guide-test")
    events = [
        {"type": "subprocess", "cmd": ["x"], "returncode": 1, "stderr_tail": "fail", "stdout_tail": ""},
    ]
    cls = _classify_interrupted_phase(events)
    assert cls is not None
    assert cls.should_report is True