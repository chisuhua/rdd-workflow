#!/usr/bin/env bats
# tests/integration/test_rdd_quick_isolation.bats
# Zero-pollution invariant tests for rdd-quick (per design.md D8).
#
# Hash-locks the four files that MUST remain byte-identical pre- and post-
# implementation. Captured at proposal time; assertion compares post-implementation
# state against the locked baseline.
#
# Per design.md D8 zero-pollution: this file NEVER writes to openspec/changes/
# or .rddf/wt/ and only READS the locked files.

load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
}

# Baseline sha256 values captured BEFORE any rdd-quick file was created.
# These are the pre-implementation state hashes.
# Note (2026-09-11): LOCKED_ARCHIVE_SH recaptured after bypass-audit-mechanism wired.
# Per the change: archive_gate_check's SKIP_RDD_VERIFIER branch now calls
# audit_bypass_log when RDDF_VERIFIER_BYPASS_REASON is set (per bypass-audit-mechanism
# improvement). The rdd-quick zero-pollution invariant (this test) is preserved:
# rdd-quick does NOT invoke archive_gate_check's SKIP_RDD_VERIFIER branch
# (rdd-quick is bypass-path per ADR-0047), so the byte change here is an additive
# audit hook with zero impact on rdd-quick's execution semantics.
# Note (2026-09-28): LOCKED_ARCHIVE_SH + LOCKED_RDD_PLANNER_ROLE_BLOCK recaptured
# again after a series of additive-only commits (29f1530 file-presence guard,
# c043e0b re-archive guard, 824b518 guide-polling回路). Per the same principle:
# rdd-quick zero-pollution invariant preserved (additive audit hooks +
# new owned boundaries, no rdd-quick execution semantics touched). This is the
# v2.1-fix-rdd-quick-archive-verifier-gaps baseline sync.
# Note (2026-11-14): LOCKED_ARCHIVE_SH recaptured after consolidate-verifier-state.
# The change touches ONE line group only: the verdict-cache path inside
# archive_gate_check (`.rddf/state/.ac-verdict-*` → `.rddf/state/verifier/.ac-verdict-*`,
# plus the matching user-facing message). The rdd-quick zero-pollution invariant is
# preserved: rdd-quick is the bypass path (per ADR-0047) and never reads a verdict
# cache — for it the gate's verdict lookup is a miss before and after the change.
# Pre-consolidation caches are not orphaned: `rddf rdd-verify` moves legacy files
# into the new namespace before the gate looks for them.
# Note (2026-11-16): LOCKED_ARCHIVE_SH recaptured after fix-p3-verifier-gate.
# The change touches ONE line group only: the `openspec_tracked=false` branch of
# archive_change gains `archive_gate_check` before `openspec archive` (it used to
# return 0 before reaching the gate at step 2.5). The rdd-quick zero-pollution
# invariant is preserved: rdd-quick archives via the same false branch only when
# openspec is untracked, and it is the bypass path (ADR-0047) — for it the gate's
# verdict lookup is now an explicit rejection instead of a silent pass, which is
# the fix itself. rdd-quick callers can still bypass with the audited
# SKIP_RDD_VERIFIER + RDDF_VERIFIER_BYPASS_REASON pair.
# Note (2026-11-16, fix-worktree-archive-path): LOCKED_ARCHIVE_SH recaptured once
# more. The change touches ONE line group: the tracked branch's gate call drops
# its `>/dev/null` so a refused archive states why (the openspec_tracked=false
# branch already behaved that way). rdd-quick still never reaches that call —
# it archives through the false branch, which is the bypass path (ADR-0047).
# Note (2026-11-17, fix-verifier-gate-cache-root): LOCKED_ARCHIVE_SH recaptured.
# The change touches the AC-verification block of archive_gate_check only:
#   * the freshness anchor is now the implementation BRANCH TIP
#     (`git rev-parse --verify --quiet openspec/<change>`) instead of HEAD —
#     this is what openspec/specs/verifier-lifecycle/spec.md:98-100 already
#     requires ("Arbitrary execution root HEAD SHALL NEVER be used as an
#     archive authorization commit");
#   * the verdict cache is looked up in the gate root first and the canonical
#     state root second, and the integrity helper receives the two roots
#     explicitly instead of through one env var.
# rdd-quick zero-pollution invariant preserved: rdd-quick is the bypass path
# (ADR-0047) — it never writes a verdict cache, so for it the lookup is a miss
# (and then the audited bypass) before and after the change.
# Note (2026-11-18, fix-worktree-archive-branch-merge rework): LOCKED_ARCHIVE_SH
# recaptured (6th time). The change closes four implementation gaps against
# ADR-0061's signed-off contract: the call site now consumes the trunk gate's
# THREE states separately (state 2 = "cannot decide" must not be folded into a
# refusal), the ref-missing path no longer prints a merge command, a
# non-repository is classified as "cannot decide" instead of "branch missing",
# and the dirty-worktree guidance is forked by "the branch has commits or not".
# rdd-quick still never reaches those paths (it is the bypass path) ⇒ the
# invariant holds.
# Note (2026-11-17, fix-worktree-archive-branch-merge): LOCKED_ARCHIVE_SH
# recaptured. The change touches the AC-verification block and the cleanup
# helper of archive.sh: the freshness anchor is now the implementation branch
# tip, the verdict cache is looked up in the gate root first and the canonical
# state root second, a new `archive_premerge_check` (the "trunk gate") refuses
# an archive whose implementation branch is not merged, and the cleanup helper
# reports its three states instead of always printing success. rdd-quick still
# never reaches those paths (it is the bypass path) ⇒ the invariant holds.
# Note (2026-11-18): recaptured again by fix-lightweight-branch-and-archive,
# which adds the lightweight mode's branch helpers
# (`lightweight_branch_prepare` / `lightweight_commit_ownership_check`) to the
# same file. rdd-quick's own path is untouched.
# Note (2026-11-18, fix-archive-cleanup-tracked-false): recaptured (8th time).
# The change adds ONE call in `archive_change`: the `openspec_tracked: false`
# early-return branch now runs `post_archive_cleanup "$main_root" "$name"`
# (it previously ran only at step 9 of the tracked path, so in a tracked=false
# project the cleanup never ran and `.rddf/plans/<name>.md` survived its own
# archive). rdd-quick still never reaches `archive_change` at all (it is the
# bypass path — it never archives), so the invariant holds.
LOCKED_ARCHIVE_SH="91820f23df132cce8215eeaa91128c441ceff730ec890323fde8dc2eb38f1d35"
# Note (2026-11-18, fix-path-anchoring-residue): recaptured (10th time). The only
# change to _lib/archive.sh is the SKIP_RDD_VERIFIER bypass audit: it now pins
# RDDF_PROJECT_ROOT to the canonical project root (${state_root:-$tasks_root})
# instead of inheriting the caller's cwd. Gate DECISION LOGIC is untouched —
# which is what this lock protects (rdd-quick must not alter the gate it bypasses).
# Role block of rdd-planner/SKILL.md (from `role:` through closing `---`).
# This is the structural-only hash that MUST be byte-identical after rdd-quick lands.
# LOCKED_RDD_PLANNER_ROLE_BLOCK: role: ... --- block sha256, captured post-ADR-0048
# (per ADR-0048 §Decision 2: planner 完全独占 roadmap, owns 块添加 features/phases/populate-state,
#  not_owns 块保持稳定). DRIFT after ADR-0048 implementation is EXPECTED; the
# baseline was recaptured after the planner-bootstrap code changes landed.
# Note (2026-09-28): recaptured to current value after 8cd4376 objective-aware
# planning + 21ff800 AUTO sentinel unify. Additive owns list changes only.
LOCKED_RDD_PLANNER_ROLE_BLOCK="c033ec89c974c6fec9bfe5bd83a836efbd4a9d3c250b51522c8427b1083e4a92"



