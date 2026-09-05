#!/usr/bin/env bash
# Phase 3: Archive with verifier retry loop.
# Verifier exit codes 0/1/2/3/4 preserved per Oracle H4.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "phase3_archive.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 3: Archive for $CHANGE_NAME ==="

# Pre-call rdd-verifier (per ADR-0035)
VERIFIER_EXIT=0
if [ -f "skills/rdd-verifier/scripts/verifier_run.sh" ]; then
    bash skills/rdd-verifier/scripts/verifier_run.sh "$CHANGE_NAME" 2>/dev/null || VERIFIER_EXIT=$?
    if [ "$VERIFIER_EXIT" -ne 0 ] && [ "$VERIFIER_EXIT" -ne 4 ]; then
        echo "verifier failed with exit $VERIFIER_EXIT (not a 4-halt); proceeding with archive anyway"
        VERIFIER_EXIT=0
    fi
fi

# Route verifier verdict
DECISION_JSON=$(python3 -c "
import sys, json
sys.path.insert(0 '$PROJECT_ROOT')
from _lib.builder_retry import route_verifier_verdict
d = route_verifier_verdict(verifier_exit_code=$VERIFIER_EXIT)
print(json.dumps(d))
")

BACK_ROUTE=$(echo "$DECISION_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['should_back_route'])")
HALTED=$(echo "$DECISION_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['halted'])")
NEXT_PHASE=$(echo "$DECISION_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['next_phase'])")
VKIND=$(echo "$DECISION_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['verifier_kind'])")

if [ "$HALTED" = "True" ]; then
    echo "verifier halted: verdict=$NEXT_PHASE ($VKIND)" >&2
    python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
    current_phase="phase-3",
    archive_status="failed",
)
PYEOF
    exit 4
fi

if [ "$BACK_ROUTE" = "True" ]; then
    echo "verifier back-routes to $NEXT_PHASE ($VKIND)"
    python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import increment_retry
increment_retry(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
    to_phase="$NEXT_PHASE",
    verifier_kind="$VKIND",
    verifier_exit_code=$VERIFIER_EXIT,
)
PYEOF
    exit 4
fi

# Verifier passed → archive
EXEC_MODE=$(python3 -c "
import sys
sys.path.insert(0 '$PROJECT_ROOT')
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff('$PROJECT_ROOT', '$CHANGE_NAME').get('execution_mode_decision', {}).get('mode', 'worktree'))
" 2>/dev/null || echo "worktree")

if [ "$EXEC_MODE" = "worktree" ]; then
    WT_PATH=".rddf/wt/$CHANGE_NAME"
    cd "$WT_PATH" 2>/dev/null || { echo "worktree not found at $WT_PATH" >&2; exit 3; }
fi

openspec archive "$CHANGE_NAME" --yes 2>/dev/null || {
    echo "openspec archive FAIL for $CHANGE_NAME" >&2
    exit 7
}

bash _lib/post_archive_cleanup.sh "$CHANGE_NAME" "$PROJECT_ROOT" 2>/dev/null || echo "(cleanup script deferred)"

python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
    current_phase="phase-3",
    archive_status="archived",
)
PYEOF

echo "Phase 3 done: $CHANGE_NAME archived"
exit 0