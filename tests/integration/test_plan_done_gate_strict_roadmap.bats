#!/usr/bin/env bats
# Test plan-done gate integration of validate_fragment_refs (Task 7 / T17, AC-2.9).
# STRICT_ROADMAP_REFS_GATE=yes must block on R1 violation; default WARNING must not block.

load ../test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr openspec/changes/test-change .rddf/roadmap/features
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    # R1 violation (CRITICAL): feature.phase_refs references non-existent phase
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
---
body
EOF
    # R5 violation (WARNING): feature with empty phase_refs
    cat > .rddf/roadmap/features/feat-no-refs.md <<'EOF'
---
id: feat-no-refs
kind: feature
status: active
phase_refs: []
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    VALIDATE_SCRIPT="/workspace/project/rdd-workflow/skills/roadmap/scripts/roadmap_validate_fragments.sh"
}

teardown() {
    rm -rf "$TMP"
    unset RDDF_PROJECT_ROOT STRICT_ROADMAP_REFS_GATE SKIP_ROADMAP_REFS_GATE
}

@test "validate-fragments: STRICT mode blocks on R1 violation" {
    export STRICT_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"CRITICAL"* ]] || [[ "$output" == *"strict"* ]]
}

@test "validate-fragments: default WARNING mode does not block (R5 WARNING only)" {
    # R5 (feature with empty phase_refs) is WARNING-level; default mode should
    # print warning but exit 0. R1 (CRITICAL) would also block; remove feat-bad
    # so only R5 remains.
    rm -f .rddf/roadmap/features/feat-bad.md
    unset STRICT_ROADMAP_REFS_GATE
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"R5"* ]]
    [[ "$output" == *"WARNING"* ]]
}

@test "validate-fragments: SKIP env exits 0 with skip message" {
    export SKIP_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"skipped"* ]]
}
