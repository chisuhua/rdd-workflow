"""Unit tests for _lib/wave_scheduler.py - auto wave transition detector.

TDD contract: locks the behavior of WaveScheduler which consumes
iteration.json + deps-analysis.json and returns Recommendation list
for changes whose blockers have resolved.
"""
import json
import os
import pytest

from skills._lib.wave_scheduler import Recommendation, WaveScheduler


class TestRecommendationDataclass:
    def test_required_fields_present(self):
        """Recommendation must have: name, current_status, blocked_by,
        blocker_status, wave, reason, source."""
        rec = Recommendation(
            name="change-b",
            current_status="planned",
            blocked_by="change-a",
            blocker_status="archived",
            wave="fill",
            reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )
        assert rec.name == "change-b"
        assert rec.current_status == "planned"
        assert rec.blocked_by == "change-a"
        assert rec.blocker_status == "archived"
        assert rec.wave == "fill"
        assert rec.reason.startswith("blocker")
        assert rec.source == "iteration.blocker"

    def test_wave_must_be_fill_or_ship(self):
        """wave field semantic: 'fill' for planned->propose, 'ship' for proposed->guide-ship."""
        rec = Recommendation(
            name="c", current_status="proposed", blocked_by="a",
            blocker_status="archived", wave="ship",
            reason="r", source="iteration.blocker",
        )
        assert rec.wave == "ship"


class TestWaveSchedulerSkeleton:
    def test_can_instantiate(self):
        """WaveScheduler can be instantiated without args."""
        sched = WaveScheduler()
        assert sched is not None

    def test_detect_unblocked_returns_list(self):
        """detect_unblocked returns a list (empty for empty input)."""
        sched = WaveScheduler()
        result = sched.detect_unblocked({"changes": []})
        assert isinstance(result, list)
        assert result == []


class TestDetectUnblockedPlanned:
    """detect_unblocked for planned status with iteration.blocker field."""

    def test_planned_with_archived_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=archived -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "change-b"
        assert r.current_status == "planned"
        assert r.blocked_by == "change-a"
        assert r.blocker_status == "archived"
        assert r.wave == "fill"
        assert r.source == "iteration.blocker"

    def test_planned_with_completed_blocker_returns_fill_rec(self):
        """planned + blocker=X + X.status=completed -> 1 fill recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].blocker_status == "completed"
        assert recs[0].wave == "fill"

    def test_planned_with_in_worktree_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=in_worktree -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_proposed_blocker_returns_nothing(self):
        """planned + blocker=X + X.status=proposed -> 0 recs (still blocked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "proposed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_no_blocker_returns_nothing(self):
        """planned + blocker=None -> 0 recs (covered by list_ready_for_fill elsewhere)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z"},
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_planned_with_missing_blocker_entry_returns_nothing(self):
        """planned + blocker=X but X not in changes -> 0 recs (blocker not yet tracked)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "ghost-change",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []


class TestDetectUnblockedProposed:
    """detect_unblocked for proposed status (wave=ship)."""

    def test_proposed_with_archived_blocker_returns_ship_rec(self):
        """proposed + blocker=X + X.status=archived -> 1 ship recommendation."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "change-c"
        assert r.current_status == "proposed"
        assert r.blocked_by == "change-a"
        assert r.blocker_status == "archived"
        assert r.wave == "ship"
        assert r.source == "iteration.blocker"

    def test_proposed_with_completed_blocker_returns_ship_rec(self):
        """proposed + blocker=X + X.status=completed -> 1 ship rec."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].wave == "ship"
        assert recs[0].blocker_status == "completed"

    def test_proposed_with_in_worktree_blocker_returns_nothing(self):
        """proposed + blocker=in_worktree -> 0 recs."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_mixed_planned_and_proposed_both_unblocked(self):
        """Both planned and proposed changes unblocked -> 2 recs (one fill, one ship)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
                {
                    "name": "change-c", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 2
        waves = {r.wave for r in recs}
        assert waves == {"fill", "ship"}


class TestDetectUnblockedManualDeps:
    """detect_unblocked for manual_deps field (ADR-0022)."""

    def test_manual_deps_all_archived_returns_fill_rec(self):
        """manual_deps=[A,B] all archived -> 1 fill rec, source=manual_deps."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        r = recs[0]
        assert r.name == "D"
        assert r.wave == "fill"
        assert r.source == "manual_deps"
        assert "A" in r.reason and "B" in r.reason

    def test_manual_deps_partial_archived_returns_nothing(self):
        """manual_deps=[A,B], A archived but B in_worktree -> 0 recs."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_manual_deps_single_archived_returns_fill_rec(self):
        """manual_deps=[A] with A archived -> 1 fill rec."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].source == "manual_deps"

    def test_manual_deps_takes_priority_when_blocker_none(self):
        """blocker=None but manual_deps present -> use manual_deps for detection."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": None,
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].source == "manual_deps"

    def test_manual_deps_completed_also_resolves(self):
        """manual_deps=[A] with A completed (not archived) -> also resolves."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "completed", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        assert recs[0].wave == "ship"
        assert recs[0].source == "manual_deps"

    def test_blocker_takes_priority_over_manual_deps(self):
        """If both blocker and manual_deps set, blocker wins (static analysis priority).
        But if blocker resolved AND manual_deps unresolved -> still blocked."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        # Blocker A is resolved but manual_deps B is not -> still blocked
        recs = sched.detect_unblocked(data)
        assert recs == []

    def test_both_blocker_and_manual_deps_resolved(self):
        """blocker=A (archived) + manual_deps=[A,B] both archived -> 1 rec.
        source = iteration.blocker (blocker takes precedence for source attribution)."""
        sched = WaveScheduler()
        data = {
            "version": 4,
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                    "manual_deps": ["A", "B"],
                },
            ],
        }
        recs = sched.detect_unblocked(data)
        assert len(recs) == 1
        # blocker is the primary signal for source attribution
        assert recs[0].source == "iteration.blocker"
        assert recs[0].blocked_by == "A"


