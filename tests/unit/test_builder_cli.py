"""Unit tests for _lib/cli/builder_cmd.py + _lib/builder_handoff.py.

Per Oracle review P0 #2: fixes ``builder_cmd.py`` pause-continue kwargs
crash (line 159/177) + ``--retry-on-fail`` unbounded recursion, and locks
the new ``update_builder_handoff`` merge API + ``increment_retry`` refactor.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project root with openspec/changes/<change>/."""
    (tmp_path / "openspec" / "changes" / "demo-change").mkdir(parents=True)
    (tmp_path / "openspec" / "changes" / "demo-change" / "proposal.md").write_text(
        "# proposal\n"
    )
    (tmp_path / "skills" / "rdd-builder" / "scripts").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# builder_handoff: update_builder_handoff API (new merge helper)
# ---------------------------------------------------------------------------

def test_update_builder_handoff_merges_partial_fields(tmp_project: Path) -> None:
    """update_builder_handoff merges partial fields without losing existing data."""
    from _lib.builder_handoff import (
        read_builder_handoff,
        update_builder_handoff,
        write_builder_handoff,
    )
    write_builder_handoff(
        str(tmp_project), "demo-change",
        current_phase="phase-0", approval_status="approved",
    )
    update_builder_handoff(
        str(tmp_project), "demo-change",
        current_phase="phase-1", worktree_path="/tmp/wt",
    )
    data = read_builder_handoff(str(tmp_project), "demo-change")
    assert data["current_phase"] == "phase-1"
    assert data["approval_status"] == "approved"
    assert data["worktree_path"] == "/tmp/wt"
    assert data["schema"] == "builder-handoff-v1"
    assert data["version"] == 1
    assert data["owner"] == "rdd-builder"


def test_increment_retry_uses_update_helper_no_kwargs_crash(tmp_project: Path) -> None:
    """increment_retry no longer crashes on auto-generated fields (Oracle P0 #2)."""
    from _lib.builder_handoff import (
        increment_retry,
        read_builder_handoff,
        write_builder_handoff,
    )
    write_builder_handoff(str(tmp_project), "demo-change", current_phase="phase-3")
    increment_retry(
        str(tmp_project), "demo-change",
        to_phase="phase-2", verifier_kind="implementation_gap", verifier_exit_code=1,
    )
    data = read_builder_handoff(str(tmp_project), "demo-change")
    assert data["retry_count"] == 1
    assert data["current_phase"] == "phase-2"
    assert data["retry_history"][0]["verifier_kind"] == "implementation_gap"
    assert data["retry_history"][0]["verifier_exit_code"] == 1


# ---------------------------------------------------------------------------
# builder_cmd CLI: pause-continue (line 159/177 kwargs crash fix)
# ---------------------------------------------------------------------------

def test_cmd_builder_help_returns_zero() -> None:
    """rddf builder --help prints usage and exits 0."""
    from _lib.cli.builder_cmd import cmd_builder
    rc = cmd_builder(["--help"])
    assert rc == 0


def test_cmd_builder_phase_approve_pause_continue_no_kwargs_crash(tmp_project: Path) -> None:
    """HARD pause path does NOT crash on kwargs leak (Oracle P0 #2 fix).

    Reproduces the builder_cmd.py:159 TypeError by touching a dummy
    phase script (so is_file() passes), mocking subprocess.run to
    succeed, and simulating user typing 'continue'.
    """
    from _lib.cli import builder_cmd
    from _lib.builder_handoff import read_builder_handoff, write_builder_handoff

    change = "demo-change"
    script = tmp_project / "skills" / "rdd-builder" / "scripts" / "phase0_approval.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/bin/bash\nexit 0\n")

    write_builder_handoff(
        str(tmp_project), change,
        current_phase="phase-0", approval_status="pending",
    )

    with patch.object(builder_cmd.subprocess, "run") as mock_run, \
         patch("builtins.input", return_value="continue"):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        rc = builder_cmd._cmd_phase("phase0", [change], str(tmp_project))

    assert rc == 0
    data = read_builder_handoff(str(tmp_project), change)
    assert data["current_phase"] == "phase-0"


