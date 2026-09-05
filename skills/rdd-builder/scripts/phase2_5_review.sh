#!/usr/bin/env bash
# Phase 2.5: Review (4-option HARD pause dispatch).
# Exit 5 if revise/abandon (no archive).
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "phase2_5_review.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 2.5: Review for $CHANGE_NAME ==="

# HARD pause: 4-option prompt (per spec §5.2, cannot bypass via --no-pause)
echo "1) merge  2) revise  3) abandon  4) archive"
read -r -p "Choose [1-4]: " choice

case "$choice" in
    1) REVIEW_STATUS="merge"; EXIT_CODE=0 ;;
    2) REVIEW_STATUS="revise"; EXIT_CODE=5 ;;
    3) REVIEW_STATUS="abandon"; EXIT_CODE=5 ;;
    4) REVIEW_STATUS="archive"; EXIT_CODE=0 ;;
    *) echo "invalid choice" >&2; exit 2 ;;
esac

python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
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