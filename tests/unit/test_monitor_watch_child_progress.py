"""AC-G4 fixture: monitor --watch=N re-renders child progress from events.jsonl.

Per ADR-0056 decision 6 AC-G4: monitor --watch=1 模式正确长跑
Per W2.3 (complete-guide-orchestrator-flow): monitor Panel 5 显示 child progress

These tests lock down:
1. _render_monitor() includes a "Child Progress" panel
2. --watch loop re-renders correctly (calls _render_monitor each tick)
3. Panel 5 reflects child_progress from workflow_synthesizer
4. No active children → "(no active stage_X children)" sentinel
5. Errors in synthesizer → graceful "(child progress unavailable)" fallback
"""
from __future__ import annotations

import io
import json
import os
import subprocess
from contextlib import redirect_stdout
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh project_root + .rddf/state/ for AC-G4 fixture."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    yield tmp_path


def _run_hook(kind: str, intent: str, owner: str = "ac_g4_owner"):
    """Same helper pattern as test_ac_g1_red_green."""
    cmd = [
        "bash", "-c",
        f'source "{HOOKS_SH}" && '
        f'rddf_session_hook_entry {kind} {intent} "ac-g4-subject" "ok"'
    ]
    import os as _os
    env = _os.environ.copy()
    env["OPENCODE_SESSION_ID"] = owner
    env["RDDF_OWNER"] = owner
    env["RDDF_OWNER_FROM"] = "shell-pid"
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
    )


def _capture_render(project_root: str) -> str:
    """Capture _render_monitor output for assertion."""
    from _lib.cli.monitor_cmd import _render_monitor
    buf = io.StringIO()
    with redirect_stdout(buf):
        _render_monitor(project_root)
    return buf.getvalue()


def _run_monitor_subprocess(project_root: Path, watch_interval: int = 1,
                            duration_sec: float = 2.5):
    """Helper: launch monitor subprocess with proper env, run for N seconds,
    capture all stdout. Returns (returncode, full_stdout)."""
    import signal
    import time
    # Inherit current env so the subprocess uses the same Python venv
    # (where jsonschema etc. are installed) and PYTHONPATH for the repo.
    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(project_root)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        ["python3", "-m", "skills._lib.cli", "monitor", f"--watch={watch_interval}"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    captured_chunks = []
    try:
        time.sleep(duration_sec)
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=3)
        captured_chunks.append(out)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        captured_chunks.append(out)
    return proc.returncode, "".join(captured_chunks)


# --- AC-G4: monitor panel 5 shows child progress ---

class TestAC_G4_ChildProgressPanel:
    """The monitor dashboard's Panel 5 must show W2.2 child progress."""

    def test_panel_5_present_in_render(self, tmp_project):
        """_render_monitor must include 'Child Progress (W2.3)' section."""
        output = _capture_render(str(tmp_project))
        assert "Child Progress (W2.3)" in output, (
            f"Panel 5 missing in monitor output:\n{output}"
        )

    def test_no_active_children_shows_sentinel(self, tmp_project):
        """No active children → '(no active stage_X children)' sentinel."""
        output = _capture_render(str(tmp_project))
        assert "(no active stage_X children)" in output, (
            f"Expected sentinel, got:\n{output}"
        )

    def test_active_builder_shows_progress(self, tmp_project):
        """Create stage_builder session → Panel 5 shows 'stage_builder 完成 0/1'."""
        proc = _run_hook("stage_builder", "rdd-builder")
        assert proc.returncode == 0
        output = _capture_render(str(tmp_project))
        assert "stage_builder" in output
        assert "完成" in output

    def test_two_active_children_show_both(self, tmp_project):
        """2 active children → Panel 5 shows both."""
        proc_b = _run_hook("stage_builder", "rdd-builder", owner="owner_B")
        proc_v = _run_hook("stage_verify", "rdd-verifier", owner="owner_V")
        assert proc_b.returncode == 0
        assert proc_v.returncode == 0
        output = _capture_render(str(tmp_project))
        assert "stage_builder" in output
        assert "stage_verify" in output


# --- --watch loop: re-renders correctly each tick ---

class TestWatchModeReRender:
    """--watch=N must call _render_monitor repeatedly with up-to-date state."""

    def test_cmd_monitor_watch_renders_multiple_times(self, tmp_project):
        """Run monitor --watch=1 for 2.5s, verify Panel 5 appears in output."""
        rc, output = _run_monitor_subprocess(tmp_project, watch_interval=1,
                                             duration_sec=2.5)
        assert "Child Progress (W2.3)" in output, (
            f"monitor --watch output missing Panel 5; output[:500]={output[:500]}"
        )
        # Verify clear-screen ANSI emitted (proves watch loop is iterating)
        assert "\x1b[2J" in output, (
            f"monitor --watch not iterating (no ANSI clear-screen); output[:200]={output[:200]}"
        )


# --- Error handling: synthesizer crash doesn't kill monitor ---

class TestPanel5GracefulFailure:
    """If synthesizer throws, monitor shows fallback message instead of crashing."""

    def test_synthesize_exception_shows_fallback(self, tmp_project, monkeypatch):
        """Patch synthesize to raise; monitor must show '(child progress unavailable)'."""
        import skills._lib.workflow_synthesizer as ws

        def boom(_root):
            raise RuntimeError("synthesizer crashed")
        monkeypatch.setattr(ws, "synthesize", boom)

        output = _capture_render(str(tmp_project))
        assert "child progress unavailable" in output, (
            f"Expected fallback message, got:\n{output}"
        )


# --- Roundtrip: monitor --watch picks up new events between ticks ---

class TestWatchPicksUpNewEvents:
    """Running --watch=1 and adding a new event mid-run should appear in next tick."""

    def test_new_session_appears_in_monitor_output(self, tmp_project):
        """Pre-populate stage_builder session, then run monitor --watch=1
        and verify Panel 5 contains 'stage_builder' in the output."""
        # Pre-create the session
        sub = _run_hook("stage_builder", "rdd-builder", owner="ac_g4_watch")
        assert sub.returncode == 0

        rc, output = _run_monitor_subprocess(tmp_project, watch_interval=1,
                                             duration_sec=2.5)
        # Panel 5 must show the builder
        assert "stage_builder" in output, (
            f"session not visible in monitor output; output[:800]={output[:800]}"
        )
        assert "完成" in output, (
            f"child progress '完成' marker missing; output[:800]={output[:800]}"
        )