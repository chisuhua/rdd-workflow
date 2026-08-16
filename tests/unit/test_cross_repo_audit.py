"""Unit tests for cross_repo_audit (JSONL append + validate)."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from skills._lib.cross_repo_audit import (
    append_audit_log_entry,
    validate_entry,
    AUDIT_LOG_FIELDS,
)


@pytest.fixture
def audit_path(tmp_path):
    return tmp_path / ".rddf" / "state" / ".cross-repo-audit.jsonl"


def test_validate_entry_required_fields():
    entry = {
        "timestamp": "2026-08-15T16:00:00Z",
        "proposal_name": "add-x",
        "hub_issue": "org/rdd-hub#42",
        "approver": "alice",
        "decision": "approved",
    }
    validate_entry(entry)  # should not raise


def test_validate_entry_missing_field():
    entry = {"timestamp": "2026-08-15T16:00:00Z", "proposal_name": "add-x"}
    with pytest.raises(ValueError, match="hub_issue"):
        validate_entry(entry)


def test_append_creates_directory(audit_path):
    entry = {
        "timestamp": "2026-08-15T16:00:00Z",
        "proposal_name": "add-x",
        "hub_issue": "org/rdd-hub#42",
        "approver": "alice",
        "decision": "approved",
    }
    append_audit_log_entry(audit_path, entry)
    assert audit_path.parent.exists()
    assert audit_path.exists()


def test_append_jsonl_format(audit_path):
    entry1 = {"timestamp": "2026-08-15T16:00:00Z", "proposal_name": "add-x",
              "hub_issue": "org/rdd-hub#42", "approver": "alice", "decision": "approved"}
    entry2 = {"timestamp": "2026-08-15T16:01:00Z", "proposal_name": "add-y",
              "hub_issue": "org/rdd-hub#43", "approver": "bob", "decision": "rejected"}
    append_audit_log_entry(audit_path, entry1)
    append_audit_log_entry(audit_path, entry2)
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # must be valid JSON


def test_audit_log_fields_constant():
    assert set(AUDIT_LOG_FIELDS) == {
        "timestamp", "proposal_name", "hub_issue", "approver", "decision"
    }
