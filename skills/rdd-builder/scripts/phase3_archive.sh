#!/usr/bin/env bash
# Phase 3: Archive, gated on the agent-produced verdict cache (ADR-0035).
# Exit codes: 2 = usage, 3 = worktree/mode precondition, 7 = archive gate or
# openspec archive failure.
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
    echo "phase3_archive.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 3: Archive for $CHANGE_NAME ==="

# --- Execution mode + tasks root -------------------------------------------
# Resolve the rdd-workflow package root — the directory that CONTAINS `_lib/`.
# It is NOT the project root: in a user project `_lib/` lives under the installed
# package (~/.agents/skills/rdd-workflow or <project>/.opencode/skills/rdd-workflow).
# Order mirrors phase2_execute.sh: the package owning this script wins (dev
# checkout / symlinked global install), then project-local, then global.
_resolve_pkg_root() {
    local c here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
    if [ -d "$here/_lib" ]; then printf '%s' "$here"; return 0; fi
    for c in \
        "$PROJECT_ROOT/.opencode/skills/rdd-workflow" \
        "$HOME/.agents/skills/rdd-workflow" \
        "$HOME/.agents/skills"
    do
        if [ -n "$c" ] && [ -d "$c/_lib" ]; then printf '%s' "$c"; return 0; fi
    done
    return 1
}
PKG_ROOT="$(_resolve_pkg_root || true)"

# archive_gate_check uses $tasks_root to locate tasks.md, the verdict cache and
# `git rev-parse HEAD`. A fresh `git worktree` carries neither openspec/ nor the
# gitignored .rddf/state/, so pick whichever root actually has tasks.md.
EXEC_MODE=$(PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 -c "
import os, sys
if os.environ.get('PKG_ROOT'):
    sys.path.insert(0, os.environ['PKG_ROOT'])
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff(os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME']).get('execution_mode_decision', {}).get('mode', 'worktree'))
" 2>/dev/null || echo "worktree")

WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
TASKS_ROOT="$PROJECT_ROOT"
if [ "$EXEC_MODE" = "worktree" ]; then
    [ -d "$WT_PATH" ] || { echo "worktree not found at $WT_PATH" >&2; exit 3; }
    if [ -f "$WT_PATH/openspec/changes/$CHANGE_NAME/tasks.md" ]; then
        TASKS_ROOT="$WT_PATH"
    fi
fi

# --- Archive gate (ADR-0035 / ADR-0045) ------------------------------------
# Verification is produced by the executing agent via the rdd-verifier skill;
# P3 only checks that a complete, non-stale verdict cache exists. The previous
# implementation pre-called a verifier script that does not exist and then
# treated its never-set exit code as "passed". The staging helper is no
# substitute either: it only writes a context file, and its exit 0 means
# "agent verification pending", not "verified".
#
# Failed-AC policy is deliberately the gate's, not P3's: a cache whose verdict
# contains failed ACs only WARNS and archiving proceeds, unless STRICT_AC_GATE=yes
# (then the gate blocks and P3 exits 7). Both states are pinned by tests.
# shellcheck source=/dev/null
source "$PKG_ROOT/_lib/archive.sh" 2>/dev/null || true
if ! declare -f archive_gate_check >/dev/null 2>&1; then
    echo "❌ archive_gate_check unavailable: failed to source $PKG_ROOT/_lib/archive.sh" >&2
    exit 7
fi
archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" || exit 7

# --- Archive ---------------------------------------------------------------
if [ "$EXEC_MODE" = "worktree" ]; then
    cd "$WT_PATH" || { echo "worktree not found at $WT_PATH" >&2; exit 3; }
fi

openspec archive "$CHANGE_NAME" --yes 2>/dev/null || {
    echo "openspec archive FAIL for $CHANGE_NAME" >&2
    exit 7
}

bash _lib/post_archive_cleanup.sh "$CHANGE_NAME" "$PROJECT_ROOT" 2>/dev/null || echo "(cleanup script deferred)"

python3 <<PYEOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from _lib.builder_handoff import update_builder_handoff
update_builder_handoff(
    "$PROJECT_ROOT",
    "$CHANGE_NAME",
    current_phase="phase-3",
    archive_status="archived",
)
PYEOF

echo "Phase 3 done: $CHANGE_NAME archived"
exit 0