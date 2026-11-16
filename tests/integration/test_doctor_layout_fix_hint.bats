#!/usr/bin/env bats
# tests/integration/test_doctor_layout_fix_hint.bats
#
# The missing-required fix_hint must be actionable: a DIRECTORY entry gets a
# trailing slash, a FILE entry must not ("create .rddf/roadmap.md/" points at a
# path that cannot be created).

setup() {
    REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../.." && pwd)"
    TMP="$(mktemp -d)"
    export RDDF_PROJECT_ROOT="$TMP"
    mkdir -p "$TMP/.rddf/state" "$TMP/.rddf/improvements" "$TMP/.rddf/plans" \
             "$TMP/.rddf/roadmap" "$TMP/.rddf/wt"
    : > "$TMP/.rddf/roadmap.md"
    : > "$TMP/.rddf/project.yaml"
    printf '.rddf/state/\n.rddf/wt/\n' > "$TMP/.gitignore"
    cd "$TMP"
    git init -q . && git config user.email t@t && git config user.name t
}

teardown() {
    cd "$REPO_ROOT"
    rm -rf "$TMP"
}

run_layout() {
    run python3 "$REPO_ROOT/skills/rdd-doctor/scripts/doctor_main.py" --category layout
}

@test "layout fix_hint: a missing FILE entry has no trailing slash" {
    rm -f "$TMP/.rddf/roadmap.md"
    run_layout
    echo "$output" | grep -q "layout.missing-required"
    echo "$output" | grep -q "create .rddf/roadmap.md"
    ! echo "$output" | grep -q "create .rddf/roadmap.md/"
}

@test "layout fix_hint: a missing DIRECTORY entry keeps its trailing slash" {
    rm -rf "$TMP/.rddf/improvements"
    run_layout
    echo "$output" | grep -q "layout.missing-required"
    echo "$output" | grep -q "create .rddf/improvements/"
}