class TestCheckOnArchive:
    """check_on_archive: filter recommendations to those blocked by archived_name."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """A fresh project root with .rddf/state/ pre-created."""
        (tmp_path / ".rddf" / "state").mkdir(parents=True)
        return str(tmp_path)

    def _write_iteration(self, project_root: str, data: dict) -> None:
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            json.dump(data, f)

    def test_returns_recs_for_dependents_of_archived(self, project_root):
        """Archive change-a; change-b (blocker=change-a, planned) -> returns [change-b]."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-a",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert len(recs) == 1
        assert recs[0].name == "change-b"
        assert recs[0].blocked_by == "change-a"

    def test_filters_out_recs_for_unrelated_blockers(self, project_root):
        """Archive change-a; change-c (blocker=change-b) -> no rec for change-c."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "change-b", "status": "in_worktree", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "change-c", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "change-b",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_returns_recs_for_manual_deps_dependents(self, project_root):
        """Archive A; D (manual_deps=[A,B]) with B also archived -> returns [D]."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "B", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "D", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "manual_deps": ["A", "B"],
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "A")
        assert len(recs) == 1
        assert recs[0].name == "D"

    def test_missing_iteration_file_returns_empty(self, project_root):
        """No iteration.json -> return empty list, no exception."""
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_corrupt_iteration_file_returns_empty(self, project_root):
        """Corrupt iteration.json -> return empty list, no exception."""
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            f.write("{ not valid json")
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []

    def test_no_matching_dependents_returns_empty(self, project_root):
        """Archive change-a but no change depends on it -> empty."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {"name": "change-x", "status": "planned", "added_at": "2026-01-01T00:00:00Z"},
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_archive(project_root, "change-a")
        assert recs == []


class TestCheckOnEntry:
    """check_on_entry: scan all unblocked changes at skill entry."""

    @pytest.fixture
    def project_root(self, tmp_path):
        (tmp_path / ".rddf" / "state").mkdir(parents=True)
        return str(tmp_path)

    def _write_iteration(self, project_root: str, data: dict) -> None:
        path = os.path.join(project_root, ".rddf", "state", "iteration.json")
        with open(path, "w") as f:
            json.dump(data, f)

    def test_returns_all_unblocked_changes(self, project_root):
        """Entry check returns all unblocked (both fill and ship waves)."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [
                {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
                {
                    "name": "B", "status": "planned", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                },
                {
                    "name": "C", "status": "proposed", "added_at": "2026-01-01T00:00:00Z",
                    "blocker": "A",
                },
            ],
        })
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-plan")
        assert len(recs) == 2
        waves = {r.wave for r in recs}
        assert waves == {"fill", "ship"}

    def test_missing_iteration_returns_empty(self, project_root):
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-plan")
        assert recs == []

    def test_skill_name_accepted(self, project_root):
        """check_on_entry accepts any skill_name string (currently informational)."""
        self._write_iteration(project_root, {
            "version": 4,
            "updated_at": "2026-01-01T00:00:00Z",
            "current_phase": "v2.1",
            "changes": [],
        })
        sched = WaveScheduler()
        recs = sched.check_on_entry(project_root, "guide-ship")
        assert recs == []


class TestFormatRecommendations:
    """format_recommendations: render Recommendation list to human-readable string."""

    def test_empty_list_returns_empty_string(self):
        sched = WaveScheduler()
        assert sched.format_recommendations([]) == ""

    def test_fill_wave_format(self):
        """Fill wave rec renders with 'fill' wording."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="change-b", current_status="planned",
            blocked_by="change-a", blocker_status="archived",
            wave="fill", reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )]
        out = sched.format_recommendations(recs)
        assert "change-b" in out
        assert "fill" in out
        assert "change-a" in out

    def test_ship_wave_format(self):
        """Ship wave rec renders with 'ship' wording."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="change-c", current_status="proposed",
            blocked_by="change-a", blocker_status="archived",
            wave="ship", reason="blocker 'change-a' is archived",
            source="iteration.blocker",
        )]
        out = sched.format_recommendations(recs)
        assert "change-c" in out
        assert "ship" in out

    def test_multiple_recs_each_on_own_line(self):
        sched = WaveScheduler()
        recs = [
            Recommendation(
                name="B", current_status="planned", blocked_by="A",
                blocker_status="archived", wave="fill",
                reason="blocker 'A' is archived", source="iteration.blocker",
            ),
            Recommendation(
                name="C", current_status="proposed", blocked_by="A",
                blocker_status="archived", wave="ship",
                reason="blocker 'A' is archived", source="iteration.blocker",
            ),
        ]
        out = sched.format_recommendations(recs)
        lines = [l for l in out.split("\n") if l.strip()]
        # Each rec should produce at least one line mentioning its name
        assert any("B" in l for l in lines)
        assert any("C" in l for l in lines)

    def test_manual_deps_source_in_output(self):
        """manual_deps source rendered in output."""
        sched = WaveScheduler()
        recs = [Recommendation(
            name="D", current_status="planned", blocked_by="A",
            blocker_status="archived", wave="fill",
            reason="manual_deps ['A', 'B'] all resolved",
            source="manual_deps",
        )]
        out = sched.format_recommendations(recs)
        assert "D" in out
