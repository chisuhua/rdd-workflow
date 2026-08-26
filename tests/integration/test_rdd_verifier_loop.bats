#!/usr/bin/env bats
# test_rdd_verifier_loop.bats — Loop boundary tests for rdd-verifier
#
# Per ADR-0034 §6.3: max_loops trigger halts archive with audit log.
# Tests the 3-retry cap, halt reason, and audit trail behavior.
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
    mkdir -p .rddf/state
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "loop: max_loops=3 then 4th call halts" {
    export RDDF_VERIFIER_MAX_LOOPS=3
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" loop-3-test implementation_gap >/dev/null 2>&1 || true
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" loop-3-test implementation_gap >/dev/null 2>&1 || true
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" loop-3-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
    [[ "$output" == *"max_loops=3"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "loop: max_loops=1 halts on 2nd call (strict mode)" {
    export RDDF_VERIFIER_MAX_LOOPS=1
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" loop-1-test implementation_gap >/dev/null 2>&1 || true
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" loop-1-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "loop: halted state has route='halted' + halt_reason" {
    export RDDF_VERIFIER_MAX_LOOPS=1
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" halted-state-test implementation_gap
    [ "$status" -eq 1 ]
    [ -f ".rddf/state/.verifier-loop.json" ]

    # Verify state structure (route + halt_reason fields populated)
    grep -q '"route": "halted"' .rddf/state/.verifier-loop.json
    grep -q '"halt_reason"' .rddf/state/.verifier-loop.json
    grep -q '"implementation_gap"' .rddf/state/.verifier-loop.json
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "loop: classification history accumulates across loops" {
    export RDDF_VERIFIER_MAX_LOOPS=5
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" history-test implementation_gap >/dev/null 2>&1 || true
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" history-test proposal_drift >/dev/null 2>&1 || true
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" history-test implementation_gap >/dev/null 2>&1 || true

    # loop_count should be 3
    grep -q '"loop_count": 3' .rddf/state/.verifier-loop.json
    # classification_history should have 3 entries
    classification_count=$(python3 -c "
import json
d = json.load(open('.rddf/state/.verifier-loop.json'))
print(len(d.get('classification_history', [])))
")
    [ "$classification_count" -eq 3 ]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "loop: non-halted state retains route='guide-ship' or 'guide-plan'" {
    export RDDF_VERIFIER_MAX_LOOPS=5
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" non-halt-test implementation_gap
    [ "$status" -eq 0 ]
    grep -q '"route": "guide-ship"' .rddf/state/.verifier-loop.json
    grep -q '"halt_reason": null' .rddf/state/.verifier-loop.json
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "loop: unknown label exits 2 (validation)" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" bad-label-test unknown_label
    [ "$status" -eq 2 ]
    [[ "$output" == *"unknown label"* ]]
}

@test "loop: max_loops=3 boundary (2 succeed, 3rd halts, 4th idempotent)" {
    export RDDF_VERIFIER_MAX_LOOPS=3
    # First 2 calls succeed (loop_count 1, 2; both < 3)
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" boundary-test implementation_gap
    [ "$status" -eq 0 ]
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" boundary-test implementation_gap
    [ "$status" -eq 0 ]
    # 3rd: loop_count=3 >= max_loops=3 → halt
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" boundary-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
    # 4th: still halted (idempotent — state remains 'halted')
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" boundary-test implementation_gap
    [ "$status" -eq 1 ]
    unset RDDF_VERIFIER_MAX_LOOPS
}