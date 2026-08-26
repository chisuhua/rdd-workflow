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

SCRIPT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)"
PROJECT_ROOT="$PROJECT_ROOT" SCRIPT_REPO_ROOT="$SCRIPT_REPO_ROOT" python3 - "$CHANGE_NAME" "$LABEL" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

project_root = Path(os.environ["PROJECT_ROOT"])
sys.path.insert(0, os.environ["SCRIPT_REPO_ROOT"])
from _lib.verifier.loop_state import (
    load_loop_state,
    append_classification,
    save_loop_state,
)

change_name = sys.argv[1]
label = sys.argv[2]

# Validate label BEFORE mutating state (schema enum check would raise otherwise)
VALID_LABELS = ("implementation_gap", "proposal_drift")
if label not in VALID_LABELS:
    print(f"❌ unknown label: {label}", file=sys.stderr)
    sys.exit(2)

state = load_loop_state(project_root, change_name)
if state is None:
    from _lib.verifier.loop_state import init_loop_state
    state = init_loop_state(
        project_root,
        change_name,
        max_loops=int(os.environ.get("RDDF_VERIFIER_MAX_LOOPS", "3")),
    )

state = append_classification(project_root, state, change_name, label, user_confirmed=True)

if state["loop_count"] >= state["max_loops"]:
    state["route"] = "halted"
    state["halt_reason"] = (
        f"max_loops={state['max_loops']} reached with label={label}"
    )
    save_loop_state(project_root, state, change_name)
    print(f"❌ HALTED: {state['halt_reason']}")
    sys.exit(1)

if label == "implementation_gap":
    state["route"] = "guide-ship"
elif label == "proposal_drift":
    state["route"] = "guide-plan"

save_loop_state(project_root, state, change_name)
print(
    f"→ Route: {state['route']} "
    f"(loop {state['loop_count']}/{state['max_loops']})"
)
PYEOF