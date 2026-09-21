"""Data layer for env-bootstrap reports.

Public API:
    build_report(phase_1_detection, phase_2_diagnosis, phase_3_init_suggestion,
                 phase_4_guided_fix, exit_code, project_root, generated_at) -> dict
    write_report(report, path) -> None  (atomic via temp + rename, validates schema)
    load_report(path) -> dict | None
    validate_report(report) -> bool

Stdlib + jsonschema only. No imports from skills._lib.* (canonical layer per P1-1b).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import jsonschema


_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "env_bootstrap_report_schema.json"


def _load_schema() -> dict[str, Any]:
    """Load and cache the v1 schema."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def build_report(
    phase_1_detection: dict[str, Any],
    phase_2_diagnosis: dict[str, Any],
    phase_3_init_suggestion: list[str],
    phase_4_guided_fix: dict[str, Any],
    exit_code: int,
    project_root: str,
    generated_at: str,
) -> dict[str, Any]:
    """Construct an env-bootstrap report dict conforming to v1 schema."""
    return {
        "version": 1,
        "generated_at": generated_at,
        "project_root": project_root,
        "phase_1_detection": phase_1_detection,
        "phase_2_diagnosis": phase_2_diagnosis,
        "phase_3_init_suggestion": phase_3_init_suggestion,
        "phase_4_guided_fix": phase_4_guided_fix,
        "exit_code": exit_code,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    """Atomically write report to path. Validates against v1 schema first.

    Uses temp file + os.replace for atomicity. Raises jsonschema.ValidationError
    if report does not match schema.
    """
    validate_report(report)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file in same dir, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.tmp.", suffix=".json", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_report(path: Path) -> dict[str, Any] | None:
    """Load report from path. Returns None if file missing."""
    path = Path(path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_report(report: dict[str, Any]) -> bool:
    """Validate report against v1 schema. Returns True if valid, False otherwise."""
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    return validator.is_valid(report)


__all__ = ["build_report", "write_report", "load_report", "validate_report"]
