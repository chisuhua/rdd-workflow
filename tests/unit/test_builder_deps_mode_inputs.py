"""Execution-mode decision: real inputs, honest reasons, fail-closed (fix-execution-mode-decision).

The decision used to be fed three placeholder values — a hardcoded
``task_count = 5`` (⇒ the ``lightweight`` branch was unreachable), an empty
risk list (⇒ the risk rule never fired) and "how many files are in the change
directory" (⇒ a number that had nothing to do with the change's size). The
reason written into the builder handoff was therefore **fabricated**
("files=6>2 AND tasks=5>3" for a change with 4 tasks).

These tests pin the replacement:

  * ``compute_mode_inputs`` reads the REAL inputs from absolute paths;
  * an unavailable input is reported as unknown and does not participate;
  * a missing task count fails CLOSED (worktree), never open;
  * the reason states the actual values — never a constant;
  * the conflict dimension exists (ADR-0024's 4th row, never implemented);
  * while the lightweight execution mode is not usable (ADR-0036 V-G), the
    decision reports worktree with a reason that says why.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _lib import builder_deps  # noqa: E402
from _lib.builder_deps import (  # noqa: E402
    LIGHTWEIGHT_EXECUTION_READY,
    RISK_KEYWORDS,
    compute_conflict,
    compute_mode_inputs,
    decide_execution_mode,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _plan(root: Path, name: str, files: list[str]) -> None:
    lines = ["# plan", "", "### Task 1: do a", "", "**Files:**"]
    lines += [f"- Modify: `{f}`" for f in files]
    lines += ["", "- [ ] step", ""]
    _write(root / ".rddf" / "plans" / f"{name}.md", "\n".join(lines))


def _change(root: Path, name: str, tasks: str | None, risk: str | None = None) -> None:
    base = root / "openspec" / "changes" / name
    base.mkdir(parents=True, exist_ok=True)
    if tasks is not None:
        _write(base / "tasks.md", tasks)
    _write(base / "proposal.md", "# proposal\n")
    if risk is not None:
        _write(base / "roadmap-meta.yaml", f"risk: {risk}\n")


# ---------------------------------------------------------------------------
# compute_mode_inputs — the real inputs
# ---------------------------------------------------------------------------

class TestComputeModeInputs:
    def test_task_count_is_the_checkbox_total(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n- [x] b\n- [ ] c\n")
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["task_count"] == 3          # total, not the open count
        assert inputs["file_count"] is None
        assert any("files=unknown" in n for n in inputs["notes"])

    def test_uppercase_checkbox_counts_too(self, tmp_path):
        _change(tmp_path, "c1", "- [X] a\n- [ ] b\n")
        assert compute_mode_inputs(str(tmp_path), "c1")["task_count"] == 2

    def test_missing_tasks_fails_closed(self, tmp_path):
        _change(tmp_path, "c1", None)
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["task_count"] is None
        assert any("tasks=unknown" in n for n in inputs["notes"])
        # fail-closed: the decision must be worktree
        decision = decide_execution_mode(inputs["file_count"], inputs["task_count"], inputs["risk_keywords"])
        assert decision["mode"] == "worktree"
        assert "tasks=unknown" in decision["reason"]

    def test_taskless_tasks_md_fails_closed(self, tmp_path):
        """The real counter-example: `phase1_plan.sh` extracts `^### Task ` while
        the plans in this repo use `## Task N:` ⇒ an empty tasks.md."""
        _change(tmp_path, "c1", "## Tasks\n\nno checkbox here\n")
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["task_count"] is None
        decision = decide_execution_mode(inputs["file_count"], inputs["task_count"], inputs["risk_keywords"])
        assert decision["mode"] == "worktree"
        assert "tasks=unknown" in decision["reason"]

    def test_file_count_comes_from_the_plan_files_block(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        _plan(tmp_path, "c1", ["src/a.py", "src/b.py:10-20", "tests/test_a.py"])
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["file_count"] == 3        # deduped, line numbers stripped
        assert not any("files=unknown" in n for n in inputs["notes"])

    def test_duplicate_paths_are_deduped(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        _plan(tmp_path, "c1", ["src/a.py", "src/a.py", "src/a.py:1-2"])
        assert compute_mode_inputs(str(tmp_path), "c1")["file_count"] == 1

    def test_missing_plan_leaves_files_unknown_and_it_does_not_participate(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["file_count"] is None
        decision = decide_execution_mode(inputs["file_count"], inputs["task_count"], inputs["risk_keywords"])
        # files=unknown must NOT be read as "small" → the reason says so
        assert "files=unknown" in decision["reason"]
        assert decision["mode"] == "worktree"

    def test_risk_comes_from_the_structured_declaration(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n", risk="high")
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["risk_keywords"]                 # the risky vocabulary
        assert set(inputs["risk_keywords"]) <= RISK_KEYWORDS
        decision = decide_execution_mode(inputs["file_count"], inputs["task_count"], inputs["risk_keywords"])
        assert decision["mode"] == "worktree"
        assert "risk_keyword=" in decision["reason"]

    def test_risk_normal_does_not_fire(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n", risk="normal")
        inputs = compute_mode_inputs(str(tmp_path), "c1")
        assert inputs["risk_keywords"] == []

    def test_missing_meta_means_normal(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        assert compute_mode_inputs(str(tmp_path), "c1")["risk_keywords"] == []

    def test_absolute_paths_only(self, tmp_path):
        """The decision must not depend on the cwd."""
        _change(tmp_path, "c1", "- [x] a\n")
        _plan(tmp_path, "c1", ["src/a.py"])
        import os
        cwd = os.getcwd()
        try:
            os.chdir("/")
            inputs = compute_mode_inputs(str(tmp_path), "c1")
        finally:
            os.chdir(cwd)
        assert inputs["task_count"] == 1
        assert inputs["file_count"] == 1


# ---------------------------------------------------------------------------
# decide_execution_mode — thresholds unchanged, reasons honest
# ---------------------------------------------------------------------------

class TestDecideExecutionMode:
    def test_thresholds_are_unchanged(self):
        # ADR-0024's decision table: >2 files or >3 tasks ⇒ worktree
        assert decide_execution_mode(file_count=3, task_count=1, risk_keywords=[])["mode"] == "worktree"
        assert decide_execution_mode(file_count=1, task_count=4, risk_keywords=[])["mode"] == "worktree"

    def test_reason_never_contains_a_constant_five(self):
        """The old fabrication was `tasks=5>3` for changes with other counts."""
        for tasks in (1, 2, 4, 9):
            reason = decide_execution_mode(file_count=99, task_count=tasks, risk_keywords=[])["reason"]
            assert "tasks=5" not in reason

    def test_small_change_is_suspended_until_lightweight_is_usable(self):
        """ADR-0036 V-G: the mode is only usable once it creates its branch and
        its archive path is complete."""
        decision = decide_execution_mode(file_count=2, task_count=3, risk_keywords=[])
        if LIGHTWEIGHT_EXECUTION_READY:
            assert decision["mode"] == "lightweight"
        else:
            assert decision["mode"] == "worktree"
            assert "lightweight 未落地" in decision["reason"]
            # …but the reason still shows the real inputs
            assert "files=2<=2" in decision["reason"]
            assert "tasks=3<=3" in decision["reason"]

    def test_signature_is_unchanged(self):
        """AC: the signature must not change (only the accepted values widen)."""
        params = list(inspect.signature(decide_execution_mode).parameters)
        assert params == ["file_count", "task_count", "risk_keywords"]


# ---------------------------------------------------------------------------
# the conflict dimension (ADR-0024's 4th row)
# ---------------------------------------------------------------------------

class TestComputeConflict:
    def test_overlapping_files_between_changes_is_a_conflict(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        _plan(tmp_path, "c1", ["src/shared.py", "src/only_a.py"])
        _change(tmp_path, "c2", "- [x] a\n")
        _plan(tmp_path, "c2", ["src/shared.py"])
        conflicts = compute_conflict(str(tmp_path), "c1")
        assert any("c2" in c and "src/shared.py" in c for c in conflicts)

    def test_disjoint_changes_do_not_conflict(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        _plan(tmp_path, "c1", ["src/a.py"])
        _change(tmp_path, "c2", "- [x] a\n")
        _plan(tmp_path, "c2", ["src/b.py"])
        assert compute_conflict(str(tmp_path), "c1") == []

    def test_an_active_worktree_is_a_conflict(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        (tmp_path / ".rddf" / "wt" / "other-change").mkdir(parents=True)
        conflicts = compute_conflict(str(tmp_path), "c1")
        assert any("other-change" in c for c in conflicts)

    def test_own_worktree_is_not_a_conflict(self, tmp_path):
        _change(tmp_path, "c1", "- [x] a\n")
        (tmp_path / ".rddf" / "wt" / "c1").mkdir(parents=True)
        assert compute_conflict(str(tmp_path), "c1") == []


# ---------------------------------------------------------------------------
# the same-name function guard (AC: inspect.signature)
# ---------------------------------------------------------------------------

def test_no_same_name_function_with_a_different_signature():
    """`_lib/subagent_strategy.py` has a `decide_execution_mode(task_type,
    quota_status)` — a different function with the same name."""
    from _lib import subagent_strategy
    other = subagent_strategy.decide_execution_mode
    mine = builder_deps.decide_execution_mode
    assert inspect.signature(other) != inspect.signature(mine)
