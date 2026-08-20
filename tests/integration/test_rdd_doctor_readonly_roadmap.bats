#!/usr/bin/env bats
# Test rdd-doctor --category roadmap-refs (Task 7 / T16, AC-2.10 read-only invariant).
# Pattern: align with existing checks/roadmap_meta_check.py — `run(project_root) -> List[Finding]`.

load ../test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr
    # Set up a project with a broken R1 violation (feature.phase_refs points to non-existent phase)
    mkdir -p .rddf/roadmap/features
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
主题: T
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    DOCTOR="/workspace/project/rdd-workflow/skills/rdd-doctor/scripts/doctor.sh"
}

teardown() {
    rm -rf "$TMP"
    unset RDDF_PROJECT_ROOT
}

@test "rdd-doctor --category roadmap-refs: reports R1 violation, exit 2 (CRITICAL), no file modifications" {
    # Snapshot file mtimes before
    SNAPSHOT_BEFORE=$(find . -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort)
    run bash "$DOCTOR" --category roadmap-refs
    # rdd-doctor exit code 2 = at least one CRITICAL finding (per doctor_render.py::exit_code_for)
    [ "$status" -eq 2 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"feat-bad"* ]]
    # No tracked/gitignored files modified (read-only invariant per AC-2.10).
    # Note: .rddf/ is gitignored in this project, so we check via mtime snapshot, not git status.
    SNAPSHOT_AFTER=$(find . -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | sort)
    [ "$SNAPSHOT_BEFORE" = "$SNAPSHOT_AFTER" ]
}

@test "rdd-doctor --category roadmap-refs: clean setup yields exit 0" {
    # Replace broken fragment with valid one
    cat > .rddf/roadmap/features/feat-good.md <<'EOF'
---
id: feat-good
kind: feature
status: active
phase_refs: [phase-1]
主题: T
---
body
EOF
    rm -f .rddf/roadmap/features/feat-bad.md
    run bash "$DOCTOR" --category roadmap-refs
    [ "$status" -eq 0 ]
    [[ "$output" == *"All checks passed"* ]] || [[ "$output" == *"✅"* ]]
}
