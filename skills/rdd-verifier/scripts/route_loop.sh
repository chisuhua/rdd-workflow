#!/usr/bin/env bash
# route_loop.sh <change_name> <classification_label> — Update loop_state, set route
#
# Usage: bash route_loop.sh <change_name> <implementation_gap|proposal_drift>
# Stdout: route decision line
# Exit: 0 if routed, 1 if halted (max_loops reached), 2 if usage error
#
# Per ADR-0034 §6: routes failure to plan/ship OR halts at max_loops.
set -euo pipefail

CHANGE_NAME="${1:-}"
LABEL="${2:-}"

if [ -z "$CHANGE_NAME" ] || [ -z "$LABEL" ]; then
    echo "❌ usage: route_loop.sh <change_name> <implementation_gap|proposal_drift>" >&2
    exit 2
fi

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

PROJECT_ROOT="$PROJECT_ROOT" python3 - "$CHANGE_NAME" "$LABEL" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

project_root = Path(os.environ.get("PROJECT_ROOT", "."))
sys.path.insert(0, str(project_root / "_lib"))
from _lib.verifier.loop_state import (
    load_loop_state,
    append_classification,
    save_loop_state,
)

change_name = sys.argv[1]
label = sys.argv[2]
state = load_loop_state(project_root)
if state is None:
    state = {
        "version": 1,
        "change": change_name,
        "loop_count": 0,
        "max_loops": int(os.environ.get("RDDF_VERIFIER_MAX_LOOPS", "3")),
        "classification_history": [],
        "codebase_commit_at_last_run": "",
        "route": "archive-ready",
        "halt_reason": None,
        "updated_at": "",
    }

state = append_classification(project_root, state, label, user_confirmed=True)

if state["loop_count"] >= state["max_loops"]:
    state["route"] = "halted"
    state["halt_reason"] = (
        f"max_loops={state['max_loops']} reached with label={label}"
    )
    save_loop_state(project_root, state)
    print(f"❌ HALTED: {state['halt_reason']}")
    sys.exit(1)

if label == "implementation_gap":
    state["route"] = "guide-ship"
elif label == "proposal_drift":
    state["route"] = "guide-plan"
else:
    print(f"❌ unknown label: {label}", file=sys.stderr)
    sys.exit(2)

save_loop_state(project_root, state)
print(
    f"→ Route: {state['route']} "
    f"(loop {state['loop_count']}/{state['max_loops']})"
)
PYEOF