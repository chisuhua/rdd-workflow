# fix-post-flow-classifier-ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Fix three contradictions in `_lib/post_flow_analysis.py` classifier per ADR-0027 §1.2: (1) F3 matches before F2 → F2 unreachable; (2) `analyze_phase_trace` vs main classifier inconsistent on "invalid state"; (3) F4 gate-raised rule entirely missing. Add F4 detection, reorder rules, unify two classifiers.

**Architecture:** Reorder F1 → F2 → F4 → F3 (gate-raised before generic invalid state). Add F4 regex matching `gate raised` / `_check_*` / `gate failure`. Extract both classifier branches to share a single `_classify_failure_pattern()` helper. Module-level export 4 `_RE_F<n>` constants.

**Tech Stack:** Python 3.11+, pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/post_flow_analysis.py` | Add F4 regex; reorder F1→F2→F4→F3; extract shared `_classify_failure_pattern()`; align `analyze_phase_trace` with main classifier |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_post_flow_classifier.py` | **NEW** — 6 unit tests: F1/F2/F3/F4 scenarios, analyze vs main consistency, F constants exported |

---

### Task 1: Add F4 gate-raised regex + reorder F1→F2→F4→F3

**Files:**
- Modify: `_lib/post_flow_analysis.py` (find `classify_phase_outcome` function)
- Test: `tests/unit/test_post_flow_classifier.py` (NEW)

- [ ] **Step 1: Write 4 scenario tests**

Create `tests/unit/test_post_flow_classifier.py`:

```python
"""Tests for fix-post-flow-classifier-ordering: F1-F4 classifier ordering + F4 gate-raised path."""
from __future__ import annotations

import pytest


def _classify_via_helper(stderr: str, phase: str = "guide-plan"):
    """Helper: invoke the internal classifier directly to bypass report_flow_bug glue."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from post_flow_analysis import classify_phase_outcome, PhaseOutcome
    return classify_phase_outcome(phase, PhaseOutcome(phase=phase, exit_code=1, stderr=stderr))


def test_f1_traceback_in_lib_classified_as_phase_crash() -> None:
    stderr = (
        "Traceback (most recent call last):\n"
        "  File \"_lib/post_flow_analysis.py\", line 234, in classify\n"
        "    raise ZeroDivisionError()\n"
        "ZeroDivisionError: division by zero\n"
    )
    classification = _classify_via_helper(stderr)
    assert classification.report_category == "phase-crash"
    assert classification.should_report is True


def test_f2_config_error_classified_as_gate_failure() -> None:
    """F2 (ConfigError) was previously unreachable because F3 matched first.
    Now F2 must win over F3 when stderr contains ConfigError but NOT 'gate raised'."""
    stderr = "Config validation failed: missing field 'arch_gate'\n"
    classification = _classify_via_helper(stderr)
    assert classification.report_category == "gate-failure", (
        f"F2 should match; got {classification.report_category}"
    )


def test_f3_invalid_state_unchanged() -> None:
    """F3 (invalid state) is still flow-bug when no F1/F2/F4 markers present."""
    stderr = "invalid state: expected 'arch_done', got 'plan_done'\n"
    classification = _classify_via_helper(stderr)
    assert classification.report_category == "flow-bug"


def test_f4_gate_raised_new_path() -> None:
    """F4 (gate raised) is the new path: stderr contains 'gate raised' in a _check_* frame."""
    stderr = (
        "Traceback (most recent call last):\n"
        "  File \"_lib/gate.py\", line 88, in _check_arch_debt\n"
        "    raise ConfigError(\"arch debt not recorded\")\n"
        "ConfigError: gate raised in _check_arch_debt\n"
    )
    classification = _classify_via_helper(stderr)
    assert classification.report_category == "gate-failure", (
        f"F4 should classify as gate-failure; got {classification.report_category}"
    )
```

- [ ] **Step 2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_post_flow_classifier.py -v`
Expected: 4 failures (ordering wrong / F4 missing).

- [ ] **Step 3: Locate `classify_phase_outcome` in `_lib/post_flow_analysis.py`**

Read the function around lines 230-260. Identify the F1/F2/F3 conditional chain. Note the line where F3 (`invalid state`) is matched BEFORE F2 (`ConfigError`).

- [ ] **Step 4: Add module-level F regex constants**

At module top (after imports), add:

```python
# ── ADR-0027 §1.2 classifier regex set (ordered: F1 < F2 < F4 < F3) ──
import re as _re

_RE_F1_TRACEBACK_IN_LIB = _re.compile(
    r"Traceback.*(?:skills/_lib/|_lib/)", _re.DOTALL
)
_RE_F2_CONFIG_ERROR = _re.compile(r"Config(?:Error| validation failed)")
_RE_F4_GATE_RAISED = _re.compile(
    r"(?:gate raised|_check_\w+.*raised|GateFailure)"
)
_RE_F3_INVALID_STATE = _re.compile(r"invalid state")
```

- [ ] **Step 5: Add `_classify_failure_pattern()` helper**

Insert after the regex constants:

```python
def _classify_failure_pattern(stderr: str) -> tuple[str, str] | None:
    """Return ``(category, skill_invoked)`` if stderr matches an F1-F4 pattern.

    **ADR-0027 §1.2 ordering**: F1 traceback > F2 ConfigError > F4 gate-raised >
    F3 invalid state. The first match wins. Returns ``None`` if no pattern
    matches (caller falls back to flow-bug classification with default
    skill_invoked).
    """
    if _RE_F1_TRACEBACK_IN_LIB.search(stderr):
        return "phase-crash", "post-flow-analysis"
    if _RE_F2_CONFIG_ERROR.search(stderr):
        return "gate-failure", "post-flow-analysis"
    if _RE_F4_GATE_RAISED.search(stderr):
        return "gate-failure", "gate-system"
    if _RE_F3_INVALID_STATE.search(stderr):
        return "flow-bug", "post-flow-analysis"
    return None
