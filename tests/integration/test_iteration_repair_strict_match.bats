#!/usr/bin/env bats
#
# tests/integration/test_iteration_repair_strict_match.bats
#
# Regression tests for force_mark_archived strict name matching (Bug D).
# Bug D: glob pattern `*-<name>` falsely matches `<date>-<name>` when
#        `<name>` happens to be a suffix of `<date>-<name>`.
#   e.g. pattern `*-08-16-foo` matches dir `2026-08-16-foo` because
#   the dir ends with `-08-16-foo` (the `*` consumes `2026`).
#
# Fix: enforce exact `<YYYY>-<MM>-<DD>-<name>` prefix in the glob.
# These tests verify:
#   1. Wrong name with date-like suffix does NOT match
#   2. Correct name still matches
#   3. Synthetic entries created with wrong names are NEVER persisted

# test_helper.bash is auto-loaded by bats; do not `load test_helper`.

load ../test_helper

setup() {
    TEST_PROJECT_ROOT="$(mktemp -d)"
    cd "$TEST_PROJECT_ROOT" || exit 1
    git init -q .
    git config user.email "test@example.com"
    git config user.name "test"
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{"version": 6, "updated_at": "2026-08-24T00:00:00+00:00", "current_phase": "default", "changes": []}
EOF
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "force_mark_archived refuses wrong name with date-suffix (Bug D)" {
    # Reproduce: archive dir is 2026-08-16-add-rdd-hub-bootstrap
    mkdir -p "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap"
    touch "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap/proposal.md"

    # Pass the wrong name (only one `-` stripped from date prefix)
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="08-16-add-rdd-hub-bootstrap" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert not result, f'force_mark_archived should refuse wrong name with date-suffix; got {result}'
"

    # iteration.json must remain empty (no phantom entry)
    run cat "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
    count=$(echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('changes',[])))")
    [ "$count" -eq 0 ]
}

@test "force_mark_archived still works with correct name" {
    mkdir -p "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap"
    touch "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap/proposal.md"

    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="add-rdd-hub-bootstrap" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert result, 'force_mark_archived should succeed with correct name'
"

    run cat "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
    name=$(echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['changes'][0]['name'])")
    [ "$name" = "add-rdd-hub-bootstrap" ]
    status=$(echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['changes'][0]['status'])")
    [ "$status" = "archived" ]
}

@test "force_mark_archived refuses name that matches a DIFFERENT archive dir" {
    # Two archive dirs: one for X, one for Y. We pass Y's name but with date-suffix.
    mkdir -p "openspec/changes/archive/2026-08-16-X"
    mkdir -p "openspec/changes/archive/2026-08-17-Y"
    touch "openspec/changes/archive/2026-08-16-X/proposal.md"
    touch "openspec/changes/archive/2026-08-17-Y/proposal.md"

    # Pass wrong name like X's prefix-suffix pattern: 08-16-X should NOT match 2026-08-17-Y
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="08-16-X" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert not result, 'force_mark_archived should not cross-match archive dirs'
"
}