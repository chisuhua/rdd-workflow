"""Integration test: full iteration.json lifecycle across hooks.

Exercises the iteration.json round-trip in the same way the v2 hooks do:
- propose: add a change with status=proposed
- guide-ship: transition to in_worktree, set plan_path and tasks_total
- execute: increment tasks_done
- deps: set blocker + parallel_group
- archive: mark_archived
- roadmap: AUTO-SPRINT block generated from final state

This is a Python-level integration test (the .md files are templates
that get evaluated at runtime; their behavior is captured by what the
hooks' Python bodies do). The corresponding bats test for the bash
side is `test_iteration_archive_hook.bats`.
"""
import os
import re
import json
import pytest

from skills._lib import iteration as it
from skills._lib import roadmap_sprint as rs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """Project root with .rddf/state/ pre-created (mimics real layout)."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def roadmap_path(project_root):
    """A roadmap.md with hand-written long-term content (no sentinels yet)."""
    p = os.path.join(project_root, "roadmap.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("# 项目路线图\n\n## v2.0 ✅\n## v2.1 (当前)\n- v2-multi-session [📋]\n## v3.0\n- v3-scheduled-triggers\n")
    return p


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------

class TestFullLifecycle:
    """Mimic the propose → guide-ship → execute → deps → archive flow."""

    def test_end_to_end(self, project_root, roadmap_path):
        # 1. PROPOSE: hook in propose.md
        data = it.load(project_root)
        data = it.add_or_update_change(
            data, name="v2-multi-session", status="proposed",
            phase="v2.1", category="session-mgmt", priority="P0",
        )
        it.save(project_root, data)

        # 2. GUIDE-SHIP: hook creates worktree + plan, status=in_worktree
        data = it.load(project_root)
        data = it.set_status(data, "v2-multi-session", "in_worktree")
        data = it.add_or_update_change(
            data, name="v2-multi-session", status="in_worktree",
            worktree_path=".rddf/wt/v2-multi-session",
            plan_path=".rddf/plans/v2-multi-session.md",
            tasks_total=5,
        )
        it.save(project_root, data)

        # 3. EXECUTE: hook in execute.md updates tasks_done
        data = it.load(project_root)
        data = it.set_tasks_done(data, "v2-multi-session", done=2, total=5)
        it.save(project_root, data)
        data = it.load(project_root)
        data = it.set_tasks_done(data, "v2-multi-session", done=4, total=5)
        it.save(project_root, data)

        # 4. DEPS: hook in deps.md sets blocker + parallel_group
        data = it.load(project_root)
        data = it.set_deps_info(
            data, "v2-multi-session",
            blocker="v2-loop-engine", parallel_group=2, conflicts=["refactor-session-api"],
        )
        it.save(project_root, data)

        # 5. ROADMAP: AUTO-SPRINT block reflects the final state
        data = it.load(project_root)
        rs.update_roadmap(roadmap_path, data)
        with open(roadmap_path, encoding="utf-8") as f:
            roadmap_content = f.read()
        assert rs.START_SENTINEL in roadmap_content
        assert rs.END_SENTINEL in roadmap_content
        assert "v2-multi-session" in roadmap_content
        assert "v2-loop-engine" in roadmap_content  # blocker

        # 6. STATUS MODE E: should render without errors (we don't invoke the
        # .md directly here; we just verify the data structure is consumable)
        active = it.list_active(data)
        assert len(active) == 1
        c = active[0]
        assert c["status"] == "in_worktree"
        assert c["blocker"] == "v2-loop-engine"
        assert c["parallel_group"] == 2
        assert "refactor-session-api" in c["conflicts"]
        assert c["tasks_done"] == 4
        assert c["tasks_total"] == 5

        # 7. ARCHIVE: hook in archive.sh marks archived
        data = it.load(project_root)
        data = it.mark_archived(data, "v2-multi-session")
        it.save(project_root, data)

        data = it.load(project_root)
        archived = it.list_archived(data)
        assert len(archived) == 1
        assert archived[0]["name"] == "v2-multi-session"
        assert archived[0]["status"] == "archived"
        assert archived[0]["archived_at"]

    def test_multiple_changes_independent_hooks(self, project_root):
        """Multiple changes can be in different lifecycle states simultaneously."""
        data = it.load(project_root)

        # Three changes at different stages
        data = it.add_or_update_change(data, name="c1", status="proposed", phase="v2.1", category="a")
        data = it.add_or_update_change(data, name="c2", status="in_worktree", phase="v2.1", category="b", tasks_done=2, tasks_total=5)
        data = it.mark_archived(it.add_or_update_change(data, name="c3", status="proposed"), "c3")
        it.save(project_root, data)

        data = it.load(project_root)
        assert len(data["changes"]) == 3
        assert len(it.list_active(data)) == 2
        assert len(it.list_archived(data)) == 1

    def test_added_at_preserved_across_lifecycle(self, project_root):
        """added_at must never be reset by updates (TDD contract)."""
        data = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        it.save(project_root, data)
        original = it.load(project_root)["changes"][0]["added_at"]

        # Multiple updates
        for status, done in [("in_worktree", 1), ("in_worktree", 2), ("completed", 3), ("in_worktree", 0)]:
            data = it.load(project_root)
            data = it.set_status(data, "c1", status)
            if done:
                data = it.set_tasks_done(data, "c1", done=done, total=5)
            it.save(project_root, data)
            data = it.load(project_root)
            assert data["changes"][0]["added_at"] == original, \
                f"added_at changed after status={status} done={done}"


# ---------------------------------------------------------------------------
# Deps-output.md parser (matches the regex used in deps.md Step 6 hook)
# ---------------------------------------------------------------------------

class TestDepsOutputParser:
    """Lock the behavior of the deps-output.md parser used by the deps hook."""

    def _parse(self, deps_output_text):
        """Inline copy of the parse logic from deps.md Step 6 hook.

        Kept in sync with the .md via this test. If deps.md regex changes,
        this test must change too.
        """
        changes_info = {}
        status_table = re.search(r'## Change 状态表\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)', deps_output_text)
        if status_table:
            rows = status_table.group(1).strip().split('\n')
            for idx, row in enumerate(rows):
                cells = [c.strip() for c in row.strip('|').split('|')]
                if len(cells) < 2:
                    continue
                name = cells[0]
                if not name or name == '—':
                    continue
                blocker = cells[2] if len(cells) > 2 and cells[2] not in ('—', '') else None
                changes_info[name] = {'blocker': blocker, 'group': idx}
        return changes_info

    def test_parses_blocked_change(self):
        md = """
