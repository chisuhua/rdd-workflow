"""Tests for doctor_render — severity aggregation + JSON payload + render modes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Inject scripts dir so we can import doctor_render without the dotted path
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import (  # noqa: E402  (sys.path manipulation above is intentional)
    Finding,
    Severity,
    render_human,
    render_json,
    render_quiet,
    exit_code_for,
)


def _finding(severity: Severity, category: str = "state") -> Finding:
    return Finding(
        severity=severity,
        category=category,
        file=".rddf/state/iteration.json",
        line=42,
        snippet='  "current_sprint":',
        fix_hint="re-run guide-plan",
    )


def test_exit_code_0_when_no_findings():
    assert exit_code_for([]) == 0


def test_exit_code_1_when_only_info_and_warning():
    findings = [_finding(Severity.INFO), _finding(Severity.WARNING)]
    assert exit_code_for(findings) == 1


def test_exit_code_2_when_critical_present():
    findings = [_finding(Severity.WARNING), _finding(Severity.CRITICAL)]
    assert exit_code_for(findings) == 2


def test_exit_code_3_on_checker_exception_marker():
    findings = [_finding(Severity.CRITICAL)]
    # checker_exception=True forces exit code 3
    assert exit_code_for(findings, checker_exception=True) == 3


def test_human_report_groups_by_severity():
    findings = [_finding(Severity.CRITICAL), _finding(Severity.WARNING)]
    out = render_human(findings, categories_checked=["state", "plans"])
    assert "=== CRITICAL" in out
    assert "=== WARNING" in out
    assert ".rddf/state/iteration.json" in out


def test_json_payload_schema():
    findings = [_finding(Severity.CRITICAL)]
    payload = render_json(findings, categories_checked=["state"])
    parsed = json.loads(payload)
    assert "timestamp" in parsed
    assert parsed["categories_checked"] == ["state"]
    assert isinstance(parsed["findings"], list)
    assert len(parsed["findings"]) == 1
    f = parsed["findings"][0]
    assert f["severity"] == "CRITICAL"
    assert f["category"] == "state"
    assert f["file"] == ".rddf/state/iteration.json"
    assert f["line"] == 42
    assert f["fix_hint"] == "re-run guide-plan"
    assert parsed["summary"] == {"critical": 1, "warning": 0, "info": 0}


def test_quiet_render_single_line():
    findings = [_finding(Severity.CRITICAL), _finding(Severity.WARNING)]
    out = render_quiet(findings)
    lines = [line for line in out.strip().split("\n") if line]
    assert len(lines) <= 1
    assert "CRITICAL" in lines[0]


def test_human_empty_findings_shows_ok():
    out = render_human([], categories_checked=["state", "plans", "roadmap-meta"])
    assert "All 3 categories OK" in out


def test_human_empty_findings_count_matches_categories():
    """Empty findings → OK message reflects the actual number of categories checked."""
    out = render_human([], categories_checked=["a", "b", "c", "d", "e", "f"])
    assert "All 6 categories OK" in out