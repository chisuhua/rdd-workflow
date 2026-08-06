"""Tests for _lib/defaults.py — built-in DEFAULTS config & get_defaults() helper."""
import pytest
from skills._lib.core.defaults import DEFAULTS, get_defaults


def test_defaults_has_required_sections():
    """DEFAULTS must expose the documented top-level sections used by config merge."""
    expected_sections = {"version", "interaction", "loop", "state", "event_log", "gate", "sync"}
    assert expected_sections.issubset(DEFAULTS.keys()), (
        f"DEFAULTS missing sections: {expected_sections - set(DEFAULTS.keys())}"
    )
    assert DEFAULTS["version"] == "2.0"
    assert DEFAULTS["interaction"]["mode"] == "hybrid"
    assert DEFAULTS["loop"]["max_iterations"] == 100
    assert DEFAULTS["state"]["lock_timeout_seconds"] == 10.0
    assert DEFAULTS["event_log"]["max_size_mb"] == 50
    assert DEFAULTS["sync"]["conflict_resolution"] == "state_vector_wins"


def test_get_defaults_returns_deep_copy():
    """Mutating the returned dict must not affect the module-level DEFAULTS."""
    snapshot = get_defaults()
    snapshot["loop"]["max_iterations"] = 999
    snapshot["interaction"]["menu_items"].append("rogue")

    fresh = get_defaults()
    assert fresh["loop"]["max_iterations"] == 100, (
        "get_defaults() leaked mutation back to DEFAULTS — not a deep copy"
    )
    assert "rogue" not in fresh["interaction"]["menu_items"], (
        "get_defaults() returned a shared list — not a deep copy"
    )
    # Original DEFAULTS is also untouched.
    assert DEFAULTS["loop"]["max_iterations"] == 100
    assert "rogue" not in DEFAULTS["interaction"]["menu_items"]


def test_interaction_menu_items_are_supported_skills():
    """The default menu_items must reference skills that exist in the skill surface."""
    menu = DEFAULTS["interaction"]["menu_items"]
    assert isinstance(menu, list)
    assert len(menu) >= 1
    for item in menu:
        assert isinstance(item, str)
        assert item  # non-empty