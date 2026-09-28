"""Unit tests for skills/rdd-quick/scripts/cleanup_context.sh.

Per rdd-workflow v2.1 fix: rdd-quick-context.json cleanup contract.

Coverage:
- Context file exists → deleted
- Context file absent → no-op, exit 0
- Audit log entry appended on successful cleanup
- Missing --reason flag → non-zero exit
- Invalid --reason value → non-zero exit, file NOT deleted
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills/rdd-quick/scripts/cleanup_context.sh"


def run_cleanup(state_dir: Path, history_file: Path,
                reason: str | None = "completed") -> subprocess.CompletedProcess:
    """Invoke cleanup_context.sh with custom state dir + history file."""
    state_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["RDDF_QUICK_STATE_DIR"] = str(state_dir)
    env["RDDF_QUICK_HISTORY_FILE"] = str(history_file)
    cmd = ["bash", str(SCRIPT)]
    if reason is not None:
        cmd += ["--reason", reason]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def test_context_file_exists_then_deleted(tmp_path: Path):
    """When rdd-quick-context.json exists, it MUST be deleted."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"change_name": "old", "proposal_path": "old/proposal.md"}')
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(state_dir, history, reason="completed")

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"
    assert not context_file.exists(), "context file should be deleted"


def test_context_file_absent_is_noop(tmp_path: Path):
    """When rdd-quick-context.json absent, MUST exit 0 with no side effects."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(state_dir, history, reason="completed")

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert not history.exists(), "No audit log should be written on no-op"


def test_cleanup_appends_audit_log_entry(tmp_path: Path):
    """When context deleted, MUST append audit log entry to .quick-history.jsonl."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"change_name": "x"}')
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(state_dir, history, reason="escalated")

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
    assert history.exists(), "audit log should be created"
    lines = history.read_text().strip().splitlines()
    assert len(lines) == 1, f"Expected 1 entry, got {len(lines)}"
    entry = json.loads(lines[0])
    assert entry["event"] == "context_cleanup"
    assert entry["reason"] == "escalated"
    assert "deleted_at" in entry
    # Timestamp should be ISO 8601 UTC
    assert entry["deleted_at"].endswith("Z")


def test_cleanup_exit_code_nonzero_on_missing_reason(tmp_path: Path):
    """Without --reason flag, MUST exit non-zero."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(state_dir, history, reason=None)

    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"


def test_cleanup_invalid_reason_exits_nonzero_and_preserves_file(tmp_path: Path):
    """Invalid --reason value MUST exit non-zero AND NOT delete the context file."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"x": 1}')
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(state_dir, history, reason="bogus")

    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
    assert context_file.exists(), "context file should NOT be deleted on invalid reason"


def test_cleanup_appends_to_existing_history(tmp_path: Path):
    """If .quick-history.jsonl exists with prior entries, new entry MUST append."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"x": 1}')
    history = state_dir / ".quick-history.jsonl"
    history.write_text('{"event": "prior_entry", "id": "abc"}\n')

    result = run_cleanup(state_dir, history, reason="completed")

    assert result.returncode == 0
    lines = history.read_text().strip().splitlines()
    assert len(lines) == 2, f"Expected 2 entries, got {len(lines)}"
    prior = json.loads(lines[0])
    new = json.loads(lines[1])
    assert prior["event"] == "prior_entry"
    assert new["event"] == "context_cleanup"