```

- [ ] **Step 6: Replace F1/F2/F3 chain in `classify_phase_outcome` with helper call**

Find the existing if/elif chain (around line 234) and replace with:

```python
match = _classify_failure_pattern(stderr)
if match is not None:
    category, skill_invoked = match
    classification = Classification(
        phase=outcome.phase,
        category=category,
        should_report=True,
        report_category=category,
        description=_extract_failure_summary(stderr, outcome.exit_code),
        stack=_extract_traceback(stderr),
        metadata={"skill_invoked": skill_invoked, "exit_code": outcome.exit_code},
    )
    return classification
```

(Adjust based on actual Classification dataclass fields in the file — read it first to confirm field names.)

- [ ] **Step 7: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_post_flow_classifier.py -v`
Expected: 4 passed.

- [ ] **Step 8: Defer commit**

---

### Task 2: Unify `analyze_phase_trace` with main classifier

**Files:**
- Modify: `_lib/post_flow_analysis.py` (find `analyze_phase_trace` around line 490)
- Test: `tests/unit/test_post_flow_classifier.py` (append consistency test)

- [ ] **Step 1: Append consistency test**

```python
def test_analyze_phase_trace_consistent_with_main_classifier() -> None:
    """The two classifier functions must agree on identical input."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from post_flow_analysis import (
        classify_phase_outcome, analyze_phase_trace, PhaseOutcome,
    )

    samples = [
        ("Traceback in _lib/foo.py\nZeroDivisionError", "phase-crash"),
        ("Config validation failed: bad yaml", "gate-failure"),
        ("gate raised in _check_arch_debt", "gate-failure"),
        ("invalid state: expected X, got Y", "flow-bug"),
    ]

    for stderr, expected in samples:
        main_class = classify_phase_outcome(
            "guide-plan", PhaseOutcome(phase="guide-plan", exit_code=1, stderr=stderr)
        )
        trace_class = analyze_phase_trace(
            phase="guide-plan", exit_code=1, stderr=stderr, stdout_tail="",
        )
        assert main_class.report_category == trace_class.report_category, (
            f"Mismatch on stderr={stderr!r}: main={main_class.report_category}, "
            f"trace={trace_class.report_category}"
        )
        assert main_class.report_category == expected, (
            f"Expected {expected}, got {main_class.report_category} for {stderr!r}"
        )
```

- [ ] **Step 2: Run test (likely FAIL before fix)**

Run: `python3 -m pytest tests/unit/test_post_flow_classifier.py::test_analyze_phase_trace_consistent_with_main_classifier -v`
Expected: FAIL on at least one sample (likely the "invalid state" case → main=F3 flow-bug, trace=F2-cumulative gate-failure).

- [ ] **Step 3: Fix `analyze_phase_trace` to use the same helper**

Replace its classifier body with a call to `_classify_failure_pattern()`. If it has additional cumulative logic (matching against multiple lines), make sure the ordering matches F1→F2→F4→F3 first-match.

- [ ] **Step 4: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_post_flow_classifier.py -v`
Expected: 5 passed.

- [ ] **Step 5: Defer commit**

---

### Task 3: Module exports sanity test

**Files:**
- Test: `tests/unit/test_post_flow_classifier.py` (append)

- [ ] **Step 1: Append exports test**

```python
def test_module_exports_f_re_constants() -> None:
    """All 4 F regex constants must be importable from post_flow_analysis."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    import post_flow_analysis as pfa

    for name in ("_RE_F1_TRACEBACK_IN_LIB", "_RE_F2_CONFIG_ERROR",
                 "_RE_F4_GATE_RAISED", "_RE_F3_INVALID_STATE"):
        assert hasattr(pfa, name), f"Missing module export: {name}"
        # Each is a compiled regex pattern with a .search method
        assert hasattr(getattr(pfa, name), "search"), (
            f"{name} is not a compiled regex"
        )
```

- [ ] **Step 2: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_post_flow_classifier.py -v`
Expected: 6 passed.

- [ ] **Step 3: Defer commit**

---

### Task 4: Run full unit test suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `tests/KNOWN_FAILURES.txt`.

- [ ] **Step 2: If new failures appear, fix them**

- [ ] **Step 3: Defer commit**

---

### Task 5: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/fix-post-flow-classifier-ordering/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add _lib/post_flow_analysis.py \
  tests/unit/test_post_flow_classifier.py \
  openspec/changes/fix-post-flow-classifier-ordering/tasks.md \
  .rddf/plans/fix-post-flow-classifier-ordering.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] All 6 AC met (AC-1 through AC-6)
- [ ] `python3 -m pytest tests/unit/test_post_flow_classifier.py -v` — 6 passed
- [ ] Full unit suite: no NEW failures
- [ ] `openspec validate fix-post-flow-classifier-ordering` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Changes to `_should_auto_submit` (env-var logic, handled by PR-1)
- ❌ Changes to `report_flow_bug` outer path (handled by PR-1)
- ❌ New category names (ADR §1.1 fixed)
- ❌ Changes to buffer / report / triage / close环
- ❌ Per-gate custom issue categories
- ❌ Phase-interrupted category rename (handled by PR-6)