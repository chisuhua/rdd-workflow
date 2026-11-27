#!/usr/bin/env bash
# Phase 3: Archive, gated on the agent-produced verdict cache (ADR-0035).
#
# Exit codes (this script's own contract):
#   2 = usage error
#   3 = precondition failure — no worktree / branch without new commits /
#       merge failed / (lightweight) no commit on the branch, or the branch
#       is not merged in a tracked=false project
#   7 = the archive gate refused (missing, stale or incomplete verdict cache)
#       OR the openspec archive command itself failed
#
# In worktree mode the archive is delegated to archive_change, whose own
# returns are mapped: 0 → 0, 3 (gate refused) → 7, anything else → 3.
# In lightweight mode P3 runs an ENUMERATED inline sequence (it cannot
# delegate: archive_change requires a worktree) — AC gate → switch to the
# default branch → commit-ownership check → merge judgment → openspec
# archive → branch cleanup → archive-moves commit → iteration sync →
# post-archive cleanup.
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
    # ── lightweight mode: enumerated inline archive ─────────────────────────
    # archive_change cannot serve this mode — it requires an existing worktree
    # (_lib/archive.sh, the `wt_path` precondition).
    #
    # Until fix-lightweight-branch-and-archive this branch ran ONLY the AC
    # gate: no merge-status check, no branch cleanup, no iteration sync, no
    # post-archive cleanup. A change archived here left iteration.json stale
    # (never reaching the `archived` state) and could archive an
    # implementation that was still stranded unmerged on its branch.
    #
    # Step list (explicit; the omissions are deliberate — see ADR-0061's
    # Consequences: issue close, tasks-completion gate, L2 collection and the
    # tasks.md sidecar stay out of the lightweight path):
    #   (a) AC archive gate          (b) switch to default branch
    #   (c) commit-ownership check   (d) merge judgment / merge
    #   (e) openspec archive         (f) branch cleanup
    #   (g) commit archive moves     (h) iteration sync with the real sha
    #   (i) post-archive cleanup
    BRANCH="openspec/$CHANGE_NAME"
    DEFAULT_BRANCH=$(cd "$PROJECT_ROOT" && find_default_branch 2>/dev/null || echo "")
    if [ -z "$DEFAULT_BRANCH" ]; then
        echo "❌ lightweight: 无法确定默认分支（归档中止）" >&2
        exit 3
    fi

    OPENSPEC_TRACKED="true"
    if [ -f "$PROJECT_ROOT/.rddf/project.yaml" ] && [ -f "$PROJECT_ROOT/_lib/project_config.sh" ]; then
        # shellcheck source=/dev/null disable=SC1090
        source "$PROJECT_ROOT/_lib/project_config.sh"
        OPENSPEC_TRACKED=$(project_yaml_get "git.openspec_tracked" "true")
    fi

    # (a) AC archive gate — unchanged, and still first (cheap; a refusal must
    #     not have mutated anything yet).
    archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" || exit 7

    # (b) Land on the default branch BEFORE the refusal checks. A refusal must
    #     not leave the repo parked on the implementation branch: the contract
    #     is "after a refusal, `git branch --show-current` is still the
    #     default branch".
    switch_to_default_branch "$PROJECT_ROOT" "$DEFAULT_BRANCH" || exit 3

    # (c) Commit-ownership check — the lightweight counterpart of the worktree
    #     path's check_worktree_commits. A branch with no commit of its own is
    #     an empty shell: the verification anchor would then point at a commit
    #     that does not contain this change's work ("archived successfully"
    #     while the code was never committed).
    #     The creation point recorded by P2 makes that exact — "branch tip ==
    #     base" means nothing was committed, while a manually merged branch
    #     (required when openspec_tracked=false) still has tip != base.
    BRANCH_BASE_SHA=$(PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 -c "
import os, sys
if os.environ.get('PKG_ROOT'):
    sys.path.insert(0, os.environ['PKG_ROOT'])
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff(os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME'])
      .get('execution_mode_decision', {}).get('branch_base_sha', '') or '')
" 2>/dev/null || echo "")
    lightweight_commit_ownership_check "$PROJECT_ROOT" "$BRANCH" "$DEFAULT_BRANCH" "$BRANCH_BASE_SHA" || exit 3

    # (d) Merge-status judgment — same semantics as the worktree path, but the
    #     dirty criterion does NOT apply: there is no worktree here, and the
    #     main repo's dirty files may belong to another change. Judging by
    #     them would refuse a perfectly good archive and the guidance would
    #     push the user to commit somebody else's work. Main-repo dirt is
    #     reported and never refuses.
    if [ -n "$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=all 2>/dev/null)" ]; then
        echo "⚠️  lightweight: 主仓存在未提交改动（不据此拒绝 —— 它们可能属于别的 change）"
    fi
    if [ "$OPENSPEC_TRACKED" = "false" ] || [ "$OPENSPEC_TRACKED" = "False" ]; then
        # The spec forbids the archive to merge on this path, so an unmerged
        # implementation is REFUSED instead of being archived and then
        # silently left on a branch that is about to be deleted.
        # Three states consumed separately (ADR-0061 V-14): 0 allow / 1 refuse
        # / 2 allow + warning (the function printed it).
        _premerge_rc=0
        archive_premerge_check "$PROJECT_ROOT" "$BRANCH" "$DEFAULT_BRANCH" "" || _premerge_rc=$?
        if [ "$_premerge_rc" -eq 1 ]; then
            echo "❌ lightweight: '$BRANCH' 尚未合入 '$DEFAULT_BRANCH'，归档被拒绝" >&2
            exit 3
        fi
    else
        _before_merge=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "")
        merge_feature_branch "$PROJECT_ROOT" "$BRANCH" "$DEFAULT_BRANCH" "$CHANGE_NAME" || exit 3
        _after_merge=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "")
        verify_merge_result "$_before_merge" "$_after_merge" "$CHANGE_NAME" || exit 3
    fi

    # (e) openspec archive
    openspec archive "$CHANGE_NAME" --yes || {
        echo "openspec archive FAIL for $CHANGE_NAME" >&2
        exit 7
    }

    # (f) Branch cleanup. wt_path is EMPTY on purpose: there is no worktree,
    #     and the main repo must never be treated as one (`git worktree
    #     remove` on the main repo would delete the checkout itself).
    #     A failed cleanup only warns — the archive already succeeded, which
    #     is the same return-code semantics as the worktree path.
    cleanup_worktree_and_branch "$CHANGE_NAME" "$PROJECT_ROOT" "" "$BRANCH" || \
        echo "⚠️  归档已完成，但分支清理未完全成功（见上）"

    # (g) Commit the archive moves — ONLY when openspec/ is tracked. The
    #     helper short-circuits on openspec_tracked=false as well; not calling
    #     it at all is the caller-side half of that contract (2x2 matrix).
    if [ "$OPENSPEC_TRACKED" != "false" ] && [ "$OPENSPEC_TRACKED" != "False" ]; then
        commit_archive_moves "$CHANGE_NAME" "$PROJECT_ROOT" || true
    fi

    # (h) Iteration sync with the REAL sha (the default branch tip after the
    #     merge and the archive commit) — not an empty string, which is what
    #     the old lightweight path left behind by never calling this at all.
    _archive_sha=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "")
    mark_iteration_archived "$CHANGE_NAME" "$PROJECT_ROOT" "$_archive_sha"

    # (i) Post-archive cleanup (residual deleted tracked files + the
    #     improvement-approved.md sync). Best effort.
    post_archive_cleanup "$PROJECT_ROOT" "$CHANGE_NAME" || true
fi

python3 <<PYEOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from _lib.builder_handoff import update_builder_handoff
update_builder_handoff(
    "$PROJECT_ROOT",
    "$CHANGE_NAME",
    current_phase="phase-3",
    # Only here is "completed" true: the tasks are checked, the change is
    # verified and archived (Phase 2's setup used to write it — see
    # fix-builder-handoff-p2-lifecycle-truth).
    execution_status="completed",
    archive_status="archived",
)
PYEOF

echo "Phase 3 done: $CHANGE_NAME archived"
exit 0