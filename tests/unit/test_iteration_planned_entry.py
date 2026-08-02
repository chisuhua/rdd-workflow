"""Regression test for iteration.json status=planned entries (D5).

Locks the public API: after design approve, the change must appear in
iteration.json with status='planned' (consumed by guide-plan fill / ship).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills._lib import iteration as it_mod  # noqa: E402


def test_planned_entry_added_via_add_or_update_change(tmp_path):
    data = it_mod.load(str(tmp_path))
    data = it_mod.add_or_update_change(
        data,
        name="move-proposal-creation-to-design",
        status="planned",
        phase="design",
        category="workflow",
        priority="P1",
    )
    it_mod.save(str(tmp_path), data)

    data2 = it_mod.load(str(tmp_path))
    assert len(data2["changes"]) == 1
    assert data2["changes"][0]["name"] == "move-proposal-creation-to-design"
    assert data2["changes"][0]["status"] == "planned"
    assert data2["changes"][0]["phase"] == "design"
    assert data2["changes"][0]["category"] == "workflow"


def test_planned_entry_idempotent(tmp_path):
    data = it_mod.load(str(tmp_path))
    for _ in range(3):
        data = it_mod.add_or_update_change(
            data,
            name="demo",
            status="planned",
            phase="design",
            category="workflow",
        )
    it_mod.save(str(tmp_path), data)

    data2 = it_mod.load(str(tmp_path))
    demos = [c for c in data2["changes"] if c["name"] == "demo"]
    assert len(demos) == 1, "add_or_update_change must be idempotent"


def test_planned_status_in_valid_set(tmp_path):
    """Ensure 'planned' is in the schema's valid statuses (no schema bypass)."""
    data = it_mod.load(str(tmp_path))
    data = it_mod.add_or_update_change(
        data,
        name="demo",
        status="planned",
        phase="design",
        category="workflow",
    )
    it_mod.save(str(tmp_path), data)

    # Re-load and validate (should succeed)
    data2 = it_mod.load(str(tmp_path))
    assert data2["changes"][0]["status"] == "planned"


def test_get_unblocked_planned_returns_planned_changes(tmp_path):
    """Lock: get_unblocked_planned returns changes with status='planned'."""
    data = it_mod.load(str(tmp_path))
    data = it_mod.add_or_update_change(
        data,
        name="alone",
        status="planned",
        phase="design",
        category="workflow",
    )
    it_mod.save(str(tmp_path), data)

    unblocked = it_mod.get_unblocked_planned(str(tmp_path))
    names = [c["name"] for c in unblocked]
    assert "alone" in names
