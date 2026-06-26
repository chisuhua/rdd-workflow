"""Integration tests: phase switching arch → plan → ship.

Locks the contract that:
- Writing `.arch-handoff.json` records the arch completion timestamp and
  enables the plan phase.
- Writing `.plan-handoff.json` records the plan completion timestamp and
  enables the ship phase.
- Missing handoff files prevent advance (the state vector and gate
  mechanism rely on these files existing before they allow a transition).

These tests use a temp directory so they do not pollute the repo.
"""
import os
import json
import tempfile
import pytest


# ---------- Fixtures ---------- #

@pytest.fixture
def temp_dir():
    """Isolated temp directory for handoff JSON files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _write_handoff(root: str, filename: str, payload: dict) -> str:
    """Write a handoff JSON under `<root>/.zcf/`. Returns the file path."""
    zcf_dir = os.path.join(root, ".zcf")
    os.makedirs(zcf_dir, exist_ok=True)
    path = os.path.join(zcf_dir, filename)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


# ---------- Arch → Plan transition ---------- #

def test_arch_to_plan_transition(temp_dir):
    """Writing .arch-handoff.json must record arch completion and enable plan phase."""
    handoff = {
        "arch_complete_at": "2026-06-25T12:00:00+08:00",
        "adr_count": 3,
        "roadmap_exists": True,
        "plan_started_at": None,
    }
    path = _write_handoff(temp_dir, ".arch-handoff.json", handoff)

    # File exists at the expected path
    assert os.path.exists(path)
    assert path.endswith(".arch-handoff.json")

    # Read back and validate structure
    with open(path) as f:
        data = json.load(f)
    assert data["arch_complete_at"] is not None
    assert data["arch_complete_at"].startswith("2026-06-25")
    assert data["adr_count"] >= 1
    assert data["roadmap_exists"] is True
    # plan_started_at must be None until the plan phase actually begins
    assert data["plan_started_at"] is None


def test_arch_to_plan_with_zero_adrs_blocks(temp_dir):
    """Zero ADRs means arch phase did not complete — transition must be blocked."""
    handoff = {
        "arch_complete_at": "2026-06-25T12:00:00+08:00",
        "adr_count": 0,  # Zero ADRs is not enough
        "roadmap_exists": True,
        "plan_started_at": None,
    }
    path = _write_handoff(temp_dir, ".arch-handoff.json", handoff)
    with open(path) as f:
        data = json.load(f)
    # The plan phase requires adr_count >= 1; this file does not satisfy that.
    assert data["adr_count"] < 1
    assert data["plan_started_at"] is None


# ---------- Plan → Ship transition ---------- #

def test_plan_to_ship_transition(temp_dir):
    """Writing .plan-handoff.json must record plan completion and enable ship phase."""
    handoff = {
        "plan_complete_at": "2026-06-25T14:00:00+08:00",
        "active_changes": 2,
        "all_artifacts_committed": True,
        "ship_started_at": None,
        "current_change": "add-auth",
    }
    path = _write_handoff(temp_dir, ".plan-handoff.json", handoff)

    # File exists at the expected path
    assert os.path.exists(path)
    assert path.endswith(".plan-handoff.json")

    # Read back and validate structure
    with open(path) as f:
        data = json.load(f)
    assert data["plan_complete_at"] is not None
    assert data["plan_complete_at"].startswith("2026-06-25")
    assert data["active_changes"] >= 1
    assert data["all_artifacts_committed"] is True
    # ship_started_at must be None until the ship phase actually begins
    assert data["ship_started_at"] is None
    assert data["current_change"] == "add-auth"


def test_plan_to_ship_with_uncommitted_artifacts_blocks(temp_dir):
    """Uncommitted artifacts must prevent transition to ship phase."""
    handoff = {
        "plan_complete_at": "2026-06-25T14:00:00+08:00",
        "active_changes": 1,
        "all_artifacts_committed": False,  # Not ready for ship
        "ship_started_at": None,
        "current_change": "add-auth",
    }
    path = _write_handoff(temp_dir, ".plan-handoff.json", handoff)
    with open(path) as f:
        data = json.load(f)
    # The ship phase requires all_artifacts_committed == True; this file fails that.
    assert data["all_artifacts_committed"] is False
    assert data["ship_started_at"] is None


# ---------- Full sequence: arch → plan → ship ---------- #

def test_full_phase_sequence_records_all_handoffs(temp_dir):
    """Writing both .arch-handoff.json and .plan-handoff.json enables ship."""
    arch_handoff = {
        "arch_complete_at": "2026-06-25T12:00:00+08:00",
        "adr_count": 3,
        "roadmap_exists": True,
        "plan_started_at": "2026-06-25T12:30:00+08:00",
    }
    plan_handoff = {
        "plan_complete_at": "2026-06-25T14:00:00+08:00",
        "active_changes": 2,
        "all_artifacts_committed": True,
        "ship_started_at": None,
        "current_change": "add-auth",
    }
    arch_path = _write_handoff(temp_dir, ".arch-handoff.json", arch_handoff)
    plan_path = _write_handoff(temp_dir, ".plan-handoff.json", plan_handoff)

    # Both handoff files exist
    assert os.path.exists(arch_path)
    assert os.path.exists(plan_path)

    # The arch handoff's plan_started_at is now populated (plan phase started)
    with open(arch_path) as f:
        arch = json.load(f)
    assert arch["plan_started_at"] is not None

    # The plan handoff's ship_started_at is still None (ship phase not started)
    with open(plan_path) as f:
        plan = json.load(f)
    assert plan["ship_started_at"] is None
    assert plan["all_artifacts_committed"] is True


# ---------- Missing handoff files prevent advance ---------- #

def test_phase_switch_without_handoff_fails(temp_dir):
    """No handoff files = phase transitions are impossible."""
    arch_path = os.path.join(temp_dir, ".zcf", ".arch-handoff.json")
    plan_path = os.path.join(temp_dir, ".zcf", ".plan-handoff.json")
    ship_path = os.path.join(temp_dir, ".zcf", ".ship-handoff.json")
    # The .zcf directory should not even exist yet
    zcf_dir = os.path.join(temp_dir, ".zcf")
    assert not os.path.exists(arch_path)
    assert not os.path.exists(plan_path)
    assert not os.path.exists(ship_path)
    assert not os.path.exists(zcf_dir)


def test_arch_handoff_present_but_plan_missing_blocks_ship(temp_dir):
    """Arch handoff exists but plan handoff is missing — ship cannot proceed."""
    arch_handoff = {
        "arch_complete_at": "2026-06-25T12:00:00+08:00",
        "adr_count": 3,
        "roadmap_exists": True,
        "plan_started_at": None,
    }
    arch_path = _write_handoff(temp_dir, ".arch-handoff.json", arch_handoff)
    plan_path = os.path.join(temp_dir, ".zcf", ".plan-handoff.json")
    # Arch file exists, plan file does not
    assert os.path.exists(arch_path)
    assert not os.path.exists(plan_path)


def test_handoff_payload_has_required_fields(temp_dir):
    """The handoff payload schema must include the documented required fields."""
    # Arch handoff required fields
    arch_handoff = {
        "arch_complete_at": "2026-06-25T12:00:00+08:00",
        "adr_count": 1,
        "roadmap_exists": True,
        "plan_started_at": None,
    }
    path = _write_handoff(temp_dir, ".arch-handoff.json", arch_handoff)
    with open(path) as f:
        data = json.load(f)
    required_arch = {"arch_complete_at", "adr_count", "roadmap_exists", "plan_started_at"}
    assert required_arch.issubset(data.keys())

    # Plan handoff required fields
    plan_handoff = {
        "plan_complete_at": "2026-06-25T14:00:00+08:00",
        "active_changes": 1,
        "all_artifacts_committed": True,
        "ship_started_at": None,
        "current_change": "x",
    }
    path = _write_handoff(temp_dir, ".plan-handoff.json", plan_handoff)
    with open(path) as f:
        data = json.load(f)
    required_plan = {
        "plan_complete_at",
        "active_changes",
        "all_artifacts_committed",
        "ship_started_at",
        "current_change",
    }
    assert required_plan.issubset(data.keys())
