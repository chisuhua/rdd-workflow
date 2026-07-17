#!/usr/bin/env python3
"""Entry-point script for skills/_lib/execute_step7.sh::run_step7_report.

Reads env vars:
- PROJECT_ROOT (required) — absolute path to project root
- CHANGE_NAME (required) — name of the change being executed

All values flow through os.environ only — no bash string interpolation.
Oracle C1 safe.
"""
import os
import sys
from pathlib import Path


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    change_name = os.environ.get("CHANGE_NAME")

    if not project_root or not change_name:
        print("ERROR: PROJECT_ROOT and CHANGE_NAME env vars required", file=sys.stderr)
        sys.exit(1)

    # Compute repo root from this script's location (grandparent of skills/_lib/)
    _repo_root = str(Path(__file__).resolve().parent.parent.parent)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

    from skills.execute.scripts import execute_step7 as es7
    es7.run_step7_report(project_root, change_name)


if __name__ == "__main__":
    main()
