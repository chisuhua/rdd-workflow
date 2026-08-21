#!/usr/bin/env bats
# populate-roadmap-from-arch v1.2 thin-wrapper tests
# (move-populate-roadmap-into-guide-arch, Task F)

load ../test_helper

setup() {
    TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p docs/adr
    echo "# ADR-0001" > docs/adr/ADR-0001-test.md
    git add . && git commit -q -m "init"
}

teardown() {
    cd /
    rm -rf "$TEST_TMPDIR" 2>/dev/null || true
}

@test "populate_wrapper: v1.2 frontmatter has version 1.2 + evolved-from" {
    grep -q "^version: 1.2" "$REPO_ROOT/skills/populate-roadmap-from-arch/SKILL.md"
    grep -q "^evolved-from: populate-roadmap-from-arch" "$REPO_ROOT/skills/populate-roadmap-from-arch/SKILL.md"
}

@test "populate_wrapper: SKILL.md contains deprecation banner mentioning guide-arch" {
    grep -q "DEPRECATED" "$REPO_ROOT/skills/populate-roadmap-from-arch/SKILL.md"
    grep -q "guide-arch" "$REPO_ROOT/skills/populate-roadmap-from-arch/SKILL.md"
}

@test "populate_wrapper: SKILL.md troubleshooting has reset command" {
    grep -q "rm .rddf/state/.populate-state.json" "$REPO_ROOT/skills/populate-roadmap-from-arch/SKILL.md"
}

@test "populate_wrapper: populate.sh sources guide-arch's roadmap_incremental_update.sh" {
    grep -q "guide-arch/scripts/roadmap_incremental_update.sh" "$REPO_ROOT/skills/populate-roadmap-from-arch/scripts/populate.sh"
}

@test "populate_wrapper: --standalone flag forces full mode (v1.1 compat)" {
    cd "$TEST_TMPDIR"
    run bash "$REPO_ROOT/skills/populate-roadmap-from-arch/scripts/populate.sh" . --standalone
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Mode: full" ]]
}

@test "populate_wrapper: --roadmap-update=off skips entirely (v1.1 compat)" {
    cd "$TEST_TMPDIR"
    run bash "$REPO_ROOT/skills/populate-roadmap-from-arch/scripts/populate.sh" . --roadmap-update=off
    [ "$status" -eq 0 ]
    [ ! -f .rddf/state/.populate-state.json ]
}
