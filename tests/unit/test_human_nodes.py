"""Tests for skills._lib.human_nodes — 7 node types + 3 verification modes."""
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_actions_module(monkeypatch):
    """Inject a stub `skills._lib.actions` module exposing run_subprocess.

    The real `actions.py` ships in a parallel task; this fixture lets our
    tests run regardless of order. monkeypatch guarantees cleanup.
    """
    from dataclasses import dataclass, field
    from typing import Optional

    @dataclass
    class _FakeActionResult:
        success: bool
        data: dict = field(default_factory=dict)
        error: Optional[str] = None

    fake_actions = types.ModuleType("skills._lib.actions")

    def fake_run_subprocess(cmd, timeout_seconds=30 * 60):
        # Real subprocess execution so SCRIPT verification exercises actual
        # shell semantics when available.
        import subprocess
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_seconds
            )
            return _FakeActionResult(
                success=(proc.returncode == 0),
                data={
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                },
                error=None if proc.returncode == 0 else f"exit {proc.returncode}",
            )
        except subprocess.TimeoutExpired:
            return _FakeActionResult(
                success=False,
                data={"timed_out": True, "timeout_seconds": timeout_seconds},
                error=f"timeout after {timeout_seconds}s",
            )
        except Exception as exc:
            return _FakeActionResult(success=False, data={"exception": str(exc)}, error=str(exc))

    fake_actions.run_subprocess = fake_run_subprocess
    monkeypatch.setitem(sys.modules, "skills._lib.actions", fake_actions)
    return fake_actions


def test_seven_node_types_registered():
    """All 7 human-in-loop node types present in registry."""
    from skills._lib.human_nodes import HumanNodeRegistry

    reg = HumanNodeRegistry()
    expected = {
        "arch.adr_create",
        "arch.roadmap_define",
        "plan.change_select",
        "plan.propose_confirm",
        "ship.archive_confirm",
        "ship.cleanup_confirm",
        "ship.execute_error",
    }
    actual = {n.name for n in reg.list_nodes()}
    assert expected == actual


def test_verification_modes_enum():
    """3 verification modes: human, multi_model, script."""
    from skills._lib.human_nodes import VerificationMode

    assert VerificationMode.HUMAN.value == "human"
    assert VerificationMode.MULTI_MODEL.value == "multi_model"
    assert VerificationMode.SCRIPT.value == "script"


def test_multi_model_without_tribunal_raises_unavailable():
    """multi_model verification raises when no Tribunal is injected."""
    from skills._lib.human_nodes import (
        HumanNodeRegistry,
        NodeTrigger,
        VerificationMode,
        MultiModelUnavailableError,
    )

    reg = HumanNodeRegistry()
    trigger = NodeTrigger(
        name="arch.adr_create",
        mode=VerificationMode.MULTI_MODEL,
        params={},
    )
    with pytest.raises(MultiModelUnavailableError, match="v2-advanced-features"):
        reg.verify(trigger)


def test_multi_model_delegates_to_injected_tribunal():
    """multi_model verification maps TribunalResult into VerificationResult."""
    from dataclasses import dataclass
    from skills._lib.human_nodes import HumanNodeRegistry, NodeTrigger, VerificationMode

    @dataclass
    class _Result:
        passed: bool = True
        exec_score: float = 0.9
        review_score: float = 0.95
        final_score: float = 0.93
        conflict: float = 0.05

    class _Tribunal:
        def __init__(self):
            self.calls = []

        def verify(self, change_name, criteria, context):
            self.calls.append((change_name, criteria, context))
            return _Result()

    tribunal = _Tribunal()
    reg = HumanNodeRegistry(tribunal=tribunal)
    trigger = NodeTrigger(
        name="plan.propose_confirm",
        mode=VerificationMode.MULTI_MODEL,
        params={
            "change_name": "v2-advanced-features",
            "criteria": "all tests pass",
            "context": {"tests": "green"},
        },
    )

    result = reg.verify(trigger)

    assert result.success is True
    assert result.data["final_score"] == 0.93
    assert tribunal.calls == [
        ("v2-advanced-features", "all tests pass", {"tests": "green"})
    ]


def test_script_verification_runs_command(fake_actions_module):
    """script verification runs configured command and uses exit code."""
    from skills._lib.human_nodes import HumanNodeRegistry, NodeTrigger, VerificationMode

    reg = HumanNodeRegistry()
    trigger = NodeTrigger(
        name="plan.change_select",
        mode=VerificationMode.SCRIPT,
        params={"command": ["true"]},
    )
    result = reg.verify(trigger)
    assert result.success is True