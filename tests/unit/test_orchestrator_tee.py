"""Unit tests for orchestrator stdout capture mode (tee/capture/passthrough).

Per openspec/changes/preserve-orchestrator-command-stdout.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from _lib.cli.orchestrate_cmd import _resolve_capture_mode


REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATE_CMD = REPO_ROOT / "_lib" / "cli" / "orchestrate_cmd.py"


@pytest.mark.parametrize(
    "env_value,expected",
    [
        ("tee", "tee"),
        ("capture", "capture"),
        ("passthrough", "passthrough"),
        ("", "tee"),  # default = tee
        ("garbage", "tee"),  # invalid → default tee
        ("TEE", "tee"),  # case-insensitive
        ("  passthrough  ", "passthrough"),  # whitespace tolerated
    ],
)
def test_resolve_capture_mode(env_value: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if env_value:
        monkeypatch.setenv("RDDF_ORCHESTRATOR_CAPTURE", env_value)
    else:
        monkeypatch.delenv("RDDF_ORCHESTRATOR_CAPTURE", raising=False)
    assert _resolve_capture_mode() == expected


def _run_orchestrate_subprocess(args: list[str], env_extra: dict) -> subprocess.CompletedProcess:
    """Helper: invoke orchestrate_cmd subprocess action via subprocess.run."""
    env = {
        "PYTHONPATH": f"{REPO_ROOT}:{REPO_ROOT}/_lib",
        "RDDF_PROJECT_ROOT": str(REPO_ROOT),
        "RDDF_PHASE": "unit-test-tee",
    }
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(ORCHESTRATE_CMD), "subprocess", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_tee_mode_emits_capture_mode_field(tmp_path: Path) -> None:
    """tee mode records stdout_capture_mode='tee' and inherits caller stdout."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "hello from tee"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "tee",
        },
    )
    assert result.returncode == 0, result.stderr
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1, f"expected 1 trace, got {len(jsonl_files)}"
    events = [json.loads(line) for line in jsonl_files[0].read_text().splitlines() if line]
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    assert len(subprocess_events) == 1
    assert subprocess_events[0]["stdout_capture_mode"] == "tee"
    assert subprocess_events[0]["reader_died"] is False


def test_passthrough_mode_no_trace_written(tmp_path: Path) -> None:
    """passthrough mode skips trace file creation entirely."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "hi"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "passthrough",
        },
    )
    assert result.returncode == 0, result.stderr
    # Zero trace files expected
    assert list(trace_dir.glob("*.jsonl")) == []


def test_capture_mode_legacy_behavior(tmp_path: Path) -> None:
    """capture mode preserves ADR-0027 §1.0.1 PIPE capture (stdout_tail populated)."""
    trace_dir = tmp_path / "trace"
    result = _run_orchestrate_subprocess(
        ["bash", "-c", 'echo "captured line"'],
        env_extra={
            "RDDF_TRACE_DIR": str(trace_dir),
            "RDDF_ORCHESTRATOR_CAPTURE": "capture",
        },
    )
    assert result.returncode == 0
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    events = [json.loads(line) for line in jsonl_files[0].read_text().splitlines() if line]
    subprocess_events = [e for e in events if e.get("type") == "subprocess"]
    assert subprocess_events[0]["stdout_capture_mode"] == "capture"
    assert "captured line" in subprocess_events[0]["stdout_tail"]


def test_trace_file_rotation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When trace file exceeds RDDF_ORCHESTRATOR_TRACE_MAX_BYTES, rotate to .1."""
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    large_content = "x" * 200
    (trace_dir / "unit-test-tee-sess1-1234-1-aaaaaaaa.jsonl").write_text(large_content)
    monkeypatch.setenv("RDDF_ORCHESTRATOR_TRACE_MAX_BYTES", "100")
    _run_orchestrate_subprocess(
        ["bash", "-c", "echo hi"],
        env_extra={"RDDF_ORCHESTRATOR_TRACE_MAX_BYTES": "100", "RDDF_TRACE_DIR": str(trace_dir)},
    )
    rotated = list(trace_dir.glob("*.1"))
    assert len(rotated) >= 1