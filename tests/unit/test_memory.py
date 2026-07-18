"""Tests for LoopMemory — execution history, recovery, and config recommendation.

Per ADR-0006, the LoopMemory module records loop execution history to a
JSONL file. It supports interruption recovery, repeated-failure warnings,
config suggestion via Jaccard similarity, and archival at MAX_RECORDS.
"""
from __future__ import annotations
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from skills._lib.loop.memory import ExecutionRecord, LoopMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    change_name: str = "test-change",
    goal: str = "implement feature X",
    config: Optional[Dict[str, Any]] = None,
    iterations: int = 1,
    result: str = "success",
    failure_reason: Optional[str] = None,
    timestamp: Optional[str] = None,
    duration_seconds: float = 1.0,
) -> ExecutionRecord:
    """Build an ExecutionRecord with sensible defaults for tests."""
    return ExecutionRecord(
        change_name=change_name,
        goal=goal,
        config=config if config is not None else {},
        iterations=iterations,
        result=result,
        failure_reason=failure_reason,
        timestamp=timestamp if timestamp is not None else f"2026-06-26T00:00:{0:02d}Z",
        duration_seconds=duration_seconds,
    )


@pytest.fixture
def memory_path(tmp_path):
    """Return a per-test memory.jsonl path inside tmp_path."""
    return str(tmp_path / "memory.jsonl")


@pytest.fixture
def memory(memory_path):
    """Return a LoopMemory bound to the per-test path."""
    return LoopMemory(path=memory_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_record_execution_writes_jsonl(tmp_path, memory_path):
    """record_execution() appends one valid JSONL line containing all fields."""
    mem = LoopMemory(path=memory_path)
    rec = _make_record(change_name="c1", goal="do thing", iterations=3)
    mem.record_execution(rec)

    with open(memory_path) as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]

    assert len(lines) == 1, "expected exactly one JSONL line"
    d = json.loads(lines[0])
    assert d["change_name"] == "c1"
    assert d["goal"] == "do thing"
    assert d["iterations"] == 3
    assert d["result"] == "success"
    assert d["failure_reason"] is None
    assert d["timestamp"] == rec.timestamp
    assert d["duration_seconds"] == 1.0
    assert d["config"] == {}


def test_get_history_filters_by_change(memory):
    """get_execution_history(change_name=X) returns only records for X."""
    for i in range(3):
        memory.record_execution(_make_record(change_name="alpha"))
    for i in range(2):
        memory.record_execution(_make_record(change_name="beta"))

    alpha_history = memory.get_execution_history(change_name="alpha")
    beta_history = memory.get_execution_history(change_name="beta")

    assert len(alpha_history) == 3
    assert len(beta_history) == 2
    assert all(r.change_name == "alpha" for r in alpha_history)
    assert all(r.change_name == "beta" for r in beta_history)


def test_get_history_respects_limit(memory):
    """get_execution_history(limit=K) returns at most K records (most recent)."""
    for i in range(5):
        memory.record_execution(_make_record(timestamp=f"2026-06-26T00:00:{i:02d}Z"))

    history = memory.get_execution_history(limit=3)
    assert len(history) == 3
    # Most-recent-first ordering — last recorded has highest timestamp.
    timestamps = [r.timestamp for r in history]
    assert timestamps == sorted(timestamps, reverse=True)


def test_insights_for_change_aggregates(memory):
    """get_insights_for_change returns aggregated counts per result type."""
    # 2 success, 2 failure, 1 interrupted for change 'c-agg'
    for _ in range(2):
        memory.record_execution(_make_record(change_name="c-agg", result="success"))
    for _ in range(2):
        memory.record_execution(
            _make_record(change_name="c-agg", result="failure", failure_reason="boom")
        )
    memory.record_execution(_make_record(change_name="c-agg", result="interrupted"))
    # Noise — should not affect aggregation for c-agg
    memory.record_execution(_make_record(change_name="other", result="failure"))

    insights = memory.get_insights_for_change("c-agg")

    assert isinstance(insights, dict)
    assert insights.get("total", insights.get("count")) == 5
    assert insights.get("successes", insights.get("success")) == 2
    assert insights.get("failures", insights.get("failure")) == 2
    assert insights.get("interrupted", 0) == 1
    # Other change must not leak into c-agg insights
    assert insights.get("failures", insights.get("failure")) == 2


def test_suggest_config_finds_similar_goal(memory):
    """suggest_config returns the config from a successful past execution whose goal
    has Jaccard similarity ≥ 0.6 to the query goal."""
    past = _make_record(
        change_name="past-change",
        goal="add user login with oauth support",
        result="success",
        config={"max_iterations": 5, "mode": "interactive"},
    )
    memory.record_execution(past)

    suggestion = memory.suggest_config("add user login with oauth")

    assert suggestion is not None
    assert suggestion == {"max_iterations": 5, "mode": "interactive"}


