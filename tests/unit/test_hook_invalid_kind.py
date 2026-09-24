"""Tests for hook entry-block fail-loud behavior (Step A.2 of complete-guide-orchestrator-flow).

BEFORE Step A.2: rddf_session_hook_entry only caught ConflictError; any other RddfSessionError
(invalid kind, schema violation) propagated as a Python traceback → bash exits non-zero but
SKILL.md caller sees a cryptic traceback instead of a clear error message.

AFTER Step A.2: rddf_session_hook_entry now catches RddfSessionError separately and exits
with code 3, printing the exception class name + message to stderr. ConflictError keeps
its resume/abandon semantics (exit 2).

This file locks down:
1. Invalid kind → exit 3 + clear stderr + no session created
2. Valid v4 kinds (stage_builder/verify/quick) → exit 0 + session created + phase_started event
3. ConflictError (legitimate cross-stage conflict) → exit 2 (unchanged behavior)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh project_root with .rddf/state/ for each test."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    # Provide minimal env for _rddf_resolve_owner (PROJECT_ROOT + OWNER)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    yield tmp_path


def _run_hook(kind: str, intent: str, owner: str = "test_owner"):
    """Invoke rddf_session_hook_entry via bash and capture (returncode, stdout, stderr)."""
    cmd = [
        "bash", "-c",
        f'source "{HOOKS_SH}" && '
        f'rddf_session_hook_entry {kind} {intent} "test-subject" "ok"'
    ]
    env = os.environ.copy()
    env["OPENCODE_SESSION_ID"] = owner
    env["RDDF_OWNER"] = owner
    env["RDDF_OWNER_FROM"] = "shell-pid"
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),  # for module imports
    )
    return proc.returncode, proc.stdout, proc.stderr


# --- Invalid kind → fail-loud (the regression test for the root cause) ---

class TestInvalidKindFailLoud:
    """Step A.2: invalid kind should exit 3 with clear stderr message."""

    def test_bogus_kind_exits_3(self, tmp_project):
        """An unknown kind like 'stage_bogus' must NOT silently pass; must fail loudly."""
        rc, stdout, stderr = _run_hook("stage_bogus", "rdd-builder")
        assert rc == 3, f"expected exit 3 (fail-loud), got {rc}. stdout={stdout!r} stderr={stderr!r}"
        assert "Invalid kind" in stderr, f"stderr should mention 'Invalid kind', got: {stderr!r}"
        assert "stage_bogus" in stderr, f"stderr should echo the bad kind, got: {stderr!r}"

    def test_bogus_kind_no_session_created(self, tmp_project):
        """Invalid kind must NOT leave a stale session in sessions.json."""
        _run_hook("stage_bogus", "rdd-builder")
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        if sessions_file.exists():
            data = json.loads(sessions_file.read_text())
            kinds = [s.get("kind") for s in data.get("sessions", [])]
            assert "stage_bogus" not in kinds, (
                f"session with invalid kind was created: {kinds}"
            )

    def test_empty_kind_exits_3(self, tmp_project):
        """Empty kind string should also fail loud."""
        # Use bash to quote the empty kind so positional arg $1 is the empty string
        # (otherwise bash collapses `rddf_session_hook_entry  rdd-builder` into 4 args,
        # making kind the test point at a real string).
        cmd = [
            "bash", "-c",
            f'source "{HOOKS_SH}" && rddf_session_hook_entry "" "rdd-builder" "test-subject" "ok"'
        ]
        env = os.environ.copy()
        env["OPENCODE_SESSION_ID"] = "test_owner"
        env["RDDF_OWNER"] = "test_owner"
        env["RDDF_OWNER_FROM"] = "shell-pid"
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))
        assert proc.returncode == 3, (
            f"expected exit 3 for empty kind, got {proc.returncode}. stderr={proc.stderr!r}"
        )
        assert "Invalid kind" in proc.stderr

    def test_legacy_wrong_kind_exits_3(self, tmp_project):
        """A kind that looks plausible but isn't in _VALID_KINDS fails loud (e.g., stage_madeup)."""
        rc, _, stderr = _run_hook("stage_madeup", "guide-orchestrator")
        assert rc == 3
        assert "Invalid kind" in stderr
        assert "stage_madeup" in stderr


# --- Valid v4 kinds → exit 0 + session created + event written ---

