"""Unit tests for cross_repo_state (pending RFC state manager)."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from skills._lib.cross_repo_state import (
    read_pending_state,
    write_pending_state,
    add_pending_entry,
    update_pending_entry,
    remove_pending_entry,
)


@pytest.fixture
def state_dir(tmp_path):
    d = tmp_path / ".rddf" / "state"
    d.mkdir(parents=True)
    return d


def test_read_pending_state_empty_returns_empty_list(state_dir):
    result = read_pending_state(state_dir)
    assert result == {"version": 1, "entries": []}


def test_add_pending_entry_writes_valid_state(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    result = read_pending_state(state_dir)
    assert len(result["entries"]) == 1
    assert result["entries"][0]["hub_issue_url"] == entry["hub_issue_url"]
    assert result["entries"][0]["status"] == "pending"


def test_update_pending_entry_changes_status(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    update_pending_entry(state_dir, "https://github.com/org/rdd-hub/issues/42", {"status": "approved"})
    result = read_pending_state(state_dir)
    assert result["entries"][0]["status"] == "approved"


def test_remove_pending_entry(state_dir):
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    remove_pending_entry(state_dir, "https://github.com/org/rdd-hub/issues/42")
    result = read_pending_state(state_dir)
    assert len(result["entries"]) == 0


def test_atomic_write_no_partial_file(state_dir):
    """Atomic write should never leave a partial file."""
    entry = {
        "hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
        "gate_type": "Design-Gate",
        "expected_status": "approved",
        "created_at": "2026-08-15T16:00:00Z",
    }
    add_pending_entry(state_dir, entry)
    files = list(state_dir.iterdir())
    assert not any(f.name.startswith(".cross-repo-pending") and f.name.endswith(".tmp") for f in files)


def test_readme_documents_cross_repo_federation():
    readme = (Path(__file__).resolve().parent.parent.parent / "README.md").read_text()
    assert "rddf report-issue --category=rfc" in readme
    assert "rddf sync-hub" in readme
    assert "rddf watch-hub" in readme
    assert ".cross-repo-pending.json" in readme
    assert "SKIP_HUB_CHECK" in readme
