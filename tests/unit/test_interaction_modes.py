"""Tests for skills._lib.interaction_modes — Loop / Menu / Hybrid."""
import pytest

from skills._lib.interaction_modes import LoopMode, MenuMode, HybridMode, make_mode
from skills._lib.human_nodes import HumanNodeRegistry, NodeTrigger, VerificationMode


@pytest.fixture
def registry():
    return HumanNodeRegistry()


def test_loop_mode_skips_human_nodes_except_on_error(registry):
    """Loop mode runs autonomously; skips human nodes unless error."""
    mode = LoopMode(registry)
    trigger = NodeTrigger("arch.adr_create", VerificationMode.HUMAN, {})
    # In success path, loop mode auto-confirms
    assert mode.should_pause(trigger, context={"error": False}) is False
    # In error path, loop mode DOES pause
    assert mode.should_pause(trigger, context={"error": True}) is True


def test_menu_mode_pauses_at_every_decision(registry):
    """Menu mode pauses at every human node."""
    mode = MenuMode(registry)
    trigger = NodeTrigger("plan.change_select", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger, context={"error": False}) is True


def test_hybrid_mode_pauses_only_at_configured_nodes(registry):
    """Hybrid mode pauses only at nodes in human_nodes config."""
    mode = HybridMode(
        registry,
        human_nodes={"arch.adr_create", "ship.archive_confirm"},
    )
    # Configured node → pause
    trigger1 = NodeTrigger("arch.adr_create", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger1, context={"error": False}) is True
    # Non-configured node → skip
    trigger2 = NodeTrigger("plan.change_select", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger2, context={"error": False}) is False
    # Error overrides whitelist — always pauses
    assert mode.should_pause(trigger2, context={"error": True}) is True


def test_mode_name_returns_correct_value(registry):
    """Each mode reports its name."""
    assert LoopMode(registry).name == "loop"
    assert MenuMode(registry).name == "menu"
    assert HybridMode(registry, human_nodes=set()).name == "hybrid"


def test_make_mode_factory_returns_correct_instances(registry):
    """make_mode() factory dispatches by name."""
    assert isinstance(make_mode("loop", registry), LoopMode)
    assert isinstance(make_mode("menu", registry), MenuMode)
    assert isinstance(make_mode("hybrid", registry, human_nodes={"x"}), HybridMode)
    # Unknown mode raises ValueError
    with pytest.raises(ValueError, match="Unknown mode"):
        make_mode("unknown", registry)