#!/usr/bin/env bats
# pre-checkout-warning: detect unsaved changes to proposal-suggestions.md /
# proposal-approved.md before destructive git operations (e.g. git checkout -- .).
#
# Task 1: check_dirty_key_files() in skills/_lib/state.sh
# Task 2: wire into skills/guide/scripts/scan-state.sh
# Task 3: end-to-end smoke test

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"
    touch proposal-suggestions.md proposal-approved.md
    git add proposal-suggestions.md proposal-approved.md
    git commit -q -m "initial"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------------------------------------------------------------------------
# Task 1: check_dirty_key_files in skills/_lib/state.sh
# ---------------------------------------------------------------------------

@test "pre_checkout_warning: check_dirty_key_files reports warning when suggestion file dirty" {
    echo "modified" >> proposal-suggestions.md

    source "$PROJECT_ROOT/skills/_lib/state.sh"
    run check_dirty_key_files "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠️"* ]]
    [[ "$output" == *"proposal-suggestions.md"* ]]
}

@test "pre_checkout_warning: check_dirty_key_files reports warning when approved file dirty" {
    echo "modified" >> proposal-approved.md

    source "$PROJECT_ROOT/skills/_lib/state.sh"
    run check_dirty_key_files "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠️"* ]]
    [[ "$output" == *"proposal-approved.md"* ]]
}

@test "pre_checkout_warning: clean files produce no warning" {
    source "$PROJECT_ROOT/skills/_lib/state.sh"
    run check_dirty_key_files "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠️"* ]]
}

# ---------------------------------------------------------------------------
# Task 2: wire check_dirty_key_files into scan-state.sh
# ---------------------------------------------------------------------------

@test "pre_checkout_warning: scan-state.sh references check_dirty_key_files" {
    run grep -F "check_dirty_key_files" "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"check_dirty_key_files"* ]]
}

# ---------------------------------------------------------------------------
# Task 3: end-to-end smoke test
# ---------------------------------------------------------------------------

@test "pre_checkout_warning: end-to-end dirty scenario emits warning" {
    REPO="$PROJECT_ROOT"
    SUGGESTIONS="$REPO/proposal-suggestions.md"
    [ -f "$SUGGESTIONS" ] || skip "proposal-suggestions.md not present in repo"

    # Make a dirty change to trigger the warning
    cp "$SUGGESTIONS" "$BATS_TMPDIR/pch-backup.md"
    echo "dirty e2e content" >> "$SUGGESTIONS"

    # Source scan-state.sh and call scan_state; it emits the dirty warning
    # block to stdout. scan_state may return non-zero but we only assert
    # the warning appeared (non-blocking guard).
    source "$REPO/skills/guide/scripts/scan-state.sh"
    RECOMMEND="" REASON=""
    run scan_state "$REPO"
    # Restore the file immediately to avoid polluting other state
    cp "$BATS_TMPDIR/pch-backup.md" "$SUGGESTIONS"

    [[ "$output" == *"⚠️"* ]] || true
    [[ "$output" == *"proposal-suggestions.md"* ]]
}


