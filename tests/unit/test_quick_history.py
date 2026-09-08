"""Unit tests for _lib/quick_history.py — TDD red→green (Task 1 of add-rdd-quick-skill).

Coverage:
- schema v1 exists and declares version
- validate_entry accepts a minimal valid entry
- validate_entry rejects entries missing required fields
- validate_entry rejects unknown outcome enum values
- append_entry creates the history file atomically when fresh
- append_entry preserves prior lines byte-identical
- append_entry validates before writing (no partial writes)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path (tests/conftest.py also does this,
# but we guard in case tests are run directly).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from _lib.quick_history import (  # noqa: E402  (sys.path mutation before import)
    append_entry,
    read_entries,
    validate_entry,
)

_MINIMAL_ENTRY = {
    "name": "quick-foo",
    "started_at": "2026-09-07T10:00:00Z",
    "ended_at": "2026-09-07T10:05:00Z",
    "plan_file": ".rddf/plans/quick-foo.md",
    "complexity": "simple",
    "reviewed_by": [],
    "verdict_summary": {"total": 1, "pass": 1, "fail": 0},
    "retry_count": 0,
    "outcome": "completed",
    "commit_sha": "abc1234",
    "upgraded_to_change": None,
}


def test_schema_v1_exists_and_loads():
    schema_path = _PROJECT_ROOT / "_lib" / "schemas" / "quick_history_schema.json"
    assert schema_path.is_file(), f"schema file missing at {schema_path}"
    data = json.loads(schema_path.read_text())
    assert data.get("version") == 1


def test_validate_entry_accepts_minimal_valid():
    assert validate_entry(_MINIMAL_ENTRY) is True


def test_validate_entry_rejects_missing_required_field():
    bad = dict(_MINIMAL_ENTRY)
    bad.pop("commit_sha")
    assert validate_entry(bad) is False


def test_validate_entry_rejects_unknown_outcome():
    bad = dict(_MINIMAL_ENTRY)
    bad["outcome"] = "bogus"
    assert validate_entry(bad) is False


def test_append_entry_creates_file_atomically(tmp_path: Path):
    history = tmp_path / ".quick-history.jsonl"
    assert not history.exists()
    append_entry(_MINIMAL_ENTRY, history)
    assert history.is_file()
    lines = history.read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["name"] == "quick-foo"


def test_append_entry_preserves_prior_lines(tmp_path: Path):
    history = tmp_path / ".quick-history.jsonl"
    # Pre-existing 2 lines, byte-identical baseline.
    prior_a = json.dumps({**_MINIMAL_ENTRY, "name": "quick-aa"})
    prior_b = json.dumps({**_MINIMAL_ENTRY, "name": "quick-bb"})
    history.write_text(prior_a + "\n" + prior_b + "\n")

    append_entry(_MINIMAL_ENTRY, history)
    text = history.read_text()
    lines = text.splitlines()
    assert len(lines) == 3
    # First two lines unchanged.
    assert lines[0] == prior_a
    assert lines[1] == prior_b
    # New entry is well-formed.
    parsed = json.loads(lines[2])
    assert parsed["name"] == "quick-foo"


def test_append_entry_does_not_write_when_validation_fails(tmp_path: Path):
    history = tmp_path / ".quick-history.jsonl"
    bad = dict(_MINIMAL_ENTRY)
    bad.pop("commit_sha")  # missing required field
    with pytest.raises(ValueError):
        append_entry(bad, history)
    # File MUST NOT exist after a failed validation.
    assert not history.exists()


def test_name_pattern_requires_quick_prefix():
    """Schema enforces name = ^quick-[a-z0-9-]+$ — covered here via validate_entry."""
    bad = dict(_MINIMAL_ENTRY)
    bad["name"] = "foo"  # missing quick- prefix
    assert validate_entry(bad) is False


def test_read_entries_roundtrip(tmp_path: Path):
    history = tmp_path / ".quick-history.jsonl"
    for n in ("quick-x", "quick-y", "quick-z"):
        append_entry({**_MINIMAL_ENTRY, "name": n}, history)
    entries = read_entries(history)
    assert [e["name"] for e in entries] == ["quick-x", "quick-y", "quick-z"]