# ---------------------------------------------------------------------------
# builder_cmd CLI: --retry-on-fail bounded by max_retries (Oracle P0 #2 fix)
# ---------------------------------------------------------------------------

def test_retry_halt_when_retry_count_exceeds_max_retries(tmp_project: Path) -> None:
    """should_halt_for_retry_exceeded returns True after max_retries reached."""
    from _lib.builder_handoff import (
        increment_retry,
        read_builder_handoff,
        write_builder_handoff,
    )
    from _lib.builder_retry import should_halt_for_retry_exceeded

    change = "demo-change"
    write_builder_handoff(str(tmp_project), change, retry_count=0, max_retries=3)
    for i in range(3):
        increment_retry(
            str(tmp_project), change,
            to_phase="phase-2", verifier_kind="implementation_gap", verifier_exit_code=1,
        )
    data = read_builder_handoff(str(tmp_project), change)
    assert should_halt_for_retry_exceeded(
        data["retry_count"], data["max_retries"]
    ) is True
    assert data["retry_count"] == 3
    assert len(data["retry_history"]) == 3


def test_retry_halt_false_under_max_retries(tmp_project: Path) -> None:
    """retry_count < max_retries must not halt (sanity check)."""
    from _lib.builder_retry import should_halt_for_retry_exceeded
    assert should_halt_for_retry_exceeded(2, 3) is False


def test_retry_halt_true_at_max_retries() -> None:
    """retry_count == max_retries must halt (boundary condition per spec §3.4)."""
    from _lib.builder_retry import should_halt_for_retry_exceeded
    assert should_halt_for_retry_exceeded(3, 3) is True
    assert should_halt_for_retry_exceeded(4, 3) is True


def test_retry_routing_covers_all_five_exit_codes() -> None:
    """route_verifier_verdict handles all 5 ADR-0034 exit codes."""
    from _lib.builder_retry import route_verifier_verdict

    assert route_verifier_verdict(0)["next_phase"] == "phase-3-archive"
    assert route_verifier_verdict(1)["next_phase"] == "phase-2"
    assert route_verifier_verdict(2)["next_phase"] == "phase-1"
    assert route_verifier_verdict(3)["next_phase"] == "halt"
    assert route_verifier_verdict(3)["verifier_kind"] == "needs_human"
    assert route_verifier_verdict(4)["next_phase"] == "halt"
    assert route_verifier_verdict(4)["verifier_kind"] == "halted_max_loops"
    unknown = route_verifier_verdict(99)
    assert unknown["halted"] is True
    assert "unknown" in unknown["verifier_kind"]


# ---------------------------------------------------------------------------
# builder_cmd CLI: list / status subcommands
# ---------------------------------------------------------------------------

def test_cmd_builder_list_returns_zero_when_no_state(tmp_project: Path) -> None:
    """rddf builder list on empty state exits 0 with 'no active changes' notice."""
    from _lib.cli.builder_cmd import cmd_builder
    rc = cmd_builder(["list"], project_root=str(tmp_project))
    assert rc == 0


def test_cmd_builder_status_returns_zero_with_state(tmp_project: Path) -> None:
    """rddf builder status prints phase / retry_count / pause_history."""
    from _lib.cli.builder_cmd import cmd_builder
    from _lib.builder_handoff import write_builder_handoff

    change = "demo-change"
    write_builder_handoff(
        str(tmp_project), change,
        current_phase="phase-1", retry_count=2, max_retries=3,
        retry_history=[{"from_phase": "phase-3", "to_phase": "phase-2",
                        "verifier_exit_code": 1, "verifier_kind": "implementation_gap",
                        "at": "2026-09-05T00:00:00+00:00"}],
    )
    rc = cmd_builder(["status", change], project_root=str(tmp_project))
    assert rc == 0