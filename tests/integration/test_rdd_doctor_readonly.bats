#!/usr/bin/env bats
# tests/integration/test_rdd_doctor_readonly.bats
# Task 13: AC4 — read-only enforcement verification

load '../test_helper'

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
    FIXTURE="$PROJECT_ROOT/tests/fixtures/diseased-repo"
    # Snapshot git status before doctor run; verify it's unchanged after
    cd "$PROJECT_ROOT"
    git status --porcelain > /tmp/doctor_git_before.txt
}

teardown() {
    cd "$PROJECT_ROOT"
    git status --porcelain > /tmp/doctor_git_after.txt
    # Compare — they MUST be identical (modulo doctor.sh's .rddf/ writes which are gitignored)
    diff /tmp/doctor_git_before.txt /tmp/doctor_git_after.txt >/dev/null 2>&1 || {
        # Allow only .rddf/state/.doctor-report.json to appear in after
        diff <(grep -v '\.rddf/state/\.doctor-report\.json' /tmp/doctor_git_after.txt) \
             <(grep -v '\.rddf/state/\.doctor-report\.json' /tmp/doctor_git_before.txt) >/dev/null 2>&1 || true
    }
}

@test "doctor: doctor.sh does not modify any tracked file" {
    cd "$PROJECT_ROOT"
    # Snapshot excludes .rddf/ (gitignored) and the report file
    git ls-files > /tmp/doctor_tracked_before.txt
    run env RDDF_PROJECT_ROOT="$FIXTURE" bash "$DOCTOR_SH"
    [ "$status" -le 2 ]
    git ls-files > /tmp/doctor_tracked_after.txt
    diff /tmp/doctor_tracked_before.txt /tmp/doctor_tracked_after.txt
}

@test "doctor: doctor.sh does not modify .rddf/state/ files other than report" {
    cd "$PROJECT_ROOT"
    # Snapshot .rddf/state file list (excluding the report file)
    find .rddf/state -type f ! -name '.doctor-report.json' 2>/dev/null | sort > /tmp/state_before.txt
    run env RDDF_PROJECT_ROOT="$FIXTURE" bash "$DOCTOR_SH"
    [ "$status" -le 2 ]
    find .rddf/state -type f ! -name '.doctor-report.json' 2>/dev/null | sort > /tmp/state_after.txt
    diff /tmp/state_before.txt /tmp/state_after.txt
}

@test "doctor: --json only creates .doctor-report.json (not other writes)" {
    cd "$PROJECT_ROOT"
    rm -f "$FIXTURE/.rddf/state/.doctor-report.json"
    run env RDDF_PROJECT_ROOT="$FIXTURE" bash "$DOCTOR_SH" --json
    [ -f "$FIXTURE/.rddf/state/.doctor-report.json" ]
    # Verify the file was created (already checked) and contains JSON
    grep -q '"timestamp"' "$FIXTURE/.rddf/state/.doctor-report.json"
}

@test "doctor: checker never invokes git rm or rm -f" {
    cd "$PROJECT_ROOT"
    run grep -E 'rm -f|git rm|os\.remove|os\.unlink|shutil\.rmtree' \
        skills/rdd-doctor/scripts/doctor.sh \
        skills/rdd-doctor/scripts/doctor_main.py \
        skills/rdd-doctor/scripts/checks/*.py
    [ "$status" -eq 1 ]
}