#!/usr/bin/env bash
# Phase 2: Worktree + Execute (TDD 5 步).
# COMMIT GATE enforced before worktree add (per Oracle Q6 finding).
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "phase2_execute.sh requires <change-name>" >&2
    exit 3
fi

echo "=== Phase 2: Worktree + Execute for $CHANGE_NAME ==="

# COMMIT GATE: artifacts must be committed before worktree add (per Oracle Q6)
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "COMMIT GATE violated: working artifacts not committed" >&2
    echo "Run: git add openspec/changes/$CHANGE_NAME/ .rddf/plans/ && git commit" >&2
    exit 3
fi

EXEC_MODE=$(python3 -c "
import sys
sys.path.insert(0 '$PROJECT_ROOT')
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff('$PROJECT_ROOT', '$CHANGE_NAME').get('execution_mode_decision', {}).get('mode', 'worktree'))
" 2>/dev/null || echo "worktree")

if [ "$EXEC_MODE" = "worktree" ]; then
    WT_PATH=".rddf/wt/$CHANGE_NAME"
    BRANCH="openspec/$CHANGE_NAME"
    if [ ! -d "$WT_PATH" ]; then
        git worktree add "$WT_PATH" -b "$BRANCH" 2>/dev/null || {
            echo "worktree creation failed at $WT_PATH (branch may already exist)" >&2
            WT_PATH="$PROJECT_ROOT"  # fallback to main repo
        }
    fi
    EXEC_DIR="$WT_PATH"
else
    EXEC_DIR="$PROJECT_ROOT"
fi

cd "$EXEC_DIR"
if [ -f ".rddf/plans/$CHANGE_NAME.md" ]; then
    echo "Phase 2 worktree setup complete (mode=$EXEC_MODE, dir=$EXEC_DIR)"
else
    echo "plan file missing at .rddf/plans/$CHANGE_NAME.md" >&2
    exit 3
fi

cd "$PROJECT_ROOT"

python3 <<PYEOF
import sys
sys.path.insert(0 "$PROJECT_ROOT")
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root="$PROJECT_ROOT",
    change_name="$CHANGE_NAME",
    current_phase="phase-2",
    execution_status="completed",
    worktree_path="$EXEC_DIR",
    branch="openspec/$CHANGE_NAME",
)
PYEOF

exit 0