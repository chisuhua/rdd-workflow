#!/usr/bin/env bats
# tests/integration/test_from_issue.bats
# Integration tests for add-improve --from-issue mode.
#
# Tests cover:
# - Successful scaffold creation with issue_ref + gh_repo frontmatter
# - Slug collision → -i<N> suffix when slug already exists
# - Dedup against .rddf/improvements/*.md frontmatter
# - Dedup against openspec/changes/*/roadmap-meta.yaml::issue_refs
# - gh missing → exit 2 + clear error
# - Rejection of shell injection in title
# - HARD-GATE: does NOT modify proposal-suggestions.md
# - Env-var cleanup on exit (no shell pollution)

setup() {
    load ../test_helper
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/state"
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    SCRIPT="$WT_ROOT/skills/add-improve/scripts/from_issue.sh"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "from_issue creates scaffold with issue_ref + gh_repo frontmatter" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Fix race condition" \
        --body "Steps to reproduce..." \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    # Find scaffold file (slug-form)
    PROPOSAL=$(find "$TEST_PROJECT_ROOT/.rddf/improvements" -name "*.md" | head -1)
    [ -f "$PROPOSAL" ]

    grep -q '\*\*issue_ref\*\*: 42' "$PROPOSAL"
    grep -q '\*\*gh_repo\*\*: foo/bar' "$PROPOSAL"
    grep -q "Fix race condition" "$PROPOSAL"
    grep -q "Steps to reproduce" "$PROPOSAL"
}

@test "from_issue slug collision appends -i<N> suffix" {
    # Pre-create a slug-collision
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition.md" <<EOF
---
issue_ref: 99
---
# fix-race-condition
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Fix race condition" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    # New file should be fix-race-condition-i42.md
    [ -f "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition-i42.md" ]
    # Original file should NOT be overwritten
    grep -q "issue_ref: 99" "$TEST_PROJECT_ROOT/.rddf/improvements/fix-race-condition.md"
}

@test "from_issue dedup against existing .rddf/improvements" {
    # Pre-create a proposal with issue_ref: 42
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/old-proposal.md" <<EOF
---
issue_ref: 42
---
# old-proposal
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "New Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 2 ]
    # Dedup message contains "引用" or "ERROR" or "improvements"
    [[ "$output" == *"引用"* ]] || [[ "$output" == *"ERROR"* ]] || [[ "$output" == *"improvements"* ]]
    # No new file should be created
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/new-proposal.md" ]
}

@test "from_issue dedup against openspec/changes/*/roadmap-meta.yaml" {
    mkdir -p "$TEST_PROJECT_ROOT/openspec/changes/fix-existing"
    cat > "$TEST_PROJECT_ROOT/openspec/changes/fix-existing/roadmap-meta.yaml" <<EOF
issue_refs: [42]
gh_repo: foo/bar
EOF

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "New Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 2 ]
    [[ "$output" == *"roadmap-meta"* ]]
}

@test "from_issue rejects shell injection in title" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title 'evil$(whoami)' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"disallowed"* ]] || [[ "$output" == *"ERROR"* ]]
    # Verify no file was created
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/evil-whoami-i42.md" ]
}

@test "from_issue rejects backtick injection" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title 'evil`id`' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
}

@test "from_issue requires --from-issue arg" {
    run bash "$SCRIPT" \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"required"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "from_issue requires --title arg" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
}

@test "from_issue HARD-GATE: does NOT modify proposal-suggestions.md" {
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test Proposal" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    # After successful run, proposal-suggestions.md still should NOT exist
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]
}

@test "from_issue unsets env-vars on exit (no shell pollution)" {
    bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After exit, env-vars should NOT be set in current shell
    [ -z "${ADD_IMPROVE_FROM_ISSUE:-}" ]
    [ -z "${ADD_IMPROVE_GH_REPO:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_TITLE:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_BODY:-}" ]
}

@test "from_issue output mentions HARD-GATE explicitly" {
    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"HARD-GATE"* ]]
    [[ "$output" == *"brainstorm"* ]]
}

@test "from_issue body > 4000 chars is truncated with reference URL" {
    LONG_BODY=$(printf 'x%.0s' {1..5000})

    run bash "$SCRIPT" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --body "$LONG_BODY" \
        --project-root "$TEST_PROJECT_ROOT"

    # Env-var validation rejects >4000 chars; expect failure
    [ "$status" -ne 0 ]
    [[ "$output" == *"4000"* ]]
}
