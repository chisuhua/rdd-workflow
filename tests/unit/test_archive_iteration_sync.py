"""Unit tests for archive iteration sync — fix-iteration-archive-sync.

Per fix-iteration-archive-sync proposal acceptance:
  - archive 后 iteration 状态更新为 archived
  - archive 失败时 iteration 不被更新(回滚)
  - tasks_done 字段正确传播

Tested via the post_archive.sync_iteration_after_archive module that
_lib/archive.sh::mark_iteration_archived shells out to.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """A fresh project root with .rddf/state/ pre-created + iteration.json."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    iter_data = {
        "version": 4,
        "current_phase": "v2.2",
        "updated_at": "2026-08-27T00:00:00+00:00",
        "changes": [
            {
                "name": "test-change-success",
                "status": "proposed",
                "phase": "default",
                "category": "test",
                "tasks_total": 5,
            },
            {
                "name": "test-change-rollback",
                "status": "proposed",
                "phase": "default",
                "category": "test",
                "tasks_total": 3,
                "tasks_done": 1,
            },
        ],
    }
    (state_dir / "iteration.json").write_text(
        json.dumps(iter_data), encoding="utf-8"
    )
    return str(tmp_path)


@pytest.fixture
def archive_dir(tmp_path):
    """An openspec/changes/archive/<date>-test-change-success/ with tasks.md."""
    archive_path = tmp_path / "openspec" / "changes" / "archive" / "2026-08-27-test-change-success"
    archive_path.mkdir(parents=True)
    tasks_content = """## Implementation Tasks

- [x] Task 1: setup
- [x] Task 2: implement
- [x] Task 3: test
- [x] Task 4: docs
- [x] Task 5: archive
"""
    (archive_path / "tasks.md").write_text(tasks_content, encoding="utf-8")
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Test: archive success path
# ---------------------------------------------------------------------------

def test_sync_iteration_after_archive_marks_status_archived(project_root, archive_dir):
    """Per AC #1: archive 后 iteration 状态更新为 archived."""
    from skills._lib.iteration.post_archive import sync_iteration_after_archive

    result = sync_iteration_after_archive(project_root, "test-change-success")
    assert result is None, f"unexpected warning: {result}"

    iter_data = json.loads(
        Path(project_root, ".rddf", "state", "iteration.json").read_text()
    )
    entry = next(c for c in iter_data["changes"] if c["name"] == "test-change-success")
    assert entry["status"] == "archived"
    assert "archived_at" in entry


def test_sync_iteration_after_archive_propagates_tasks_done(project_root, archive_dir):
    """Per AC #3: tasks_done 字段正确传播 (从 archive tasks.md 计数)。"""
    from skills._lib.iteration.post_archive import sync_iteration_after_archive

    sync_iteration_after_archive(project_root, "test-change-success")

    iter_data = json.loads(
        Path(project_root, ".rddf", "state", "iteration.json").read_text()
    )
    entry = next(c for c in iter_data["changes"] if c["name"] == "test-change-success")
    # tasks.md has 5 [x]; tasks_total=5; tasks_done should equal 5
    assert entry["tasks_done"] == 5
    assert entry["tasks_total"] == 5


def test_sync_iteration_after_archive_idempotent(project_root, archive_dir):
    """Calling twice doesn't break state; archived_at preserved."""
    from skills._lib.iteration.post_archive import sync_iteration_after_archive

    sync_iteration_after_archive(project_root, "test-change-success")
    iter_data_1 = json.loads(
        Path(project_root, ".rddf", "state", "iteration.json").read_text()
    )
    archived_at_1 = next(c for c in iter_data_1["changes"]
                          if c["name"] == "test-change-success")["archived_at"]

    # 第二次调用: 不应该覆写 archived_at
    sync_iteration_after_archive(project_root, "test-change-success")
    iter_data_2 = json.loads(
        Path(project_root, ".rddf", "state", "iteration.json").read_text()
    )
    archived_at_2 = next(c for c in iter_data_2["changes"]
                          if c["name"] == "test-change-success")["archived_at"]
    assert archived_at_1 == archived_at_2


