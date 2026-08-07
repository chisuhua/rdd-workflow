"""Tests for state_schema_check (cat-1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Inject scripts dir + checks dir
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
_CHECKS_DIR = _SCRIPTS_DIR / "checks"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Finding, Severity  # noqa: E402
from checks.state_schema_check import run as run_check  # noqa: E402


def _write_state(tmp_path: Path, name: str, data: dict) -> Path:
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    f = state / name
    f.write_text(json.dumps(data))
    return f


def _valid_iteration() -> dict:
    return {
        "version": 5,
        "updated_at": "2026-08-07T00:00:00+00:00",
        "current_phase": "v2.1",
        "changes": [],
    }


def _setup_real_lib_with_iteration_schema(tmp_path: Path) -> None:
    real_lib = tmp_path / "_lib" / "schemas"
    real_lib.mkdir(parents=True)
    schema_path = real_lib / "iteration_schema.json"
    schema_path.write_text(json.dumps({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["version", "updated_at", "current_phase", "changes"],
        "additionalProperties": False,
        "properties": {
            "version": {"type": "integer"},
            "updated_at": {"type": "string"},
            "current_phase": {"type": "string"},
            "changes": {"type": "array"},
        },
    }))


def test_healthy_state_returns_no_findings(tmp_path: Path):
    _setup_real_lib_with_iteration_schema(tmp_path)
    _write_state(tmp_path, "iteration.json", _valid_iteration())
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_required_field_reports_critical(tmp_path: Path):
    _setup_real_lib_with_iteration_schema(tmp_path)
    bad = _valid_iteration()
    del bad["current_phase"]
    _write_state(tmp_path, "iteration.json", bad)
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.CRITICAL for f in findings)
    assert any("current_phase" in f.snippet for f in findings)


def test_no_state_directory_emits_no_findings(tmp_path: Path):
    """Empty project (fresh) is OK — INFO not finding."""
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_uses_real_lib_path_not_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify state check resolves _lib/schemas/ from real location, not shim."""
    _write_state(tmp_path, "iteration.json", _valid_iteration())

    # Create real _lib/schemas/ with valid iteration schema
    _setup_real_lib_with_iteration_schema(tmp_path)

    # Create shim skills/_lib/schemas/ with WRONG schema (catches if shim is used)
    shim_lib = tmp_path / "skills" / "_lib" / "schemas"
    shim_lib.mkdir(parents=True)
    (shim_lib / "iteration_schema.json").write_text('{"WRONG": "schema"}')

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(project_root=tmp_path)
    # If real path is used: passes. If shim: would fail with CRITICAL.
    assert findings == []