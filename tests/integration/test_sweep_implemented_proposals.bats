#!/usr/bin/env bats
#
# tests/integration/test_sweep_implemented_proposals.bats
#
# Regression coverage for `_lib/state.sh::sweep_implemented_proposals`'s
# **second retirement path**:
#
#   Path 1 (pre-existing): a row in improvement-approved.md's pending table
#   with a matching `openspec/changes/archive/<date>-<name>/` directory.
#
#   Path 2 (new): an improvement file whose front matter `状态` says it is
#   delivered, but which never went through the approval flow and therefore
#   has **no openspec change** ⇒ no archive dir to match against (rdd-quick /
#   in-place execution, ADR-0047). Those proposals could never retire before:
#   they stayed in the Pending pool forever.
#
# Contract asserted here:
#   - terminal status + no index row  ⇒ registered in the 已实施 section
#   - terminal status + pending row    ⇒ moved from 已批准 to 已实施
#   - the completion date comes from the status field, not from "today"
#   - a voided proposal (作废) is NOT registered
#   - an open proposal (draft) is left alone
#   - the sweep is idempotent

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/.rddf/improvement-approved.md" <<'MD'
# 已批准提案（Plan 阶段输入）

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|
| [still-pending](improvements/still-pending.md) | P1 | 2026-11-01 | guide-design |
| [moved-to-done](improvements/moved-to-done.md) | P2 | 2026-11-02 | guide-design |

## 已实施
| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|----------|------|
| [already-done](improvements/already-done.md) | P1 | 2026-10-01 | 已实施 |
MD

    cat > "$TEST_DIR/.rddf/improvements/still-pending.md" <<'MD'
---
优先级: P1
状态: draft
---
# still-pending
MD

    cat > "$TEST_DIR/.rddf/improvements/moved-to-done.md" <<'MD'
---
优先级: P2
状态: implemented (2026-11-17)
---
# moved-to-done
MD

    cat > "$TEST_DIR/.rddf/improvements/already-done.md" <<'MD'
---
优先级: P1
状态: ✅ 已实施 (2026-10-01, commit abc1234)
---
# already-done
MD

    cat > "$TEST_DIR/.rddf/improvements/never-approved.md" <<'MD'
---
优先级: P0
状态: implemented (2026-09-28 首轮 → 2026-09-29 收尾)
---
# never-approved
MD

    cat > "$TEST_DIR/.rddf/improvements/voided.md" <<'MD'
---
优先级: P2
状态: 作废
---
# voided
MD

    # shellcheck source=/dev/null
    source "$REPO_ROOT/_lib/state.sh"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "sweep: terminal status without an index row is registered as 已实施" {
    run sweep_implemented_proposals "$TEST_DIR"
    [ "$status" -eq 0 ]

    run grep -F "[never-approved](improvements/never-approved.md)" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]

    # The completion date comes from the status field (last date), not today.
    run grep -F "| P0 | 2026-09-29 | 已实施 |" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]
}

@test "sweep: terminal status in the pending table is moved to 已实施" {
    run sweep_implemented_proposals "$TEST_DIR"
    [ "$status" -eq 0 ]

    run grep -F "[moved-to-done](improvements/moved-to-done.md)" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]

    # It must no longer sit in the 已批准 table (one occurrence only).
    run grep -c "moved-to-done" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$output" -eq 1 ]

    run grep -F "| P2 | 2026-11-17 | 已实施 |" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]
}

@test "sweep: voided and open proposals are left alone" {
    run sweep_implemented_proposals "$TEST_DIR"
    [ "$status" -eq 0 ]

    run grep -F "voided" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -ne 0 ]

    run grep -F "still-pending" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]
}

@test "sweep: the second retirement path is idempotent" {
    run sweep_implemented_proposals "$TEST_DIR"
    [ "$status" -eq 0 ]
    cp "$TEST_DIR/.rddf/improvement-approved.md" "$TEST_DIR/after-first.md"

    run sweep_implemented_proposals "$TEST_DIR"
    [ "$status" -eq 0 ]

    run diff "$TEST_DIR/after-first.md" "$TEST_DIR/.rddf/improvement-approved.md"
    [ "$status" -eq 0 ]
}

@test "sweep: an improvement dir without an index file is a no-op" {
    EMPTY_DIR=$(mktemp -d)
    mkdir -p "$EMPTY_DIR/.rddf/improvements"

    run sweep_implemented_proposals "$EMPTY_DIR"
    [ "$status" -eq 0 ]

    rm -rf "$EMPTY_DIR"
}
