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


def test_multi_model_raises_not_implemented():
    """multi_model verification raises NotImplementedError until v2-advanced-features."""
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
    # MultiModelUnavailableError is a NotImplementedError subclass, so both match.
    with pytest.raises(NotImplementedError, match="v2-advanced-features"):
        reg.verify(trigger)
    # And specifically MultiModelUnavailableError (not just any NotImplementedError).
    with pytest.raises(MultiModelUnavailableError, match="Tribunal"):
        reg.verify(trigger)


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