load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-e2e"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p openspec/changes/alpha .rddf/state
    printf '# P\n' > openspec/changes/alpha/proposal.md
    printf '# D\n' > openspec/changes/alpha/design.md
    printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/alpha/tasks.md
    echo '{}' > .rddf/state/.plan-handoff.json
    echo '{}' > .rddf/state/iteration.json
    git add -A
    git commit -q -m "init"
}

@test "rddf discover-ship-changes reports alpha" {
    RDDF_PROJECT_ROOT="$TEST_REPO" \
        run python3 -m skills._lib.cli discover-ship-changes
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"name": "alpha"' ]]
}

@test "singleton auto-select surfaces alpha via bash wrapper" {
    source "$PROJECT_ROOT/_lib/discover_ship_changes.sh"
    run ship_top_candidate "$TEST_REPO"
    [ "$status" -eq 0 ]
    [ "$output" = "alpha" ]
}

@test "candidate carries iteration_status from iteration.json" {
    cd "$TEST_REPO"
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [{"name": "alpha", "status": "proposed"}]}
EOF
    source "$PROJECT_ROOT/_lib/discover_ship_changes.sh"
    run ship_candidates_json "$TEST_REPO"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"iteration_status": "proposed"' ]]
}

@test "single change gets priority over disk-only with branch" {
    cd "$TEST_REPO"
    # Create second disk-only change; first still wins because it has iteration
    mkdir -p openspec/changes/beta
    printf '# P\n' > openspec/changes/beta/proposal.md
    printf '# D\n' > openspec/changes/beta/design.md
    printf -- '- [ ] x\n' > openspec/changes/beta/tasks.md
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [{"name": "alpha", "status": "proposed"}]}
EOF
    source "$PROJECT_ROOT/_lib/discover_ship_changes.sh"
    run ship_top_candidate "$TEST_REPO"
    [ "$output" = "alpha" ]
}