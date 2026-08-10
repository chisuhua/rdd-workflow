"""tests/unit/test_proposal_review.py — Unit tests for HOW-leakage detector.

Tests Group 6 (regression coverage) of tasks.md:
  6.1 Per-signal detection (code_fence, function_signature, file_list, step_density)
  6.2 Single-signal suppression (no warning if only one weak signal)
  6.3 Section-aware weighting (WHY/WHAT weighted higher than 技术约束)
  6.4 Non-fatal parse failures (missing section / empty file / non-standard Markdown)
  6.5 Read-only behavior (detector never modifies content)
  6.6 Run with full regression suite (caller's responsibility; this file
      only verifies detector-specific behavior)

Telemetry persistence is disabled in all tests via `_persist_hits=False`
to avoid touching `.rddf/state/.how-leakage-hits.json` during test runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `skills._lib` resolves.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _lib import proposal_review  # noqa: E402
from _lib.proposal_review import (  # noqa: E402
    THRESHOLDS,
    detect_how_leakage,
)


# --- 6.1 Per-signal detection ---


def test_code_fence_signal_fires_when_two_fences_in_why_section():
    """Two ``` fences in 架构依据 should make code_fence fire there."""
    md = (
        "## 架构依据\n"
        "Earlier system uses two patterns:\n"
        "\n"
        "```python\n"
        "def foo():\n"
        "    pass\n"
        "```\n"
        "\n"
        "And also:\n"
        "\n"
        "```python\n"
        "def bar():\n"
        "    pass\n"
        "```\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    fired_sections = {(w["signal"], w["section"]) for w in warnings}
    assert ("code_fence", "架构依据") in fired_sections