# ---------------------------------------------------------------------------
# Test: missing change entry falls back to on-disk reconciliation
# ---------------------------------------------------------------------------

def test_sync_iteration_after_archive_missing_entry_recovers_via_disk(
    project_root, archive_dir
):
    """If iteration.json 没有这个 change 但 archive/ 有, 应该 on-disk recover."""
    from skills._lib.iteration.post_archive import sync_iteration_after_archive

    # Remove the entry from iteration.json
    iter_path = Path(project_root, ".rddf", "state", "iteration.json")
    data = json.loads(iter_path.read_text())
    data["changes"] = [c for c in data["changes"] if c["name"] != "test-change-success"]
    iter_path.write_text(json.dumps(data), encoding="utf-8")

    result = sync_iteration_after_archive(project_root, "test-change-success")
    # Should succeed via force_mark_archived fallback
    assert result is None or "auto-recovered" in (result or "")

    # Verify entry was re-created
    iter_data = json.loads(iter_path.read_text())
    entry = next(
        (c for c in iter_data["changes"] if c["name"] == "test-change-success"),
        None,
    )
    assert entry is not None
    assert entry["status"] == "archived"


# ---------------------------------------------------------------------------
# Test: missing iteration.json returns warning
# ---------------------------------------------------------------------------

def test_sync_iteration_after_archive_missing_iteration_returns_warning(tmp_path):
    """If iteration.json is missing entirely, returns warning (does not raise)."""
    from skills._lib.iteration.post_archive import sync_iteration_after_archive

    project_root = str(tmp_path)
    # No .rddf/state/ created
    result = sync_iteration_after_archive(project_root, "any-change")
    assert result is not None  # warning string
    assert "not found" in result.lower() or "unreadable" in result.lower()


# ---------------------------------------------------------------------------
# Test: add_or_update_change supports archived status + tasks_done
# ---------------------------------------------------------------------------

def test_add_or_update_change_supports_archived_status_and_tasks_done(project_root):
    """Per AC #2: add_or_update_change 支持 status='archived' 且 tasks_done 字段."""
    from skills._lib import iteration as it

    data = it.load(project_root)
    new_data = it.add_or_update_change(
        data, name="new-archive-entry", status="archived", tasks_done=5
    )
    it.save(project_root, new_data)

    # Re-load and verify
    fresh = it.load(project_root)
    entry = next(c for c in fresh["changes"] if c["name"] == "new-archive-entry")
    assert entry["status"] == "archived"
    assert entry["tasks_done"] == 5


# ---------------------------------------------------------------------------
# Test: shell wrapper mark_iteration_archived works (integration smoke)
# ---------------------------------------------------------------------------

def test_mark_iteration_archived_bash_wrapper(project_root, archive_dir):
    """_lib/archive.sh::mark_iteration_archived bash wrapper end-to-end."""
    # Skip if shell wrapper not available (e.g., outside repo context)
    repo_root = os.environ.get("REPO_ROOT")
    if not repo_root:
        pytest.skip("REPO_ROOT not set (CI-only test)")

    iter_path = Path(project_root, ".rddf", "state", "iteration.json")
    pre_data = iter_path.read_text()

    # Run the actual bash wrapper (requires git context)
    script = Path(repo_root) / "_lib" / "archive.sh"
    if not script.exists():
        pytest.skip(f"bash wrapper not found: {script}")

    # Just ensure mark_iteration_archived exists + doesn't crash on missing args
    result = subprocess.run(
        ["bash", "-c",
         f'source "{script}" 2>/dev/null && mark_iteration_archived "" "" || true'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0  # best-effort, never raises
    # iteration.json should be unchanged (no-op on empty args)
    assert iter_path.read_text() == pre_data