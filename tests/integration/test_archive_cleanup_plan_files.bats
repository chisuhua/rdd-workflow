#!/usr/bin/env bats
# tests/integration/test_archive_cleanup_plan_files.bats
#
# Regression tests for the archive-cleanup-plan-files change:
#   - Task 1: cleanup_plan_file() in ship_archive.sh
#   - Task 2: check_orphan_plan_files() in scan-state.sh
#   - Task 3: e2e cleanup + scan regression tests
#
# NOTE: bats-assert is NOT loaded. Use simple patterns:
#   [ "$status" -eq 0 ]          for exit code
#   [[ "$output" == *"..."* ]]   for substring check
#   [[ ! -f "$file" ]]           for path not exists

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR" || return 1
    mkdir -p .rddf/plans openspec/changes
}

teardown() {
    [ -n "$TEST_DIR" ] && rm -rf "$TEST_DIR"
}

# ---------------------------------------------------------------------------
# Task 1: cleanup_plan_file() in ship_archive.sh
# ---------------------------------------------------------------------------

@test "archive_cleanup_plan_files: cleanup_plan_file exists in ship_archive.sh" {
    run grep -F "cleanup_plan_file" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    [ "$status" -eq 0 ]
}

@test "archive_cleanup_plan_files: cleanup_plan_file deletes existing plan file" {
    echo "# Plan" > ".rddf/plans/test-change.md"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    cleanup_plan_file "$TEST_DIR" "test-change"

    [[ ! -f "$TEST_DIR/.rddf/plans/test-change.md" ]]
}

@test "archive_cleanup_plan_files: cleanup_plan_file is idempotent (no file = no error)" {
    # No plan file exists
    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    run cleanup_plan_file "$TEST_DIR" "nonexistent-change"
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Task 2: check_orphan_plan_files() in scan-state.sh
# ---------------------------------------------------------------------------

@test "archive_cleanup_plan_files: check_orphan_plan_files exists in scan-state.sh" {
    run grep -F "check_orphan_plan_files" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]
}

@test "archive_cleanup_plan_files: orphan plan file triggers warning" {
    # Create orphan plan file (no corresponding change)
    echo "# Orphan" > ".rddf/plans/orphan-change.md"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    run check_orphan_plan_files "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠️"* ]]
    [[ "$output" == *"孤立"* ]]
}

@test "archive_cleanup_plan_files: matched plan file (active change) no warning" {
    # Create active change + its plan file
    mkdir -p openspec/changes/active-change
    echo "# Plan" > ".rddf/plans/active-change.md"

    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    run check_orphan_plan_files "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ ! "$output" == *"孤立"* ]]
}

@test "archive_cleanup_plan_files: missing .rddf/plans/ dir is silent" {
    rm -rf .rddf/plans

    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    run check_orphan_plan_files "$TEST_DIR"
    [ "$status" -eq 0 ]
}
