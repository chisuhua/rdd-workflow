"""skills/propose/scripts/propose_quality_hook.py - Phase 4 quality hook.

Wires propose_quality_check.run_all_checks into the propose flow.
Called by propose.md Phase 4 after artifact creation.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[3])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from skills._lib.arch_quality_gate import is_strict_mode  # noqa: E402
from skills.propose.scripts.propose_quality_check import run_all_checks  # noqa: E402


PROPOSE_QUALITY_SCHEMA_VERSION = 1


def run_quality_check(project_root: str, change_name: str) -> dict[str, Any]:
    """Run all 5 structural checks and persist a machine-readable report.

    Returns the report dict and writes it to
    <project_root>/.rddf/state/propose-quality.json.
    """
    warnings = run_all_checks(change_name, project_root)
    strict_mode = is_strict_mode("STRICT_PROPOSE_GATE")
    report = {
        "schema_version": PROPOSE_QUALITY_SCHEMA_VERSION,
        "change": change_name,
        "warnings": warnings,
        "checked_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "strict_mode": strict_mode,
        "check_count": 5,
        "passed_count": 5 - len(warnings),
    }
    report_path = os.path.join(project_root, ".rddf", "state", "propose-quality.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return report


def invoke_from_propose_phase4(change_name: str) -> int:
    """Bash-callable entrypoint.

    Reads PROJECT_ROOT from environment. Prints warnings and exits:
      - 0 by default, or when strict + no warnings
      - 1 when STRICT_PROPOSE_GATE=yes and there are warnings
    """
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    report = run_quality_check(project_root, change_name)
    warnings = report["warnings"]

    if warnings:
        print(f"⚠️  Quality warnings for '{change_name}':")
        for w in warnings:
            print(f"   - {w}")
        if report["strict_mode"]:
            print("❌ STRICT_PROPOSE_GATE=yes: exiting with error")
            return 1
        print("ℹ️  Set STRICT_PROPOSE_GATE=yes to upgrade warnings to errors")
    else:
        print(f"✅ '{change_name}' passes all quality checks")

    return 0


if __name__ == "__main__":
    change_name = os.environ.get("CHANGE_NAME") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not change_name:
        print("❌ CHANGE_NAME or positional argument required", file=sys.stderr)
        sys.exit(2)
    sys.exit(invoke_from_propose_phase4(change_name))
