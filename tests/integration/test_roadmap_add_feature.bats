#!/usr/bin/env bats
# tests/integration/test_roadmap_add_feature.bats
# Integration tests for rddf roadmap add-feature CLI primitive.

setup() {
    load test_helper
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    SCRIPT="$REPO_ROOT/skills/roadmap/scripts/roadmap_add_feature.sh"
    WRAPPER="$REPO_ROOT/_lib/roadmap_state_wrapper.py"
    TMPDIR="$(mktemp -d)"
    cd "$TMPDIR"
    git init -q .
    mkdir -p .rddf/roadmap/phases
    echo "# Roadmap" > .rddf/roadmap.md
    cat > .rddf/roadmap/phases/phase-1.md <<'EOF'
---
id: phase-1
kind: phase
status: active
phase_refs: []
主题: test
---

# phase-1
EOF
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "sh: script exists and is executable" {
    [ -f "$SCRIPT" ]
    [ -x "$SCRIPT" ]
}

@test "sh: rejects missing name (exit 2)" {
    run bash "$SCRIPT" --phase-refs phase-1 --theme "test"
    [ "$status" -eq 2 ]
}

@test "sh: rejects missing --phase-refs (exit 2)" {
    run bash "$SCRIPT" --name test --theme "test"
    [ "$status" -eq 2 ]
}

@test "sh: rejects missing --theme (exit 2)" {
    run bash "$SCRIPT" --name test --phase-refs phase-1
    [ "$status" -eq 2 ]
}

@test "sh: creates fragment with valid frontmatter" {
    PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" smoke-test --phase-refs phase-1 --theme "smoke test"
    [ -f "$TMPDIR/.rddf/roadmap/features/feat-smoke-test.md" ]
    grep -q "id: feat-smoke-test" "$TMPDIR/.rddf/roadmap/features/feat-smoke-test.md"
    grep -q "主题: smoke test" "$TMPDIR/.rddf/roadmap/features/feat-smoke-test.md"
}

@test "sh: refreshes AUTO-INDEX in main roadmap doc" {
    PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" idx-test --phase-refs phase-1 --theme "indexed"
    grep -q "feat-idx-test" "$TMPDIR/.rddf/roadmap.md"
}

@test "sh: rejects duplicate without --force (exit 1)" {
    PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" dup --phase-refs phase-1 --theme "first"
    run env PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" dup --phase-refs phase-1 --theme "second"
    [ "$status" -eq 1 ]
}

@test "sh: --force overwrites existing fragment" {
    PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" force --phase-refs phase-1 --theme "first"
    PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" force --phase-refs phase-1 --theme "second" --force
    grep -q "主题: second" "$TMPDIR/.rddf/roadmap/features/feat-force.md"
}

@test "sh: rejects invalid --status (exit 2)" {
    run bash "$SCRIPT" test --phase-refs phase-1 --theme "t" --status xyz
    [ "$status" -eq 2 ]
}

@test "sh: rejects unknown phase_ref (exit 1)" {
    run env PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" test --phase-refs phase-99 --theme "t"
    [ "$status" -eq 1 ]
}

@test "sh: rejects invalid kebab-case name (exit 1)" {
    run env PROJECT_ROOT="$TMPDIR" bash "$SCRIPT" "Bad_Name" --phase-refs phase-1 --theme "t"
    [ "$status" -eq 1 ]
}

@test "rddf roadmap --help lists add-feature subcommand" {
    cd "$REPO_ROOT"
    PROJECT_ROOT="$REPO_ROOT" run python3 _lib/cli/roadmap_cmd.py --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"add-feature"* ]]
}

@test "rddf roadmap add-feature unknown subcommand returns exit 2" {
    cd "$REPO_ROOT"
    run python3 _lib/cli/roadmap_cmd.py add-feature-bogus
    [ "$status" -eq 2 ]
}

@test "guide-arch SKILL.md contains 添加 feature fragment menu option" {
    grep -q "添加 feature fragment" "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "guide-arch SKILL.md role.boundaries.owns includes features/*.md" {
    grep -q "\.rddf/roadmap/features/\*\.md" "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "roadmap SKILL.md documents add-feature subcommand" {
    grep -q "add-feature" "$REPO_ROOT/skills/roadmap/SKILL.md"
}