"""Unit tests for skills/_lib/iteration.py — current sprint state manager.

TDD contract: these tests lock the behavior of every public function in
iteration.py. Hooks in propose.md, status.md, archive.sh, execute.md,
deps.md and roadmap.md all depend on this contract — changing iteration.py
without updating these tests means a breaking change for downstream hooks.
"""
import json
import os
import pytest

from skills._lib import iteration as it


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """A fresh project root with .rddf/state/ pre-created."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def iteration_path(project_root):
    """The canonical iteration.json path under a project_root."""
    return os.path.join(project_root, ".rddf", "state", "iteration.json")


# ---------------------------------------------------------------------------
# create_empty
# ---------------------------------------------------------------------------

class TestCreateEmpty:
    def test_default_phase(self):
        d = it.create_empty()
        assert d["current_phase"] == "default"
        assert d["version"] == 3
        assert d["changes"] == []
        assert "updated_at" in d

    def test_custom_phase(self):
        d = it.create_empty(current_phase="v2.1")
        assert d["current_phase"] == "v2.1"


# ---------------------------------------------------------------------------
# add_or_update_change
# ---------------------------------------------------------------------------

class TestAddOrUpdateChange:
    def test_add_new_change(self):
        d = it.create_empty("v2.1")
        d = it.add_or_update_change(
            d, name="v2-multi-session", status="proposed",
            phase="v2.1", category="session-mgmt", priority="P0",
        )
        assert len(d["changes"]) == 1
        c = d["changes"][0]
        assert c["name"] == "v2-multi-session"
        assert c["status"] == "proposed"
        assert c["phase"] == "v2.1"
        assert c["added_at"]  # ISO timestamp populated

    def test_update_preserves_added_at(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="c1", status="proposed")
        original_added_at = d["changes"][0]["added_at"]
        d = it.add_or_update_change(d, name="c1", status="in_worktree")
        assert d["changes"][0]["added_at"] == original_added_at  # NOT reset

    def test_update_does_not_drop_existing_fields(self):
        d = it.create_empty()
        d = it.add_or_update_change(
            d, name="c1", status="proposed",
            phase="v2.1", category="session-mgmt",
        )
        d = it.add_or_update_change(d, name="c1", status="in_worktree")
        # phase and category preserved
        assert d["changes"][0]["phase"] == "v2.1"
        assert d["changes"][0]["category"] == "session-mgmt"
        assert d["changes"][0]["status"] == "in_worktree"

    def test_rejects_invalid_status(self):
        d = it.create_empty()
        with pytest.raises(ValueError, match="invalid status"):
            it.add_or_update_change(d, name="c1", status="flying")

    def test_rejects_missing_name(self):
        d = it.create_empty()
        with pytest.raises(ValueError, match="requires 'name'"):
            it.add_or_update_change(d, status="proposed")

    def test_rejects_missing_status(self):
        d = it.create_empty()
        with pytest.raises(ValueError, match="requires 'status'"):
            it.add_or_update_change(d, name="c1")

    def test_does_not_mutate_input(self):
        d = it.create_empty()
        original_changes = d["changes"]
        it.add_or_update_change(d, name="c1", status="proposed")
        # Input unchanged (add_or_update_change returns a new dict)
        assert d["changes"] == original_changes
        assert len(d["changes"]) == 0


# ---------------------------------------------------------------------------
# set_status
# ---------------------------------------------------------------------------

class TestSetStatus:
    def test_creates_entry_if_missing(self):
        d = it.create_empty()
        d = it.set_status(d, "c1", "in_worktree")
        assert len(d["changes"]) == 1
        assert d["changes"][0]["status"] == "in_worktree"

    def test_updates_existing(self):
        d = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        d = it.set_status(d, "c1", "completed")
        assert d["changes"][0]["status"] == "completed"

    def test_rejects_invalid_status(self):
        d = it.create_empty()
        with pytest.raises(ValueError, match="invalid status"):
            it.set_status(d, "c1", "banana")


# ---------------------------------------------------------------------------
# set_tasks_done
# ---------------------------------------------------------------------------

class TestSetTasksDone:
    def test_updates_done_only(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="in_worktree",
        )
        d = it.set_tasks_done(d, "c1", done=3)
        assert d["changes"][0]["tasks_done"] == 3
        assert "tasks_total" not in d["changes"][0]  # unchanged

    def test_updates_done_and_total(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="in_worktree",
        )
        d = it.set_tasks_done(d, "c1", done=3, total=10)
        assert d["changes"][0]["tasks_done"] == 3
        assert d["changes"][0]["tasks_total"] == 10

    def test_preserves_status_as_in_worktree(self):
        """If a change has tasks_done, it must be in_worktree (not still proposed)."""
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        d = it.set_tasks_done(d, "c1", done=1)
        assert d["changes"][0]["status"] == "in_worktree"

    def test_rejects_negative(self):
        d = it.create_empty()
        with pytest.raises(ValueError, match=">= 0"):
            it.set_tasks_done(d, "c1", done=-1)
        with pytest.raises(ValueError, match=">= 0"):
            it.set_tasks_done(d, "c1", done=0, total=-1)


# ---------------------------------------------------------------------------
# set_deps_info
# ---------------------------------------------------------------------------

class TestSetDepsInfo:
    def test_preserves_status_for_existing_change(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="in_worktree",
        )
        d = it.set_deps_info(d, "c1", blocker="c2", parallel_group=1)
        assert d["changes"][0]["status"] == "in_worktree"  # NOT downgraded to proposed
        assert d["changes"][0]["blocker"] == "c2"
        assert d["changes"][0]["parallel_group"] == 1
        assert d["changes"][0]["last_deps_at"]

    def test_creates_entry_with_proposed_if_missing(self):
        d = it.create_empty()
        d = it.set_deps_info(d, "c1", blocker=None, parallel_group=0, conflicts=[])
        assert d["changes"][0]["status"] == "proposed"

    def test_records_conflicts(self):
        d = it.create_empty()
        d = it.set_deps_info(d, "c1", conflicts=["c2", "c3"])
        assert d["changes"][0]["conflicts"] == ["c2", "c3"]

    def test_explicit_none_clears_blocker(self):
        """set_deps_info(..., blocker=None) explicitly clears a previously-recorded blocker.

        The contract changed in v2.0.1: callers use the _UNSET sentinel
        to leave a field untouched, and pass None to clear it. This
        matches deps semantics where a fresh run always knows the full
        blocker state for each change.
        """
        from skills._lib.iteration import _UNSET
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        d = it.set_deps_info(d, "c1", blocker="c2", parallel_group=1)
        assert d["changes"][0]["blocker"] == "c2"
        d = it.set_deps_info(d, "c1", blocker=None, parallel_group=2)
        # blocker explicitly cleared
        assert d["changes"][0]["blocker"] is None
        # parallel_group updated
        assert d["changes"][0]["parallel_group"] == 2

    def test_unset_argument_preserves_existing(self):
        """Omitting an argument (default _UNSET) leaves the existing value untouched."""
        from skills._lib.iteration import _UNSET
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        d = it.set_deps_info(d, "c1", blocker="c2", parallel_group=1, conflicts=["c3"])
        d = it.set_deps_info(d, "c1", parallel_group=2)  # only update parallel_group
        # blocker preserved
        assert d["changes"][0]["blocker"] == "c2"
        # conflicts preserved
        assert d["changes"][0]["conflicts"] == ["c3"]
        # parallel_group updated
        assert d["changes"][0]["parallel_group"] == 2


# ---------------------------------------------------------------------------
# mark_archived
# ---------------------------------------------------------------------------

class TestMarkArchived:
    def test_sets_status_and_timestamp(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="in_worktree",
        )
        d = it.mark_archived(d, "c1")
        assert d["changes"][0]["status"] == "archived"
        assert d["changes"][0]["archived_at"]


# ---------------------------------------------------------------------------
# remove_change
# ---------------------------------------------------------------------------

class TestRemoveChange:
    def test_removes_existing(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        d = it.add_or_update_change(d, name="c2", status="proposed")
        d = it.remove_change(d, "c1")
        assert len(d["changes"]) == 1
        assert d["changes"][0]["name"] == "c2"

    def test_safe_to_remove_nonexistent(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        d = it.remove_change(d, "ghost")
        assert len(d["changes"]) == 1


# ---------------------------------------------------------------------------
# set_current_phase
# ---------------------------------------------------------------------------

class TestSetCurrentPhase:
    def test_updates_phase(self):
        d = it.create_empty("v2.0")
        d = it.set_current_phase(d, "v2.1")
        assert d["current_phase"] == "v2.1"


# ---------------------------------------------------------------------------
# get_change
# ---------------------------------------------------------------------------

class TestGetChange:
    def test_returns_existing(self):
        d = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        c = it.get_change(d, "c1")
        assert c is not None
        assert c["name"] == "c1"

    def test_returns_none_for_missing(self):
        d = it.create_empty()
        assert it.get_change(d, "ghost") is None


# ---------------------------------------------------------------------------
# list_active / list_archived
# ---------------------------------------------------------------------------

class TestListActive:
    def test_excludes_archived(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="c1", status="proposed")
        d = it.add_or_update_change(d, name="c2", status="in_worktree")
        d = it.add_or_update_change(d, name="c3", status="completed")
        d = it.add_or_update_change(d, name="c4", status="archived")
        active = it.list_active(d)
        names = [c["name"] for c in active]
        assert sorted(names) == ["c1", "c2", "c3"]


class TestListArchived:
    def test_returns_only_archived(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="c1", status="proposed")
        d = it.add_or_update_change(d, name="c2", status="archived")
        archived = it.list_archived(d)
        assert len(archived) == 1
        assert archived[0]["name"] == "c2"

    def test_sorted_most_recent_first(self):
        d = it.create_empty()
        d = it.mark_archived(it.add_or_update_change(d, name="c1", status="proposed"), "c1")
        d = it.mark_archived(it.add_or_update_change(d, name="c2", status="proposed"), "c2")
        archived = it.list_archived(d)
        # c2 was archived after c1, so it comes first
        assert archived[0]["name"] == "c2"
        assert archived[1]["name"] == "c1"


# ---------------------------------------------------------------------------
# Queue management helpers: list_planned / list_ready_for_fill /
# list_ready_for_ship / list_blocked
# ---------------------------------------------------------------------------

class TestListPlanned:
    def test_empty_input(self):
        d = it.create_empty()
        assert it.list_planned(d) == []

    def test_all_planned(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="a", status="planned")
        d = it.add_or_update_change(d, name="b", status="planned")
        d = it.add_or_update_change(d, name="c", status="planned")
        out = it.list_planned(d)
        assert len(out) == 3
        assert {c["name"] for c in out} == {"a", "b", "c"}

    def test_mixed_statuses(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="p1", status="planned")
        d = it.add_or_update_change(d, name="p2", status="planned")
        d = it.add_or_update_change(d, name="pr1", status="proposed")
        d = it.add_or_update_change(d, name="ar1", status="archived")
        out = it.list_planned(d)
        assert len(out) == 2
        assert {c["name"] for c in out} == {"p1", "p2"}


class TestListReadyForFill:
    def test_planned_no_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="p1", status="planned")
        out = it.list_ready_for_fill(d)
        assert {c["name"] for c in out} == {"p1"}

    def test_planned_with_archived_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="archived")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_ready_for_fill(d)
        assert {c["name"] for c in out} == {"p1"}

    def test_planned_with_completed_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="completed")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_ready_for_fill(d)
        assert {c["name"] for c in out} == {"p1"}

    def test_planned_with_in_worktree_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="in_worktree")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_ready_for_fill(d)
        assert out == []

    def test_planned_with_planned_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="planned")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_ready_for_fill(d)
        assert {c["name"] for c in out} == {"blocker"}

    def test_planned_with_review_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="review")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_ready_for_fill(d)
        assert out == []

    def test_proposed_excluded_even_without_blocker(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="pr1", status="proposed")
        out = it.list_ready_for_fill(d)
        assert out == []

    def test_blocker_name_does_not_exist_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="ghost")
        out = it.list_ready_for_fill(d)
        assert {c["name"] for c in out} == {"p1"}


class TestListReadyForShip:
    def test_proposed_no_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="pr1", status="proposed")
        out = it.list_ready_for_ship(d)
        assert {c["name"] for c in out} == {"pr1"}

    def test_proposed_with_archived_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="archived")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_ready_for_ship(d)
        assert {c["name"] for c in out} == {"pr1"}

    def test_proposed_with_completed_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="completed")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_ready_for_ship(d)
        assert {c["name"] for c in out} == {"pr1"}

    def test_proposed_with_in_worktree_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="in_worktree")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_ready_for_ship(d)
        assert out == []

    def test_proposed_with_planned_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="planned")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_ready_for_ship(d)
        assert out == []

    def test_proposed_with_review_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="review")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_ready_for_ship(d)
        assert out == []

    def test_planned_excluded_even_without_blocker(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="p1", status="planned")
        out = it.list_ready_for_ship(d)
        assert out == []

    def test_in_worktree_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="w1", status="in_worktree")
        out = it.list_ready_for_ship(d)
        assert out == []


class TestListBlocked:
    def test_proposed_with_in_worktree_blocker_in_result(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="in_worktree")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_blocked(d)
        assert {c["name"] for c in out} == {"pr1"}

    def test_proposed_with_proposed_blocker_excluded(self):
        # Per design: "proposed" means "ready to ship" — not actively blocking.
        # _BLOCKING_STATUSES = (planned, in_worktree, review) excludes proposed.
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="proposed")
        d = it.add_or_update_change(d, name="p1", status="planned", blocker="blocker")
        out = it.list_blocked(d)
        assert out == []

    def test_proposed_with_archived_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="archived")
        d = it.add_or_update_change(d, name="pr1", status="proposed", blocker="blocker")
        out = it.list_blocked(d)
        assert out == []

    def test_proposed_no_blocker_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="pr1", status="proposed")
        out = it.list_blocked(d)
        assert out == []

    def test_in_worktree_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="w1", status="in_worktree")
        out = it.list_blocked(d)
        assert out == []

    def test_archived_excluded(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="blocker", status="in_worktree")
        d = it.add_or_update_change(d, name="a1", status="archived", blocker="blocker")
        out = it.list_blocked(d)
        assert out == []


# ---------------------------------------------------------------------------
# Feature grouping: derive_feature_name / list_feature_groups / feature_progress
# ---------------------------------------------------------------------------

class TestDeriveFeatureName:
    def test_feature_with_sub(self):
        assert it.derive_feature_name("feature-stream-core") == "feature-stream"

    def test_feature_single(self):
        assert it.derive_feature_name("feature-stream") == "feature-stream"

    def test_no_feature_prefix(self):
        assert it.derive_feature_name("debt-cleanup-foo") == "debt-cleanup-foo"

    def test_fix_prefix(self):
        assert it.derive_feature_name("fix-bug-123") == "fix-bug-123"

    def test_empty_string(self):
        assert it.derive_feature_name("") == ""

    def test_prefix_in_name_but_not_at_start(self):
        assert it.derive_feature_name("v2-multi-session") == "v2-multi-session"

    def test_parent_feature_field_overrides_name(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="my-change", status="proposed", parent_feature="feature-stream")
        assert it.derive_feature_name("my-change", d) == "feature-stream"

    def test_parent_feature_field_without_data_uses_name(self):
        assert it.derive_feature_name("my-change") == "my-change"

    def test_parent_feature_field_empty_uses_name(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="my-change", status="proposed")
        assert it.derive_feature_name("my-change", d) == "my-change"

    def test_parent_feature_field_none_uses_name(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="my-change", status="proposed", parent_feature=None)
        assert it.derive_feature_name("my-change", d) == "my-change"


class TestListFeatureGroups:
    def test_empty_data(self):
        d = it.create_empty()
        assert it.list_feature_groups(d) == {}

    def test_same_feature_grouped(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="archived")
        d = it.add_or_update_change(d, name="feature-stream-adapters", status="in_worktree")
        d = it.add_or_update_change(d, name="feature-stream-tests", status="planned")
        groups = it.list_feature_groups(d)
        assert set(groups.keys()) == {"feature-stream"}
        assert len(groups["feature-stream"]) == 3

    def test_parent_feature_field_overrides_name_prefix(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="odd-name", status="proposed", parent_feature="feature-stream")
        d = it.add_or_update_change(d, name="also-odd", status="proposed", parent_feature="feature-stream")
        groups = it.list_feature_groups(d)
        # parent_feature overrides name-prefix derivation
        assert set(groups.keys()) == {"feature-stream"}
        assert len(groups["feature-stream"]) == 2

    def test_mixed_features_and_standalone(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="archived")
        d = it.add_or_update_change(d, name="feature-cdc-scan", status="planned")
        d = it.add_or_update_change(d, name="fix-bug-123", status="proposed")
        groups = it.list_feature_groups(d)
        assert set(groups.keys()) == {"feature-stream", "feature-cdc", "fix-bug-123"}
        assert len(groups["feature-stream"]) == 1
        assert len(groups["fix-bug-123"]) == 1

    def test_non_feature_prefix_maps_to_own_name(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="fix-a", status="proposed")
        d = it.add_or_update_change(d, name="fix-b", status="proposed")
        groups = it.list_feature_groups(d)
        # Each non-feature change is its own group
        assert len(groups) == 2
        assert "fix-a" in groups
        assert "fix-b" in groups


class TestFeatureProgress:
    def test_empty_data(self):
        d = it.create_empty()
        assert it.feature_progress(d) == {}

    def test_all_archived(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="archived")
        d = it.add_or_update_change(d, name="feature-stream-adapters", status="archived")
        d = it.add_or_update_change(d, name="feature-stream-tests", status="archived")
        progress = it.feature_progress(d)
        assert progress["feature-stream"] == (3, 3)

    def test_partial_archived(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="archived")
        d = it.add_or_update_change(d, name="feature-stream-adapters", status="in_worktree")
        d = it.add_or_update_change(d, name="feature-stream-tests", status="planned")
        progress = it.feature_progress(d)
        assert progress["feature-stream"] == (1, 3)

    def test_completed_does_not_count_as_done(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="completed")
        d = it.add_or_update_change(d, name="feature-stream-adapters", status="archived")
        progress = it.feature_progress(d)
        # completed is a transitional state, only archived counts
        assert progress["feature-stream"] == (1, 2)

    def test_mixed_features(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="feature-stream-core", status="archived")
        d = it.add_or_update_change(d, name="feature-stream-adapters", status="in_worktree")
        d = it.add_or_update_change(d, name="feature-cdc-scan", status="archived")
        d = it.add_or_update_change(d, name="feature-cdc-impl", status="archived")
        d = it.add_or_update_change(d, name="fix-bug-123", status="archived")
        progress = it.feature_progress(d)
        assert progress["feature-stream"] == (1, 2)
        assert progress["feature-cdc"] == (2, 2)
        assert progress["fix-bug-123"] == (1, 1)

    def test_parent_feature_field_in_progress(self):
        d = it.create_empty()
        d = it.add_or_update_change(d, name="odd-core", status="archived", parent_feature="feature-stream")
        d = it.add_or_update_change(d, name="odd-adapters", status="in_worktree", parent_feature="feature-stream")
        progress = it.feature_progress(d)
        assert progress["feature-stream"] == (1, 2)


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_save_creates_file(self, project_root, iteration_path):
        d = it.create_empty("v2.1")
        it.save(project_root, d)
        assert os.path.isfile(iteration_path)

    def test_load_returns_empty_when_missing(self, project_root):
        d = it.load(project_root)
        # Compare structurally (ignore updated_at which is wall-clock-dependent)
        assert d["version"] == 3
        assert d["current_phase"] == "default"
        assert d["changes"] == []
        # Note: load does NOT create the file
        assert not os.path.isfile(os.path.join(project_root, ".rddf", "state", "iteration.json"))

    def test_roundtrip_preserves_data(self, project_root):
        d = it.create_empty("v2.1")
        d = it.add_or_update_change(
            d, name="c1", status="in_worktree",
            phase="v2.1", category="session-mgmt", priority="P0",
            tasks_done=2, tasks_total=5, blocker="c0", parallel_group=2,
            conflicts=["c2"],
        )
        it.save(project_root, d)
        loaded = it.load(project_root)
        assert loaded["current_phase"] == "v2.1"
        c = loaded["changes"][0]
        assert c["name"] == "c1"
        assert c["status"] == "in_worktree"
        assert c["phase"] == "v2.1"
        assert c["category"] == "session-mgmt"
        assert c["priority"] == "P0"
        assert c["tasks_done"] == 2
        assert c["tasks_total"] == 5
        assert c["blocker"] == "c0"
        assert c["parallel_group"] == 2
        assert c["conflicts"] == ["c2"]

    def test_save_updates_updated_at(self, project_root):
        d = it.create_empty("v2.1")
        it.save(project_root, d)
        original_updated_at = d["updated_at"]
        # Mutate and save again
        d2 = it.add_or_update_change(d, name="c1", status="proposed")
        # add_or_update_change does NOT touch updated_at (that's save's job)
        assert d2["updated_at"] == original_updated_at
        it.save(project_root, d2)
        loaded = it.load(project_root)
        # save() set a new updated_at
        assert loaded["updated_at"] >= original_updated_at

    def test_save_rejects_invalid_data(self, project_root):
        d = {"version": 1, "changes": "not a list"}  # schema-invalid
        with pytest.raises(Exception):  # jsonschema.ValidationError
            it.save(project_root, d)

    def test_load_returns_empty_on_corrupt_json(self, project_root, iteration_path):
        with open(iteration_path, "w") as f:
            f.write("{ this is not valid json")
        d = it.load(project_root)
        # load returns empty state on corruption
        assert d["version"] == 3
        assert d["changes"] == []

    def test_load_returns_empty_on_schema_violation(self, project_root, iteration_path):
        with open(iteration_path, "w") as f:
            json.dump({"version": 999, "changes": []}, f)  # version: 999 violates const: 3
        d = it.load(project_root)
        assert d["version"] == 3  # falls back to default
        assert d["changes"] == []

    def test_atomic_write_does_not_leave_tmp(self, project_root, iteration_path):
        d = it.create_empty("v2.1")
        it.save(project_root, d)
        assert not os.path.exists(iteration_path + ".tmp")


# ---------------------------------------------------------------------------
# Corruption backup (M3 fix)
# ---------------------------------------------------------------------------

class TestCorruptionBackup:
    """When iteration.json is unreadable (corrupt JSON or schema violation),
    load() must copy the bad file aside before returning empty state. The
    backup gives the user a recovery path (they can inspect the corrupt
    file to recover change history) without preventing the hooks from
    proceeding with a fresh empty state.

    Before the M3 fix, the corrupt file was silently overwritten on the
    next save, permanently destroying history."""

    def _backup_files(self, state_dir):
        """Helper: return list of corrupt-backup files in state_dir."""
        return [
            f for f in os.listdir(state_dir)
            if ".corrupt." in f and f != "iteration.json"
        ]

    def test_corrupt_json_triggers_backup(self, project_root, iteration_path):
        original_content = "{ this is not valid json"
        with open(iteration_path, "w") as f:
            f.write(original_content)
        it.load(project_root)  # triggers detection + backup

        # A backup file should exist alongside iteration.json
        state_dir = os.path.dirname(iteration_path)
        backups = self._backup_files(state_dir)
        assert len(backups) >= 1, f"expected a corrupt backup, got: {os.listdir(state_dir)}"
        # The backup content matches the original corrupt content
        with open(os.path.join(state_dir, backups[0]), encoding="utf-8") as f:
            assert f.read() == original_content

    def test_schema_violation_triggers_backup(self, project_root, iteration_path):
        original_content = json.dumps({"version": 999, "changes": []})
        with open(iteration_path, "w") as f:
            f.write(original_content)
        it.load(project_root)

        state_dir = os.path.dirname(iteration_path)
        backups = self._backup_files(state_dir)
        assert len(backups) >= 1
        with open(os.path.join(state_dir, backups[0]), encoding="utf-8") as f:
            assert f.read() == original_content

    def test_valid_file_does_not_trigger_backup(self, project_root, iteration_path):
        """A normal valid iteration.json must NOT create a corrupt backup."""
        d = it.create_empty("v2.1")
        d = it.add_or_update_change(d, name="c1", status="proposed")
        it.save(project_root, d)
        it.load(project_root)  # valid load, no backup expected

        state_dir = os.path.dirname(iteration_path)
        backups = self._backup_files(state_dir)
        assert backups == []

    def test_missing_file_does_not_trigger_backup(self, project_root):
        """No file = no backup (nothing to back up)."""
        it.load(project_root)
        state_dir = os.path.join(project_root, ".rddf", "state")
        backups = self._backup_files(state_dir)
        assert backups == []

    def test_backup_filename_includes_timestamp(self, project_root, iteration_path):
        """Backup filenames must include a timestamp suffix.

        The format is `iteration.corrupt.<timestamp>` (microsecond
        precision) so multiple corruption events don't overwrite each
        other. We just check the suffix pattern exists.
        """
        with open(iteration_path, "w") as f:
            f.write("{ not json")
        it.load(project_root)

        state_dir = os.path.dirname(iteration_path)
        backups = self._backup_files(state_dir)
        assert len(backups) >= 1
        # Pattern: <basename>.corrupt.<ISO-like timestamp>
        import re
        assert re.search(r"\.corrupt\.\d{8}T\d{6}\d{6}$", backups[0]), \
            f"backup filename lacks timestamp suffix: {backups[0]}"

    def test_save_after_corrupt_replaces_iteration(self, project_root, iteration_path):
        """After corruption + load (which backs up), save() writes fresh
        iteration.json. The original corrupt content is gone from
        iteration.json but preserved in the backup.
        """
        with open(iteration_path, "w") as f:
            f.write("{ corrupt }")
        it.load(project_root)

        # Save fresh state
        d = it.create_empty("v2.1")
        d = it.add_or_update_change(d, name="c-new", status="proposed")
        it.save(project_root, d)

        # iteration.json now has fresh content
        with open(iteration_path, encoding="utf-8") as f:
            assert "c-new" in f.read()
            assert "{ corrupt }" not in f.read()
        # Backup preserves the old corrupt content
        state_dir = os.path.dirname(iteration_path)
        backups = self._backup_files(state_dir)
        assert len(backups) >= 1


# ---------------------------------------------------------------------------
# End-to-end lifecycle (the actual hook contract)
# ---------------------------------------------------------------------------

class TestLifecycle:
    """Simulate the full propose → guide-ship → execute → archive flow."""

    def test_propose_then_ship_then_archive(self, project_root):
        # 1. propose hook
        d = it.load(project_root)
        d = it.add_or_update_change(
            d, name="v2-multi-session", status="proposed",
            phase="v2.1", category="session-mgmt", priority="P0",
        )
        it.save(project_root, d)

        # 2. guide-ship creates worktree
        d = it.load(project_root)
        d = it.set_status(d, "v2-multi-session", "in_worktree")
        d = it.add_or_update_change(
            d, name="v2-multi-session", status="in_worktree",
            worktree_path=".rddf/wt/v2-multi-session",
            plan_path=".rddf/plans/v2-multi-session.md",
            tasks_total=5,
        )
        it.save(project_root, d)

        # 3. execute makes progress
        d = it.load(project_root)
        d = it.set_tasks_done(d, "v2-multi-session", done=3, total=5)
        it.save(project_root, d)

        # 4. archive
        d = it.load(project_root)
        d = it.mark_archived(d, "v2-multi-session")
        it.save(project_root, d)

        # Final state
        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["name"] == "v2-multi-session"
        assert c["status"] == "archived"
        assert c["phase"] == "v2.1"
        assert c["tasks_done"] == 3
        assert c["tasks_total"] == 5
        assert c["worktree_path"] == ".rddf/wt/v2-multi-session"
        assert c["plan_path"] == ".rddf/plans/v2-multi-session.md"
        assert c["archived_at"]
        # Original added_at preserved across the full lifecycle
        assert c["added_at"]
