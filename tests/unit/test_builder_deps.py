"""Unit tests for _lib/builder_deps.py (Oracle P2 #5)."""
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow')

import pytest
from _lib.builder_deps import (
    decide_execution_mode,
    analyze_deps,
    analyze_deps_with_strict_gate,
    RISK_KEYWORDS,
)


class TestDecideExecutionMode:
    def test_decide_lightweight_small_change(self):
        result = decide_execution_mode(file_count=2, task_count=3, risk_keywords=[])
        assert result["mode"] == "lightweight"
        assert "files=2<=2 AND tasks=3<=3" in result["reason"]

    def test_decide_worktree_too_many_files(self):
        result = decide_execution_mode(file_count=5, task_count=2, risk_keywords=[])
        assert result["mode"] == "worktree"
        assert "files=5>2" in result["reason"]

    def test_decide_worktree_too_many_tasks(self):
        result = decide_execution_mode(file_count=1, task_count=10, risk_keywords=[])
        assert result["mode"] == "worktree"
        assert "tasks=10>3" in result["reason"]

    def test_decide_worktree_risk_keyword(self):
        result = decide_execution_mode(file_count=1, task_count=1, risk_keywords=["refactor"])
        assert result["mode"] == "worktree"
        assert "risk_keyword=" in result["reason"]

    def test_decide_worktree_combined_rules(self):
        result = decide_execution_mode(file_count=5, task_count=10, risk_keywords=["migration"])
        assert result["mode"] == "worktree"
        assert "files=5>2" in result["reason"]
        assert "tasks=10>3" in result["reason"]
        assert "risk_keyword=" in result["reason"]

    def test_decide_risk_keyword_set_completeness(self):
        for keyword in RISK_KEYWORDS:
            result = decide_execution_mode(file_count=1, task_count=1, risk_keywords=[keyword])
            assert result["mode"] == "worktree", f"keyword={keyword} should trigger worktree"


class TestAnalyzeDeps:
    def test_analyze_deps_basic(self):
        result = analyze_deps(
            change_name="test-change",
            proposal_path="/tmp/proposal.md",
            manual_deps=["dep1"],
            cross_repo=False,
        )
        assert result["manual_deps"] == ["dep1"]
        assert result["cross_repo_pending"] == []
        assert result["blockers"] == []

    def test_analyze_deps_cross_repo_pending_hub(self):
        result = analyze_deps(
            change_name="test-change",
            proposal_path="/tmp/proposal.md",
            manual_deps=[],
            cross_repo=True,
            hub_issue_status="pending",
        )
        assert "hub_issue_pending" in result["cross_repo_pending"]

    def test_analyze_deps_cross_repo_hub_closed(self):
        result = analyze_deps(
            change_name="test-change",
            proposal_path="/tmp/proposal.md",
            manual_deps=[],
            cross_repo=True,
            hub_issue_status="closed",
        )
        assert result["cross_repo_pending"] == []


class TestStrictGate:
    def test_strict_gate_pass_empty(self):
        result = analyze_deps_with_strict_gate(blockers=[])
        assert result["passes"] is True
        assert result["passes_list"] == ["strict_deps_gate"]
        assert result["failures"] == []

    def test_strict_gate_fail_with_blockers(self):
        result = analyze_deps_with_strict_gate(blockers=["x"])
        assert result["passes"] is False
        assert result["failures"] == ["x"]
        assert result["passes_list"] == []
