#!/usr/bin/env bash
# scan_queue.sh — List implemented, task-complete changes from iteration.json
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE_FILE="$PROJECT_ROOT/.rddf/state/iteration.json"
MAX_CHANGES="${RDDF_VERIFIER_MAX_CHANGES:-10}"

[ -f "$STATE_FILE" ] || exit 0

STATE_FILE="$STATE_FILE" MAX_CHANGES="$MAX_CHANGES" python3 - <<'PY'
import json
import os

try:
    doc = json.loads(open(os.environ["STATE_FILE"], encoding="utf-8").read())
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    raise SystemExit(0)

eligible = []
for change in doc.get("changes", []):
    status = change.get("status")
    total = change.get("tasks_total") or 0
    done = change.get("tasks_done") or 0
    if status in {"in_worktree", "completed"} and total > 0 and done == total:
        name = change.get("name")
        if name:
            eligible.append(name)

print(" ".join(eligible[:max(0, int(os.environ["MAX_CHANGES"]))]))
PY