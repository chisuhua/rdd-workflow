load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-ship-singleton"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p openspec/changes/alpha
    printf '# Tasks\n- [ ] a\n- [ ] b\n' > openspec/changes/alpha/tasks.md
    printf '# Proposal\n' > openspec/changes/alpha/proposal.md
    printf '# Design\n' > openspec/changes/alpha/design.md
    mkdir -p .rddf/state
    echo '{}' > .rddf/state/.plan-handoff.json
    git add -A
    git commit -q -m "init"
}

@test "singleton change auto-selects top candidate" {
    source "$PROJECT_ROOT/skills/_lib/discover_ship_changes.sh"
    run ship_top_candidate "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ "$output" = "alpha" ]
}

@test "multi-change shows count=2 (menu path)" {
    mkdir -p openspec/changes/beta
    printf '# Tasks\n- [ ] x\n' > openspec/changes/beta/tasks.md
    printf '# P\n' > openspec/changes/beta/proposal.md
    printf '# D\n' > openspec/changes/beta/design.md
    source "$PROJECT_ROOT/skills/_lib/discover_ship_changes.sh"
    run ship_candidate_count "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ "$output" = "2" ]
}

@test "disk-only candidate is flagged needs_reconciliation" {
    source "$PROJECT_ROOT/skills/_lib/discover_ship_changes.sh"
    run ship_candidates_json "$TEST_REPO"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "\"name\": \"alpha\"" ]]
    [[ "$output" =~ "\"filesystem_present\": true" ]]
}