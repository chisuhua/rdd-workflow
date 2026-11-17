"""Contract tests for the tasks_done / tasks_total pair.

Background (fix-iteration-tasks-total): in v4 the WRITER of `tasks_total` was
lost. The field is only read by `_lib/verifier/discovery.py::_is_eligible`
(`done == total > 0`) and `skills/rdd-verifier/scripts/scan_queue.sh` — so
with no writer the eligible set was permanently empty and batch verification
found nothing. `iteration_schema.json` still claimed the field was a
"plan generation snapshot", which is also where it went wrong: nothing wrote
it at plan time either.

These tests pin four things:

  1. ONE canonical checkbox counter (`archive_sidecar.count_tasks`). The five
     previous call sites disagreed — some accepted uppercase `[X]`, some did
     not; some counted indented sub-tasks, some did not; some accepted `-[x]`
     without a space. done and total must come from the same source, or
     `done > total` is reachable.
  2. `store.set_tasks_done` gains an optional `status` (default stays
     `in_worktree`, so `test_preserves_status_as_in_worktree` stays green).
  3. The writers actually write: P1 writes `tasks_total` without flipping
     status, P2 writes done+total, the archive sync writes both.
  4. Re-running a writer is idempotent: it must not flip `in_worktree` back to
     `proposed`, and must not walk a recorded `tasks_done` backwards.

CHANGED 2026-11-17: added by fix-iteration-tasks-total.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import through the `skills._lib.*` shim (as tests/unit/test_iteration.py
# does): importing `_lib.iteration` directly makes the package's own
# `from skills._lib.iteration import ...` re-export collide with the partially
# initialised module (circular import).
from skills._lib import iteration as it_store  # noqa: E402
from skills._lib.iteration.archive_sidecar import (  # noqa: E402
    count_done_tasks,
    count_tasks,
)


# ---------------------------------------------------------------------------
# 1. the canonical counter
# ---------------------------------------------------------------------------

class TestCountTasks:
    def test_counts_done_and_total_from_the_same_source(self):
        text = (
            "## Tasks\n"
            "- [x] one\n"
            "- [ ] two\n"
            "- [X] three\n"
        )
        done, total = count_tasks(text)
        assert done == 2      # [x] and [X]
        assert total == 3

    def test_counts_indented_subtasks(self):
        """Indented checkboxes are sub-tasks of a parent task — they are tasks."""
        text = (
            "- [ ] parent\n"
            "  - [ ] child one\n"
            "  - [x] child two\n"
        )
        done, total = count_tasks(text)
        assert done == 1
        assert total == 3

    def test_accepts_checkbox_without_a_space(self):
        text = "-[x] no space\n"
        assert count_tasks(text) == (1, 1)

    def test_never_reports_done_greater_than_total(self):
        """The invariant the five old call sites could each violate."""
        for text in (
            "- [x] a\n- [ ] b\n",
            "- [X] a\n",
            "no checkboxes at all\n",
            "",
        ):
            done, total = count_tasks(text)
            assert done <= total, text

    def test_empty_text_is_zero_not_an_error(self):
        assert count_tasks("") == (0, 0)

    def test_count_done_tasks_stays_compatible(self):
        """The old single-value helper must remain the `done` half."""
        text = "- [x] a\n- [ ] b\n- [X] c\n"
        assert count_done_tasks(text) == count_tasks(text)[0]


# ---------------------------------------------------------------------------
# 2. store.set_tasks_done gains an optional status
# ---------------------------------------------------------------------------

class TestSetTasksDoneStatus:
    def test_default_status_is_still_in_worktree(self):
        """Regression guard for tests/unit/test_iteration.py::
        test_preserves_status_as_in_worktree — a change with tasks_done must
        not stay `proposed`."""
        d = it_store.add_or_update_change(
            it_store.create_empty(), name="c1", status="proposed",
        )
        d = it_store.set_tasks_done(d, "c1", done=1)
        assert d["changes"][0]["status"] == "in_worktree"

    def test_explicit_status_is_honoured(self):
        """The archive path must be able to record `archived` without the
        helper forcing `in_worktree` back."""
        d = it_store.add_or_update_change(
            it_store.create_empty(), name="c1", status="archived",
        )
        d = it_store.set_tasks_done(d, "c1", done=3, total=3, status="archived")
        assert d["changes"][0]["status"] == "archived"
        assert d["changes"][0]["tasks_done"] == 3
        assert d["changes"][0]["tasks_total"] == 3

    def test_total_omitted_leaves_total_untouched(self):
        d = it_store.add_or_update_change(
            it_store.create_empty(), name="c1", status="in_worktree",
        )
        d = it_store.set_tasks_done(d, "c1", done=3)
        assert "tasks_total" not in d["changes"][0]


# ---------------------------------------------------------------------------
# 3 + 4. the writers
# ---------------------------------------------------------------------------

def _write_iteration(project_root: Path, changes: list[dict]) -> Path:
    """Write a schema-valid iteration.json (via the store, not by hand)."""
    state = project_root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    data = it_store.create_empty()
    for change in changes:
        data = it_store.add_or_update_change(data, **change)
    path = state / "iteration.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestWriters:
    def test_p1_snapshot_writes_total_without_flipping_status(self, tmp_path):
        """P1 records the plan-time task count; it must NOT move a change
        out of `proposed` (that transition belongs to P2)."""
        from _lib.iteration.writer import record_tasks_snapshot

        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text(
            "- [ ] a\n- [ ] b\n- [ ] c\n", encoding="utf-8"
        )
        _write_iteration(tmp_path, [
            {"name": "c1", "status": "proposed"},
        ])

        msg = record_tasks_snapshot(str(tmp_path), "c1", phase="plan")
        assert msg is None, msg

        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert entry["status"] == "proposed"        # NOT flipped
        assert entry["tasks_total"] == 3
        assert "tasks_done" not in entry             # P1 does not write progress

    def test_p2_snapshot_makes_the_change_verifier_eligible(self, tmp_path):
        """The whole point: P1 alone is not eligible, P2 completion is."""
        from _lib.iteration.writer import record_tasks_snapshot
        from _lib.verifier.discovery import discover_eligible

        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        tasks = change_dir / "tasks.md"
        tasks.write_text("- [ ] a\n- [ ] b\n", encoding="utf-8")
        _write_iteration(tmp_path, [{"name": "c1", "status": "proposed"}])

        record_tasks_snapshot(str(tmp_path), "c1", phase="plan")
        assert discover_eligible(tmp_path) == []      # planned, not executed

        tasks.write_text("- [x] a\n- [x] b\n", encoding="utf-8")
        record_tasks_snapshot(str(tmp_path), "c1", phase="execute")
        assert discover_eligible(tmp_path) == ["c1"]

    def test_p2_rerun_does_not_walk_done_backwards(self, tmp_path):
        from _lib.iteration.writer import record_tasks_snapshot

        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        tasks = change_dir / "tasks.md"
        tasks.write_text("- [x] a\n- [x] b\n- [x] c\n", encoding="utf-8")
        _write_iteration(tmp_path, [{"name": "c1", "status": "in_worktree"}])

        record_tasks_snapshot(str(tmp_path), "c1", phase="execute")
        # A later edit unchecks one box; a re-run must not lose the recorded 3.
        tasks.write_text("- [x] a\n- [x] b\n- [ ] c\n", encoding="utf-8")
        record_tasks_snapshot(str(tmp_path), "c1", phase="execute")

        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert entry["tasks_done"] == 3
        assert entry["tasks_total"] == 3

    def test_no_tasks_md_writes_nothing(self, tmp_path):
        """rdd-quick path: no tasks.md ⇒ no ghost entry, no counts."""
        from _lib.iteration.writer import record_tasks_snapshot

        _write_iteration(tmp_path, [{"name": "c1", "status": "proposed"}])
        msg = record_tasks_snapshot(str(tmp_path), "c1", phase="execute")
        assert msg and "no tasks.md" in msg

        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert "tasks_done" not in entry
        assert "tasks_total" not in entry

    def test_zero_checkbox_tasks_md_writes_nothing(self, tmp_path):
        from _lib.iteration.writer import record_tasks_snapshot

        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text("## Tasks\n\nno checkboxes\n", encoding="utf-8")
        _write_iteration(tmp_path, [{"name": "c1", "status": "in_worktree"}])

        msg = record_tasks_snapshot(str(tmp_path), "c1", phase="execute")
        assert msg and "no checkboxes" in msg

    def test_archive_sync_writes_both_done_and_total(self, tmp_path):
        """The archive sync used to write only tasks_done, so an archived
        change could never satisfy `done == total`."""
        from skills._lib.iteration.post_archive import sync_iteration_after_archive

        change_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-c1"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text(
            "- [x] a\n- [x] b\n- [ ] c\n", encoding="utf-8"
        )
        _write_iteration(tmp_path, [
            {"name": "c1", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
        ])

        msg = sync_iteration_after_archive(str(tmp_path), "c1")
        assert msg is None, msg

        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert entry["status"] == "archived"
        assert entry["tasks_done"] == 2
        assert entry["tasks_total"] == 3

    def test_archive_sync_prefers_the_archived_snapshot(self, tmp_path):
        """After archiving, tasks.md is replaced by a skeleton — the counts
        must come from tasks.md.archived-snapshot, not the skeleton (which
        has zero checkboxes and would zero the record)."""
        from skills._lib.iteration.post_archive import sync_iteration_after_archive

        change_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-c1"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text(
            "# Tasks: archived snapshot\n", encoding="utf-8"
        )
        (change_dir / "tasks.md.archived-snapshot").write_text(
            "- [x] a\n- [x] b\n", encoding="utf-8"
        )
        _write_iteration(tmp_path, [
            {"name": "c1", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
        ])

        msg = sync_iteration_after_archive(str(tmp_path), "c1")
        assert msg is None, msg

        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert entry["tasks_done"] == 2
        assert entry["tasks_total"] == 2

    def test_archive_sync_does_not_flip_status_to_in_worktree(self, tmp_path):
        """Regression: the archive path must never route through
        set_tasks_done's default status."""
        from skills._lib.iteration.post_archive import sync_iteration_after_archive

        change_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-c1"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text("- [x] a\n", encoding="utf-8")
        _write_iteration(tmp_path, [
            {"name": "c1", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
        ])

        sync_iteration_after_archive(str(tmp_path), "c1")
        doc = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        entry = next(c for c in doc["changes"] if c["name"] == "c1")
        assert entry["status"] == "archived"


# ---------------------------------------------------------------------------
# 5. the two eligibility implementations must agree, and the viewers must show
#    partial progress instead of hiding it
# ---------------------------------------------------------------------------

class TestEligibilityParity:
    def test_scan_queue_sh_and_discovery_py_agree(self, tmp_path):
        """Two implementations encode the same rule (`done == total > 0`).

        scan_queue.sh is bash+inline-python; discovery.py is the library. They
        were written independently, so nothing stopped them from drifting.
        """
        import subprocess

        def entry(status, done, total):
            doc = it_store.create_empty()
            doc = it_store.add_or_update_change(
                doc, name="c1", status=status,
            )
            doc = it_store.set_tasks_done(doc, "c1", done=done, total=total, status=status)
            it_store.save(str(tmp_path), doc)

        from _lib.verifier.discovery import discover_eligible

        cases = [
            ("in_worktree", 3, 3, ["c1"]),
            ("in_worktree", 3, 4, []),
            ("proposed", 0, 3, []),
            ("archived", 3, 3, []),
        ]
        for status, done, total, expected in cases:
            entry(status, done, total)
            py = discover_eligible(tmp_path)
            sh = subprocess.run(
                ["bash", str(REPO_ROOT / "skills/rdd-verifier/scripts/scan_queue.sh")],
                capture_output=True, text=True,
                env={**__import__("os").environ, "PROJECT_ROOT": str(tmp_path)},
            ).stdout.split()
            assert py == expected, (status, done, total, py)
            assert sh == expected, (status, done, total, sh)


class TestStatusDisplay:
    def test_partial_progress_shows_done_with_unknown_total(self, tmp_path, capsys):
        """`-` hid a recorded 4 done; `4/-` says what is known."""
        from _lib.cli.status_cmd import cmd_status_detail

        doc = it_store.create_empty()
        doc = it_store.add_or_update_change(doc, name="old", status="in_worktree")
        doc["changes"][0]["tasks_done"] = 4          # no tasks_total at all
        state = tmp_path / ".rddf" / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "iteration.json").write_text(json.dumps(doc), encoding="utf-8")

        assert cmd_status_detail("old", str(tmp_path)) == 0
        out = capsys.readouterr().out
        assert "4/-" in out, out

    def test_full_total_still_renders_as_ratio(self, tmp_path, capsys):
        from _lib.cli.status_cmd import cmd_status_detail

        doc = it_store.create_empty()
        doc = it_store.add_or_update_change(doc, name="c1", status="in_worktree")
        doc = it_store.set_tasks_done(doc, "c1", done=4, total=4)
        state = tmp_path / ".rddf" / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "iteration.json").write_text(json.dumps(doc), encoding="utf-8")

        assert cmd_status_detail("c1", str(tmp_path)) == 0
        assert "4/4" in capsys.readouterr().out


