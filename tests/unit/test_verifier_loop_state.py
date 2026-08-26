"""Tests for per-change verifier loop state.

Per fix-rdd-verifier-lifecycle-dashboard Task 2 + ADR-0034 §6:
- Each change has its own loop state at .rddf/state/verifier/<change>.json
- Two changes cannot overwrite each other's retry history
- Legacy single-file .verifier-loop.json migrates only when its 'change' field matches the sole eligible change
"""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.loop_state import (
    init_loop_state, load_loop_state, save_loop_state,
    append_classification, _state_path, _LEGACY_PATH,
)


def test_per_change_state_path(tmp_path):
    p = _state_path(tmp_path, "my-change")
    assert p == tmp_path / ".rddf" / "state" / "verifier" / "my-change.json"


def test_init_creates_state(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    assert state["change"] == "test-change"
    assert state["loop_count"] == 0
    assert state["max_loops"] == 3
    assert state["route"] == "archive-ready"
    assert state["classification_history"] == []
    assert state["verification_state"] == "pending"


def test_init_persists_per_change_file(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    expected = tmp_path / ".rddf" / "state" / "verifier" / "test-change.json"
    assert expected.is_file()


def test_load_returns_saved_state(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    loaded = load_loop_state(tmp_path, "test-change")
    assert loaded is not None
    assert loaded["change"] == "test-change"
    assert loaded["max_loops"] == 3


def test_load_missing_returns_none(tmp_path):
    init_loop_state(tmp_path, "exists")
    assert load_loop_state(tmp_path, "nope") is None


def test_load_corrupt_returns_none(tmp_path):
    p = _state_path(tmp_path, "corrupt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{invalid json")
    assert load_loop_state(tmp_path, "corrupt") is None


def test_save_validates_schema(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    state = load_loop_state(tmp_path, "test-change")
    assert state is not None
    state["route"] = "INVALID"
    with pytest.raises(jsonschema.ValidationError):
        save_loop_state(tmp_path, state, "test-change")


def test_append_classification(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    updated = append_classification(tmp_path, state, "test-change",
                                    "implementation_gap", user_confirmed=True)
    assert updated["loop_count"] == 1
    assert len(updated["classification_history"]) == 1
    assert updated["classification_history"][0]["label"] == "implementation_gap"
    assert updated["classification_history"][0]["user_confirmed"] is True
    assert updated["classification_history"][0]["loop"] == 1


def test_append_increments_loop_count(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    state = append_classification(tmp_path, state, "test-change",
                                  "implementation_gap", user_confirmed=True)
    state = append_classification(tmp_path, state, "test-change",
                                  "proposal_drift", user_confirmed=False)
    assert state["loop_count"] == 2
    assert len(state["classification_history"]) == 2


def test_append_persists_to_disk(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    append_classification(tmp_path, state, "test-change",
                          "implementation_gap", user_confirmed=True)
    loaded = load_loop_state(tmp_path, "test-change")
    assert loaded["loop_count"] == 1


def test_two_changes_dont_overwrite_each_other(tmp_path):
    a = init_loop_state(tmp_path, "alpha")
    a["loop_count"] = 3
    save_loop_state(tmp_path, a, "alpha")

    b = init_loop_state(tmp_path, "beta")
    b["loop_count"] = 7
    save_loop_state(tmp_path, b, "beta")

    assert load_loop_state(tmp_path, "alpha")["loop_count"] == 3
    assert load_loop_state(tmp_path, "beta")["loop_count"] == 7


def test_append_isolates_per_change(tmp_path):
    a = init_loop_state(tmp_path, "alpha")
    b = init_loop_state(tmp_path, "beta")

    a = append_classification(tmp_path, a, "alpha",
                              "implementation_gap", user_confirmed=True)
    a = append_classification(tmp_path, a, "alpha",
                              "proposal_drift", user_confirmed=False)

    assert a["loop_count"] == 2
    assert load_loop_state(tmp_path, "beta")["loop_count"] == 0


def test_legacy_migration_when_change_matches(tmp_path):
    legacy = {
        "version": 1,
        "change": "sole-change",
        "loop_count": 2,
        "max_loops": 3,
        "classification_history": [
            {"loop": 1, "label": "implementation_gap", "user_confirmed": True,
             "at": "2026-08-25T00:00:00Z"}
        ],
        "codebase_commit_at_last_run": "abc123",
        "route": "guide-ship",
        "halt_reason": None,
        "updated_at": "2026-08-25T00:00:00Z",
    }
    legacy_dir = tmp_path / ".rddf" / "state"
    legacy_dir.mkdir(parents=True)
    (_LEGACY_PATH(tmp_path)).write_text(json.dumps(legacy))

    state = init_loop_state(tmp_path, "sole-change")
    assert state["loop_count"] == 2
    assert state["codebase_commit_at_last_run"] == "abc123"
    assert state["route"] == "guide-ship"


def test_legacy_not_migrated_when_change_differs(tmp_path):
    legacy = {
        "version": 1,
        "change": "other-change",
        "loop_count": 5,
        "max_loops": 3,
        "classification_history": [],
        "codebase_commit_at_last_run": "xyz",
        "route": "halted",
        "halt_reason": "legacy test",
        "updated_at": "2026-08-25T00:00:00Z",
    }
    legacy_dir = tmp_path / ".rddf" / "state"
    legacy_dir.mkdir(parents=True)
    (_LEGACY_PATH(tmp_path)).write_text(json.dumps(legacy))

    state = init_loop_state(tmp_path, "fresh-change")
    assert state["loop_count"] == 0
    assert state["codebase_commit_at_last_run"] == ""


def test_legacy_multi_change_does_not_overwrite(tmp_path):
    legacy = {
        "version": 1,
        "change": "stale-change",
        "loop_count": 5,
        "max_loops": 3,
        "classification_history": [],
        "codebase_commit_at_last_run": "xyz",
        "route": "halted",
        "halt_reason": "stale",
        "updated_at": "2026-08-25T00:00:00Z",
    }
    legacy_dir = tmp_path / ".rddf" / "state"
    legacy_dir.mkdir(parents=True)
    (_LEGACY_PATH(tmp_path)).write_text(json.dumps(legacy))

    init_loop_state(tmp_path, "change-a")
    init_loop_state(tmp_path, "change-b")
    a = load_loop_state(tmp_path, "change-a")
    b = load_loop_state(tmp_path, "change-b")
    assert a is not None and a["loop_count"] == 0
    assert b is not None and b["loop_count"] == 0