def test_suggest_config_returns_none_when_no_match(memory):
    """suggest_config returns None when no past execution has sufficient similarity."""
    memory.record_execution(
        _make_record(
            change_name="past",
            goal="completely unrelated database migration",
            result="success",
            config={"k": "v"},
        )
    )

    suggestion = memory.suggest_config("render a unicorn with rainbow mane")

    assert suggestion is None


def test_interrupted_recovery_returns_last(memory):
    """get_last_interrupted returns the most recent record whose result == 'interrupted'."""
    memory.record_execution(_make_record(change_name="c", result="success", timestamp="2026-06-26T00:00:00Z"))
    memory.record_execution(
        _make_record(change_name="c", result="interrupted", timestamp="2026-06-26T00:00:01Z")
    )
    memory.record_execution(
        _make_record(change_name="c", result="interrupted", timestamp="2026-06-26T00:00:02Z")
    )
    memory.record_execution(_make_record(change_name="c", result="success", timestamp="2026-06-26T00:00:03Z"))

    last = memory.get_last_interrupted()
    assert last is not None
    assert last.result == "interrupted"
    assert last.timestamp == "2026-06-26T00:00:02Z"


def test_repeated_failure_warning_at_threshold(memory):
    """repeated_failure_warning returns a warning string at ≥ 3 failures, else None."""
    # 2 failures — below threshold
    for _ in range(2):
        memory.record_execution(_make_record(change_name="flaky", result="failure"))
    assert memory.repeated_failure_warning("flaky") is None

    # 3rd failure — at threshold
    memory.record_execution(_make_record(change_name="flaky", result="failure"))
    warning = memory.repeated_failure_warning("flaky")
    assert warning is not None
    assert isinstance(warning, str)
    assert len(warning) > 0
    # Warning text should at minimum mention the change or the count
    assert ("flaky" in warning) or ("3" in warning)


def test_archive_when_over_cap(memory, monkeypatch):
    """When records exceed MAX_RECORDS, archive() moves the oldest to archive file."""
    monkeypatch.setattr(LoopMemory, "MAX_RECORDS", 5)

    for i in range(8):
        memory.record_execution(_make_record(timestamp=f"2026-06-26T00:00:{i:02d}Z"))

    archived_count = memory.archive()

    # archive returns the count of archived records
    assert archived_count == 3

    # Main file should now contain at most MAX_RECORDS entries (oldest 3 archived)
    with open(memory.path) as f:
        main_lines = [ln for ln in f.read().splitlines() if ln.strip()]
    assert len(main_lines) == 5

    # Archive file exists and has the 3 oldest
    archive_path = memory.path + ".archive.jsonl"
    assert os.path.exists(archive_path)
    with open(archive_path) as f:
        archive_lines = [ln for ln in f.read().splitlines() if ln.strip()]
    assert len(archive_lines) == 3

    # The archived records must be the OLDEST — by timestamp
    archive_records = [json.loads(ln) for ln in archive_lines]
    archived_timestamps = sorted(r["timestamp"] for r in archive_records)
    main_records = [json.loads(ln) for ln in main_lines]
    main_timestamps = sorted(r["timestamp"] for r in main_records)
    assert archived_timestamps == [r["timestamp"] for r in sorted(archive_records, key=lambda r: r["timestamp"])]
    assert max(archived_timestamps) < min(main_timestamps)


def test_concurrent_writes_safe_via_lock(tmp_path, memory_path):
    """Concurrent writers through FileLock must produce all records without corruption."""
    mem = LoopMemory(path=memory_path)
    thread_count = 4
    writes_per_thread = 25
    errors: List[BaseException] = []

    def worker(tid: int):
        try:
            for i in range(writes_per_thread):
                mem.record_execution(
                    _make_record(
                        change_name=f"c-{tid}",
                        timestamp=f"2026-06-26T00:{tid:02d}:{i:02d}Z",
                    )
                )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"concurrent writers raised: {errors}"

    # Every recorded line must be valid JSON, and counts must add up exactly
    with open(memory_path) as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    assert len(lines) == thread_count * writes_per_thread
    for ln in lines:
        d = json.loads(ln)  # must not raise
        assert "change_name" in d
        assert "result" in d

    # Each thread's records must all be present (no lost writes)
    by_thread: Dict[str, int] = {}
    for ln in lines:
        d = json.loads(ln)
        by_thread[d["change_name"]] = by_thread.get(d["change_name"], 0) + 1
    for tid in range(thread_count):
        assert by_thread[f"c-{tid}"] == writes_per_thread