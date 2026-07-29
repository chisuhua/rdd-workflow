#!/usr/bin/env bats
# tests/integration/test_approved_inconsistency.bats
# Regression: detect suggestions marked "completed" in proposal-suggestions.md
# that have no corresponding entry in proposal-approved.md.
#
# bats-assert is NOT loaded. Assertions use bash builtins:
#   - assert_success  -> [ "$status" -eq 0 ]
#   - refute_output --partial "X" -> [[ "$output" != *"X"* ]]
#   - assert_output --partial "X"  -> [[ "$output" == *"X"* ]]

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    touch README.md
    git add README.md
    git commit -q -m "init"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------------------------------------------------------------------------
# Task 1 tests: detect_approved_inconsistency() in state.sh
# ---------------------------------------------------------------------------

@test "approved_inconsistency: detect function exists in state.sh" {
    source "$REPO_ROOT/skills/_lib/state.sh"
    declare -f detect_approved_inconsistency >/dev/null
}

@test "approved_inconsistency: completed suggestion with no approved record shows warning" {
    cat > proposal-suggestions.md << 'EOF'
# Pool
| 提案 | 优先级 | 来源 | 添加时间 |
|------|--------|------|----------|
| [orphan](improvements/orphan.md) | P1 | test | completed |
EOF

    source "$REPO_ROOT/skills/_lib/state.sh"
    run detect_approved_inconsistency "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠️"* ]]
    [[ "$output" == *"orphan"* ]]
}

@test "approved_inconsistency: completed suggestion with approved record shows no warning" {
    cat > proposal-suggestions.md << 'EOF'
# Pool
| 提案 | 优先级 | 来源 | 添加时间 |
|------|--------|------|----------|
| [covered](improvements/covered.md) | P1 | test | completed |
EOF
    cat > proposal-approved.md << 'EOF'
# Approved
## 已批准提案
| 提案 | 优先级 |
|------|--------|
| [covered](improvements/covered.md) | P1 |
EOF

    source "$REPO_ROOT/skills/_lib/state.sh"
    run detect_approved_inconsistency "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠️"* ]]
}

@test "approved_inconsistency: missing proposal-suggestions.md is silent" {
    source "$REPO_ROOT/skills/_lib/state.sh"
    run detect_approved_inconsistency "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠️"* ]]
}

@test "approved_inconsistency: no completed entries is silent" {
    cat > proposal-suggestions.md << 'EOF'
# Pool
| 提案 | 优先级 | 来源 | 添加时间 |
|------|--------|------|----------|
| [pending](improvements/pending.md) | P1 | test | 2026-07-29 |
EOF

    source "$REPO_ROOT/skills/_lib/state.sh"
    run detect_approved_inconsistency "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠️"* ]]
}

# ---------------------------------------------------------------------------
# Task 2 tests: guide_entry.sh wires detect_approved_inconsistency
# ---------------------------------------------------------------------------

@test "approved_inconsistency: guide_entry.sh calls detect_approved_inconsistency" {
    run grep -F "detect_approved_inconsistency" "$REPO_ROOT/skills/guide/scripts/guide_entry.sh"
    [ "$status" -eq 0 ]
}

@test "approved_inconsistency: guide_entry.sh sources state.sh" {
    run grep -E "source.*state\.sh" "$REPO_ROOT/skills/guide/scripts/guide_entry.sh"
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Task 3 tests: e2e smoke regression
# ---------------------------------------------------------------------------

@test "approved_inconsistency: smoke regression - no false positive on clean project" {
    # Empty repo, no proposal-suggestions.md -> silent
    source "$REPO_ROOT/skills/_lib/state.sh"
    run detect_approved_inconsistency "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠️"* ]]
}

@test "approved_inconsistency: smoke regression - existing state.sh functions still work" {
    source "$REPO_ROOT/skills/_lib/state.sh"
    run bash -c "
        source $REPO_ROOT/skills/_lib/state.sh
        type list_improvements > /dev/null
    "
    [ "$status" -eq 0 ]
}
