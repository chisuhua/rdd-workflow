"""Tests for subagent_strategy module.

Validates the decision matrix and quota probe logic per .rddf/improvements/subagent-orchestrator-execution-strategy.md.
"""
import pytest
from unittest.mock import patch, MagicMock

from skills._lib.subagent_strategy import (
    TaskType,
    QuotaStatus,
    ExecutionMode,
    decide_execution_mode,
    probe_subagent_quota,
    record_quota_failure,
    load_quota_failures,
)


class TestExecutionModeDecision:
    """Test the decision matrix (5×2 = 10 cells)."""

    def test_small_single_file_always_orchestrator(self):
        """单文件小改 (<50 行) → 无论配额状态, orchestrator 直接."""
        assert decide_execution_mode(TaskType.SINGLE_FILE_SMALL, QuotaStatus.HEALTHY) == ExecutionMode.ORCHESTRATOR
        assert decide_execution_mode(TaskType.SINGLE_FILE_SMALL, QuotaStatus.TIGHT) == ExecutionMode.ORCHESTRATOR

    def test_large_single_file_prefers_subagent_when_healthy(self):
        """单文件大改 (>50 行) + 配额充足 → 子代理."""
        assert decide_execution_mode(TaskType.SINGLE_FILE_LARGE, QuotaStatus.HEALTHY) == ExecutionMode.SUBAGENT

    def test_large_single_file_falls_back_when_tight(self):
        """单文件大改 + 配额紧张 → orchestrator 直接."""
        assert decide_execution_mode(TaskType.SINGLE_FILE_LARGE, QuotaStatus.TIGHT) == ExecutionMode.ORCHESTRATOR

    def test_cross_file_tdd_uses_subagent_when_healthy(self):
        """跨文件 + TDD 多步 + 配额充足 → 子代理."""
        assert decide_execution_mode(TaskType.CROSS_FILE_TDD, QuotaStatus.HEALTHY) == ExecutionMode.SUBAGENT

    def test_cross_file_tdd_uses_subagent_even_when_tight(self):
        """跨文件 + TDD 多步 + 配额紧张 → 子代理 (但允许降级)."""
        # Per design: subagent with fallback to orchestrator
        assert decide_execution_mode(TaskType.CROSS_FILE_TDD, QuotaStatus.TIGHT) == ExecutionMode.SUBAGENT

    def test_cross_worktree_parallel_uses_subagent_when_healthy(self):
        """跨 worktree 并行 + 配额充足 → 子代理并行."""
        assert decide_execution_mode(TaskType.CROSS_WORKTREE_PARALLEL, QuotaStatus.HEALTHY) == ExecutionMode.SUBAGENT

    def test_cross_worktree_serial_when_tight(self):
        """跨 worktree 并行 + 配额紧张 → 串行子代理."""
        assert decide_execution_mode(TaskType.CROSS_WORKTREE_PARALLEL, QuotaStatus.TIGHT) == ExecutionMode.SUBAGENT

    def test_plan_generation_uses_subagent(self):
        """计划生成 (无副作用) → 子代理 (无论配额)."""
        assert decide_execution_mode(TaskType.PLAN_GENERATION, QuotaStatus.HEALTHY) == ExecutionMode.SUBAGENT
        assert decide_execution_mode(TaskType.PLAN_GENERATION, QuotaStatus.TIGHT) == ExecutionMode.SUBAGENT


class TestQuotaProbe:
    """Test the probe_subagent_quota function."""

    def test_probe_returns_healthy_on_success(self):
        """Successful probe returns HEALTHY."""
        with patch("skills._lib.subagent_strategy._ping_subagent") as mock_ping:
            mock_ping.return_value = {"status": "ok"}
            assert probe_subagent_quota() == QuotaStatus.HEALTHY

    def test_probe_returns_tight_on_quota_exceeded(self):
        """Probe returning quota_exceeded sets TIGHT."""
        with patch("skills._lib.subagent_strategy._ping_subagent") as mock_ping:
            mock_ping.return_value = {"status": "quota_exceeded"}
            assert probe_subagent_quota() == QuotaStatus.TIGHT

    def test_probe_returns_tight_on_exception(self):
        """Probe exception is treated as TIGHT (fail-safe)."""
        with patch("skills._lib.subagent_strategy._ping_subagent") as mock_ping:
            mock_ping.side_effect = RuntimeError("connection error")
            assert probe_subagent_quota() == QuotaStatus.TIGHT


class TestQuotaFailureTracking:
    """Test the quota_failures.json tracking."""

    def test_record_quota_failure_creates_file(self, tmp_path, monkeypatch):
        """Recording a failure creates .rddf/state/quota_failures.json."""
        monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
        record_quota_failure("task_quota_exceeded", tool="task", count=1)
        failures = load_quota_failures()
        assert len(failures) == 1
        assert failures[0]["type"] == "task_quota_exceeded"
        assert failures[0]["tool"] == "task"
        assert failures[0]["count"] == 1

    def test_record_multiple_failures_aggregates_count(self, tmp_path, monkeypatch):
        """Recording same type multiple times increments count."""
        monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
        record_quota_failure("task_quota_exceeded", tool="task", count=1)
        record_quota_failure("task_quota_exceeded", tool="task", count=1)
        record_quota_failure("task_quota_exceeded", tool="task", count=1)
        failures = load_quota_failures()
        assert len(failures) == 1
        assert failures[0]["count"] == 3

    def test_load_quota_failures_empty_when_no_file(self, tmp_path, monkeypatch):
        """Loading from non-existent path returns empty list."""
        monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
        assert load_quota_failures() == []
