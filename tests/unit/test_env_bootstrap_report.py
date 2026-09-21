"""Unit tests for _lib/env_bootstrap_report.py data layer + scripts/detect_environment.py + diagnose.py + guided_fix.py.

Tests cover:
- Schema v1 validity (Task 1)
- build_report / write_report / load_report / validate_report (Task 1)
- Phase 1 detect_* functions (Task 2)
- Phase 2 classify_finding (Task 3)
- Phase 4 run_fix / run_guided_fix (Task 4)

Stdlib + pytest only. No external test deps.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure _lib + scripts are importable from the worktree root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# ---- Task 1: Schema + data layer ----

def test_schema_v1_exists_and_loads():
    """Schema file exists, parses as JSON, declares version: 1."""
    schema_path = PROJECT_ROOT / "_lib" / "schemas" / "env_bootstrap_report_schema.json"
    assert schema_path.is_file(), f"Schema not found: {schema_path}"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data.get("version") == 1


def test_build_report_produces_all_required_fields():
    """build_report returns dict with all required top-level keys."""
    from _lib.env_bootstrap_report import build_report
    phase_1 = {"is_git_repo": True, "has_rddf_dir": False, "language_hints": ["python"]}
    phase_2 = {"doctor_invoked": True, "total_findings": 1, "auto_fixable": 1, "user_decision": 0, "manual_only": 0, "findings": []}
    phase_3 = ["rddf init"]
    phase_4 = {"executed": [], "skipped": [], "manual_required": []}
    report = build_report(phase_1, phase_2, phase_3, phase_4, exit_code=0, project_root="/tmp/test", generated_at="2026-09-22T00:00:00Z")

    for key in ("version", "generated_at", "project_root", "phase_1_detection",
                "phase_2_diagnosis", "phase_3_init_suggestion", "phase_4_guided_fix", "exit_code"):
        assert key in report, f"Missing required field: {key}"
    assert report["version"] == 1
    assert report["exit_code"] == 0


def test_write_report_creates_file_atomically(tmp_path):
    """write_report creates the file atomically (no leftover .tmp)."""
    from _lib.env_bootstrap_report import build_report, write_report
    report = build_report(
        {"is_git_repo": True}, {"doctor_invoked": False, "total_findings": 0}, [],
        {"executed": [], "skipped": [], "manual_required": []},
        exit_code=0, project_root="/tmp/test", generated_at="2026-09-22T00:00:00Z"
    )
    report_path = tmp_path / "report.json"
    write_report(report, report_path)
    assert report_path.is_file()
    # No leftover temp file
    leftovers = list(tmp_path.glob("*.tmp.*"))
    assert not leftovers, f"Leftover temp files: {leftovers}"
    # File content is valid JSON
    parsed = json.loads(report_path.read_text(encoding="utf-8"))
    assert parsed["version"] == 1


def test_load_report_round_trips(tmp_path):
    """write_report → load_report deep-equal."""
    from _lib.env_bootstrap_report import build_report, write_report, load_report
    original = build_report(
        {"is_git_repo": True, "language_hints": ["python"]},
        {"doctor_invoked": True, "total_findings": 1, "auto_fixable": 1, "user_decision": 0, "manual_only": 0, "findings": [{"category": "ai-context-bootstrap", "message": "未部署"}]},
        ["rddf setup ai-context"],
        {"executed": [{"finding": "未部署", "command": "rddf setup ai-context --yes", "status": "success"}], "skipped": [], "manual_required": []},
        exit_code=1, project_root="/tmp/test", generated_at="2026-09-22T00:00:00Z"
    )
    report_path = tmp_path / "report.json"
    write_report(original, report_path)
    loaded = load_report(report_path)
    assert loaded == original


def test_validate_report_rejects_missing_field():
    """validate_report rejects report missing a required field."""
    from _lib.env_bootstrap_report import validate_report
    bad = {"version": 1, "generated_at": "now", "project_root": "/x"}  # missing phase_*
    assert not validate_report(bad)


# ---- Task 2: Phase 1 detect_* functions ----

def test_detect_git_repo_true_for_repo_with_git_dir(tmp_path):
    """detect_git_repo returns True when .git/ exists."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from detect_environment import detect_git_repo
    (tmp_path / ".git").mkdir()
    assert detect_git_repo(tmp_path) is True


def test_detect_language_python_for_pyproject_toml(tmp_path):
    """detect_language returns ['python'] when pyproject.toml exists."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from detect_environment import detect_language
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert "python" in detect_language(tmp_path)


def test_detect_ai_config_files_finds_agents_md(tmp_path):
    """detect_ai_config_files returns AGENTS.md when present."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from detect_environment import detect_ai_config_files
    (tmp_path / "AGENTS.md").write_text("# agents\n")
    found = detect_ai_config_files(tmp_path)
    assert any("AGENTS.md" in p for p in found)


# ---- Task 3: Phase 2 classify_finding ----

def test_classify_finding_auto_fixable_ai_context_undeployed():
    """Finding ai-context-bootstrap: 未部署 → 'auto-fixable'."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from diagnose import classify_finding
    finding = {"category": "ai-context-bootstrap", "severity": "warning", "message": "未部署 Layer 0 协议块"}
    assert classify_finding(finding) == "auto-fixable"


def test_classify_finding_user_decision_gitignore_missing():
    """Finding gitignore → 'user-decision'."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from diagnose import classify_finding
    finding = {"category": "gitignore", "severity": "warning", "message": "openspec/ 缺失"}
    assert classify_finding(finding) == "user-decision"


# ---- Task 4: Phase 4 run_fix / run_guided_fix ----

def test_run_fix_success_returns_executed():
    """run_fix with successful command returns status='success'."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from guided_fix import run_fix
    finding = {"message": "未部署 Layer 0"}
    result = run_fix(finding, ["true"], target_root="/tmp", timeout=5)
    assert result["status"] == "success"
    assert result["finding"] == "未部署 Layer 0"


def test_run_fix_failure_returns_failed():
    """run_fix with failing command returns status='failed'."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from guided_fix import run_fix
    finding = {"message": "块已陈旧"}
    result = run_fix(finding, ["false"], target_root="/tmp", timeout=5)
    assert result["status"] == "failed"


def test_run_fix_aggregates_into_executed_list():
    """run_guided_fix with 2 findings (1 success, 1 fail) populates executed[]."""
    sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-env-bootstrap" / "scripts"))
    from guided_fix import run_guided_fix
    findings = [
        {"message": "未部署 Layer 0"},
        {"message": "块已陈旧"},
    ]
    commands = [["true"], ["false"]]
    cmd_iter = iter(commands)

    def fix_command_for(f):
        return next(cmd_iter)

    result = run_guided_fix(findings, "/tmp", fix_command_for, auto_fix=True)
    assert len(result["executed"]) == 2
    statuses = [e["status"] for e in result["executed"]]
    assert "success" in statuses
    assert "failed" in statuses
