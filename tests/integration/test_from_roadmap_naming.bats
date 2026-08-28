#!/usr/bin/env bats
# tests/integration/test_from_roadmap_naming.bats
# Integration tests for from_roadmap flexible naming
# (improve-from-roadmap-naming-flexibility, 2026-08-28).
#
# Covers:
# 1. Default naming backward compat (from-roadmap-<phase>-<category>)
# 2. --name-prefix overrides naming
# 3. --name-suffix appends
# 4. --auto-name generates timestamp-unique name
# 5. --multi generates N sub-proposals from one theme
# 6. Conflict (name exists) auto-appends -2, -3

setup() {
    load ../test_helper
    TEST_REPO="$BATS_TMPDIR/test-from-roadmap-naming"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO/.rddf/improvements"
    mkdir -p "$TEST_REPO/.rddf/roadmap/phases"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    cat > ".rddf/roadmap/phases/phase-1.md" <<EOF
---
phase: phase-1
---
主题: 定时循环
EOF
    SCRIPT="$PROJECT_ROOT/skills/add-improve/scripts/from_roadmap.sh"
    PY="$PROJECT_ROOT/skills/add-improve/scripts/from_roadmap.py"
}

teardown() {
    rm -rf "$TEST_REPO"
    unset ADD_IMPROVE_FROM_ROADMAP ADD_IMPROVE_THEME ADD_IMPROVE_NAME_PREFIX \
          ADD_IMPROVE_NAME_SUFFIX ADD_IMPROVE_AUTO_NAME ADD_IMPROVE_MULTI
}

@test "from_roadmap: default naming backward compat (from-roadmap-<phase>-<category>)" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch" \
        --theme "定时循环" \
        --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
    grep -q "^# from-roadmap-phase-1-arch" "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md"
}

@test "from_roadmap: --name-prefix overrides naming" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch" \
        --theme "定时循环" \
        --name-prefix "fix-audit-" \
        --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/fix-audit-phase-1-arch.md" ]
    [ ! -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
}

@test "from_roadmap: --name-suffix appends" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch" \
        --theme "定时循环" \
        --name-prefix "feat-" \
        --name-suffix "-rfc" \
        --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ -f "$TEST_REPO/.rddf/improvements/feat-phase-1-arch-rfc.md" ]
}

@test "from_roadmap: --auto-name generates timestamp-unique name" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch" \
        --theme "定时循环" \
        --name-prefix "batch-" \
        --auto-name \
        --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    files=("$TEST_REPO"/.rddf/improvements/batch-phase-1-arch-*.md)
    [ ${#files[@]} -eq 1 ]
    [[ "${files[0]}" =~ batch-phase-1-arch-[0-9]{14}\.md$ ]]
}

@test "from_roadmap: --multi generates N sub-proposals from one theme" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch" \
        --theme "定时循环" \
        --multi 3 \
        --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    for i in 1 2 3; do
        [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch-sub-$i.md" ]
        grep -q "\*\*主题\*\*: 定时循环" "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch-sub-$i.md"
    done
    [ ! -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
}

@test "from_roadmap: conflict (name exists) auto-appends -2, -3" {
    # First run creates the default file
    PROJECT_ROOT="$TEST_REPO" \
    ADD_IMPROVE_FROM_ROADMAP="phase-1/arch" \
    ADD_IMPROVE_THEME="定时循环" \
    python3 "$PY"
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
    # Second run with same name appends -2 (never overwrites)
    PROJECT_ROOT="$TEST_REPO" \
    ADD_IMPROVE_FROM_ROADMAP="phase-1/arch" \
    ADD_IMPROVE_THEME="定时循环" \
    python3 "$PY"
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch-2.md" ]
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch.md" ]
    # Third run appends -3
    PROJECT_ROOT="$TEST_REPO" \
    ADD_IMPROVE_FROM_ROADMAP="phase-1/arch" \
    ADD_IMPROVE_THEME="定时循环" \
    python3 "$PY"
    [ -f "$TEST_REPO/.rddf/improvements/from-roadmap-phase-1-arch-3.md" ]
}
