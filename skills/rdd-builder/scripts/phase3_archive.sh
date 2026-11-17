#!/usr/bin/env bash
# Phase 3: Archive, gated on the agent-produced verdict cache (ADR-0035).
#
# Exit codes (this script's own contract):
#   2 = usage error
#   3 = precondition failure — no worktree / branch without new commits /
#       merge failed
#   7 = the archive gate refused (missing, stale or incomplete verdict cache)
#       OR the openspec archive command itself failed
#
# In worktree mode the archive is delegated to archive_change, whose own
# returns are mapped: 0 → 0, 3 (gate refused) → 7, anything else → 3.
# In lightweight mode P3 runs the gate and the openspec archive itself.
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

# archive_gate_check uses $tasks_root to locate tasks.md and the verdict cache.
# A fresh `git worktree` carries neither openspec/ nor the gitignored
# .rddf/state/, so pick whichever root actually has tasks.md.
#
# CONTRACT (fix-verifier-gate-cache-root) — two roots, one anchor:
#
#   gate root  = $TASKS_ROOT — the change's ARTIFACTS (tasks.md, proposal.md)
#                and the CONTRACT root for the verdict cache.
#   state root = the canonical project root — the project REGISTRY
#                (.rddf/state/iteration.json; .rddf/state/ is gitignored, so a
#                linked worktree never carries it) and where the batch CLI
#                `rddf rdd-verify` writes its cache.
#
#   ANCHOR = the implementation branch tip:
#     git -C $TASKS_ROOT rev-parse --verify --quiet openspec/<change>
#   NOT `git rev-parse HEAD`. The branch tip is what the write side records
#   (_lib/verifier/branch.py::resolve_implementation_commit) and it is
#   ROOT-INDEPENDENT — the same SHA is visible from the main repo and from
#   every linked worktree. HEAD was wrong twice over: the write side never
#   recorded it, and in the openspec_tracked=false path the main repo has just
#   been switched to the default branch, so HEAD != branch tip and a perfectly
#   good cache was reported as stale.
#
#   DUAL-CACHE POLICY: the gate reads the gate root first and the state root
#   second. Both sides holding a cache is reported and the gate root wins
#   (never merged, never silently preferred). A cache on one side only is
#   used, and which side it came from is reported — this is why the write
#   side may stamp either root without breaking the gate.
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

# shellcheck source=/dev/null
source "$PKG_ROOT/_lib/archive.sh" 2>/dev/null || true

# --- Archive ----------------------------------------------------------------
# Worktree mode: delegate to archive_change — the single implementation. It
# owns the gate / merge / openspec archive / cleanup / iteration sync, and
# (unlike the previous inline path) it archives in the MAIN repo, which is the
# authoritative openspec/ when that directory is untracked
# (git.openspec_tracked = false). Archiving inside the worktree wrote the
# record into a throwaway copy that the worktree cleanup then deleted.
#
# The archive gate lives inside archive_change, so P3 must NOT run its own
# gate here: the two would use different roots (archive_gate_check's
# tasks_root vs archive_change's choice) and could disagree.
#
# CONTRACT — where the verdict cache is stamped. The gate compares the cache's
# codebase_commit with the implementation BRANCH TIP (root-independent, so it
# no longer depends on which root the gate reads from):
#   openspec_tracked=true  → gate root = the worktree  ⇒ verify in the worktree
#   openspec_tracked=false → gate root = the main repo  ⇒ verify in the main repo
#                             (that branch exists precisely because openspec/ is
#                              untracked, so the worktree has neither tasks.md
#                              nor .rddf/state/verifier/)
# In lightweight mode the gate root is $TASKS_ROOT (the root that holds
# openspec/changes/<name>/tasks.md).
# The canonical state root is read as a fallback, so a cache stamped by the
# batch CLI `rddf rdd-verify` (which always writes to the canonical root) is
# found as well — see the CONTRACT block above.
#
# Failed-AC policy is deliberately the gate's, not P3's: a cache whose verdict
# contains failed ACs only WARNS and archiving proceeds, unless
# STRICT_AC_GATE=yes (then the gate blocks and P3 exits 7). Both states are
# pinned by tests.
#
# Return-code mapping (archive_change → phase3):
#   0 → 0   archived
#   3 → 7   the archive gate refused (missing / stale / incomplete verdict cache)
#   1 → 3   precondition failure (no worktree, branch without new commits,
#            merge failed, openspec archive failed)
if [ "$EXEC_MODE" = "worktree" ]; then
    if ! declare -f archive_change >/dev/null 2>&1; then
        echo "❌ archive_change unavailable: failed to source $PKG_ROOT/_lib/archive.sh" >&2
        exit 7
    fi
    # archive_change runs `openspec archive` against the CALLER's cwd, so the
    # project root has to be the cwd before delegating.
    cd "$PROJECT_ROOT"
    rc=0
    archive_change "$CHANGE_NAME" || rc=$?
    case "$rc" in
        0) ;;
        3) echo "❌ archive gate refused the archive for $CHANGE_NAME" >&2; exit 7 ;;
        *) echo "❌ archive_change failed for $CHANGE_NAME (exit $rc)" >&2; exit 3 ;;
    esac
else
    # lightweight mode: inline archive. archive_change cannot serve this mode —
    # it requires an existing worktree (_lib/archive.sh:589-592).
    # KNOWN GAP (documented in .rddf/improvements/fix-worktree-archive-path.md):
    # this branch runs neither the archive_change cleanup nor its iteration
    # sync; the gate below is the only pre-archive check.
    archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" || exit 7
    openspec archive "$CHANGE_NAME" --yes 2>/dev/null || {
        echo "openspec archive FAIL for $CHANGE_NAME" >&2
        exit 7
    }
fi

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