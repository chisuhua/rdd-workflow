"""Tests for .verifier-loop.json load/save with schema validation.

Per ADR-0034 §6: tracks loop count, classification history, route, halt reason.
"""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.loop_state import (
    load_loop_state, save_loop_state, init_loop_state, append_classification
)


def test_init_creates_state(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    assert state["change"] == "test-change"
    assert state["loop_count"] == 0
    assert state["max_loops"] == 3
    assert state["route"] == "archive-ready"
    assert state["classification_history"] == []


def test_init_persists_to_disk(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    init_loop_state(tmp_path, "test-change", max_loops=3)
    assert (state_dir / ".verifier-loop.json").is_file()


def test_load_returns_saved_state(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    loaded = load_loop_state(tmp_path)
    assert loaded is not None
    assert loaded["change"] == "test-change"
    assert loaded["max_loops"] == 3


def test_load_missing_returns_none(tmp_path):
    assert load_loop_state(tmp_path) is None


def test_load_corrupt_returns_none(tmp_path):
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / ".verifier-loop.json").write_text("{invalid json")
    assert load_loop_state(tmp_path) is None


def test_save_validates_schema(tmp_path):
    init_loop_state(tmp_path, "test-change", max_loops=3)
    state = load_loop_state(tmp_path)
    state["route"] = "INVALID"
    with pytest.raises(jsonschema.ValidationError):
        save_loop_state(tmp_path, state)


def test_append_classification(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    updated = append_classification(tmp_path, state, "implementation_gap",
                                    user_confirmed=True)
    assert updated["loop_count"] == 1
    assert len(updated["classification_history"]) == 1
    assert updated["classification_history"][0]["label"] == "implementation_gap"
    assert updated["classification_history"][0]["user_confirmed"] is True
    assert updated["classification_history"][0]["loop"] == 1


def test_append_increments_loop_count(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    state = append_classification(tmp_path, state, "implementation_gap",
                                   user_confirmed=True)
    state = append_classification(tmp_path, state, "proposal_drift",
                                   user_confirmed=False)
    assert state["loop_count"] == 2
    assert len(state["classification_history"]) == 2


def test_append_persists_to_disk(tmp_path):
    state = init_loop_state(tmp_path, "test-change", max_loops=3)
    append_classification(tmp_path, state, "implementation_gap",
                           user_confirmed=True)
    loaded = load_loop_state(tmp_path)
    assert loaded["loop_count"] == 1