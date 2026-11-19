"""Unit tests for _lib/recommender.py — the single stage-recommendation ladder.

ADR-0062: this module is the ONE implementation of "which stage runs next".
The consumers (``rddf guide`` CLI and ``rddf monitor``) only render its
output; the wiring is asserted in
``test_stage_consumers_agreement.py`` and the structural guarantees in
``test_recommender.py``.

The ladder's behaviour is frozen to what ``guide_cmd._scan_state`` did
before the consolidation (ADR-0062 Decision 4). The path-coverage tests
below were migrated from ``test_workflow_synthesizer.py``, where they
covered the now-deleted ``_decision_tree``.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from skills._lib.recommender import (
    _worktree_has_incomplete_tasks,
    scan_state,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: Stage identifiers a ladder may return. A function that can return at
#: least this many of them is a decision ladder.
STAGE_LITERALS = frozenset({
    "rdd-arch", "rdd-planner", "rdd-builder", "rdd-verifier", "rdd-quick",
})

#: Function names that used to hold a ladder. Renaming must not create a
#: second one — the stage-literal check below is the real guard; this list
#: only makes the intent explicit in the failure message.
LEGACY_LADDER_NAMES = ("_scan_state", "_decision_tree")


def _py_files() -> list[Path]:
    roots = [REPO_ROOT / "_lib", REPO_ROOT / "skills"]
    out: list[Path] = []
    for root in roots:
        for path in root.rglob("*.py"):
            if any(part in {"__pycache__", "node_modules"} for part in path.parts):
                continue
            out.append(path)
    return out


def _returned_stage_literals(func: ast.FunctionDef) -> set[str]:
    """Stage identifiers the function can RETURN.

    Only direct returns count — a returned tuple/list of string literals, or
    a returned string literal. A stage id used as a menu ``id=`` argument or
    as a value inside a returned dataclass call is a *menu entry*, not a
    decision, and must not make the function look like a second ladder.
    """
    found: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            candidates = [value]
        elif isinstance(value, (ast.Tuple, ast.List)):
            candidates = list(value.elts)
        else:
            continue
        for el in candidates:
            if isinstance(el, ast.Constant) and isinstance(el.value, str):
                if el.value in STAGE_LITERALS:
                    found.add(el.value)
    return found


def _ladder_functions() -> list[tuple[Path, str, set[str]]]:
    """Functions that can return at least 3 distinct stage identifiers."""
    out: list[tuple[Path, str, set[str]]] = []
    for path in _py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            lits = _returned_stage_literals(node)
            if len(lits) >= 3:
                out.append((path, node.name, lits))
    return out


class TestSingleImplementationStructure:
    """AC-1 / AC-2: exactly ONE decision ladder exists.

    These are the assertions that actually prevent a second ladder from
    growing back. The consumer-agreement assertions in
    ``test_stage_consumers_agreement.py`` cannot do this on their own: two
    consumers reading the same shared module agree by construction, so only
    a *structural* check can catch "somebody added their own ladder".
    """

    def test_exactly_one_decision_ladder_exists(self):
        ladders = _ladder_functions()
        names = [f"{p.relative_to(REPO_ROOT)}::{n}" for p, n, _ in ladders]
        assert len(ladders) == 1, (
            f"expected exactly 1 decision ladder, got {len(ladders)}: {names}"
        )

    def test_the_single_ladder_is_the_shared_module(self):
        ladders = _ladder_functions()
        assert len(ladders) == 1
        path, name, _ = ladders[0]
        assert path.relative_to(REPO_ROOT) == Path("_lib/recommender.py"), (
            f"the decision ladder lives in {path.relative_to(REPO_ROOT)}, "
            f"expected _lib/recommender.py"
        )
        assert name == "scan_state"

    def test_no_legacy_ladder_function_names_remain(self):
        pattern = re.compile(
            r"^\s*def\s+(" + "|".join(LEGACY_LADDER_NAMES) + r")\b", re.MULTILINE
        )
        offenders = []
        for path in _py_files():
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
        assert not offenders, f"legacy ladder functions still defined in: {offenders}"

    def test_both_consumers_route_through_the_shared_ladder(self):
        """Wiring assertion: neither consumer keeps its own ladder."""
        guide_src = (REPO_ROOT / "_lib" / "cli" / "guide_cmd.py").read_text(encoding="utf-8")
        synth_src = (REPO_ROOT / "_lib" / "workflow_synthesizer.py").read_text(encoding="utf-8")
        assert "recommender" in guide_src
        assert "recommender.scan_state" in synth_src


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path):
    """Empty project root with .rddf/state/ + openspec/changes/ created."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    return str(tmp_path)


