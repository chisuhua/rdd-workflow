"""Tests for iteration v7 schema (verification object).

Per fix-rdd-verifier-lifecycle-dashboard Task 1:
- version enum must include 7 (in addition to 3-6 for backward compat)
- changes.items must carry optional `verification` object
- verification must require state + archive_ready, with nullable sub-fields
"""
import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "_lib" / "schemas" / "iteration_schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_v7_enum_includes_seven():
    schema = _load_schema()
    assert 7 in schema["properties"]["version"]["enum"], (
        "version enum must include 7 for verification lifecycle support"
    )
    # backward compatibility
    for v in (3, 4, 5, 6):
        assert v in schema["properties"]["version"]["enum"]


def test_verification_object_present():
    schema = _load_schema()
    change_props = schema["properties"]["changes"]["items"]["properties"]
    assert "verification" in change_props, "changes.items must have verification property"
    ver = change_props["verification"]
    assert "object" in ver["type"]
    assert "properties" in ver


def test_verification_state_enum_covers_all_states():
    schema = _load_schema()
    ver = schema["properties"]["changes"]["items"]["properties"]["verification"]
    states = ver["properties"]["state"]["enum"]
    expected = {"pending", "running", "passed", "failed", "halted", "bypassed", "legacy", "unknown"}
    # enum also includes None for backward compat with missing/null
    actual_states = {s for s in states if s is not None}
    assert expected.issubset(actual_states), f"missing states: {expected - actual_states}"


def test_verification_required_fields():
    schema = _load_schema()
    ver = schema["properties"]["changes"]["items"]["properties"]["verification"]
    assert "state" in ver["required"]
    assert "archive_ready" in ver["required"]


def test_verification_subfields_nullable():
    schema = _load_schema()
    ver = schema["properties"]["changes"]["items"]["properties"]["verification"]
    nullable = ("verdict_sha", "checked_at", "route", "loop_count",
                "failed_acs", "bypass_reason", "bypass_source")
    for f in nullable:
        assert "null" in ver["properties"][f]["type"], f"{f} must allow null"


def test_archive_ready_is_boolean():
    schema = _load_schema()
    ver = schema["properties"]["changes"]["items"]["properties"]["verification"]
    assert ver["properties"]["archive_ready"]["type"] == "boolean"
