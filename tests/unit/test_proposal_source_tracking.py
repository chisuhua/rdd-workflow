"""Unit tests for proposal source tracking fields (add-proposal-source-tracking).

Locks the public API: when approve_proposal.sh creates a new OpenSpec change,
it records which rddf-session / audit event produced it via the
``source_session_id`` and ``audit_source`` fields on the iteration.json entry.

Covers the 5 scenarios:
  1. New proposal auto-writes source_session_id (from RDDF_PROPOSAL_SOURCE_SESSION env)
  2. audit_source field is recorded correctly
  3. Legacy entries (no source_session_id) are not broken (backward compat)
  4. RDDF_PROPOSAL_SOURCE_SESSION unset -> field is None (graceful)
  5. add_or_update_change accepts the two new fields
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills._lib import iteration as it_mod  # noqa: E402
from skills._lib.iteration.store import proposal_source_fields  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure the proposal-source env vars are unset between tests."""
    monkeypatch.delenv("RDDF_PROPOSAL_SOURCE_SESSION", raising=False)
    monkeypatch.delenv("RDDF_PROPOSAL_AUDIT_SOURCE", raising=False)


def _build_change(name="add-proposal-source-tracking", **extra):
    data = it_mod.create_empty()
    return it_mod.add_or_update_change(
        data,
        name=name,
        status="planned",
        phase="phase-2",
        category="governance",
        **extra,
    )


def test_new_proposal_writes_source_session_id_from_env():
    """Scenario 1: env RDDF_PROPOSAL_SOURCE_SESSION -> source_session_id recorded."""
    os.environ["RDDF_PROPOSAL_SOURCE_SESSION"] = "rds_abc123"
    src = proposal_source_fields()
    data = _build_change(**src)
    change = data["changes"][0]
    assert change["source_session_id"] == "rds_abc123"


def test_audit_source_recorded():
    """Scenario 2: env RDDF_PROPOSAL_AUDIT_SOURCE -> audit_source recorded."""
    os.environ["RDDF_PROPOSAL_AUDIT_SOURCE"] = "2026-08-27-ship-audit"
    src = proposal_source_fields()
    data = _build_change(**src)
    change = data["changes"][0]
    assert change["audit_source"] == "2026-08-27-ship-audit"


def test_legacy_entry_without_source_session_id_preserved():
    """Scenario 3: updating a legacy entry must not inject source fields."""
    data = it_mod.create_empty()
    data = it_mod.add_or_update_change(
        data,
        name="legacy-change",
        status="planned",
        phase="phase-2",
        category="workflow",
    )
    legacy = data["changes"][0]
    assert "source_session_id" not in legacy
    assert "audit_source" not in legacy

    # Update status only (as a later phase would) — no source fields should appear.
    data = it_mod.set_status(data, name="legacy-change", status="in_worktree")
    updated = data["changes"][0]
    assert updated["name"] == "legacy-change"
    assert updated["status"] == "in_worktree"
    assert "source_session_id" not in updated
    assert "audit_source" not in updated


def test_env_unset_graceful_none():
    """Scenario 4: unset env vars -> fields are None, no crash."""
    src = proposal_source_fields()
    assert src["source_session_id"] is None
    assert src["audit_source"] is None
    # Passing None values must still produce a valid entry.
    data = _build_change(**src)
    change = data["changes"][0]
    assert change["source_session_id"] is None
    assert change["audit_source"] is None


def test_add_or_update_change_accepts_new_fields():
    """Scenario 5: add_or_update_change accepts source_session_id + audit_source."""
    data = _build_change(
        source_session_id="rds_xyz",
        audit_source="hybrid-path",
    )
    change = data["changes"][0]
    assert change["source_session_id"] == "rds_xyz"
    assert change["audit_source"] == "hybrid-path"
