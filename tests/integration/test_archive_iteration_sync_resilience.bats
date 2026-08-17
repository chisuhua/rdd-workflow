#!/usr/bin/env bats
#
# tests/integration/test_archive_iteration_sync_resilience.bats
#
# Integration tests for archive.sh iteration.json sync resilience.
# Covers 3 scenarios:
#   1. force_mark_archived writes status=archived when archive dir exists
#   2. force_mark_archived no-op when archive dir missing
#   3. force_mark_archived idempotent (second call is no-op)

# test_helper.bash is auto-loaded by bats; do not `load test_helper`.

load ../test_helper

setup() {
    TEST_PROJECT_ROOT="$(mktemp -d)"
    cd "$TEST_PROJECT_ROOT" || exit 1
    git init -q .
    git config user.email "test@example.com"
    git config user.name "test"
    mkdir -p .rddf/state
    mkdir -p "openspec/changes/archive/2026-08-16-test-change"
    echo '{"version": 7, "changes": [{"name": "test-change", "status": "planned", "added_at": "2026-08-16T00:00:00Z"}]}' > .rddf/state/iteration.json
    touch "openspec/changes/archive/2026-08-16-test-change/proposal.md"
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "force_mark_archived writes status=archived to iteration.json" {
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert result, 'force_mark_archived should return True'
"

    run grep -q '"status": "archived"' "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
}

@test "force_mark_archived no-op when archive dir missing" {
    rm -rf "$TEST_PROJECT_ROOT/openspec/changes/archive/2026-08-16-test-change"

    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert not result, 'force_mark_archived should return False when no archive dir'
"
}

@test "force_mark_archived idempotent (second call is no-op)" {
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
r1 = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
r2 = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert r1 and not r2, f'expected r1=True, r2=False, got r1={r1}, r2={r2}'
"
}

@test "reconcile subcommand in archive.sh fixes stale iteration entry" {
    source "$REPO_ROOT/_lib/archive.sh"
    cd "$TEST_PROJECT_ROOT"
    run reconcile "$TEST_PROJECT_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-change: fixed"* ]]
}

@test "reconcile is idempotent (second call no-op)" {
    source "$REPO_ROOT/_lib/archive.sh"
    cd "$TEST_PROJECT_ROOT"
    reconcile "$TEST_PROJECT_ROOT" > /dev/null 2>&1
    run reconcile "$TEST_PROJECT_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-change: already synced"* ]]
}