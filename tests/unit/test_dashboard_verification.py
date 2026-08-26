"""Tests for dashboard verification dimension (Tasks 17-19)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.dashboard import ChangeEntry, DashboardData


def _make_entry(**kwargs) -> ChangeEntry:
    defaults = dict(name="x", status="completed")
    defaults.update(kwargs)
    return ChangeEntry(**defaults)


def test_change_entry_carries_verification():
    e = _make_entry(verification={"state": "passed", "archive_ready": True})
    assert e.verification_state == "passed"
    assert e.archive_ready is True


def test_change_entry_default_unknown_for_active():
    e = _make_entry(status="in_worktree")
    assert e.verification_state == "unknown"
    assert e.archive_ready is False


def test_change_entry_legacy_for_archived_without_verification():
    e = _make_entry(status="archived")
    assert e.verification_state == "legacy"
    assert e.archive_ready is False


def test_change_entry_legacy_for_archived_partial_without_verification():
    e = _make_entry(status="archived_partial")
    assert e.verification_state == "legacy"


def test_change_entry_archived_with_verification_uses_explicit_state():
    e = _make_entry(status="archived",
                     verification={"state": "passed", "archive_ready": True})
    assert e.verification_state == "passed"
    assert e.archive_ready is True


def test_change_entry_failed_not_archive_ready():
    e = _make_entry(verification={"state": "failed", "archive_ready": False})
    assert e.verification_state == "failed"
    assert e.archive_ready is False


def test_change_entry_halted_not_archive_ready():
    e = _make_entry(verification={"state": "halted", "archive_ready": False})
    assert e.archive_ready is False


def test_change_entry_bypassed_with_archive_ready():
    e = _make_entry(verification={"state": "bypassed", "archive_ready": True,
                                   "bypass_reason": "x"})
    assert e.verification_state == "bypassed"
    assert e.archive_ready is True


def test_dashboard_data_accepts_changes_with_verification(tmp_path):
    d = DashboardData(project_root=str(tmp_path))
    d.changes.append(_make_entry(verification={"state": "passed", "archive_ready": True}))
    d.changes.append(_make_entry(status="archived"))
    assert d.changes[0].archive_ready is True
    assert d.changes[1].verification_state == "legacy"


@pytest.mark.parametrize("state", ["pending", "running", "passed", "failed",
                                    "halted", "bypassed", "legacy", "unknown"])
def test_all_eight_states_have_correct_property(state):
    e = _make_entry(
        status="archived" if state == "legacy" else "completed",
        verification={"state": state, "archive_ready": state in ("passed", "bypassed")},
    )
    assert e.verification_state == state


def test_dashboard_data_json_round_trip_preserves_verification(tmp_path):
    d = DashboardData(project_root=str(tmp_path))
    d.changes.append(_make_entry(verification={"state": "passed", "archive_ready": True}))
    doc = {
        "changes": [{
            "name": c.name, "status": c.status,
            "verification_state": c.verification_state,
            "archive_ready": c.archive_ready,
        } for c in d.changes]
    }
    encoded = json.dumps(doc)
    decoded = json.loads(encoded)
    assert decoded["changes"][0]["verification_state"] == "passed"
    assert decoded["changes"][0]["archive_ready"] is True
