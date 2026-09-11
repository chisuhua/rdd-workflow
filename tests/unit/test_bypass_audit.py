"""Tests for bypass-audit mechanism (per improvement #bypass-audit-mechanism).

Covers:
- audit_bypass_log: appends valid JSONL entry
- audit_bypass_read: returns all events as JSON array
- audit_bypass_monthly_count: aggregates by env_var for current month
- bypass_audit_check.run: emits WARNING/CRITICAL based on threshold
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


_BYPASS_AUDIT_SCRIPTS = str(Path(__file__).resolve().parents[2] / "skills" / "rdd-doctor" / "scripts")
if _BYPASS_AUDIT_SCRIPTS not in sys.path:
    sys.path.insert(0, _BYPASS_AUDIT_SCRIPTS)
from checks import bypass_audit_check  # type: ignore  # noqa: E402


@pytest.fixture
def tmp_project_root():
    """Create temporary project root with .rddf/state dir."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / ".rddf" / "state").mkdir(parents=True)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def run_bash_in_env(script_inline: str, env: dict) -> subprocess.CompletedProcess:
    """Run an inline bash script with custom env."""
    return subprocess.run(
        ["bash", "-c", script_inline],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def append_bypass_log(project_root: Path, env_var: str, reason: str, change: str = "", scope: str = "") -> None:
    """Helper to append a single bypass-audit event."""
    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(project_root)
    inline = (
        f"source _lib/bypass_audit.sh && "
        f'audit_bypass_log "{env_var}" "{reason}" "{change}" "{scope}"'
    )
    result = run_bash_in_env(inline, env)
    assert result.returncode == 0, f"audit_bypass_log failed: {result.stderr}"


def test_audit_bypass_log_writes_valid_jsonl(tmp_project_root: Path) -> None:
    """audit_bypass_log should append a valid JSON line with all required fields."""
    append_bypass_log(tmp_project_root, "TEST_VAR", "unit test reason", "test-change", "test-scope")

    audit_file = tmp_project_root / ".rddf" / "state" / ".bypass-audit.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text().strip().splitlines()
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["env_var"] == "TEST_VAR"
    assert event["reason"] == "unit test reason"
    assert event["change"] == "test-change"
    assert event["scope"] == "test-scope"
    assert event["ts"].endswith("Z")
    assert "actor" in event
    assert "codebase_commit" in event


def test_audit_bypass_log_multiple_appends(tmp_project_root: Path) -> None:
    """Multiple audit_bypass_log calls should append, not overwrite."""
    for i in range(3):
        append_bypass_log(tmp_project_root, f"VAR{i}", f"reason {i}", f"change{i}")

    audit_file = tmp_project_root / ".rddf" / "state" / ".bypass-audit.jsonl"
    lines = audit_file.read_text().strip().splitlines()
    assert len(lines) == 3
    env_vars = [json.loads(line)["env_var"] for line in lines]
    assert env_vars == ["VAR0", "VAR1", "VAR2"]


def test_audit_bypass_read_empty_returns_empty_array(tmp_project_root: Path) -> None:
    """audit_bypass_read should return [] when file doesn't exist."""
    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(tmp_project_root)
    result = run_bash_in_env(
        "source _lib/bypass_audit.sh && audit_bypass_read",
        env,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "[]"


def test_audit_bypass_log_rejects_missing_args(tmp_project_root: Path) -> None:
    """audit_bypass_log should fail when env_var or reason is empty."""
    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(tmp_project_root)

    # Missing reason
    result = run_bash_in_env(
        "source _lib/bypass_audit.sh && audit_bypass_log TEST_VAR ''",
        env,
    )
    assert result.returncode == 2
    assert "env_var and reason are required" in result.stderr

    # Missing env_var
    result = run_bash_in_env(
        "source _lib/bypass_audit.sh && audit_bypass_log '' 'reason'",
        env,
    )
    assert result.returncode == 2


def test_bypass_audit_check_warning_threshold(tmp_project_root: Path) -> None:
    """Threshold breach should emit WARNING (count > limit but <= 2x limit)."""
    for i in range(6):  # limit=3, 6 > 3 but < 6 = 2x3
        append_bypass_log(tmp_project_root, "ARCHIVE_ON_MAIN", f"r{i}", f"change{i}")

    findings = bypass_audit_check.run(tmp_project_root)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity.value == "WARNING"
    assert f.category == "bypass-audit"
    assert "ARCHIVE_ON_MAIN" in f.snippet
    assert "limit=3" in f.snippet


def test_bypass_audit_check_critical_threshold(tmp_project_root: Path) -> None:
    """Count > 2x limit should emit CRITICAL."""
    for i in range(11):  # 11 > 2*3 = 6 → CRITICAL
        append_bypass_log(tmp_project_root, "ARCHIVE_ON_MAIN", f"r{i}")

    findings = bypass_audit_check.run(tmp_project_root)
    assert len(findings) == 1
    assert findings[0].severity.value == "CRITICAL"


def test_bypass_audit_check_under_threshold_returns_empty(tmp_project_root: Path) -> None:
    """Count <= limit should emit no findings."""
    for i in range(3):  # 3 == limit → no finding
        append_bypass_log(tmp_project_root, "ARCHIVE_ON_MAIN", f"r{i}")

    findings = bypass_audit_check.run(tmp_project_root)
    assert findings == []


def test_bypass_audit_check_no_audit_file_returns_empty(tmp_project_root: Path) -> None:
    """Missing audit file should emit no findings (no false positives)."""
    findings = bypass_audit_check.run(tmp_project_root)
    assert findings == []


def test_bypass_audit_check_skips_malformed_lines(tmp_project_root: Path) -> None:
    """Malformed JSONL lines should be skipped silently, not crash."""
    audit_file = tmp_project_root / ".rddf" / "state" / ".bypass-audit.jsonl"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text(
        'not-valid-json\n'
        '{"ts": "2026-09-11T00:00:00Z", "env_var": "OK_VAR", "reason": "ok"}\n'
        'also-not-valid\n'
    )

    findings = bypass_audit_check.run(tmp_project_root)
    assert findings == []


def test_audit_bypass_monthly_count_aggregates_correctly(tmp_project_root: Path) -> None:
    """audit_bypass_monthly_count should aggregate current-month events by env_var."""
    audit_file = tmp_project_root / ".rddf" / "state" / ".bypass-audit.jsonl"
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = []
    for _ in range(3):
        events.append({"ts": now, "env_var": "VAR_A", "reason": "r"})
    for _ in range(2):
        events.append({"ts": now, "env_var": "VAR_B", "reason": "r"})
    events.append({"ts": "2020-01-01T00:00:00Z", "env_var": "VAR_A", "reason": "old"})

    audit_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(tmp_project_root)
    result = run_bash_in_env(
        "source _lib/bypass_audit.sh && audit_bypass_monthly_count",
        env,
    )
    assert result.returncode == 0
    counts = json.loads(result.stdout.strip())
    assert counts == {"VAR_A": 3, "VAR_B": 2}


def test_bypass_audit_check_default_threshold(tmp_project_root: Path) -> None:
    """Unknown env_var should use default threshold (10)."""
    for i in range(11):  # 11 > 10 = default → WARNING
        append_bypass_log(tmp_project_root, "UNKNOWN_BYPASS_VAR", f"r{i}")

    findings = bypass_audit_check.run(tmp_project_root)
    assert len(findings) == 1
    assert findings[0].severity.value == "WARNING"
    assert "limit=10" in findings[0].snippet