class TestDoctorTasksTotalHint:
    def test_warns_when_done_recorded_but_total_missing(self, tmp_path):
        """Entries written before the fix have `done` but no `total` — they can
        never be verified, so the doctor must say so (WARNING, not CRITICAL)."""
        import sys as _sys

        _sys.path.insert(0, str(REPO_ROOT / "skills" / "rdd-doctor" / "scripts"))
        _sys.path.insert(0, str(REPO_ROOT / "skills" / "rdd-doctor" / "scripts" / "checks"))
        from state_schema_check import _check_tasks_total_presence  # type: ignore

        doc = it_store.create_empty()
        doc = it_store.add_or_update_change(doc, name="old", status="in_worktree")
        doc["changes"][0]["tasks_done"] = 4     # no tasks_total
        state = tmp_path / ".rddf" / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "iteration.json").write_text(json.dumps(doc), encoding="utf-8")

        findings = _check_tasks_total_presence(tmp_path)
        assert len(findings) == 1, findings
        assert findings[0].category == "state"
        assert "tasks_total" in findings[0].snippet


class TestShimResolution:
    def test_shim_detects_itself_registered_under_the_real_name(self):
        """Regression for the identity-merge shim's self-detection bug.

        When `skills/` is the path entry that resolves `_lib` (it happens in
        feature_cli.py's environment), Python resolves
        `import _lib.tasks_count` to `skills/_lib/tasks_count.py` — the shim —
        and registers it under the real name *before* executing it. A plain
        `_sys.modules.get("_lib.tasks_count")` then returns the shim itself, the
        shim skips exec'ing the real source, and every later
        `from _lib.tasks_count import count_tasks` fails with ImportError.

        That exact path broke 6 cases in tests/integration/test_feature_skill.bats
        (feature_view → skills._lib.iteration → archive_sidecar → _lib.tasks_count).

        Subprocess + a sys.path containing ONLY `skills/` so the shim is the
        resolution target; otherwise the real module wins and the bug hides.
        """
        import subprocess
        import sys as _sys

        code = (
            "import sys\n"
            # Keep the stdlib, drop the repo root: `_lib` must resolve to
            # skills/_lib (the shim), not to <repo>/_lib (the real module).
            f"sys.path[:] = [{str(REPO_ROOT / 'skills')!r}] + [p for p in sys.path if 'rdd-workflow' not in p]\n"
            "import _lib.tasks_count as m\n"
            "assert m.__file__.endswith('_lib/tasks_count.py'), m.__file__\n"
            "assert 'skills/_lib' not in m.__file__, (\n"
            "    'still the shim: ' + m.__file__)\n"
            "assert m.count_tasks('- [x] a\\n- [ ] b\\n') == (1, 2)\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [_sys.executable, "-c", code], capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        assert "ok" in result.stdout
