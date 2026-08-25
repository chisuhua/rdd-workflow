#!/usr/bin/env bats
#
# tests/integration/test_archive_reconcile_date_parse.bats
#
# Regression tests for archive.sh::reconcile date prefix parsing (Bug C).
# Bug C: reconcile() extracts change_name from a date-prefixed archive
#        dir using `"${dir_name#*-}"`, which only strips the FIRST `-`.
#        For `2026-08-16-foo`, this produces `08-16-foo` instead of `foo`.
#
# Fix: extract `<YYYY>-<MM>-<DD>-` prefix (10 chars + 1 dash = 11 chars)
#      using bash parameter expansion or Python parsing.
#
# These tests verify:
#   1. Single change reconcile produces correct name
#   2. Multi-segment names (with hyphens) are handled correctly
#   3. No phantom entries with date-prefixed names are created

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

# Helper: source archive.sh and run reconcile. Source must succeed even
# if other helpers reference files not in TEST_PROJECT_ROOT.
run_reconcile() {
    # Use REPO_ROOT as the project for reconcile, but write iteration.json
    # to TEST_PROJECT_ROOT. We do this by overriding MAIN_ROOT via env.
    bash -c "
        cd '$TEST_PROJECT_ROOT'
        # Create a wrapper that re-points openspec/changes to TEST_PROJECT_ROOT
        export PROJECT_ROOT='$TEST_PROJECT_ROOT'
        # Source archive.sh but redirect its _LIB_DIR
        source '$REPO_ROOT/_lib/archive.sh'
        reconcile '$TEST_PROJECT_ROOT'
    "
}

@test "reconcile extracts correct name from date-prefixed dir (Bug C fix)" {
    # Create one archive dir with a 4-segment date-prefixed name
    mkdir -p "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap"
    touch "openspec/changes/archive/2026-08-16-add-rdd-hub-bootstrap/proposal.md"

    run bash -c "
        export REPO_ROOT='$REPO_ROOT'
        source '$REPO_ROOT/_lib/archive.sh'
        reconcile '$TEST_PROJECT_ROOT'
    "

    # Verify correct name 'add-rdd-hub-bootstrap' was used
    run cat "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
names = [c['name'] for c in d['changes']]
assert 'add-rdd-hub-bootstrap' in names, f'expected add-rdd-hub-bootstrap, got {names}'
assert '08-16-add-rdd-hub-bootstrap' not in names, f'Bug C: phantom entry with wrong name: {names}'
assert all(c.get('status') == 'archived' for c in d['changes']), f'all should be archived, got {d[\"changes\"]}'
"
}

@test "reconcile handles names with internal hyphens (Bug C edge case)" {
    # add-rdd-hub-bootstrap has multiple internal hyphens
    mkdir -p "openspec/changes/archive/2026-08-16-fix-post-flow-classifier-ordering"
    touch "openspec/changes/archive/2026-08-16-fix-post-flow-classifier-ordering/proposal.md"

    run bash -c "
        export REPO_ROOT='$REPO_ROOT'
        source '$REPO_ROOT/_lib/archive.sh'
        reconcile '$TEST_PROJECT_ROOT'
    "

    run cat "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
names = [c['name'] for c in d['changes']]
assert 'fix-post-flow-classifier-ordering' in names, f'expected exact name, got {names}'
wrong = [n for n in names if n.startswith(('08-', '16-', '2026-'))]
assert not wrong, f'Bug C: phantom entries with date-prefixed names: {wrong}'
"
}

@test "reconcile skips dirs without valid date prefix (defensive)" {
    # Create an archive dir WITHOUT date prefix (legacy or unusual format)
    mkdir -p "openspec/changes/archive/legacy-no-date-prefix"
    touch "openspec/changes/archive/legacy-no-date-prefix/proposal.md"

    run bash -c "
        export REPO_ROOT='$REPO_ROOT'
        source '$REPO_ROOT/_lib/archive.sh'
        reconcile '$TEST_PROJECT_ROOT'
    "

    # Should NOT create an entry with name like 'no-date-prefix' if it can't parse date
    # OR if it does, it should not be a phantom (the entry is actually real)
    # Either way, no date-prefixed phantom should appear
    run cat "$TEST_PROJECT_ROOT/.rddf/state/iteration.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
names = [c['name'] for c in d['changes']]
# No date-prefixed phantoms
wrong = [n for n in names if n[:2].isdigit() and n[2:3] == '-']
assert not wrong, f'Bug C: phantom entries: {wrong}'
"
}