"""Unit tests for _lib/roadmap_sprint.py — AUTO-SPRINT section renderer."""
import os
import pytest

from skills._lib import iteration as it
from skills._lib import roadmap_sprint as rs
from skills._lib.core import lock as core_lock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_data():
    """A realistic iteration.json state for testing the renderer."""
    data = it.create_empty("v2.1")
    data = it.add_or_update_change(
        data, name="v2-multi-session", status="in_worktree",
        phase="v2.1", category="session-management", priority="P0",
        tasks_done=2, tasks_total=5, blocker="v2-loop-engine",
        parallel_group=2, plan_path=".rddf/plans/v2-multi-session.md",
    )
    data = it.add_or_update_change(
        data, name="fix-loop-crash", status="proposed",
        phase="v2.1", category="loop-engine", priority="P0",
    )
    return data


# ---------------------------------------------------------------------------
# render_sprint_table
# ---------------------------------------------------------------------------

class TestRenderSprintTable:
    def test_header_line_present(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        assert "Phase: `v2.1`" in out
        assert "Active: 2" in out
        assert "Archived: 0" in out

    def test_table_header(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        assert "| Change | Phase | Cat | Status | Blocker | Group | Conflicts | Tasks | Plan |" in out
        assert "|--------|-------|-----|--------|---------|-------|-----------|-------|------|" in out

    def test_active_changes_rendered(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        assert "v2-multi-session" in out
        assert "fix-loop-crash" in out
        assert "🔄 in_worktree" in out
        assert "📋 proposed" in out

    def test_blocker_shown(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        assert "v2-loop-engine" in out
        # fix-loop-crash has no blocker
        lines_with_fixloop = [
            l for l in out.split("\n") if "fix-loop-crash" in l
        ]
        assert "—" in lines_with_fixloop[0]  # blocker column is "—"

    def test_tasks_progress_shown(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        assert "2/5" in out  # v2-multi-session
        # fix-loop-crash has no tasks_total
        assert "—" in out

    def test_plan_column(self, sample_data):
        out = rs.render_sprint_table(sample_data)
        # v2-multi-session has plan_path
        # fix-loop-crash does not
        assert "✅" in out

    def test_empty_state_message(self):
        data = it.create_empty("v2.1")
        out = rs.render_sprint_table(data)
        assert "无 active change" in out
        assert "Active: 0" in out

    def test_archived_footer(self):
        data = it.create_empty("v2.1")
        data = it.mark_archived(
            it.add_or_update_change(data, name="v2-loop-engine", status="in_worktree"),
            "v2-loop-engine",
        )
        out = rs.render_sprint_table(data)
        assert "🗄️ Archived" in out
        assert "v2-loop-engine" in out

    def test_no_sentinels_in_inner_content(self, sample_data):
        """render_sprint_table returns only the table; sentinels are render_full_block's job."""
        out = rs.render_sprint_table(sample_data)
        assert "AUTO-SPRINT-START" not in out
        assert "AUTO-SPRINT-END" not in out

    def test_long_phase_truncated(self):
        data = it.create_empty("v2.1-with-very-long-suffix")
        data = it.add_or_update_change(
            data, name="c1", status="proposed", phase="v2.1-with-very-long-suffix"
        )
        out = rs.render_sprint_table(data)
        # Truncated to 8 chars
        assert "v2.1-wi" in out


# ---------------------------------------------------------------------------
# render_full_block
# ---------------------------------------------------------------------------

class TestRenderFullBlock:
    def test_contains_sentinels(self, sample_data):
        out = rs.render_full_block(sample_data)
        assert rs.START_SENTINEL in out
        assert rs.END_SENTINEL in out

    def test_sentinels_bracket_inner(self, sample_data):
        out = rs.render_full_block(sample_data)
        start = out.find(rs.START_SENTINEL)
        end = out.find(rs.END_SENTINEL)
        assert start < end
        # Inner content between sentinels should be non-empty
        inner = out[start + len(rs.START_SENTINEL):end].strip()
        assert "v2-multi-session" in inner


# ---------------------------------------------------------------------------
# update_roadmap
# ---------------------------------------------------------------------------

class TestUpdateRoadmap:
    def test_appends_when_no_sentinels(self, tmp_path):
        """If roadmap.md has no sentinels, the full block is appended."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("# 项目路线图\n\n## v2.1\n- 长期 phase\n", encoding="utf-8")

        data = it.create_empty("v2.1")
        data = it.add_or_update_change(data, name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # User content preserved
        assert "# 项目路线图" in content
        assert "## v2.1" in content
        # AUTO-SPRINT block appended
        assert rs.START_SENTINEL in content
        assert rs.END_SENTINEL in content
        # Table content present
        assert "c1" in content

    def test_replaces_existing_block(self, tmp_path):
        """If sentinels exist, only the inner content is replaced."""
        roadmap = tmp_path / "roadmap.md"
        initial = (
            "# 项目路线图\n\n"
            "## v2.1\n"
            "长期 phase 内容\n\n"
            f"{rs.START_SENTINEL}\n"
            "OLD TABLE CONTENT\n"
            f"{rs.END_SENTINEL}\n\n"
            "## v3.0\n"
            "v3 长期 phase\n"
        )
        roadmap.write_text(initial, encoding="utf-8")

        data = it.create_empty("v2.1")
        data = it.add_or_update_change(data, name="new-change", status="in_worktree")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # Old content replaced
        assert "OLD TABLE CONTENT" not in content
        # New content present
        assert "new-change" in content
        # Before and after content preserved
        assert "# 项目路线图" in content
        assert "长期 phase 内容" in content
        assert "## v3.0" in content
        assert "v3 长期 phase" in content

    def test_silent_when_roadmap_missing(self, tmp_path):
        """If roadmap.md doesn't exist, no error and no file is created."""
        missing = tmp_path / "nonexistent.md"
        data = it.create_empty("v2.1")
        # Should NOT raise
        rs.update_roadmap(str(missing), data)
        assert not missing.exists()

    def test_atomic_write_no_tmp_left(self, tmp_path):
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("# 路线图\n", encoding="utf-8")
        data = it.create_empty("v2.1")
        data = it.add_or_update_change(data, name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)
        assert not (tmp_path / "roadmap.md.tmp").exists()

    def test_repeated_calls_idempotent(self, tmp_path):
        """Calling update_roadmap multiple times should not accumulate sentinels."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text("# 路线图\n", encoding="utf-8")
        data = it.create_empty("v2.1")
        data = it.add_or_update_change(data, name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)
        rs.update_roadmap(str(roadmap), data)
        rs.update_roadmap(str(roadmap), data)
        content = roadmap.read_text(encoding="utf-8")
        # Exactly one pair of sentinels
        assert content.count(rs.START_SENTINEL) == 1
        assert content.count(rs.END_SENTINEL) == 1


# ---------------------------------------------------------------------------
# Dangling sentinel self-healing (M2 fix)
# ---------------------------------------------------------------------------

class TestDanglingSentinel:
    """When roadmap.md has a malformed AUTO-SPRINT block (one sentinel
    present but the other missing, or sentinels in wrong order), update_roadmap
    must self-heal: strip the dangling markers and produce a clean block,
    rather than appending a duplicate pair that leaves the file in a
    malformed intermediate state.

    Before the M2 fix, the code treated all malformed-sentinel cases as
    "no sentinels" and appended a fresh block, producing files with
    duplicated START markers or duplicate table headers."""

    def test_dangling_start_without_end_is_healed(self, tmp_path):
        """START marker exists but END is missing (interrupted previous write)."""
        roadmap = tmp_path / "roadmap.md"
        # Previous update was interrupted after writing START but before END
        roadmap.write_text(
            "# 路线图\n"
            "## v2.1\n"
            f"{rs.START_SENTINEL}\n"
            "_partial_never_finished_\n",
            encoding="utf-8",
        )
        data = it.add_or_update_change(it.create_empty("v2.1"), name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # After heal: exactly one START and one END (no duplicates)
        assert content.count(rs.START_SENTINEL) == 1
        assert content.count(rs.END_SENTINEL) == 1
        # Orphan partial content from the previous interrupted write is gone
        assert "_partial_never_finished_" not in content
        # Fresh block has the new change
        assert "c1" in content

    def test_dangling_end_without_start_is_healed(self, tmp_path):
        """END marker exists without START (user manually added it)."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text(
            "# 路线图\n"
            "## v2.1\n"
            f"{rs.END_SENTINEL}\n",
            encoding="utf-8",
        )
        data = it.add_or_update_change(it.create_empty("v2.1"), name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # After heal: exactly one START and one END
        assert content.count(rs.START_SENTINEL) == 1
        assert content.count(rs.END_SENTINEL) == 1
        assert "c1" in content

    def test_end_before_start_is_treated_as_no_sentinels(self, tmp_path):
        """END appears before START (malformed order) — strip both, append fresh."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text(
            "# 路线图\n"
            f"{rs.END_SENTINEL}\n"
            "orphaned\n"
            f"{rs.START_SENTINEL}\n"
            "more orphans\n",
            encoding="utf-8",
        )
        data = it.add_or_update_change(it.create_empty("v2.1"), name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # After heal: exactly one START and one END (the malformed pair is gone)
        assert content.count(rs.START_SENTINEL) == 1
        assert content.count(rs.END_SENTINEL) == 1
        # Orphan content is gone
        assert "orphaned" not in content
        assert "more orphans" not in content
        # Fresh block has the new change
        assert "c1" in content

    def test_dangling_start_preserves_user_content(self, tmp_path):
        """When START is dangling, user-written content above it must survive."""
        roadmap = tmp_path / "roadmap.md"
        roadmap.write_text(
            "# 项目路线图\n\n## v2.0 ✅\n## v2.1 (当前)\n- v2-multi-session\n\n"
            f"{rs.START_SENTINEL}\n"
            "previous interrupted content\n",
            encoding="utf-8",
        )
        data = it.add_or_update_change(it.create_empty("v2.1"), name="c1", status="proposed")
        rs.update_roadmap(str(roadmap), data)

        content = roadmap.read_text(encoding="utf-8")
        # User content preserved
        assert "# 项目路线图" in content
        assert "## v2.0 ✅" in content
        assert "v2-multi-session" in content
        # Dangling partial gone
        assert "previous interrupted content" not in content
        # New block added
        assert "c1" in content

    def test_split_around_sentinels_returns_clean_tuple(self, tmp_path):
        """_split_around_sentinels is the unit-level function behind the fix.

        Returns (before, after) for content with malformed sentinels:
        - dangling markers should be stripped from `before`
        - dangling markers should NOT appear in `after`
        """
        content = (
            "# 路线图\n"
            f"{rs.START_SENTINEL}\n"
            "stale inner\n"
        )
        before, after = rs._split_around_sentinels(content)
        # The dangling START is stripped from `before`
        assert rs.START_SENTINEL not in before
        assert "stale inner" not in before
        # No `after` because treated as no sentinels
        assert after == ""
        # User content preserved
        assert "# 路线图" in before


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

class TestStaleness:
    def test_format_staleness_never(self):
        assert rs._format_staleness(None) == "never"

    def test_format_staleness_minutes(self):
        # 5 minutes ago
        ts = rs._now().replace(microsecond=0) - datetime.timedelta(minutes=5)
        out = rs._format_staleness(ts.isoformat())
        assert "m ago" in out

    def test_format_staleness_hours(self):
        ts = rs._now().replace(microsecond=0) - datetime.timedelta(hours=5)
        out = rs._format_staleness(ts.isoformat())
        assert "h ago" in out

    def test_format_staleness_days(self):
        ts = rs._now().replace(microsecond=0) - datetime.timedelta(days=3)
        out = rs._format_staleness(ts.isoformat())
        assert "d ago" in out


# ---------------------------------------------------------------------------
# Project table (Stage 2.5 P0-1: planner AUTO-SPRINT render contract)
# ---------------------------------------------------------------------------

class TestProjectTable:
    def test_render_project_table_renders_project_rows(self):
        """render_project_table renders the planner project table shape."""
        data = {
            "current_sprint": "sprint-2026-09",
            "active_projects": [
                {"project_id": "p1", "phase": "phase-2", "priority": "P1",
                 "feedback_status": "none", "proposal": "foo"},
                {"project_id": "p2", "phase": "phase-3", "priority": "P2",
                 "feedback_status": "needs-revision", "proposal": "bar"},
            ],
        }
        out = rs.render_project_table(data)
        assert "## Current Sprint: sprint-2026-09" in out
        assert "| Project | Phase | Priority | Feedback | Proposal |" in out
        assert "| p1 | phase-2 | P1 | none | foo |" in out
        assert "| p2 | phase-3 | P2 | needs-revision | bar |" in out

    def test_render_project_table_empty(self):
        out = rs.render_project_table({"current_sprint": "sprint-x", "active_projects": []})
        assert "_No active projects in current sprint._" in out

    def test_render_project_table_with_unmapped(self):
        out = rs.render_project_table({
            "current_sprint": "sprint-x",
            "active_projects": [],
            "unmapped_proposals": ["a", "b"],
        })
        assert "### Unmapped (2)" in out
        assert "- a" in out
        assert "- b" in out

    def test_update_roadmap_dispatches_project_table(self, monkeypatch):
        """update_roadmap(..., table='project') renders via render_project_table."""
        import os
        captured = {}
        monkeypatch.setattr(rs, "render_project_table",
                            lambda d: (captured.setdefault("data", d), "PROJECT-INNER")[1])
        tmp = os.path.join("/tmp", "_rs_dummy_" + str(os.getpid()))
        # create empty file so update_roadmap reads OK
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("# X\n")
        try:
            rs.update_roadmap(tmp, {"current_sprint": "sprint-2026-09", "active_projects": []},
                              table="project")
            assert "data" in captured
        finally:
            try:
                os.unlink(tmp)
                os.unlink(tmp + ".lock")
            except OSError:
                pass

    def test_update_roadmap_acquires_roadmap_lock(self, tmp_path, monkeypatch):
        """update_roadmap acquires a FileLock at <roadmap_path>.lock."""
        rm_path = tmp_path / "roadmap.md"
        rm_path.write_text("# R\n")
        seen_locks = []
        orig_lock = rs.FileLock
        def spy(lock_path, *a, **kw):
            seen_locks.append(str(lock_path))
            return orig_lock(lock_path, *a, **kw)
        monkeypatch.setattr(rs, "FileLock", spy)
        rs.update_roadmap(str(rm_path), {"current_sprint": "sprint-x", "active_projects": []},
                          table="project")
        assert any(str(rm_path.with_suffix(".lock")) == p for p in seen_locks)


# Need to import datetime at top level
import datetime  # noqa: E402
