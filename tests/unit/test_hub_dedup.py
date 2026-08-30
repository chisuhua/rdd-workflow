"""Hub auto-file dedup via proposal content hash."""
from __future__ import annotations
import json
from pathlib import Path

from _lib.hub_dedup import compute_proposal_hash, was_filed_recently


def _write_imp(tmp_path, name, body="# Test\n\n## Why\nx\n"):
    p = tmp_path / ".rddf" / "improvements" / f"{name}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def test_compute_proposal_hash_deterministic(tmp_path):
    """Same content → same hash."""
    p = _write_imp(tmp_path, "foo")
    h1 = compute_proposal_hash(p)
    h2 = compute_proposal_hash(p)
    assert h1 == h2
    assert len(h1) == 64


def test_was_filed_recently_match_returns_true(tmp_path):
    """Hash match in audit log → skip (already filed)."""
    p = _write_imp(tmp_path, "foo")
    log = tmp_path / "audit.jsonl"
    h = compute_proposal_hash(p)
    log.write_text(json.dumps({
        "timestamp": "2026-08-29T10:00:00+00:00",
        "proposal_name": "foo",
        "hub_issue": "https://github.com/org/rdd-hub/issues/42",
        "hub_hash": h,
        "approver": "test",
        "decision": "approve-auto-issue",
    }) + "\n")
    assert was_filed_recently("foo", h, log) is True


def test_was_filed_recently_no_match_returns_false(tmp_path):
    """Hash mismatch in audit log → file again."""
    p = _write_imp(tmp_path, "foo")
    log = tmp_path / "audit.jsonl"
    log.write_text(json.dumps({
        "timestamp": "2026-08-29T10:00:00+00:00",
        "proposal_name": "foo",
        "hub_issue": "https://github.com/org/rdd-hub/issues/42",
        "hub_hash": "different_hash",
        "approver": "test",
        "decision": "approve-auto-issue",
    }) + "\n")
    assert was_filed_recently("foo", compute_proposal_hash(p), log) is False


def test_was_filed_recently_empty_log_returns_false(tmp_path):
    """No audit log → file."""
    log = tmp_path / "audit.jsonl"
    p = _write_imp(tmp_path, "foo")
    assert was_filed_recently("foo", compute_proposal_hash(p), log) is False