## Change 状态表

| Change | 状态 | 阻塞于 | 阻塞了谁 | 冲突 | 置信度 | 推荐 |
|--------|------|--------|---------|------|--------|------|
| c1 | ✅ ready | — | c2 | — | 高 | 第 1 |
| c2 | ⚠️ blocked_by | c1 | — | — | 高 | 等 c1 完成后 |
"""
        result = self._parse(md)
        assert "c1" in result
        assert "c2" in result
        assert result["c1"]["blocker"] is None
        assert result["c2"]["blocker"] == "c1"
        assert result["c1"]["group"] == 0
        assert result["c2"]["group"] == 1

    def test_parses_only_dash_blocker(self):
        md = """
## Change 状态表

| Change | 状态 | 阻塞于 | 阻塞了谁 | 冲突 | 置信度 | 推荐 |
|--------|------|--------|---------|------|--------|------|
| c1 | ✅ ready | — | — | — | — | 第 1 |
"""
        result = self._parse(md)
        assert result["c1"]["blocker"] is None


# ---------------------------------------------------------------------------
# Roadmap update integration
# ---------------------------------------------------------------------------

class TestRoadmapIntegration:
    def test_full_roadmap_round_trip(self, project_root, roadmap_path):
        """The roadmap's AUTO-SPRINT block reflects iteration state changes."""
        data = it.add_or_update_change(it.create_empty("v2.1"), name="c1", status="proposed")
        it.save(project_root, data)

        # First update: appends block
        rs.update_roadmap(roadmap_path, data)
        with open(roadmap_path, encoding="utf-8") as f:
            content = f.read()
        assert "## v2.0 ✅" in content  # user content preserved
        assert "## v2.1 (当前)" in content
        assert rs.START_SENTINEL in content
        assert "c1" in content

        # Second update: changes a field, replaces block in place
        data = it.set_status(data, "c1", "in_worktree")
        data = it.set_tasks_done(data, "c1", done=2, total=5)
        it.save(project_root, data)
        rs.update_roadmap(roadmap_path, data)
        with open(roadmap_path, encoding="utf-8") as f:
            content = f.read()
        # No drift: exactly one pair of sentinels
        assert content.count(rs.START_SENTINEL) == 1
        assert content.count(rs.END_SENTINEL) == 1
        # Status changed
        assert "🔄 in_worktree" in content
        # Tasks updated
        assert "2/5" in content
        # User content still intact
        assert "## v3.0" in content
