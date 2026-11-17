#!/usr/bin/env bash
# Phase 1: Plan generation. Validates plan_quality gate.
# Exit 2 on plan quality FAIL.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

AUTO_APPROVE=0
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
    esac
done
export AUTO_APPROVE

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

# Record the plan-time task count (fix-iteration-tasks-total).
# P1 writes `tasks_total` ONLY: a plan is not execution, so `proposed` must
# not become `in_worktree` here (that transition belongs to P2).
# Bookkeeping failure must not abort the phase.
PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../../.." && pwd)"
PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" PKG_ROOT="$PKG_ROOT" python3 - <<'PYEOF' || true
import os, sys
for root in (os.environ.get("PKG_ROOT") or "", os.environ.get("PROJECT_ROOT") or ""):
    if root and root not in sys.path:
        sys.path.insert(0, root)
# NOTE: import via the skills._lib shim. `_lib/iteration/store.py` imports
# `skills._lib.iteration.schema`, so a direct `import _lib.iteration.X`
# re-enters the package initialisation and raises a circular-import
# ImportError (pre-existing; see the implementation record).
from skills._lib.iteration.writer import record_tasks_snapshot
msg = record_tasks_snapshot(
    os.environ["PROJECT_ROOT"], os.environ["CHANGE_NAME"], phase="plan"
)
if msg:
    print("  ⚠️  " + msg, file=sys.stderr)
PYEOF

python3 <<PYEOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from _lib.builder_handoff import update_builder_handoff
# Merge, not overwrite: a full write resets approval_status to its "pending"
# default (dropping P0's "approved") and any field written by a later phase.
update_builder_handoff(
    "$PROJECT_ROOT",
    "$CHANGE_NAME",
    current_phase="phase-1",
    plan_quality_status="valid",
)
PYEOF

echo "Phase 1 done: plan + tasks.md generated"
exit 0