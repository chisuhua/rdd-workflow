#!/usr/bin/env python3
"""skills/rdd-quick/scripts/append_history.py

Reads a JSON entry from stdin, validates via _lib.quick_history, and atomically
appends one JSONL line to the audit log. Stdlib + jsonschema only.

Environment:
  RDDF_QUICK_HISTORY_FILE  default "<project_root>/.rddf/state/.quick-history.jsonl"

Exit codes:
  0  appended successfully
  1  schema validation failed (no write performed)
  2  usage error (empty stdin / invalid JSON / _lib not found)

Per design.md D8 zero-pollution: NO imports from skills._lib.*. The helper
imports _lib.quick_history directly via sys.path resolution.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Project root resolution: walk up from this script until _lib/ is found.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR
for _ in range(6):
    if (PROJECT_ROOT / "_lib").is_dir():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent
else:
    print("ERROR: cannot locate _lib/ from script path", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(PROJECT_ROOT))

# Import after sys.path mutation; pylint: disable=wrong-import-position
from _lib.quick_history import append_entry, validate_entry  # noqa: E402

HISTORY_FILE = Path(
    os.environ.get(
        "RDDF_QUICK_HISTORY_FILE",
        PROJECT_ROOT / ".rddf" / "state" / ".quick-history.jsonl",
    )
)


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: empty stdin (expected JSON entry)", file=sys.stderr)
        return 2

    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(entry, dict):
        print("ERROR: stdin JSON must be an object", file=sys.stderr)
        return 2

    if not validate_entry(entry):
        print("ERROR: entry fails quick-history schema v1 validation", file=sys.stderr)
        return 1

    append_entry(entry, HISTORY_FILE)
    print(f"appended: {entry.get('name', '<noname>')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())