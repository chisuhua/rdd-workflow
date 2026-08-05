"""Subagent orchestrator execution strategy.

Per improvements/subagent-orchestrator-execution-strategy.md:
- Probe subagent quota before parallel dispatch
- Decision matrix based on task type and quota status
- Auto-fallback to orchestrator direct execution on quota errors
- Track failures in .rddf/state/quota_failures.json

Out of scope: Modifying the task() tool itself, introducing new subagent models.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional


class TaskType(Enum):
    """Classification of task complexity for decision matrix."""
    SINGLE_FILE_SMALL = "single_file_small"  # <50 lines
    SINGLE_FILE_LARGE = "single_file_large"  # >50 lines
    CROSS_FILE_TDD = "cross_file_tdd"        # multi-file with TDD
    CROSS_WORKTREE_PARALLEL = "cross_worktree_parallel"  # multiple worktrees
    PLAN_GENERATION = "plan_generation"      # no side effects


class QuotaStatus(Enum):
    """Subagent quota availability."""
    HEALTHY = "healthy"      # quota available
    TIGHT = "tight"          # quota exhausted or unknown


class ExecutionMode(Enum):
    """Selected execution mode."""
    ORCHESTRATOR = "orchestrator"  # Main session executes directly
    SUBAGENT = "subagent"          # Delegate to subagent (parallel or serial)


def decide_execution_mode(task_type: TaskType, quota_status: QuotaStatus) -> ExecutionMode:
    """Decision matrix: pick execution mode based on task type and quota.

    Per proposal design:
    | 任务类型 | 配额充足 | 配额紧张/未知 |
    |---------|---------|------------|
    | 单文件小改 (<50 行) | orchestrator 直接 | orchestrator 直接 |
    | 单文件大改 (>50 行) | 子代理 | orchestrator 直接 |
    | 跨文件 + TDD 多步 | 子代理 | 子代理 (降级: orchestrator 直接) |
    | 跨 worktree 并行 N 个 | 子代理并行 | 串行子代理 → 失败则 orchestrator |
    | 计划生成 (无副作用) | 子代理并行 | 串行子代理 |
    """
    matrix = {
        (TaskType.SINGLE_FILE_SMALL, QuotaStatus.HEALTHY): ExecutionMode.ORCHESTRATOR,
        (TaskType.SINGLE_FILE_SMALL, QuotaStatus.TIGHT): ExecutionMode.ORCHESTRATOR,
        (TaskType.SINGLE_FILE_LARGE, QuotaStatus.HEALTHY): ExecutionMode.SUBAGENT,
        (TaskType.SINGLE_FILE_LARGE, QuotaStatus.TIGHT): ExecutionMode.ORCHESTRATOR,
        (TaskType.CROSS_FILE_TDD, QuotaStatus.HEALTHY): ExecutionMode.SUBAGENT,
        (TaskType.CROSS_FILE_TDD, QuotaStatus.TIGHT): ExecutionMode.SUBAGENT,
        (TaskType.CROSS_WORKTREE_PARALLEL, QuotaStatus.HEALTHY): ExecutionMode.SUBAGENT,
        (TaskType.CROSS_WORKTREE_PARALLEL, QuotaStatus.TIGHT): ExecutionMode.SUBAGENT,
        (TaskType.PLAN_GENERATION, QuotaStatus.HEALTHY): ExecutionMode.SUBAGENT,
        (TaskType.PLAN_GENERATION, QuotaStatus.TIGHT): ExecutionMode.SUBAGENT,
    }
    return matrix[(task_type, quota_status)]


def _ping_subagent() -> dict:
    """Send a minimal probe to subagent to verify quota availability.

    In production, this calls task() with a tiny prompt. The function is
    mocked in unit tests to control return values.
    """
    # Defer import to avoid circular dependencies
    try:
        from task import task  # noqa
        result = task(subagent_type="general", prompt="ping", timeout=30)
        return {"status": "ok" if result.status != "quota_exceeded" else "quota_exceeded"}
    except Exception as e:
        # Network error, quota error, or any other exception → treat as tight
        if "quota" in str(e).lower():
            return {"status": "quota_exceeded"}
        raise


def probe_subagent_quota() -> QuotaStatus:
    """Probe whether subagent quota is available.

    Returns HEALTHY if probe succeeds, TIGHT if quota_exceeded or any error.
    Fail-safe: any exception results in TIGHT to avoid wasted retries.
    """
    try:
        result = _ping_subagent()
        return QuotaStatus.HEALTHY if result.get("status") == "ok" else QuotaStatus.TIGHT
    except Exception:
        return QuotaStatus.TIGHT


def _get_quota_failures_path() -> Path:
    """Resolve .rddf/state/quota_failures.json path."""
    rddf_state = os.environ.get("RDDF_STATE_DIR")
    if rddf_state:
        return Path(rddf_state) / "quota_failures.json"
    # Default: PROJECT_ROOT/.rddf/state/
    project_root = Path(os.environ.get("PROJECT_ROOT", "."))
    return project_root / ".rddf" / "state" / "quota_failures.json"


def load_quota_failures() -> List[dict]:
    """Load quota failures from JSON file. Returns empty list if file missing."""
    path = _get_quota_failures_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("failures", [])
    except (json.JSONDecodeError, OSError):
        return []


def _save_quota_failures(failures: List[dict]) -> None:
    """Atomic write of quota failures to JSON file."""
    path = _get_quota_failures_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w") as f:
        json.dump({"failures": failures, "updated_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)
    tmp_path.replace(path)


def record_quota_failure(failure_type: str, tool: str = "unknown", count: int = 1, **metadata) -> None:
    """Record a quota failure event.

    Aggregates consecutive failures of the same type/tool by incrementing count.
    """
    failures = load_quota_failures()
    now = datetime.now(timezone.utc).isoformat()

    # Find existing entry with same type + tool
    existing = None
    for f in failures:
        if f.get("type") == failure_type and f.get("tool") == tool:
            existing = f
            break

    if existing is not None:
        existing["count"] = existing.get("count", 0) + count
        existing["last_occurred_at"] = now
    else:
        failures.append({
            "type": failure_type,
            "tool": tool,
            "count": count,
            "first_occurred_at": now,
            "last_occurred_at": now,
            **metadata,
        })

    _save_quota_failures(failures)
