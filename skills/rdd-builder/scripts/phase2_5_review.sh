#!/usr/bin/env bash
# Phase 2.5: Review (4-option HARD pause dispatch).
# Exit 5 if revise/abandon (no archive).
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
    echo "phase2_5_review.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 2.5: Review for $CHANGE_NAME ==="

# --- Implementation truth before the decision -------------------------------
# This is the ONLY place in the flow that reads the handoff to decide whether
# to merge (per fix-builder-handoff-p2-lifecycle-truth D-1). It therefore has
# to show the implementation's REAL state — the task counter on disk — and
# flag a handoff that claims "completed" while tasks are unchecked (the
# legacy setup-time value).
PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../../.." && pwd)"
PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 - <<'PYEOF'
import os
import sys

sys.path.insert(0, os.environ["PKG_ROOT"])
from _lib.builder_handoff import implementation_state

state = implementation_state(os.environ["PROJECT_ROOT"], os.environ["CHANGE_NAME"])
done, total = state.tasks_done, state.tasks_total
mark = "已完成" if state.actually_complete else "未完成"
print(f"实现状态：tasks {done}/{total}（{mark}）   handoff execution_status="
      f"{state.handoff_status or '-'}")
if state.inconsistent:
    print("⚠️  不一致：handoff 声称 completed，但 tasks 未全勾"
          "（存量 setup 语义或写入方未修）⇒ 以 tasks 为准", file=sys.stderr)
PYEOF

# HARD pause: 4-option prompt (per spec §5.2, cannot bypass via --no-pause)
echo "1) merge  2) revise  3) abandon  4) archive"
if [ "${AUTO_APPROVE:-0}" = "1" ]; then
    choice="1"
else
    read -r -p "Choose [1-4]: " choice
fi

case "$choice" in
    1) REVIEW_STATUS="merge"; EXIT_CODE=0 ;;
    2) REVIEW_STATUS="revise"; EXIT_CODE=5 ;;
    3) REVIEW_STATUS="abandon"; EXIT_CODE=5 ;;
    4) REVIEW_STATUS="archive"; EXIT_CODE=0 ;;
    *) echo "invalid choice" >&2; exit 2 ;;
esac

python3 <<PYEOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from _lib.builder_handoff import update_builder_handoff
# Merge, not overwrite: a full write resets approval_status to its
# "pending" default and drops fields written by earlier phases.
update_builder_handoff(
    "$PROJECT_ROOT",
    "$CHANGE_NAME",
    current_phase="phase-2.5",
    review_status="$REVIEW_STATUS",
)
PYEOF

if [ "$REVIEW_STATUS" = "merge" ] || [ "$REVIEW_STATUS" = "archive" ]; then
    echo "Phase 2.5 done: review=$REVIEW_STATUS, proceeding to Phase 3"
    exit 0
else
    echo "Phase 2.5 done: review=$REVIEW_STATUS, halting (no archive)"
    exit $EXIT_CODE
fi