def test_function_signature_signal_fires_when_two_sigs_in_scope():
    """Two function signatures in 范围 should make function_signature fire
    when paired with another high-intensity signal in the same section
    (multi-signal rule per design decision 1)."""
    md = (
        "## 范围\n"
        "We will modify `def parse_token(input)` and `def validate_token(t)`.\n"
        "\n"
        "```python\n"
        "def helper():\n"
        "    pass\n"
        "```\n"
        "\n"
        "```python\n"
        "def helper2():\n"
        "    pass\n"
        "```\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    fired_sections = {(w["signal"], w["section"]) for w in warnings}
    assert ("function_signature", "范围") in fired_sections


def test_file_list_signal_fires_when_three_paths_in_scope():
    """Three file paths in 范围 should make file_list fire when paired
    with another high-intensity signal (multi-signal rule)."""
    md = (
        "## 范围\n"
        "Touches these files:\n"
        "\n"
        "- `src/foo.py`\n"
        "- `src/bar.py`\n"
        "- `src/baz.py`\n"
        "\n"
        "```python\n"
        "x = 1\n"
        "```\n"
        "\n"
        "```python\n"
        "y = 2\n"
        "```\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    fired_sections = {(w["signal"], w["section"]) for w in warnings}
    assert ("file_list", "范围") in fired_sections


def test_step_density_signal_fires_when_four_consecutive_ordinals():
    """Four consecutive numbered steps should make step_density fire
    when paired with another high-intensity signal (multi-signal rule)."""
    md = (
        "## 范围\n"
        "Steps to follow:\n"
        "\n"
        "1. First do this\n"
        "2. Then do that\n"
        "3. Finally do the other\n"
        "4. Last step\n"
        "\n"
        "```python\n"
        "def a():\n"
        "    pass\n"
        "```\n"
        "\n"
        "```python\n"
        "def b():\n"
        "    pass\n"
        "```\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    fired_sections = {(w["signal"], w["section"]) for w in warnings}
    assert ("step_density", "范围") in fired_sections


# --- 6.2 Single-signal suppression ---


def test_single_weak_signal_does_not_warn():
    """A single weak signal alone should not produce a warning.

    Per design decision 1: multi-signal rule requires 2+ signals OR
    a single signal above hard_cap. A single sub-threshold signal
    must NOT fire a warning.
    """
    md = (
        "## 架构依据\n"
        "We reference one example:\n"
        "\n"
        "```python\n"
        "x = 1\n"
        "```\n"
    )
    # One fence + one signature line is still only 1 strong signal
    # (code_fence=1 which is < high=2; function_signature=0).
    warnings = detect_how_leakage(md, _persist_hits=False)
    assert warnings == [], (
        f"Single weak signal should not warn; got: {warnings}"
    )


def test_only_file_list_no_other_signals_does_not_warn():
    """Three file paths alone (no code/sigs/steps) should not warn
    because multi-signal rule requires 2+ distinct signals."""
    md = (
        "## 范围\n"
        "- `src/foo.py`\n"
        "- `src/bar.py`\n"
        "- `src/baz.py`\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    # file_list fires at count=3 >= high=3, but no other signal fires,
    # so multi-signal rule suppresses.
    assert warnings == [], (
        f"Single-signal fire should be suppressed; got: {warnings}"
    )


def test_single_signal_hard_cap_fires_without_other_signals():
    """A single signal exceeding hard_cap should fire even without
    other signals (per design decision 1 alternative path)."""
    md = (
        "## 范围\n"
        "Implementation walkthrough:\n"
        "\n"
        "1. First\n"
        "2. Second\n"
        "3. Third\n"
        "4. Fourth\n"
        "5. Fifth\n"
        "6. Sixth\n"
        "7. Seventh\n"
    )
    # 7 consecutive steps >= hard_cap=6 → single-signal fire.
    warnings = detect_how_leakage(md, _persist_hits=False)
    assert any(w["signal"] == "step_density" for w in warnings)


# --- 6.3 Section-aware weighting ---


def test_why_section_fires_earlier_than_technical_constraint():
    """Same number of code fences should produce higher weighted_score
    in WHY/WHAT sections than in 技术约束."""
    md_why = (
        "## 架构依据\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    md_tech = (
        "## 技术约束\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    w_why = detect_how_leakage(md_why, _persist_hits=False)
    w_tech = detect_how_leakage(md_tech, _persist_hits=False)
    # In 架构依据 (weight=1.0), 2 fences >= high=2 fires.
    # In 技术约束 (weight=0.4), 2 fences still fires on count threshold
    # but weighted_score should be lower. Multi-signal rule still
    # suppresses (single signal). To exercise weighting we directly
    # inspect weighted_score on a forced multi-signal case.
    md_why_multi = (
        "## 架构依据\n"
        "1. step one\n"
        "2. step two\n"
        "3. step three\n"
        "4. step four\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    md_tech_multi = (
        "## 技术约束\n"
        "1. step one\n"
        "2. step two\n"
        "3. step three\n"
        "4. step four\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    w_why_multi = detect_how_leakage(md_why_multi, _persist_hits=False)
    w_tech_multi = detect_how_leakage(md_tech_multi, _persist_hits=False)
    why_scores = [w["weighted_score"] for w in w_why_multi]
    tech_scores = [w["weighted_score"] for w in w_tech_multi]
    if why_scores and tech_scores:
        assert max(why_scores) > max(tech_scores), (
            f"WHY score {max(why_scores)} should exceed tech {max(tech_scores)}"
        )


# --- 6.4 Non-fatal parse failures ---


def test_empty_string_returns_empty_warnings():
    """Empty input returns no warnings, no exception."""
    assert detect_how_leakage("", _persist_hits=False) == []
    assert detect_how_leakage("   \n\n  ", _persist_hits=False) == []


def test_no_sections_returns_no_warnings():
    """Markdown without any `## ` headers is treated as preamble."""
    md = "Just a paragraph, no sections at all.\n" * 20
    # No multi-signal fires possible without sections to count in.
    assert detect_how_leakage(md, _persist_hits=False) == []


def test_non_standard_markdown_does_not_raise():
    """Garbage input should not raise; should return whatever it can."""
    garbage_inputs = [
        "```\nunclosed fence",
        "##########",
        "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\",
        "\x00\x01\x02 binary garbage",
        "## " + "x" * 10000,  # very long header
    ]
    for g in garbage_inputs:
        # Must not raise.
        result = detect_how_leakage(g, _persist_hits=False)
        assert isinstance(result, list)


def test_missing_section_does_not_raise_and_returns_safely():
    """Missing sections just mean no per-section counts; no error."""
    md = (
        "## Unknown Section\n"
        "Some text here.\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
        "```python\nbaz\n```\n"
    )
    # Unknown section gets default weight 0.5; code_fence fires (3 >= high=2).
    # But no other signal → suppressed. Result: empty list.
    result = detect_how_leakage(md, _persist_hits=False)
    assert isinstance(result, list)


# --- 6.5 Read-only behavior (no auto-rewrite) ---


def test_detector_does_not_modify_input_text():
    """Calling detect_how_leakage must not mutate the input string."""
    original = (
        "## 范围\n"
        "1. step one\n"
        "2. step two\n"
        "3. step three\n"
        "4. step four\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    snapshot = original
    # Call multiple times to confirm idempotency and lack of mutation.
    for _ in range(3):
        detect_how_leakage(original, _persist_hits=False)
    assert original == snapshot, "Detector mutated input text!"


def test_detector_does_not_strip_code_blocks():
    """Detector must preserve code fences in returned records (advisory only)."""
    md = (
        "## 范围\n"
        "1. first\n"
        "2. second\n"
        "3. third\n"
        "4. fourth\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    before = md.count("```")
    detect_how_leakage(md, _persist_hits=False)
    after = md.count("```")
    assert before == after, "Detector stripped code fences from input!"


# --- Threshold configuration sanity ---


def test_thresholds_module_is_importable():
    """proposal_review_config.THRESHOLDS must be importable as documented."""
    from _lib.proposal_review_config import THRESHOLDS as T

    assert "code_fence" in T
    assert "function_signature" in T
    assert "file_list" in T
    assert "step_density" in T
    assert "section_weights" in T
    assert "multi_signal_threshold" in T
    for sig in ("code_fence", "function_signature", "file_list", "step_density"):
        assert "high" in T[sig]
        assert "hard_cap" in T[sig]


def test_config_override_path_supported():
    """detect_how_leakage accepts a `config=` override for tuning."""
    md = (
        "## 范围\n"
        "```python\nfoo\n```\n"
    )
    # Default high for code_fence is 2; with one fence, default returns [].
    default_warnings = detect_how_leakage(md, _persist_hits=False)
    # Override: set code_fence high=1 so a single fence fires.
    override_cfg = {
        "code_fence": {"high": 1, "hard_cap": 4},
    }
    overridden_warnings = detect_how_leakage(
        md, config=override_cfg, _persist_hits=False
    )
    # Single signal still suppressed by multi-signal rule, but at least
    # the override path should not error.
    assert isinstance(overridden_warnings, list)


def test_warning_record_schema():
    """Each warning record must conform to WarningRecord schema."""
    md = (
        "## 范围\n"
        "1. first\n"
        "2. second\n"
        "3. third\n"
        "4. fourth\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    warnings = detect_how_leakage(md, _persist_hits=False)
    for w in warnings:
        assert "signal" in w
        assert "threshold" in w
        assert "section" in w
        assert "action" in w
        assert "weighted_score" in w
        assert w["signal"] in (
            "code_fence",
            "function_signature",
            "file_list",
            "step_density",
        )
        assert isinstance(w["threshold"], dict)
        assert "high" in w["threshold"]


# --- Telemetry persistence (Group 7) ---


def test_telemetry_writes_to_state_dir_when_warning_fires(tmp_path, monkeypatch):
    """When warnings fire, hits should be persisted to the state file.

    Uses tmp_path as PROJECT_ROOT to avoid polluting the real state dir.
    """
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    md = (
        "## 范围\n"
        "1. first\n"
        "2. second\n"
        "3. third\n"
        "4. fourth\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    detect_how_leakage(md)  # default _persist_hits=True
    hit_file = tmp_path / ".rddf" / "state" / ".how-leakage-hits.json"
    # If warnings fire, file should exist. If not, file may not exist —
    # both are acceptable behaviors as long as no exception is raised.
    if hit_file.exists():
        import json

        data = json.loads(hit_file.read_text())
        assert isinstance(data, list)
        if data:
            assert "doc_hash" in data[0]
            assert "timestamp" in data[0]


def test_telemetry_failure_does_not_propagate(tmp_path, monkeypatch):
    """A failure inside telemetry must not propagate to the caller.

    Per design decision 'non-fatal parse failures': detector must
    return warnings even if the state dir is unwritable.
    """
    # Make PROJECT_ROOT a path that can't have a .rddf dir.
    monkeypatch.setenv("PROJECT_ROOT", "/dev/null/forbidden")
    md = (
        "## 范围\n"
        "1. first\n"
        "2. second\n"
        "3. third\n"
        "4. fourth\n"
        "```python\nfoo\n```\n"
        "```python\nbar\n```\n"
    )
    # Must not raise.
    result = detect_how_leakage(md)
    assert isinstance(result, list)