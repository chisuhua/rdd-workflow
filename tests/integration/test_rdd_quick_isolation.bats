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
LOCKED_SELECT_WORKTREE_SH="478eadec2dcba30ab37a2c20e2e21409031879dae509d7393b6b67d064c9e9f0"
LOCKED_TASKS_WRITEBACK_SH="e9e0065de4f65fbeef763be3b3eb09626c99920744e6bb2585311a2b21483264"
# Note (2026-09-11): LOCKED_ARCHIVE_SH recaptured after bypass-audit-mechanism wired.
# Per the change: archive_gate_check's SKIP_RDD_VERIFIER branch now calls
# audit_bypass_log when RDDF_VERIFIER_BYPASS_REASON is set (per bypass-audit-mechanism
# improvement). The rdd-quick zero-pollution invariant (this test) is preserved:
# rdd-quick does NOT invoke archive_gate_check's SKIP_RDD_VERIFIER branch
# (rdd-quick is bypass-path per ADR-0047), so the byte change here is an additive
# audit hook with zero impact on rdd-quick's execution semantics.
LOCKED_ARCHIVE_SH="12670407979ace43cd990baffb609dd627599f1a102cd4fc7e2ffe7b278474f3"
# Role block of rdd-planner/SKILL.md (from `role:` through closing `---`).
# This is the structural-only hash that MUST be byte-identical after rdd-quick lands.
# LOCKED_RDD_PLANNER_ROLE_BLOCK: role: ... --- block sha256, captured post-ADR-0048
# (per ADR-0048 §Decision 2: planner 完全独占 roadmap, owns 块添加 features/phases/populate-state,
#  not_owns 块保持稳定). DRIFT after ADR-0048 implementation is EXPECTED; the
# baseline was recaptured after the planner-bootstrap code changes landed.
LOCKED_RDD_PLANNER_ROLE_BLOCK="58ef8cd7c907dbf8520d83face0f2d0b475df72caf0a52dbe80fa0670132c70a"

@test "rdd-quick: select_worktree.sh sha256 unchanged" {
    [ -f "$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh" ]
    actual=$(sha256sum "$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh" | awk '{print $1}')
    [ "$actual" = "$LOCKED_SELECT_WORKTREE_SH" ] || {
        echo "select_worktree.sh hash drifted: expected=$LOCKED_SELECT_WORKTREE_SH actual=$actual"
        false
    }
}

@test "rdd-quick: tasks_writeback.sh sha256 unchanged" {
    [ -f "$PROJECT_ROOT/skills/execute/scripts/tasks_writeback.sh" ]
    actual=$(sha256sum "$PROJECT_ROOT/skills/execute/scripts/tasks_writeback.sh" | awk '{print $1}')
    [ "$actual" = "$LOCKED_TASKS_WRITEBACK_SH" ] || {
        echo "tasks_writeback.sh hash drifted: expected=$LOCKED_TASKS_WRITEBACK_SH actual=$actual"
        false
    }
}

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