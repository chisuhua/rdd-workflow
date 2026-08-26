#!/usr/bin/env bats
# test_rdd_verifier_helpers.bats — Integration tests for 4 bash helpers
#
# Per ADR-0034 §4.1: scan_queue / run_verification / classify_failure / route_loop
#
# CRITICAL: test_helper.bash exports PROJECT_ROOT=$REPO_ROOT globally.
# We must unset it in setup() so our scripts fall back to git toplevel
# (= TEST_TMP after setup's `cd $TEST_TMP` + `git init`) for proper isolation.
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    unset PROJECT_ROOT  # Force fallback to git toplevel (= TEST_TMP)
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

# === scan_queue.sh ===

@test "scan_queue.sh: empty iteration.json returns empty stdout" {
    echo '{"changes": []}' > .rddf/state/iteration.json
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "scan_queue.sh: filters ship-done only (returns 'a c')" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "a", "status": "ship-done"},
  {"name": "b", "status": "planned"},
  {"name": "c", "status": "ship-done"}
]}
EOF
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ "$output" = "a c" ]
}

@test "scan_queue.sh: missing iteration.json returns empty" {
    rm -f .rddf/state/iteration.json
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "scan_queue.sh: honors RDDF_VERIFIER_MAX_CHANGES (returns 'a b')" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "a", "status": "ship-done"},
  {"name": "b", "status": "ship-done"},
  {"name": "c", "status": "ship-done"}
]}
EOF
    export RDDF_VERIFIER_MAX_CHANGES=2
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/scan_queue.sh"
    [ "$status" -eq 0 ]
    [ "$output" = "a b" ]
    unset RDDF_VERIFIER_MAX_CHANGES
}

# === run_verification.sh ===

@test "run_verification.sh: missing change_name exits 2" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/run_verification.sh"
    [ "$status" -eq 2 ]
}

@test "run_verification.sh: missing ac-verifier skill (in TEST_TMP) exits 3" {
    # TEST_TMP has no skills/, so ac-verifier not found → exit 3
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/run_verification.sh" nonexistent-change
    [ "$status" -eq 3 ]
    [[ "$output" == *"ac-verifier skill not found"* ]]
}

# === classify_failure.sh ===

@test "classify_failure.sh: missing cache exits 1" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" no-cache-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"verdict cache missing"* ]]
}

@test "classify_failure.sh: missing change_name exits 2" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh"
    [ "$status" -eq 2 ]
}

@test "classify_failure.sh: classifies 'missing' as implementation_gap" {
    cat > .rddf/state/.ac-verdict-test.json <<'EOF'
{"version":1,"change":"test","codebase_commit":"abc1234","verdict":[
  {"ac_id":"AC-1","status":"fail","confidence":0.9,"evidence":[],"reasoning":"Function is missing from codebase"}
],"ran_at":"2026-08-26T00:00:00Z","ran_by":"rdd-verifier"}
EOF
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test
    [ "$status" -eq 0 ]
    [ "$output" = "AC-1:implementation_gap" ]
}

@test "classify_failure.sh: classifies 'exists but' as proposal_drift" {
    cat > .rddf/state/.ac-verdict-test.json <<'EOF'
{"version":1,"change":"test","codebase_commit":"abc1234","verdict":[
  {"ac_id":"AC-1","status":"fail","confidence":0.9,"evidence":[],"reasoning":"Code exists but mismatches the AC"}
],"ran_at":"2026-08-26T00:00:00Z","ran_by":"rdd-verifier"}
EOF
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/classify_failure.sh" test
    [ "$status" -eq 0 ]
    [ "$output" = "AC-1:proposal_drift" ]
}

# === route_loop.sh ===

@test "route_loop.sh: missing args exits 2" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"usage"* ]]
}

@test "route_loop.sh: missing label exits 2" {
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" only-change
    [ "$status" -eq 2 ]
}

@test "route_loop.sh: implementation_gap routes to guide-ship" {
    export RDDF_VERIFIER_MAX_LOOPS=3
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" route-gap-test implementation_gap
    [ "$status" -eq 0 ]
    [[ "$output" == *"guide-ship"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "route_loop.sh: proposal_drift routes to guide-plan" {
    export RDDF_VERIFIER_MAX_LOOPS=3
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" route-drift-test proposal_drift
    [ "$status" -eq 0 ]
    [[ "$output" == *"guide-plan"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "route_loop.sh: halts after max_loops=2 (export env)" {
    export RDDF_VERIFIER_MAX_LOOPS=2
    bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" halt-loop-test implementation_gap
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" halt-loop-test implementation_gap
    [ "$status" -eq 1 ]
    [[ "$output" == *"HALTED"* ]]
    unset RDDF_VERIFIER_MAX_LOOPS
}

@test "route_loop.sh: writes halted state to disk" {
    export RDDF_VERIFIER_MAX_LOOPS=1
    run bash "$REPO_ROOT/skills/rdd-verifier/scripts/route_loop.sh" halt-disk-test implementation_gap
    [ "$status" -eq 1 ]
    [ -f ".rddf/state/.verifier-loop.json" ]
    grep -q '"route": "halted"' .rddf/state/.verifier-loop.json
    unset RDDF_VERIFIER_MAX_LOOPS
}