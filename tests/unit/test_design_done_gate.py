"""Unit tests for skills/guide-design/scripts/design_done_gate.py.

Locks the behavior of check_hub_pending() and check_cross_repo_approvals()
(wired into check_design_done_gate by fix-orphan-hub-gates-wiring).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "guide-design" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from design_done_gate import (  # noqa: E402
    _COMMANDS,
    check_cross_repo_approvals,
    check_hub_pending,
    main,
)


@pytest.fixture(autouse=True)
def _project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("SKIP_HUB_CHECK", raising=False)
    return tmp_path


def _write_pending(root: Path, status: str = "pending"):
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / ".cross-repo-pending.json").write_text(json.dumps({
        "version": 1,
        "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42",
                      "status": status}],
    }))


def _write_cross_repo_change(root: Path, name: str = "some-change"):
    d = root / "openspec" / "changes" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "roadmap-meta.yaml").write_text(
        "phase: core-impl\ncategory: cross-repo-federation\nchange_type: fix\npriority: P1\n"
    )


def _write_audit(root: Path, proposal_name: str, decision: str = "approve"):
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    with open(state / ".cross-repo-audit.jsonl", "a") as f:
        f.write(json.dumps({"proposal_name": proposal_name, "decision": decision}) + "\n")


class TestCheckHubPending:
    def test_blocks_on_pending_entry(self, tmp_path):
        _write_pending(tmp_path, "pending")
        assert check_hub_pending() is True

    def test_passes_when_no_file(self, tmp_path):
        assert check_hub_pending() is False

    def test_passes_when_all_approved(self, tmp_path):
        _write_pending(tmp_path, "approved")
        assert check_hub_pending() is False

    def test_skip_hub_check_bypasses(self, tmp_path, monkeypatch):
        _write_pending(tmp_path, "pending")
        monkeypatch.setenv("SKIP_HUB_CHECK", "true")
        assert check_hub_pending() is False

    def test_malformed_json_fails_open(self, tmp_path):
        state = tmp_path / ".rddf" / "state"
        state.mkdir(parents=True)
        (state / ".cross-repo-pending.json").write_text("{not json")
        assert check_hub_pending() is False


class TestCheckCrossRepoApprovals:
    def test_blocks_unapproved_cross_repo_change(self, tmp_path):
        _write_cross_repo_change(tmp_path)
        assert check_cross_repo_approvals() is True

    def test_passes_with_approve_audit_entry(self, tmp_path):
        """approve_proposal.sh writes decision='approve' (ADR-0031 P0)."""
        _write_cross_repo_change(tmp_path)
        _write_audit(tmp_path, "some-change", decision="approve")
        assert check_cross_repo_approvals() is False

    def test_passes_with_approved_audit_entry(self, tmp_path):
        _write_cross_repo_change(tmp_path)
        _write_audit(tmp_path, "some-change", decision="approved")
        assert check_cross_repo_approvals() is False

    def test_ignores_non_cross_repo_changes(self, tmp_path):
        d = tmp_path / "openspec" / "changes" / "normal-change"
        d.mkdir(parents=True)
        (d / "roadmap-meta.yaml").write_text("category: core-impl\n")
        assert check_cross_repo_approvals() is False

    def test_passes_when_no_changes_dir(self, tmp_path):
        assert check_cross_repo_approvals() is False


class TestMainCli:
    def test_check_hub_pending_exit_codes(self, tmp_path):
        assert main(["check-hub-pending"]) == 0
        _write_pending(tmp_path)
        assert main(["check-hub-pending"]) == 1

    def test_check_cross_repo_approvals_exit_codes(self, tmp_path):
        assert main(["check-cross-repo-approvals"]) == 0
        _write_cross_repo_change(tmp_path)
        assert main(["check-cross-repo-approvals"]) == 1

    def test_usage_error(self, capsys):
        assert main([]) == 2
        assert main(["bogus"]) == 2

    def test_check_rfc_draft_removed(self):
        """G1 architecture debt: check_rfc_draft() is orphan (never called by
        check_design_done_gate), so it must be deleted together with its
        _COMMANDS entry.
        """
        # Gateway must no longer be registered
        assert "check-rfc-draft" not in _COMMANDS, (
            "check_rfc_draft() is orphan (never called by check_design_done_gate); "
            "delete function and _COMMANDS entry"
        )
        # Exactly the 2 wired gates remain
        assert set(_COMMANDS) == {"check-hub-pending", "check-cross-repo-approvals"}
        # CLI invocation is a usage error (exit 2)
        assert main(["check-rfc-draft"]) == 2
        # Wired gates still work
        assert main(["check-hub-pending"]) == 0
