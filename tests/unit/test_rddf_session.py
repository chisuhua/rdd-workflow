"""Tests for RddfSessionCoordinator — user-perspective workflow session persistence (ADR-0017)."""
import json
import os
import time
from pathlib import Path

import jsonschema
import pytest

from skills._lib.rddf_session import RddfSessionCoordinator, RddfSessionError


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_create_session_returns_valid_id(coordinator):
    """create_session MUST return id matching rds_<12 hex chars>."""
    sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_test123",
        goal={"intent": "guide-plan", "subject": "change-auth", "expected_outcome": "plan-done"},
    )
    assert sid.startswith("rds_")
    assert len(sid) == 16  # "rds_" + 12 hex


def test_create_session_persists_to_file(coordinator, sessions_file):
    """After create_session, sessions.json MUST contain the new entry."""
    sid = coordinator.create_session(
        kind="stage_arch",
        owner_opencode_session_id="ses_abc",
        goal={"intent": "guide-arch"},
    )
    assert sessions_file.exists()
    data = json.loads(sessions_file.read_text())
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["session_id"] == sid
    assert data["sessions"][0]["state"] == "active"
    assert data["sessions"][0]["kind"] == "stage_arch"


def test_create_session_writes_valid_schema(coordinator, sessions_file):
    """sessions.json output MUST pass sessions_schema.json validation."""
    sid = coordinator.create_session(
        kind="stage_ship",
        owner_opencode_session_id="ses_xyz",
        goal={"intent": "guide-ship", "subject": "change-x"},
    )
    schema_path = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "sessions_schema.json"
    schema = json.loads(schema_path.read_text())
    data = json.loads(sessions_file.read_text())
    jsonschema.validate(instance=data, schema=schema)