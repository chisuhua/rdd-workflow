#!/usr/bin/env bats
# tests/integration/test_rdd_doctor_proposal_section.bats
#
# Regression coverage for fix-proposal-approved-sync (P2, 2026-08-21):
# rdd-doctor MUST have a "proposal-section" category that detects
# proposal-approved.md "## 已批准提案" entries with matching
# openspec/changes/archive/<date>-<name>/ directories.
#
# The original bug (2026-08-21): the sync never happened, so the
# index showed "not yet implemented" long after archive — and no
# automated check surfaced this drift. This test pins the new
# category so future drift is caught before users notice.
load '../test_helper'

setup() {
    TEST_TMPDIR="$(mktemp -d)"
    cp -r "$BATS_TEST_DIRNAME/../../skills/rdd-doctor" "$TEST_TMPDIR/rdd-doctor"
    PROJECT_ROOT="$TEST_TMPDIR"
    export RDDF_PROJECT_ROOT="$TEST_TMPDIR"
    cd "$TEST_TMPDIR"
    mkdir -p openspec/changes/archive .rddf/state
}

teardown() { rm -rf "$TEST_TMPDIR"; }

# Build a minimal proposal-approved.md string for a list of approved entries.
_mk_approved_file() {
    local body="## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|
"
    for entry in "$@"; do
        body+="
| [${entry}](.rddf/improvements/${entry}.md) | P1 | 2026-08-21 | guide-arch |"
    done
    body+="

## 已实施

| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|----------|------|"
    printf '%s' "$body" > proposal-approved.md
}

@test "proposal-section: approved entry + matching archive dir -> CRITICAL" {
    _mk_approved_file "fix-drift-1"
    mkdir -p openspec/changes/archive/2026-08-21-fix-drift-1
    touch openspec/changes/archive/2026-08-21-fix-drift-1/.marker

    cd "$TEST_TMPDIR"
    run python3 "$TEST_TMPDIR/rdd-doctor/scripts/doctor_main.py" \
        --category proposal-section
    [ "$status" -eq 2 ]  # CRITICAL exit code
    [[ "$output" == *"fix-drift-1"* ]]
}

@test "proposal-section: approved entry without archive dir -> clean" {
    _mk_approved_file "fix-still-pending"

    cd "$TEST_TMPDIR"
    run python3 "$TEST_TMPDIR/rdd-doctor/scripts/doctor_main.py" \
        --category proposal-section --quiet
    [ "$status" -eq 0 ]  # clean
}

@test "proposal-section: multiple drifted -> multiple findings" {
    _mk_approved_file "fix-drift-a" "fix-drift-b"
    mkdir -p openspec/changes/archive/2026-08-21-fix-drift-a
    mkdir -p openspec/changes/archive/2026-08-21-fix-drift-b
    touch openspec/changes/archive/2026-08-21-fix-drift-a/.marker
    touch openspec/changes/archive/2026-08-21-fix-drift-b/.marker

    cd "$TEST_TMPDIR"
    run python3 "$TEST_TMPDIR/rdd-doctor/scripts/doctor_main.py" \
        --category proposal-section --json
    [ "$status" -eq 2 ]  # CRITICAL
    # --json writes to .rddf/state/.doctor-report.json; read from there
    [ -f .rddf/state/.doctor-report.json ]
    report=$(cat .rddf/state/.doctor-report.json)
    [[ "$report" == *"fix-drift-a"* ]]
    [[ "$report" == *"fix-drift-b"* ]]
}

@test "proposal-section: implemented entry + matching archive dir -> clean" {
    cat > proposal-approved.md <<'EOF'
## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|

## 已实施

| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|----------|------|
| [fix-already-synced](.rddf/improvements/fix-already-synced.md) | P1 | 2026-08-21 |
EOF
    mkdir -p openspec/changes/archive/2026-08-21-fix-already-synced
    touch openspec/changes/archive/2026-08-21-fix-already-synced/.marker

    cd "$TEST_TMPDIR"
    run python3 "$TEST_TMPDIR/rdd-doctor/scripts/doctor_main.py" \
        --category proposal-section --quiet
    [ "$status" -eq 0 ]
}

@test "proposal-section: missing proposal-approved.md -> clean (degraded)" {
    cd "$TEST_TMPDIR"
    run python3 "$TEST_TMPDIR/rdd-doctor/scripts/doctor_main.py" \
        --category proposal-section --quiet
    [ "$status" -eq 0 ]
}
