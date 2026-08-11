#!/usr/bin/env bats
#
# tests/integration/test_mark_approved_completed.bats
#
# Regression coverage for `_lib/state.sh::mark_approved_completed`:
#   - Idempotent call on an entry already in the `## 已实施` section must
#     preserve the original completion date (not rewrite it to today).
#   - First-time archive (entry in `## 已批准提案` only) must still use
#     today's UTC date (baseline behavior).
#
# See openspec/changes/fix-mark-approved-completed-date-drift/.

load ../test_helper

@test "mark-approved-completed: idempotent call preserves original completion date" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
| [fix-scan-state-bats](.rddf/improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 |
MD
    echo "# x" > "$TEST_DIR/.rddf/improvements/fix-scan-state-bats.md"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/_lib/state.sh"

    # Idempotent call: entry is already in the 已实施 table (date 2026-07-23).
    run mark_approved_completed "$TEST_DIR" "fix-scan-state-bats"
    [ "$status" -eq 0 ]

    # Original date must still be present.
    run grep -F '2026-07-23' "$TEST_DIR/proposal-approved.md"
    [ "$status" -eq 0 ]

    # Today's UTC date must NOT have been introduced.
    today=$(date -u +%Y-%m-%d)
    if [ "$today" = "2026-07-23" ]; then
        skip "today == 2026-07-23 (fixture date); cannot prove drift suppression"
    fi
    run grep -F "$today" "$TEST_DIR/proposal-approved.md"
    [ "$status" -ne 0 ]

    rm -rf "$TEST_DIR"
}

@test "mark-approved-completed: first-time archive uses today's date" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [new-change](.rddf/improvements/new-change.md) | P1 | 2026-07-31 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
    echo "# x" > "$TEST_DIR/.rddf/improvements/new-change.md"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/_lib/state.sh"

    run mark_approved_completed "$TEST_DIR" "new-change"
    [ "$status" -eq 0 ]

    today=$(date -u +%Y-%m-%d)
    run grep -F "$today" "$TEST_DIR/proposal-approved.md"
    [ "$status" -eq 0 ]

    rm -rf "$TEST_DIR"
}