"""Tests for _lib/builder_handoff.py"""
import sys
import threading
import json
from pathlib import Path

import pytest

sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.builder_handoff import (
    write_builder_handoff,
    read_builder_handoff,
    update_builder_handoff,
    increment_retry,
)


class TestWriteBasicRoundtrip:
    def test_write_basic_roundtrip(self, tmp_path):
        result = write_builder_handoff(
            project_root=str(tmp_path),
            change_name="test-change",
            current_phase="phase-1",
            approval_status="approved",
            plan_quality_status="pass",
            execution_mode_decision={"mode": "worktree"},
            deps_status={"blockers": [], "manual_deps": ["other"], "cross_repo_pending": []},
            worktree_path=".rddf/wt/test-change",
            branch="openspec/test-change",
            execution_status="in-progress",
            review_status="pending",
            archive_status="pending",
            verifier_report_path=".rddf/state/.verifier-report.json",
            retry_count=0,
            max_retries=3,
            retry_history=[],
            phase_pause_history=[],
        )
        assert result["change_name"] == "test-change"
        assert result["current_phase"] == "phase-1"
        assert result["approval_status"] == "approved"
        assert result["plan_quality_status"] == "pass"
        assert result["execution_mode_decision"] == {"mode": "worktree"}
        assert result["deps_status"] == {"blockers": [], "manual_deps": ["other"], "cross_repo_pending": []}
        assert result["worktree_path"] == ".rddf/wt/test-change"
        assert result["branch"] == "openspec/test-change"
        assert result["execution_status"] == "in-progress"
        assert result["review_status"] == "pending"
        assert result["archive_status"] == "pending"
        assert result["retry_count"] == 0
        assert result["max_retries"] == 3
        assert result["retry_history"] == []
        assert result["phase_pause_history"] == []
        assert result["schema"] == "builder-handoff-v1"
        assert result["version"] == 1
        assert result["owner"] == "rdd-builder"
        assert "updated_at" in result

        read_back = read_builder_handoff(str(tmp_path), "test-change")
        assert read_back["change_name"] == "test-change"
        assert read_back["current_phase"] == "phase-1"
        assert read_back["approval_status"] == "approved"
        assert read_back["plan_quality_status"] == "pass"
        assert read_back["execution_mode_decision"] == {"mode": "worktree"}


class TestPerChangeFileLayout:
    def test_per_change_file_layout(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="my-change",
            current_phase="phase-2",
        )
        expected_path = tmp_path / ".rddf" / "state" / "builder" / "my-change.json"
        assert expected_path.exists(), f"Expected {expected_path}"
        with open(expected_path) as f:
            data = json.load(f)
        assert data["change_name"] == "my-change"
        assert data["current_phase"] == "phase-2"


class TestUpdateMergesPartialFields:
    def test_update_merges_partial_fields(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="merge-test",
            current_phase="phase-0",
            approval_status="pending",
            plan_quality_status="pending",
            execution_status="pending",
            review_status="pending",
            archive_status="pending",
        )
        update_builder_handoff(
            project_root=str(tmp_path),
            change_name="merge-test",
            current_phase="phase-1",
            approval_status="approved",
        )
        result = read_builder_handoff(str(tmp_path), "merge-test")
        assert result["current_phase"] == "phase-1"
        assert result["approval_status"] == "approved"
        assert result["plan_quality_status"] == "pending"
        assert result["execution_status"] == "pending"
        assert result["review_status"] == "pending"
        assert result["archive_status"] == "pending"


class TestUpdateAutoFillsMeta:
    def test_update_auto_fills_meta(self, tmp_path):
        update_builder_handoff(
            project_root=str(tmp_path),
            change_name="brand-new",
            current_phase="phase-1",
            approval_status="approved",
        )
        result = read_builder_handoff(str(tmp_path), "brand-new")
        assert result["schema"] == "builder-handoff-v1"
        assert result["version"] == 1
        assert result["owner"] == "rdd-builder"
        assert result["change_name"] == "brand-new"
        assert result["current_phase"] == "phase-1"
        assert result["approval_status"] == "approved"


class TestUpdatePreservesChangeName:
    def test_update_overrides_change_name(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="original-name",
            current_phase="phase-1",
        )
        update_builder_handoff(
            project_root=str(tmp_path),
            change_name="original-name",
            current_phase="phase-2",
        )
        result = read_builder_handoff(str(tmp_path), "original-name")
        assert result["change_name"] == "original-name"


class TestIncrementRetryBasic:
    def test_increment_retry_basic(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="retry-test",
            current_phase="phase-3",
            retry_count=0,
            max_retries=3,
        )
        increment_retry(
            project_root=str(tmp_path),
            change_name="retry-test",
            to_phase="phase-1",
            verifier_kind="llm",
            verifier_exit_code=1,
        )
        result = read_builder_handoff(str(tmp_path), "retry-test")
        assert result["retry_count"] == 1
        assert len(result["retry_history"]) == 1
        assert result["retry_history"][0]["to_phase"] == "phase-1"
        assert result["retry_history"][0]["verifier_kind"] == "llm"
        assert result["retry_history"][0]["verifier_exit_code"] == 1


class TestIncrementRetryMultiple:
    def test_increment_retry_multiple(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="multi-retry",
            current_phase="phase-3",
            retry_count=0,
            max_retries=5,
        )
        for i in range(3):
            increment_retry(
                project_root=str(tmp_path),
                change_name="multi-retry",
                to_phase=f"phase-{i}",
                verifier_kind="llm",
                verifier_exit_code=1,
            )
        result = read_builder_handoff(str(tmp_path), "multi-retry")
        assert result["retry_count"] == 3
        assert len(result["retry_history"]) == 3


class TestIncrementRetryVerifierMetadata:
    def test_increment_retry_verifier_metadata(self, tmp_path):
        write_builder_handoff(
            project_root=str(tmp_path),
            change_name="metadata-test",
            current_phase="phase-3",
            retry_count=0,
            max_retries=3,
        )
        increment_retry(
            project_root=str(tmp_path),
            change_name="metadata-test",
            to_phase="phase-1",
            verifier_kind="ac-verifier",
            verifier_exit_code=42,
        )
        result = read_builder_handoff(str(tmp_path), "metadata-test")
        entry = result["retry_history"][0]
        assert entry["verifier_kind"] == "ac-verifier"
        assert entry["verifier_exit_code"] == 42
        assert "at" in entry


class TestReadMissingChange:
    def test_read_missing_change(self, tmp_path):
        result = read_builder_handoff(str(tmp_path), "nonexistent-change")
        assert result == {}


class TestFileLockConcurrentWrites:
    def test_file_lock_concurrent_writes(self, tmp_path):
        errors = []
        barrier = threading.Barrier(2)

        def writer(thread_id):
            try:
                barrier.wait()
                for i in range(10):
                    data = {"thread": thread_id, "seq": i, "change": "concurrent-test"}
                    update_builder_handoff(
                        project_root=str(tmp_path),
                        change_name="concurrent-test",
                        **data,
                    )
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=writer, args=(1,))
        t2 = threading.Thread(target=writer, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert errors == [], f"Errors during concurrent writes: {errors}"
        result = read_builder_handoff(str(tmp_path), "concurrent-test")
        assert "thread" in result
        assert "seq" in result
        assert result["change"] == "concurrent-test"
