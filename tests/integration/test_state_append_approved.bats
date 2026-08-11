#!/usr/bin/env bats
# tests/integration/test_state_append_approved.bats
#
# Regression tests for append_approved() in _lib/state.sh.
# Verifies no double-echo bug (fix: 0232805) and correct return semantics.
# Run: bats tests/integration/test_state_append_approved.bats

load ../test_helper

setup() {
    # Create a minimal proposal-approved.md fixture with approved table
    FIXTURE_DIR=$(mktemp -d)
    cat > "$FIXTURE_DIR/proposal-approved.md" << 'EOF'
# 已批准提案（Plan 阶段输入）

| 提案 | 优先级 | 批准时间 | 批准人 |
|------|--------|----------|--------|

| [existing-change](.rddf/improvements/existing-change.md) | P0 | 2026-07-01 | guide-arch |

## 已实施

| 提案 | 优先级 | 实施时间 |
|------|--------|----------|
EOF
}

teardown() {
    rm -rf "$FIXTURE_DIR"
}

@test "append_approved: single output line per approval" {
    # Regression: fix 0232805 removed internal echo that caused double output
    source "$REPO_ROOT/_lib/state.sh"
    run bash -c "source '$REPO_ROOT/_lib/state.sh' && append_approved '$FIXTURE_DIR' 'test-new-approval' 'P2'"
    # Should have at most 1 line of output (or 0) — no duplicate echo
    [ "$(echo "$output" | wc -l)" -le 1 ]
}

@test "append_approved: returns 0 on success" {
    source "$REPO_ROOT/_lib/state.sh"
    run bash -c "source '$REPO_ROOT/_lib/state.sh' && append_approved '$FIXTURE_DIR' 'test-return-code' 'P2'"
    [ "$status" -eq 0 ]
}

@test "append_approved: appends row to approved table" {
    source "$REPO_ROOT/_lib/state.sh"
    append_approved "$FIXTURE_DIR" 'test-verify-row' 'P2'
    grep -q '\[test-verify-row\]' "$FIXTURE_DIR/proposal-approved.md"
}