def _write_handoff(project_root: str, name: str, payload) -> None:
    path = Path(project_root) / ".rddf" / "state" / name
    text = payload if isinstance(payload, str) else json.dumps(payload)
    path.write_text(text, encoding="utf-8")


def _write_arch_handoff(project_root: str, *, adr_count=5, roadmap_path="roadmap.md"):
    _write_handoff(project_root, ".arch-handoff.json", {
        "version": 1,
        "arch_complete_at": "2026-01-01T00:00:00+00:00",
        "adr_count": adr_count,
        "roadmap_path": roadmap_path,
    })


def _write_planner_handoff(project_root: str):
    _write_handoff(project_root, ".planner-handoff.json", {
        "schema": "planner-handoff-v1",
        "version": 1,
        "owner": "rdd-planner",
        "awaiting_builder": ["change-1"],
    })


def _write_design_handoff(project_root: str):
    _write_handoff(project_root, ".design-handoff.json", {
        "version": 1,
        "design_complete_at": "2026-01-01T12:00:00+00:00",
        "proposals_reviewed": 3,
    })


def _write_plan_handoff(project_root: str, *, active_changes=1):
    _write_handoff(project_root, ".plan-handoff.json", {
        "version": 1,
        "plan_done_at": "2026-01-02T00:00:00+00:00",
        "active_changes": active_changes,
    })


def _make_change_dir(project_root: str, name="change-1"):
    (Path(project_root) / "openspec" / "changes" / name).mkdir(parents=True)


# ---------------------------------------------------------------------------
# Path coverage — the whole ladder
# ---------------------------------------------------------------------------


class TestPathArchHandoff:
    def test_arch_missing_and_no_roadmap_recommends_rdd_arch(self, project_root):
        """No handoff at all + no roadmap.md → rdd-arch."""
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-arch"
        assert "roadmap" in reason.lower() or "架构" in reason
        assert confidence == "high"

    def test_adr_count_zero_recommends_rdd_arch(self, project_root):
        """arch-handoff exists but adr_count=0 → rdd-arch (recover)."""
        _write_arch_handoff(project_root, adr_count=0)
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-arch"
        assert "ADR" in reason
        assert confidence == "high"

    def test_adr_count_missing_recommends_rdd_arch(self, project_root):
        """arch-handoff without adr_count field → rdd-arch."""
        _write_handoff(project_root, ".arch-handoff.json", {"version": 1})
        action, _, _ = scan_state(project_root)
        assert action == "rdd-arch"

    def test_arch_done_without_planner_recommends_rdd_planner(self, project_root):
        """arch-handoff ok, no planner-handoff → rdd-planner."""
        _write_arch_handoff(project_root)
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-planner"
        assert "planner" in reason
        assert confidence == "high"