@test "rdd-quick: _lib/archive.sh sha256 unchanged" {
    [ -f "$PROJECT_ROOT/_lib/archive.sh" ]
    actual=$(sha256sum "$PROJECT_ROOT/_lib/archive.sh" | awk '{print $1}')
    [ "$actual" = "$LOCKED_ARCHIVE_SH" ] || {
        echo "_lib/archive.sh hash drifted: expected=$LOCKED_ARCHIVE_SH actual=$actual"
        false
    }
}

@test "rdd-quick: rdd-planner/SKILL.md role block sha256 unchanged" {
    [ -f "$PROJECT_ROOT/skills/rdd-planner/SKILL.md" ]
    # Extract the role block (from `role:` line through closing `---`).
    # Pipe directly to sha256sum so awk's trailing newline is preserved
    # (matching the locked baseline that was captured with `awk | sha256sum`).
    actual=$(awk '
        BEGIN { in_block = 0 }
        /^role:/ { in_block = 1 }
        in_block { print }
        /^---$/ && in_block { exit }
    ' "$PROJECT_ROOT/skills/rdd-planner/SKILL.md" | sha256sum | awk '{print $1}')
    [ "$actual" = "$LOCKED_RDD_PLANNER_ROLE_BLOCK" ] || {
        echo "rdd-planner role block hash drifted: expected=$LOCKED_RDD_PLANNER_ROLE_BLOCK actual=$actual"
        false
    }
}