"""Tests for fix-post-flow-classifier-ordering: F1-F4 classifier ordering + F4 gate-raised path.

ADR-0027 §1.2 fine-grained mapping:
    F1 (traceback in ``_lib/``) → ``phase-crash``;
    F2 (ConfigError) → ``gate-failure``;
    F3 (invalid state) → ``flow-bug``;
    F4-gate (gate raised) → ``gate-failure``.

Rule evaluation order: F4 > F1 > F2 > F3 (gate-raised is the most specific
signal and must win over a generic traceback in ``_lib/``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from post_flow_analysis import (  # type: ignore[import-not-found]
    PhaseOutcome,
    Classification,
    classify_phase_outcome,
    analyze_phase_trace,
)


def _classify(stderr: str, phase: str = "guide-plan") -> Classification:
    """Invoke classify_phase_outcome directly (no report_flow_bug glue)."""
    return classify_phase_outcome(
        phase, PhaseOutcome(phase=phase, exit_code=1, stderr=stderr)
    )


# ── Task 1: F1-F4 scenario tests ──────────────────────────────────────


def test_f1_traceback_in_lib_classified_as_phase_crash() -> None:
    """F1: traceback with a frame in _lib/ → phase-crash."""
    stderr = (
        "Traceback (most recent call last):\n"
        '  File "_lib/post_flow_analysis.py", line 234, in classify\n'
        "    raise ZeroDivisionError()\n"
        "ZeroDivisionError: division by zero\n"
    )
    classification = _classify(stderr)
    assert classification.report_category == "phase-crash"
    assert classification.should_report is True


def test_f2_config_error_classified_as_gate_failure() -> None:
    """F2 (ConfigError) was previously unreachable because F3 matched first.

    Now F2 must win over F3 when stderr contains ConfigError but NOT
    'gate raised'.
    """
    stderr = "Config validation failed: missing field 'arch_gate'\n"
    classification = _classify(stderr)
    assert classification.report_category == "gate-failure", (
        f"F2 should match; got {classification.report_category}"
    )


def test_f3_invalid_state_unchanged() -> None:
    """F3 (invalid state) is still flow-bug when no F1/F2/F4 markers present."""
    stderr = "invalid state: expected 'arch_done', got 'plan_done'\n"
    classification = _classify(stderr)
    assert classification.report_category == "flow-bug"


def test_f4_gate_raised_new_path() -> None:
    """F4 (gate raised) is the new path: gate-raised signal wins over traceback.

    stderr contains 'gate raised' in a _check_* frame — even though there
    is a traceback in _lib/gate.py, the gate-raised signal is more specific.
    """
    stderr = (
        "Traceback (most recent call last):\n"
        '  File "_lib/gate.py", line 88, in _check_arch_debt\n'
        '    raise ConfigError("arch debt not recorded")\n'
        "ConfigError: gate raised in _check_arch_debt\n"
    )
    classification = _classify(stderr)
    assert classification.report_category == "gate-failure", (
        f"F4 should classify as gate-failure; got {classification.report_category}"
    )


# ── Task 2: consistency between two classifiers ────────────────────────


def test_analyze_phase_trace_consistent_with_main_classifier() -> None:
    """The two classifier functions must agree on identical input."""
    samples = [
        ("Traceback in _lib/foo.py\nZeroDivisionError", "phase-crash"),
        ("Config validation failed: bad yaml", "gate-failure"),
        ("gate raised in _check_arch_debt", "gate-failure"),
        ("invalid state: expected X, got Y", "flow-bug"),
    ]

    for stderr, expected in samples:
        main_class = classify_phase_outcome(
            "guide-plan",
            PhaseOutcome(phase="guide-plan", exit_code=1, stderr=stderr),
        )
        trace_class = analyze_phase_trace(
            phase="guide-plan",
            exit_code=1,
            stderr=stderr,
            stdout_tail="",
        )
        assert main_class.report_category == trace_class.report_category, (
            f"Mismatch on stderr={stderr!r}: main={main_class.report_category}, "
            f"trace={trace_class.report_category}"
        )
        assert main_class.report_category == expected, (
            f"Expected {expected}, got {main_class.report_category} for {stderr!r}"
        )


# ── Task 3: module exports sanity ─────────────────────────────────────


def test_module_exports_f_re_constants() -> None:
    """All 4 F regex constants must be importable from post_flow_analysis."""
    import post_flow_analysis as pfa  # type: ignore[import-not-found]

    for name in (
        "_RE_F1_TRACEBACK_IN_LIB",
        "_RE_F2_CONFIG_ERROR",
        "_RE_F4_GATE_RAISED",
        "_RE_F3_INVALID_STATE",
    ):
        assert hasattr(pfa, name), f"Missing module export: {name}"
        # Each is a compiled regex pattern with a .search method
        assert hasattr(getattr(pfa, name), "search"), (
            f"{name} is not a compiled regex"
        )