class TestValidV4KindsSucceed:
    """The 3 new kinds from Step A.1 should now work end-to-end through the bash hook."""

    @pytest.mark.parametrize("kind,intent", [
        ("stage_builder", "rdd-builder"),
        ("stage_verify", "rdd-verifier"),
        ("stage_quick", "rdd-quick"),
    ])
    def test_v4_kind_creates_session(self, tmp_project, kind, intent):
        rc, stdout, stderr = _run_hook(kind, intent)
        assert rc == 0, f"expected exit 0 for valid kind {kind}, got {rc}. stderr={stderr!r}"
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        assert sessions_file.exists(), "sessions.json should be created"
        data = json.loads(sessions_file.read_text())
        kinds = [s.get("kind") for s in data.get("sessions", [])]
        assert kind in kinds, f"session with kind={kind} not found; got {kinds}"

    @pytest.mark.parametrize("kind,intent", [
        ("stage_builder", "rdd-builder"),
        ("stage_verify", "rdd-verifier"),
        ("stage_quick", "rdd-quick"),
    ])
    def test_v4_kind_alias_resolves(self, tmp_project, kind, intent):
        """rdd-* aliases resolve to canonical stage_* names (per _KIND_ALIAS)."""
        alias_map = {"stage_builder": "rdd-builder", "stage_verify": "rdd-verifier", "stage_quick": "rdd-quick"}
        # Use the alias form as the kind argument
        rc, _, _ = _run_hook(intent, intent)
        assert rc == 0, f"alias {intent} should resolve to canonical {kind}"
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        data = json.loads(sessions_file.read_text())
        canonical_kinds = [s.get("kind") for s in data.get("sessions", [])]
        assert kind in canonical_kinds, (
            f"alias resolution failed: passed kind={intent}, expected canonical {kind} in file; got {canonical_kinds}"
        )


# --- ConflictError keeps its exit-2 + resume/abandon semantic ---

class TestConflictErrorSemantic:
    """Verify the v3 ConflictError path is unchanged (still exit 2 with CONFLICT message)."""

    def test_cross_stage_conflict_exits_2(self, tmp_project):
        """stage_arch active → stage_design should ConflictError (exit 2, not 3)."""
        # First create arch session
        rc1, _, _ = _run_hook("stage_arch", "guide-arch", owner="owner_A")
        assert rc1 == 0, f"arch create failed: {rc1}"

        # Now try to create design from a different owner → cross-stage singleton blocks
        rc2, stdout, stderr = _run_hook("stage_design", "guide-design", owner="owner_B")
        assert rc2 == 2, (
            f"cross-stage conflict should exit 2 (resume/abandon), got {rc2}. "
            f"stderr={stderr!r} stdout={stdout!r}"
        )
        assert "CONFLICT" in stdout, f"stdout should contain CONFLICT message, got: {stdout!r}"


# --- Source-level verification of the fail-loud pattern ---

class TestHookSourcePattern:
    """Verify the rddf_session_hooks.sh source contains the fail-loud handler."""

    def test_hook_imports_rddf_session_error(self):
        """The entry-block heredoc must import RddfSessionError (parent class)."""
        text = HOOKS_SH.read_text()
        assert "RddfSessionError" in text, (
            "rddf_session_hooks.sh must import RddfSessionError in entry block "
            "(Step A.2 fail-loud fix)"
        )

    def test_entry_block_has_rddf_session_error_handler(self):
        """The entry heredoc must have an `except RddfSessionError` branch with sys.exit(3)."""
        text = HOOKS_SH.read_text()
        # Look for the entry block (between `rddf_session_hook_entry()` def and matching close)
        # The fix is in the entry heredoc, not guide_entry
        assert "except RddfSessionError as e:" in text, (
            "rddf_session_hooks.sh must have `except RddfSessionError` handler "
            "in the entry block (Step A.2 fail-loud fix)"
        )
        assert "sys.exit(3)" in text, (
            "rddf_session_hooks.sh entry block must exit(3) on RddfSessionError "
            "(Step A.2 fail-loud fix — distinct from exit(2) for ConflictError)"
        )

    def test_conflict_handler_still_present(self):
        """The ConflictError handler must be preserved (exit 2 + CONFLICT message)."""
        text = HOOKS_SH.read_text()
        assert "except ConflictError as e:" in text, (
            "ConflictError handler must be preserved (v3 semantic)"
        )
        assert "sys.exit(2)" in text
        assert "CONFLICT:" in text or "CONFLICT" in text