class TestPathPlannerMarker:
    def test_planner_done_with_active_change_recommends_rdd_builder(self, project_root):
        """v4 planner-handoff + a change on disk → rdd-builder (execute)."""
        _write_arch_handoff(project_root)
        _write_planner_handoff(project_root)
        _make_change_dir(project_root)
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-builder"
        assert "变更执行" in reason
        assert confidence == "high"

    def test_planner_done_without_active_change_recommends_change_generation(
        self, project_root
    ):
        """v4 planner-handoff + no change on disk → rdd-builder (generate)."""
        _write_arch_handoff(project_root)
        _write_planner_handoff(project_root)
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "变更生成" in reason

    def test_corrupt_planner_handoff_reports_diagnostic(self, project_root):
        """A corrupt planner-handoff must be visible, not silently treated as
        'planner not run' — otherwise the agent cannot tell a corrupt
        handoff from a missing one."""
        _write_arch_handoff(project_root)
        _write_handoff(project_root, ".planner-handoff.json", '{"schema": TRUNCATED')
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-planner"
        assert "损坏" in reason

    def test_non_object_handoff_is_not_treated_as_valid(self, project_root):
        """A handoff whose top-level JSON is not an object is not a handoff."""
        _write_arch_handoff(project_root)
        _write_handoff(project_root, ".planner-handoff.json", '["not", "an", "object"]')
        action, _, _ = scan_state(project_root)
        assert action == "rdd-planner"


class TestPathLegacyV3Handoff:
    def test_v3_design_handoff_recommends_change_generation(self, project_root):
        """v3 DESIGN handoff → rdd-builder (change generation)."""
        _write_arch_handoff(project_root)
        _write_design_handoff(project_root)
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "变更生成" in reason
        assert "残留" not in reason

    def test_v3_plan_handoff_zero_active_recommends_cleanup(self, project_root):
        """v3 PLAN handoff with active_changes=0 → rdd-builder (cleanup)."""
        _write_arch_handoff(project_root)
        _write_plan_handoff(project_root, active_changes=0)
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "残留" in reason

    def test_v3_plan_handoff_stale_recommends_rdd_arch(self, project_root):
        """v3 PLAN handoff claims active changes but the filesystem has none
        → rdd-arch (the stale-handoff cross-check)."""
        _write_arch_handoff(project_root)
        _write_plan_handoff(project_root, active_changes=2)
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-arch"
        assert "stale" in reason.lower()

    def test_v3_plan_handoff_consistent_recommends_rdd_builder(self, project_root):
        """v3 PLAN handoff + matching change on disk → rdd-builder."""
        _write_arch_handoff(project_root)
        _write_plan_handoff(project_root, active_changes=1)
        _make_change_dir(project_root)
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "变更执行" in reason


class TestPathWorktreeAndGit:
    """These paths are only reachable when NO handoff exists at all."""

    def test_worktree_with_incomplete_tasks_recommends_rdd_builder(
        self, project_root, monkeypatch
    ):
        from skills._lib import recommender

        monkeypatch.setattr(
            recommender, "openspec_worktrees", lambda pr: ["/fake/wt"]
        )
        monkeypatch.setattr(
            recommender, "_worktree_has_incomplete_tasks", lambda wt: True
        )
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-builder"
        assert "任务未完成" in reason
        assert confidence == "medium"

    def test_detached_worktrees_count_in_reason(self, project_root, monkeypatch):
        from skills._lib import recommender

        monkeypatch.setattr(
            recommender, "openspec_worktrees", lambda pr: ["/wt1", "/wt2", "/wt3"]
        )
        monkeypatch.setattr(
            recommender, "_worktree_has_incomplete_tasks", lambda wt: False
        )
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-builder"
        assert "3" in reason
        assert confidence == "medium"

    def test_committed_change_in_head_recommends_rdd_builder(
        self, project_root, monkeypatch
    ):
        from skills._lib import recommender

        monkeypatch.setattr(recommender, "openspec_worktrees", lambda pr: [])
        monkeypatch.setattr(
            recommender, "_has_committed_change_in_head", lambda pr: True
        )
        action, reason, confidence = scan_state(project_root)
        assert action == "rdd-builder"
        assert "commit" in reason
        assert confidence == "medium"


