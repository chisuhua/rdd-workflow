"""Tests for _collect_existing_features() helper in propose_change.py."""
import json
import sys
from pathlib import Path

import pytest

# Add project root to sys.path so we can import the module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "propose" / "scripts"))

from propose_change import _collect_existing_features  # noqa: E402


def _write_iteration(tmp_path: Path, changes: list[dict]) -> Path:
    """Helper: write a test iteration.json under tmp_path."""
    iter_path = tmp_path / ".rddf" / "state" / "iteration.json"
    iter_path.parent.mkdir(parents=True, exist_ok=True)
    iter_path.write_text(json.dumps({"version": 1, "changes": changes}))
    return iter_path


def test_typo_detection_returns_existing_features(tmp_path):
    """GIVEN iteration.json with parent_feature='wave-core'
       WHEN helper collects existing features
       THEN 'wave-core' is in result, typo 'wave-cores' would be detected as missing."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "wave-core", "status": "proposed"},
    ])
    result = _collect_existing_features(tmp_path)
    assert "wave-core" in result
    assert "wave-cores" not in result  # typo is NOT in existing set


def test_correct_spelling_silent_pass(tmp_path):
    """GIVEN iteration.json with parent_feature='wave-core'
       WHEN checking new value 'wave-core' against result
       THEN no missing (i.e., value is in set → no warning needed)."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "wave-core", "status": "proposed"},
    ])
    result = _collect_existing_features(tmp_path)
    # Correct spelling: result contains the value → silent pass
    assert "wave-core" in result


def test_empty_iteration_passes_all_values(tmp_path):
    """GIVEN iteration.json does not exist
       WHEN helper is called
       THEN returns empty set (any parent_feature value passes)."""
    # tmp_path has no .rddf/state/iteration.json
    result = _collect_existing_features(tmp_path)
    assert result == set()


def test_ungrouped_excluded(tmp_path):
    """GIVEN iteration.json with parent_feature='__ungrouped__'
       WHEN helper collects
       THEN __ungrouped__ is excluded (synthetic key, not user-selectable)."""
    _write_iteration(tmp_path, [
        {"name": "change-a", "parent_feature": "__ungrouped__", "status": "proposed"},
    ])
    result = _collect_existing_features(tmp_path)
    assert "__ungrouped__" not in result
