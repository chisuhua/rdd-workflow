load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-exec-mode-per-change"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p openspec/changes
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

teardown() {
    rm -rf "$TEST_REPO"
}

create_change() {
    local name="$1"
    local proposal_text="$2"
    local tasks_count="${3:-3}"
    mkdir -p "openspec/changes/$name"
    echo "schema: spec-driven" > "openspec/changes/$name/.openspec.yaml"
    echo "# $name" > "openspec/changes/$name/proposal.md"
    echo "$proposal_text" >> "openspec/changes/$name/proposal.md"
    echo "## Implementation Tasks" > "openspec/changes/$name/tasks.md"
    for i in $(seq 1 "$tasks_count"); do
        echo "- [ ] Task $i" >> "openspec/changes/$name/tasks.md"
    done
}

@test "per-change: lightweight when small (no risk, ≤5 tasks)" {
    create_change "small-fix" "Minor doc tweak."
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "small-fix"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "lightweight" ]]
}

@test "per-change: worktree when proposal has refactor keyword" {
    create_change "refactor-foo" "Need to refactor the existing module."
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "refactor-foo"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worktree" ]]
}

@test "per-change: worktree when proposal has migration keyword" {
    create_change "migrate-bar" "Schema migration required."
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "migrate-bar"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worktree" ]]
}

@test "per-change: worktree when proposal has breaking keyword" {
    create_change "breaking-baz" "This is a breaking API change."
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "breaking-baz"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worktree" ]]
}

@test "per-change: worktree when task_count > 5" {
    create_change "big-tasks" "Some change." 8
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "big-tasks"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worktree" ]]
}

@test "fallback: worktree when multiple active changes exist" {
    create_change "first-change" "Tweak A." 2
    create_change "second-change" "Tweak B." 2
    git add -A && git commit -q -m "init"
    PROJECT_ROOT="$TEST_REPO" run detect_execution_mode "$TEST_REPO" "first-change"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "worktree" ]]
    [[ "$output" =~ "并行风险" ]]
}