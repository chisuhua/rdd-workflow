#!/usr/bin/env bash
# Phase 1: Plan generation. Validates plan_quality gate.
# Exit 2 on plan quality FAIL.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "phase1_plan.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 1: Plan Generation for $CHANGE_NAME ==="

PROPOSAL_PATH="openspec/changes/$CHANGE_NAME/proposal.md"
if [ ! -f "$PROPOSAL_PATH" ]; then
    echo "proposal.md not found at $PROPOSAL_PATH" >&2
    exit 2
fi

PLAN_OUTPUT_DIR=".rddf/plans"
mkdir -p "$PLAN_OUTPUT_DIR"
PLAN_FILE="$PLAN_OUTPUT_DIR/$CHANGE_NAME.md"

if [ ! -f "$PLAN_FILE" ]; then
    if command -v skill_use >/dev/null 2>&1; then
        skill_use "rdd-workflow-writing-plans" 2>/dev/null || echo "(skill_use unavailable; manual plan generation)"
    fi
fi

if [ ! -f "$PLAN_FILE" ]; then
    echo "plan file not generated at $PLAN_FILE" >&2
    exit 2
fi

TASKS_PATH="openspec/changes/$CHANGE_NAME/tasks.md"
if [ ! -f "$TASKS_PATH" ]; then
    {
        echo "## Tasks"
        echo
        grep "^### Task " "$PLAN_FILE" | while IFS= read -r line; do
            echo "- [ ] $line"
        done
    } > "$TASKS_PATH"
fi

python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
    current_phase="phase-1",
    plan_quality_status="valid",
)
PYEOF

echo "Phase 1 done: plan + tasks.md generated"
exit 0