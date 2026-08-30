"""`rddf hub retry-failed` CLI: list + retry failed entries (test via list only)."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from _lib.cli.hub_retry_cmd import cmd_hub_retry


def _write_audit(state_dir, name, decision="fail-auto-issue", hub_issue=""):
    audit = state_dir / ".rddf" / "state" / ".cross-repo-audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a") as f:
        f.write(json.dumps({
            "timestamp": "2026-08-29T10:00:00+00:00",
            "proposal_name": name,
            "hub_issue": hub_issue,
            "approver": "test",
            "decision": decision,
        }) + "\n")


def test_retry_failed_lists_only_failed_entries(tmp_path, monkeypatch):
    state_dir = tmp_path / "proj"
    state_dir.mkdir()
    _write_audit(state_dir, "foo", decision="fail-auto-issue")
    _write_audit(state_dir, "bar", decision="approve-auto-issue")
    _write_audit(state_dir, "baz", decision="fail-auto-issue")
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(state_dir))
    rc = cmd_hub_retry(["list"])
    assert rc == 0


def test_retry_failed_no_audit_returns_0(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = cmd_hub_retry(["list"])
    assert rc == 0


def test_retry_failed_no_args_shows_help(monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", "/nonexistent")
    rc = cmd_hub_retry([])
    assert rc == 0


def test_retry_failed_unknown_subcommand(monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", "/nonexistent")
    assert cmd_hub_retry(["bogus"]) == 2