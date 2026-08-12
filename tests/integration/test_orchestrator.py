"""Integration tests for rddf orchestrate end-to-end behavior.

Per spec 2026-08-12 §9 / §12.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "_lib" / "cli"


def _run_orchestrate(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Run `python3 _lib/cli/orchestrate_cmd.py <args>` directly."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "orchestrate_cmd.py"), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def trace_dir(tmp_path):
    d = tmp_path / "trace"
    d.mkdir()
    return d


def test_subprocess_invokes_real_command(trace_dir):
    result = _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "print('hello world')",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    assert len(traces) == 1
    events = [
        json.loads(line) for line in traces[0].read_text().splitlines() if line
    ]
    assert any(e.get("type") == "subprocess" for e in events)


def test_subprocess_preserves_return_code(trace_dir):
    result = _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "import sys; sys.exit(42)",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    assert result.returncode == 42


def test_finalize_appends_finalize_event_with_correct_counts(trace_dir):
    _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "print('ok')",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "import sys; sys.exit(1)",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    result = _run_orchestrate(
        "finalize",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    events = [
        json.loads(line) for line in traces[0].read_text().splitlines() if line
    ]
    last = events[-1]
    assert last["type"] == "finalize"
    assert last["subprocess_failures"] == 1


def test_sweep_deletes_unfinalized_old_traces(trace_dir):
    trace = trace_dir / "guide-arch-ses_x-1-1000000-eeeeeeee.jsonl"
    trace.write_text(
        '{"ts":"2026-08-12T09:00:00Z","type":"subprocess","cmd":["x"],"returncode":0}\n'
    )
    import os
    os.utime(trace, (1000000, 1000000))
    result = _run_orchestrate(
        "sweep-stale-traces",
        env_extra={
            "RDDF_PHASE": "guide-arch",
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_TRACE_STALE_MINUTES": "0",
            "RDDF_PROJECT_ROOT": str(trace_dir),
        },
    )
    assert result.returncode == 0
    assert not trace.exists()


def test_mark_checkpoint_records_event(trace_dir):
    _run_orchestrate(
        "subprocess",
        sys.executable,
        "-c",
        "print('x')",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    result = _run_orchestrate(
        "mark-checkpoint",
        "--name",
        "after-setup",
        "--state-marker",
        "phase_started",
        env_extra={"RDDF_PHASE": "int-test", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    assert result.returncode == 0
    traces = list(trace_dir.glob("*.jsonl"))
    events = [
        json.loads(line) for line in traces[0].read_text().splitlines() if line
    ]
    assert any(e.get("type") == "checkpoint" for e in events)
    checkpoints = [e for e in events if e.get("type") == "checkpoint"]
    assert checkpoints[0]["name"] == "after-setup"