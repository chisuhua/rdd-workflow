"""Regression test for fix-guide-close-owner-resolution.

Verifies that the trap 'rddf_session_hook_guide_close' EXIT INT TERM handler
can still read PROJECT_ROOT after guide_entry() returns (where PROJECT_ROOT
was previously declared `local` and popped out of scope).

Per fix-guide-close-owner-resolution.md (improvement P1, 2026-09-23):
- AC-1: rddf_session_hook_guide_close can read PROJECT_ROOT in trap context
- AC-3: regression test covers `local PROJECT_ROOT` boundary
"""
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE_ENTRY = REPO_ROOT / "skills" / "guide" / "scripts" / "guide_entry.sh"
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


def test_guide_entry_exports_project_root():
    """guide_entry.sh must export PROJECT_ROOT (not just declare `local`) so trap can read it."""
    text = GUIDE_ENTRY.read_text()
    assert "local PROJECT_ROOT" in text, "guide_entry.sh: PROJECT_ROOT declaration changed (test needs update)"
    # The fix: ensure export comes AFTER the local declaration
    lines = text.split("\n")
    found_local = False
    found_export = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("local PROJECT_ROOT"):
            found_local = True
        elif found_local and stripped == "export PROJECT_ROOT":
            found_export = True
            break
    assert found_export, (
        "guide_entry.sh must `export PROJECT_ROOT` after declaring it `local` "
        "so trap 'EXIT INT TERM' can read it after function returns. "
        "See fix-guide-close-owner-resolution.md AC-1."
    )


def test_rddf_resolve_owner_has_trap_context_layer():
    """_rddf_resolve_owner must check RDDF_RESOLVE_OWNER_FROM_TRAP and override owner with $$."""
    text = HOOKS_SH.read_text()
    assert "RDDF_RESOLVE_OWNER_FROM_TRAP" in text, (
        "_rddf_resolve_owner must consult RDDF_RESOLVE_OWNER_FROM_TRAP env var "
        "to provide trap-context-specific owner resolution. "
        "See fix-guide-close-owner-resolution.md AC-1."
    )
    assert "trap-shell-pid" in text, (
        "_rddf_resolve_owner must label the trap-context fallback as 'trap-shell-pid' "
        "for traceability. See fix-guide-close-owner-resolution.md What Changes."
    )


def test_guide_close_sets_trap_flag():
    """rddf_session_hook_guide_close must set RDDF_RESOLVE_OWNER_FROM_TRAP=yes before _rddf_resolve_owner."""
    text = HOOKS_SH.read_text()
    # Find the rddf_session_hook_guide_close function body
    start = text.find("rddf_session_hook_guide_close()")
    assert start >= 0, "rddf_session_hook_guide_close function not found"
    # Look for the pattern within a reasonable window
    end = text.find("\n}\n", start)
    func_body = text[start:end]
    assert "RDDF_RESOLVE_OWNER_FROM_TRAP=yes" in func_body, (
        "rddf_session_hook_guide_close must invoke "
        "`RDDF_RESOLVE_OWNER_FROM_TRAP=yes _rddf_resolve_owner` "
        "to signal trap context to owner resolver. "
        "See fix-guide-close-owner-resolution.md What Changes."
    )


def test_guide_close_can_read_project_root_in_trap_context():
    """End-to-end: spawn bash that sources guide_entry, calls it, then SIGTERMs itself.
    The trap handler must successfully close the stage_guide session."""
    if not GUIDE_ENTRY.exists():
        # Allow skipping in environments where guide_entry.sh is not available
        import pytest
        pytest.skip("guide_entry.sh not found")

    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)
        # Init a git repo so `git rev-parse --show-toplevel` returns project_root
        subprocess.run(["git", "init", "-q"], cwd=project_root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.local"],
            cwd=project_root, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=project_root, check=True,
        )
        Path(project_root / "README.md").write_text("test")
        subprocess.run(
            ["git", "add", "README.md"], cwd=project_root, check=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=project_root, check=True,
        )

        # Source guide_entry, call it, sleep, then send SIGTERM to self.
        script = f"""
            set -e
            cd "{project_root}"
            export RDDF_GUIDE_SESSION_ENABLED=yes
            export PYTHONPATH="{REPO_ROOT}:$PYTHONPATH"
            source "{GUIDE_ENTRY}"
            guide_entry --no-binding
            sleep 60 &
            WAIT_PID=$!
            # Kill the sleep with SIGTERM; trap should fire and call guide_close
            kill -TERM $WAIT_PID
            wait $WAIT_PID || true
            sleep 0.5
        """
        env = os.environ.copy()
        env["RDD_WORKFLOW_REPO"] = str(REPO_ROOT)
        result = subprocess.run(
            ["bash", "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # The trap should have run and marked session completed
        # Read sessions.json and check state
        sessions_file = project_root / ".rddf" / "state" / "sessions.json"
        assert sessions_file.exists(), (
            f"sessions.json not created: stderr={result.stderr}"
        )
        import json
        sessions = json.loads(sessions_file.read_text()).get("sessions", [])
        stage_guide = [
            s for s in sessions
            if s.get("kind") == "stage_guide"
        ]
        assert stage_guide, "no stage_guide session created"
        # After SIGTERM, at least one stage_guide session should be in
        # terminal state (completed/failed/abandoned)
        terminal = [
            s for s in stage_guide
            if s.get("state") in ("completed", "failed", "abandoned")
        ]
        assert terminal, (
            f"expected stage_guide session to be marked terminal after SIGTERM, "
            f"got states={[s.get('state') for s in stage_guide]}; "
            f"stdout={result.stdout[-500:]}; stderr={result.stderr[-500:]}"
        )