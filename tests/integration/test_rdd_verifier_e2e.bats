#!/usr/bin/env bats
# test_rdd_verifier_e2e.bats — End-to-end flow tests using mock fixtures
#
# Per ADR-0034 §8.1: end-to-end integration with fixtures from
# tests/_lib/verifier_mocks/{pass,fail,proposal_drift,implementation_gap}.json
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    unset PROJECT_ROOT
    cd "$TEST_TMP"
    git init -q
    git config user.email "t@t"
    git config user.name "T"
    echo "x" > x.txt
    git add x.txt
    git commit -q -m "init"
    mkdir -p .rddf/state openspec/changes/test-change
    cat > openspec/changes/test-change/tasks.md <<'EOF'
# Tasks
- [x] task 1 done
EOF
    cat > openspec/changes/test-change/proposal.md <<'EOF'
# Test
## 验收标准
- AC-1: A criterion
EOF
    git add . && git commit -q -m "add change"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Helper: copy a fixture and substitute the current commit SHA
_seed_fixture_cache() {
    local fixture_name="$1"
    local change_name="$2"
    local sha
    sha=$(git rev-parse HEAD)
    local fixture_path="$REPO_ROOT/tests/_lib/verifier_mocks/${fixture_name}.json"
    sed "s/abc1234567/$sha/g" "$fixture_path" \
        > ".rddf/state/.ac-verdict-${change_name}.json"
}

@test "e2e: all-pass queue (pass.json fixture) classifies nothing" {
    _seed_fixture_cache "pass" "test-change"
    cat > .rddf/state/iteration.json <<'EOF'
{"version": 7, "changes": [{"name": "test-change", "status": "completed", "tasks_done": 1, "tasks_total": 1}]}
EOF

    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test-change
    [ "$status" -eq 0 ]
    # No ACs fail → no output (only failing ACs get classified)
    [ -z "$output" ]
}

@test "e2e: SKIP_RDD_VERIFIER without reason fails closed" {
    _seed_fixture_cache "pass" "test-change"
    cat > .rddf/state/iteration.json <<'EOF'
{"version": 7, "changes": [{"name": "test-change", "status": "completed", "tasks_done": 1, "tasks_total": 1}]}
EOF

    SKIP_RDD_VERIFIER=yes run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 3 ]
    [[ "$output" == *"RDDF_VERIFIER_BYPASS_REASON"* ]]
}

@test "e2e: implementation_gap fixture routes to guide-ship" {
    _seed_fixture_cache "implementation_gap" "test-change"

    export RDDF_VERIFIER_MAX_LOOPS=3
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" test-change implementation_gap
    [ "$status" -eq 0 ]
    [[ "$output" == *"guide-ship"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "e2e: proposal_drift fixture routes to guide-plan" {
    _seed_fixture_cache "proposal_drift" "test-change"

    export RDDF_VERIFIER_MAX_LOOPS=3
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" test-change proposal_drift
    [ "$status" -eq 0 ]
    [[ "$output" == *"guide-plan"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "e2e: implementation_gap fixture classifies ACs correctly" {
    _seed_fixture_cache "implementation_gap" "test-change"

    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test-change
    [ "$status" -eq 0 ]
    # 2 ACs both fail with 'missing'/'absent' → both labeled implementation_gap
    [ "$output" = "AC-1:implementation_gap
AC-2:implementation_gap" ]
}

@test "e2e: proposal_drift fixture classifies ACs correctly" {
    _seed_fixture_cache "proposal_drift" "test-change"

    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test-change
    [ "$status" -eq 0 ]
    # 2 ACs both fail with 'exists but'/'differs from ac' → both labeled proposal_drift
    [ "$output" = "AC-1:proposal_drift
AC-2:proposal_drift" ]
}

@test "e2e: dry-run with completed change lists it" {
    _seed_fixture_cache "pass" "test-change"
    cat > .rddf/state/iteration.json <<'EOF'
{"version": 7, "changes": [{"name": "test-change", "status": "completed", "tasks_done": 1, "tasks_total": 1}]}
EOF

    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-change"* ]]
    [[ "$output" == *"Would verify"* ]]
}

@test "e2e: ambiguous fail fixture defaults to implementation_gap" {
    _seed_fixture_cache "fail" "test-change"

    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test-change
    [ "$status" -eq 0 ]
    # Per Oracle §E: ambiguous → conservative default = implementation_gap
    [ "$output" = "AC-1:implementation_gap" ]
}