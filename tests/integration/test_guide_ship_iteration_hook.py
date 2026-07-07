"""Integration test: guide-ship Phase 1 hook updates iteration.json.

guide-ship.md is a markdown documentation file (not directly executed).
This test exercises the Python hook BODY that the markdown describes,
proving the contract: after a worktree is created and a plan is
generated, the iteration.json entry transitions from "proposed" to
"in_worktree" with worktree_path + plan_path + tasks_total populated.

To avoid coupling to the markdown source, we replicate the hook's
Python body in pure Python here. If the markdown diverges from this
test, the contract is broken — fix one or the other.
"""
import os
import sys
import json
import pytest

from skills._lib import iteration as it


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "plans").mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def plan_file(project_root):
    """Create a fake plan file matching the contract."""
    p = os.path.join(project_root, ".rddf", "plans", "v2-multi-session.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("# Plan\n\n### Task 1\n- [ ] step a\n- [ ] step b\n### Task 2\n- [ ] step c\n")
    return p


# ---------------------------------------------------------------------------
# The hook (replicated from guide-ship.md Phase 1)
# ---------------------------------------------------------------------------

def _guide_ship_phase1_hook(
    project_root: str,
    change_name: str,
    mode: str,
    wt_path: str,
    plan_step_count: int,
) -> None:
    """Replicate the Python body of the guide-ship Phase 1 hook.

    The original is embedded in a python3 -c "..." block inside
    guide-ship.md. We test the Python code directly so a markdown
    typo won't silently break the contract.
    """
    from skills._lib import iteration as it_mod  # mirror the import
    data = it_mod.load(project_root)
    kwargs = {
        "name": change_name,
        "status": "in_worktree",
        "plan_path": f".rddf/plans/{change_name}.md",
        "tasks_total": int(plan_step_count or 0),
    }
    if mode == "worktree" and wt_path:
        kwargs["worktree_path"] = f".rddf/wt/{change_name}"
    data = it_mod.add_or_update_change(data, **kwargs)
    it_mod.save(project_root, data)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGuideShipPhase1Hook:
    def test_worktree_mode_sets_all_fields(self, project_root, plan_file):
        # Seed: change is in proposed state
        data = it.add_or_update_change(
            it.create_empty("v2.1"), name="v2-multi-session", status="proposed",
            phase="v2.1", category="session-mgmt", priority="P0",
        )
        it.save(project_root, data)

        _guide_ship_phase1_hook(
            project_root=project_root,
            change_name="v2-multi-session",
            mode="worktree",
            wt_path="/tmp/test/.rddf/wt/v2-multi-session",
            plan_step_count=3,
        )

        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["name"] == "v2-multi-session"
        assert c["status"] == "in_worktree"
        assert c["worktree_path"] == ".rddf/wt/v2-multi-session"
        assert c["plan_path"] == ".rddf/plans/v2-multi-session.md"
        assert c["tasks_total"] == 3
        # phase/category preserved from the propose entry
        assert c["phase"] == "v2.1"
        assert c["category"] == "session-mgmt"
        # added_at preserved (not reset by this hook)
        assert c["added_at"]

    def test_lightweight_mode_omits_worktree_path(self, project_root, plan_file):
        data = it.add_or_update_change(
            it.create_empty("v2.1"), name="v2-multi-session", status="proposed",
        )
        it.save(project_root, data)

        _guide_ship_phase1_hook(
            project_root=project_root,
            change_name="v2-multi-session",
            mode="lightweight",
            wt_path="",  # no worktree
            plan_step_count=5,
        )

        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["status"] == "in_worktree"
        # worktree_path must NOT be set in lightweight mode
        assert "worktree_path" not in c or c.get("worktree_path") is None
        # But plan_path still recorded
        assert c["plan_path"] == ".rddf/plans/v2-multi-session.md"
        assert c["tasks_total"] == 5

    def test_zero_tasks_still_records(self, project_root, plan_file):
        """Edge case: plan file present but contains 0 steps (corrupt)."""
        data = it.add_or_update_change(
            it.create_empty(), name="empty-change", status="proposed",
        )
        it.save(project_root, data)

        _guide_ship_phase1_hook(
            project_root=project_root,
            change_name="empty-change",
            mode="worktree",
            wt_path="/tmp/wt",
            plan_step_count=0,
        )

        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["tasks_total"] == 0
        assert c["status"] == "in_worktree"

    def test_hook_creates_entry_if_missing(self, project_root, plan_file):
        """If the change was never proposed (edge case), hook still works."""
        _guide_ship_phase1_hook(
            project_root=project_root,
            change_name="orphan-change",
            mode="worktree",
            wt_path="/tmp/wt",
            plan_step_count=2,
        )
        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "orphan-change" in names
        c = loaded["changes"][0]
        assert c["status"] == "in_worktree"

    def test_full_lifecycle_with_all_hooks(self, project_root, plan_file):
        """End-to-end: propose → ship → execute → archive, all hooks fired."""
        # 1. propose hook
        data = it.load(project_root)
        data = it.add_or_update_change(
            data, name="c1", status="proposed",
            phase="v2.1", category="test", priority="P0",
        )
        it.save(project_root, data)

        # 2. guide-ship Phase 1 hook
        _guide_ship_phase1_hook(project_root, "c1", "worktree", "/tmp/wt/c1", 5)

        # 3. execute hook (manual call simulating task completions)
        data = it.load(project_root)
        data = it.set_tasks_done(data, "c1", done=2, total=5)
        it.save(project_root, data)

        # 4. archive hook
        data = it.load(project_root)
        data = it.mark_archived(data, "c1")
        it.save(project_root, data)

        # Final state
        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["status"] == "archived"
        assert c["phase"] == "v2.1"
        assert c["category"] == "test"
        assert c["worktree_path"] == ".rddf/wt/c1"
        assert c["plan_path"] == ".rddf/plans/c1.md"
        assert c["tasks_done"] == 2
        assert c["tasks_total"] == 5
        assert c["archived_at"]
        # added_at preserved across all 4 transitions
        assert c["added_at"]
