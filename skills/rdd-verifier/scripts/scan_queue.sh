#!/usr/bin/env bash
# scan_queue.sh — List ship-done changes from iteration.json
#
# Usage: PROJECT_ROOT=/path bash scan_queue.sh
# Stdout: space-separated change names
# Exit: 0 always (empty stdout if no changes)
#
# Per ADR-0034 §4.1: discovery backend for rdd-verifier state machine.
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE_DIR="$PROJECT_ROOT/.rddf/state"
MAX_CHANGES="${RDDF_VERIFIER_MAX_CHANGES:-10}"

if [ ! -f "$STATE_DIR/iteration.json" ]; then
    exit 0
fi

python3 - "$STATE_DIR/iteration.json" "$MAX_CHANGES" <<'PYEOF'
import json
import sys

state_file, max_changes = sys.argv[1], int(sys.argv[2])
try:
    doc = json.loads(open(state_file, encoding="utf-8").read())
except Exception:
    sys.exit(0)

queue = [
    c["name"] for c in doc.get("changes", [])
    if c.get("status") == "ship-done"
][:max_changes]
print(" ".join(queue))
PYEOF