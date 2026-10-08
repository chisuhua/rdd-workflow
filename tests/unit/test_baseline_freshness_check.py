"""Unit tests for skills/rdd-doctor/scripts/checks/baseline_freshness_check.py."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.baseline_freshness_check import run  # noqa: E402


def _write_baseline(tmp_path: Path, content: str) -> Path:
    baseline = tmp_path / "tests" / "KNOWN_FAILURES.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(content, encoding="utf-8")
    return baseline


def test_missing_baseline_warns(tmp_path: Path):
    """No KNOWN_FAILURES.txt at all → WARNING (bootstrap needed)."""
    findings = run(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("missing-file" in f.category for f in findings)


def test_no_refresh_summary_warns(tmp_path: Path):
    """Baseline exists but has no refresh summary comment → WARNING."""
    _write_baseline(tmp_path, "test 1 # reason\ntest 2 # reason\n")
    findings = run(project_root=tmp_path)
    assert any("no-refresh-summary" in f.category for f in findings)


def test_recent_refresh_healthy(tmp_path: Path):
    """Refresh today → INFO (healthy) + no placeholder → no WARNING."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = (
        f"# === {today} refresh summary (selective): kept=0, removed=0, added=0 ===\n"
        "test 1 # placeholder for triage\n"
    )
    _write_baseline(tmp_path, content)
    findings = run(project_root=tmp_path)
    assert any("healthy" in f.category and f.severity == Severity.INFO for f in findings)
    # No staleness / no-refresh findings
    assert not any(f.severity in (Severity.WARNING, Severity.CRITICAL) for f in findings)


def test_stale_refresh_warning(tmp_path: Path):
    """Refresh 60 days ago → WARNING (between 30 and 90 day threshold)."""
    stale = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    _write_baseline(tmp_path, f"# === {stale} refresh summary (selective): kept=0 ===\n")
    findings = run(project_root=tmp_path)
    matches = [f for f in findings if "stale-refresh" in f.category]
    assert len(matches) == 1
    assert matches[0].severity == Severity.WARNING
    assert "60 days" in matches[0].snippet


def test_very_stale_refresh_critical(tmp_path: Path):
    """Refresh 120 days ago → CRITICAL."""
    stale = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
    _write_baseline(tmp_path, f"# === {stale} refresh summary (selective): kept=0 ===\n")
    findings = run(project_root=tmp_path)
    matches = [f for f in findings if "stale-refresh" in f.category]
    assert len(matches) == 1
    assert matches[0].severity == Severity.CRITICAL
    assert "120 days" in matches[0].snippet


def test_placeholder_reasons_detected(tmp_path: Path):
    """Entries with '# reason required' → WARNING (regardless of freshness)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = (
        f"# === {today} refresh summary (selective): kept=0, removed=0, added=3 ===\n"
        "# Newly added failures as of today:\n"
        "test A # reason required (added today by refresh_known_failures.sh)\n"
        "test B # reason required (added today by refresh_known_failures.sh)\n"
        "test C # reason required (added today by refresh_known_failures.sh)\n"
        "test D # real reason: pre-existing integration drift\n"
    )
    _write_baseline(tmp_path, content)
    findings = run(project_root=tmp_path)
    matches = [f for f in findings if "placeholder-reasons" in f.category]
    assert len(matches) == 1
    assert matches[0].severity == Severity.WARNING
    assert "3 entries" in matches[0].snippet


def test_picks_latest_refresh_when_multiple(tmp_path: Path):
    """When multiple refresh summaries exist, use the most recent date."""
    old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
    new = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    content = (
        f"# === {old} refresh summary (selective): kept=0 ===\n"
        f"# === {new} refresh summary (selective): kept=0 ===\n"
    )
    _write_baseline(tmp_path, content)
    findings = run(project_root=tmp_path)
    matches = [f for f in findings if "stale-refresh" in f.category]
    assert len(matches) == 0, f"recent summary should mask old one: {findings}"
    # And healthy INFO should be present
    assert any("healthy" in f.category for f in findings)


def test_placeholder_count_excludes_comments(tmp_path: Path):
    """'# reason required' inside a comment line must NOT be counted."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = (
        f"# === {today} refresh summary (selective): kept=0, removed=0, added=1 ===\n"
        "# Note: future runs should not use '# reason required' placeholder.\n"
        "test 1 # real reason: tracked in feat-x\n"
    )
    _write_baseline(tmp_path, content)
    findings = run(project_root=tmp_path)
    matches = [f for f in findings if "placeholder-reasons" in f.category]
    assert len(matches) == 0, f"comment mention should not count: {findings}"
