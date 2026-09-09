#!/usr/bin/env bash
# rdd-planner stage exit: emit .planner-handoff.json with awaiting_builder list
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "planner_stage_exit.sh requires <change-name>" >&2
    exit 2
fi

if [ ! -d "openspec/changes/$CHANGE_NAME" ]; then
    echo "openspec/changes/$CHANGE_NAME not found" >&2
    exit 2
fi

PROPOSALS=$(python3 -c "
import json
from pathlib import Path
state = Path('.rddf/state/.planner-state.json')
if state.exists():
    d = json.loads(state.read_text())
    print('\n'.join(d.get('active_projects', [])))
" 2>/dev/null || true)
FEATURES=$(rddf roadmap list-features 2>/dev/null | grep -oE 'feat-[a-zA-Z0-9-]+' | head -10 || true)
CURRENT_SPRINT="sprint-$(date -u +%Y-%m)"
APPROVED=$(rddf status --json 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(sum(1 for c in d.get('changes', []) if c.get('status')=='approved'))" 2>/dev/null || echo "0")
AWAITING="add-$CHANGE_NAME"

export PROJECT_ROOT PROPOSALS_READY="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" FEATURES_ACTIVE="$FEATURES" CURRENT_SPRINT AWAITING_BUILDER="$AWAITING"

python3 -m _lib.planner_handoff
echo "planner stage exit complete: $AWAITING -> rdd-builder"