class TestPathRoadmapAndChanges:
    def test_no_roadmap_recommends_rdd_arch(self, project_root):
        """roadmap.md absent → rdd-arch."""
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-arch"
        assert "roadmap" in reason.lower() or "架构" in reason

    def test_roadmap_from_handoff_is_honoured(self, project_root):
        """arch-handoff's roadmap_path is the one checked."""
        _write_arch_handoff(project_root, roadmap_path="docs/my-roadmap.md")
        (Path(project_root) / "docs").mkdir()
        (Path(project_root) / "docs" / "my-roadmap.md").write_text("# R\n")
        action, _, _ = scan_state(project_root)
        assert action != "rdd-arch"

    def test_no_changes_dir_recommends_change_generation(self, project_root):
        """roadmap present but no openspec/changes/ → rdd-builder."""
        (Path(project_root) / "roadmap.md").write_text("# R\n")
        import shutil

        shutil.rmtree(Path(project_root) / "openspec" / "changes")
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "变更生成" in reason

    def test_pending_proposal_recommends_design_stage(self, project_root):
        """An unapproved improvement → rdd-builder (design stage)."""
        (Path(project_root) / "roadmap.md").write_text("# R\n")
        imp = Path(project_root) / ".rddf" / "improvements"
        imp.mkdir()
        (imp / "test-prop.md").write_text("# test-prop\n")
        (Path(project_root) / "improvement-approved.md").write_text(
            "# 已批准提案\n\n| 提案 | 优先级 |\n|---|---|\n"
        )
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "未审查提案" in reason

    def test_no_pending_proposal_is_default(self, project_root):
        """Everything satisfied → rdd-builder (default)."""
        (Path(project_root) / "roadmap.md").write_text("# R\n")
        action, reason, _ = scan_state(project_root)
        assert action == "rdd-builder"
        assert "准备 ship" in reason or "ship" in reason.lower()


# ---------------------------------------------------------------------------
# Helper unit tests (migrated from test_workflow_synthesizer.py)
# ---------------------------------------------------------------------------


class TestWorktreeHasIncompleteTasks:
    def test_incomplete_tasks_detected(self, tmp_path):
        wt = tmp_path / "wt"
        (wt / "openspec" / "changes" / "c1").mkdir(parents=True)
        (wt / "openspec" / "changes" / "c1" / "tasks.md").write_text(
            "- [ ] first task incomplete\n"
        )
        assert _worktree_has_incomplete_tasks(str(wt)) is True

    def test_all_complete_tasks_returns_false(self, tmp_path):
        wt = tmp_path / "wt"
        (wt / "openspec" / "changes" / "c1").mkdir(parents=True)
        (wt / "openspec" / "changes" / "c1" / "tasks.md").write_text(
            "- [x] done\n"
        )
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_no_tasks_md_returns_false(self, tmp_path):
        wt = tmp_path / "wt"
        (wt / "openspec" / "changes" / "c1").mkdir(parents=True)
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_no_changes_dir_returns_false(self, tmp_path):
        wt = tmp_path / "wt"
        wt.mkdir()
        assert _worktree_has_incomplete_tasks(str(wt)) is False

    def test_incomplete_task_at_file_start(self, tmp_path):
        wt = tmp_path / "wt"
        (wt / "openspec" / "changes" / "c1").mkdir(parents=True)
        (wt / "openspec" / "changes" / "c1" / "tasks.md").write_text(
            "- [ ] task at start\n- [x] later\n"
        )
        assert _worktree_has_incomplete_tasks(str(wt)) is True

    def test_skips_archive_dir(self, tmp_path):
        wt = tmp_path / "wt"
        archive = wt / "openspec" / "changes" / "archive" / "old-change"
        archive.mkdir(parents=True)
        (archive / "tasks.md").write_text("- [ ] incomplete in archive\n")
        assert _worktree_has_incomplete_tasks(str(wt)) is False
