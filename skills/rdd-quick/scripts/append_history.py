#!/usr/bin/env python3
"""skills/rdd-quick/scripts/append_history.py

Reads a JSON entry from stdin, validates via _lib.quick_history, and atomically
appends one JSONL line to the audit log. Stdlib + jsonschema only.

Environment:
  RDDF_QUICK_HISTORY_FILE  default "<project_root>/.rddf/state/.quick-history.jsonl"

Exit codes:
  0  appended successfully
  1  schema validation failed (no write performed)
  2  usage error (empty stdin / invalid JSON)

Per design.md D8 zero-pollution: NO imports from skills._lib.*. The helper
imports _lib.quick_history directly via sys.path resolution.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# --- import bootstrap ONLY (probe anchor + sys.path) ---
# skills/rdd-quick/scripts/<this file> -> scripts -> rdd-quick -> skills -> <repo root>
# A fixed-depth anchor, NOT a directory-shape probe: the sibling skills/_lib/
# directory used to fool a walk-up loop into stopping at <repo>/skills/.
_SCRIPT_ROOT = Path(__file__).resolve().parents[3]
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

# --- project root resolution (single authority) ---
# _SCRIPT_ROOT only anchors the resolver's git probe; the resolver owns the answer.
from _lib._python_resolve_project_root import resolve_project_root  # noqa: E402
from _lib.quick_history import append_entry, validate_entry  # noqa: E402

PROJECT_ROOT = Path(resolve_project_root(start_dir=_SCRIPT_ROOT))

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