r"""Smoke tests for the 7 new public functions added to populate_lib.py (Task C).

Asserts each function exists with the documented signature (inspect.signature).
Behavioral / scenario coverage lives in test_populate_lib_incremental.py.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "populate-roadmap-from-arch" / "scripts"))


def test_load_populate_state_or_default_exists():
    from populate_lib import load_populate_state_or_default
    sig = inspect.signature(load_populate_state_or_default)
    assert "project_root" in sig.parameters


def test_save_populate_state_exists():
    from populate_lib import save_populate_state
    sig = inspect.signature(save_populate_state)
    assert set(sig.parameters.keys()) >= {"state", "project_root", "codebase_commit"}


def test_detect_adr_changes_exists():
    from populate_lib import detect_adr_changes
    sig = inspect.signature(detect_adr_changes)
    assert set(sig.parameters.keys()) >= {"state", "project_root", "scan_adr_catalog_fn"}


def test_detect_code_changes_exists():
    from populate_lib import detect_code_changes
    sig = inspect.signature(detect_code_changes)
    assert set(sig.parameters.keys()) >= {"state", "project_root"}


def test_decide_update_mode_exists():
    from populate_lib import decide_update_mode
    sig = inspect.signature(decide_update_mode)
    assert set(sig.parameters.keys()) >= {"adr_changes", "code_changes"}


def test_select_adrs_for_incremental_verify_exists():
    from populate_lib import select_adrs_for_incremental_verify
    sig = inspect.signature(select_adrs_for_incremental_verify)
    assert set(sig.parameters.keys()) >= {"adrs", "state", "mode", "extra"}


def test_should_rewrite_phase_fragment_exists():
    from populate_lib import should_rewrite_phase_fragment
    sig = inspect.signature(should_rewrite_phase_fragment)
    assert set(sig.parameters.keys()) >= {"phase_id", "prev_state", "new_state", "mode"}


def test_all_seven_names_in___all__():
    import populate_lib
    expected = {
        "load_populate_state_or_default",
        "save_populate_state",
        "detect_adr_changes",
        "detect_code_changes",
        "decide_update_mode",
        "select_adrs_for_incremental_verify",
        "should_rewrite_phase_fragment",
    }
    assert expected.issubset(set(populate_lib.__all__))
