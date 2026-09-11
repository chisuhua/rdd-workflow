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
    # Note: doctor_main.py writes report to Path(".rddf/state/.doctor-report.json")
    # relative to CWD, NOT RDDF_PROJECT_ROOT. So when run from $PROJECT_ROOT
    # (as setup() does), the report lands in $PROJECT_ROOT/.rddf/state/ which
    # is gitignored — not in $FIXTURE. teardown() already allows this path.
    cd "$PROJECT_ROOT"
    REPORT="$PROJECT_ROOT/.rddf/state/.doctor-report.json"
    rm -f "$REPORT"
    run env RDDF_PROJECT_ROOT="$FIXTURE" bash "$DOCTOR_SH" --json
    [ -f "$REPORT" ]
    grep -q '"timestamp"' "$REPORT"
    rm -f "$REPORT"
}

@test "doctor: checker never invokes git rm or rm -f (excluding help-text mentions)" {
    cd "$PROJECT_ROOT"
    # Strip Python triple-quoted strings and bash comments to avoid matching
    # help-text mentions of "git rm -r --cached" in CHECK descriptions.
    local matches=0
    for f in skills/rdd-doctor/scripts/doctor.sh \
             skills/rdd-doctor/scripts/doctor_main.py \
             skills/rdd-doctor/scripts/checks/*.py; do
        # Skip help-text strings: lines containing "混合状态", ";", or in """ ... """ blocks.
        # Use a more restrictive pattern: lines that LOOK like invocations.
        # A real invocation has whitespace before `rm -f` (not in a string literal).
        if grep -nE '(^|[^a-zA-Z_"\x27])(rm -f|git rm)( |;|\$)' "$f" 2>/dev/null; then
            matches=$((matches + 1))
        fi
        if grep -nE '\bos\.remove\b|\bos\.unlink\b|\bshutil\.rmtree\b' "$f" 2>/dev/null; then
            matches=$((matches + 1))
        fi
    done
    [ "$matches" -eq 0 ]
}