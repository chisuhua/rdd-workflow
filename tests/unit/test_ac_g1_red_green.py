"""End-to-end AC-G1 verification: hook entry → sessions.json + events.jsonl落盘。

Locks down the red→green criterion from ADR-0056 decision 6:
- AC-G1: `rddf_session_hook_entry` 调用 stage_builder/verify/quick 时,
  session 真的落盘 + events.jsonl 写 phase_started

Step A.1+A.2 修复前 fail (kind enum 拒绝 → RddfSessionError 静默 → 双空)
Step A.1+A.2 修复后 pass (本文件锁定行为)

Conftest 的 sys.path 注入使 `from skills.rddf_session...` 可解析。
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh project_root + .rddf/state/ for AC-G1 red→green tests."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    yield tmp_path


def _run_hook(kind: str, intent: str, owner: str = "ac_g1_owner"):
    """Invoke rddf_session_hook_entry via bash."""
    cmd = [
        "bash", "-c",
        f'source "{HOOKS_SH}" && '
        f'rddf_session_hook_entry {kind} {intent} "ac-g1-subject" "ok"'
    ]
    import os
    env = os.environ.copy()
    env["OPENCODE_SESSION_ID"] = owner
    env["RDDF_OWNER"] = owner
    env["RDDF_OWNER_FROM"] = "shell-pid"
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
    )


# --- RED state: invalid kind must NOT create session or event ---

class TestAC_G1_RedState:
    """Bogus kind → no session, no event, exit 3 (fail-loud from Step A.2)."""

    def test_bogus_kind_does_not_create_session(self, tmp_project):
        proc = _run_hook("stage_bogus", "rdd-builder")
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        assert not sessions_file.exists(), (
            "sessions.json should NOT exist after bogus kind call"
        )

    def test_bogus_kind_does_not_create_event(self, tmp_project):
        proc = _run_hook("stage_bogus", "rdd-builder")
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        assert not events_file.exists(), (
            "events.jsonl should NOT exist after bogus kind call"
        )

    def test_bogus_kind_exits_3(self, tmp_project):
        proc = _run_hook("stage_bogus", "rdd-builder")
        assert proc.returncode == 3


# --- GREEN state: valid v4 kinds create session + phase_started event ---

class TestAC_G1_GreenState:
    """Step A.1+A.2 修复后:3 新 kind 各创建 session + phase_started event."""

    @pytest.mark.parametrize("kind,intent", [
        ("stage_builder", "rdd-builder"),
        ("stage_verify", "rdd-verifier"),
        ("stage_quick", "rdd-quick"),
    ])
    def test_kind_creates_session_in_sessions_json(self, tmp_project, kind, intent):
        proc = _run_hook(kind, intent)
        assert proc.returncode == 0
        sessions_file = tmp_project / ".rddf" / "state" / "sessions.json"
        assert sessions_file.exists(), f"sessions.json missing after {kind} hook"
        data = json.loads(sessions_file.read_text())
        kinds = [s.get("kind") for s in data.get("sessions", [])]
        assert kind in kinds, f"expected kind={kind} in sessions; got {kinds}"

    @pytest.mark.parametrize("kind,intent", [
        ("stage_builder", "rdd-builder"),
        ("stage_verify", "rdd-verifier"),
        ("stage_quick", "rdd-quick"),
    ])
    def test_kind_writes_phase_started_event(self, tmp_project, kind, intent):
        """Assert events.jsonl contains phase_started event with context.kind == <kind>."""
        proc = _run_hook(kind, intent)
        assert proc.returncode == 0
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        assert events_file.exists(), f"events.jsonl missing after {kind} hook"
        lines = events_file.read_text().strip().split("\n")
        matched = []
        for line in lines:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event_type") == "phase_started":
                matched.append(ev)
        assert matched, f"no phase_started events in events.jsonl; lines={lines}"
        context_kinds = [ev.get("context", {}).get("kind") for ev in matched]
        assert kind in context_kinds, (
            f"expected context.kind={kind} in phase_started events; "
            f"got context_kinds={context_kinds}"
        )

    def test_three_kinds_three_sessions_and_events(self, tmp_project):
        """3 hooks in sequence → 3 distinct sessions + 3 phase_started events."""
        for kind, intent in [
            ("stage_builder", "rdd-builder"),
            ("stage_verify", "rdd-verifier"),
            ("stage_quick", "rdd-quick"),
        ]:
            proc = _run_hook(kind, intent)
            assert proc.returncode == 0, f"{kind} failed: {proc.stderr}"
        sessions = json.loads(
            (tmp_project / ".rddf" / "state" / "sessions.json").read_text()
        )
        kinds = sorted([s["kind"] for s in sessions["sessions"]])
        assert kinds == ["stage_builder", "stage_quick", "stage_verify"]
        events = []
        for line in (tmp_project / ".rddf" / "state" / "events.jsonl").read_text().strip().split("\n"):
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event_type") == "phase_started":
                events.append(ev)
        event_kinds = sorted([ev["context"]["kind"] for ev in events])
        assert event_kinds == ["stage_builder", "stage_quick", "stage_verify"], (
            f"events: {event_kinds}"
        )


# --- Reference: AC-G1 jq-based manual check (documented in ADR-0056 + improvement) ---

class TestAC_G1_DocumentedAssertion:
    """The jq assertion from ADR-0056 §决策 6 + improvement §Acceptance must work."""

    def test_jq_assertion_path_is_correct(self, tmp_project):
        """`.context.kind` is the right jq path per EventsLog implementation."""
        proc = _run_hook("stage_builder", "rdd-builder")
        assert proc.returncode == 0
        events_file = tmp_project / ".rddf" / "state" / "events.jsonl"
        # Read events.jsonl and apply the documented jq assertion
        import subprocess as sp
        jq_result = sp.run(
            ["jq", "-r", 'select(.event_type=="phase_started") | .context.kind',
             str(events_file)],
            capture_output=True, text=True,
        )
        assert jq_result.returncode == 0, f"jq failed: {jq_result.stderr}"
        assert jq_result.stdout.strip() == "stage_builder", (
            f"documented jq assertion failed; got {jq_result.stdout!r}"
        )