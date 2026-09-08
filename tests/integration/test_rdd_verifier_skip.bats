#!/usr/bin/env bats
# test_rdd_verifier_skip.bats — SKIP_RDD_VERIFIER + cost guardrail tests
#
# Per ADR-0034 §7.3: SKIP env var + MAX_CHANGES cost guardrail.
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

@test "skip: SKIP_RDD_VERIFIER=yes returns exit 3 (fail closed bypass)" {
    # v4 ADR-0034 §7.1 amended by ADR-0045: SKIP without RDDF_VERIFIER_BYPASS_REASON
    # is fail-closed (exit 3, requires audited bypass reason). v3 expected exit 2.
    SKIP_RDD_VERIFIER=yes run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 3 ]
    [[ "$output" == *"SKIP_RDD_VERIFIER"* ]]
    [[ "$output" == *"RDDF_VERIFIER_BYPASS_REASON"* ]]
}

@test "skip: SKIP_RDD_VERIFIER=yes overrides --max-changes and other args" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [{"name": "a", "status": "completed", "tasks_done": 1, "tasks_total": 1}]}
EOF
    SKIP_RDD_VERIFIER=yes run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --max-changes 5
    [ "$status" -eq 3 ]
    [[ "$output" == *"SKIP_RDD_VERIFIER"* ]]
}

@test "skip: SKIP_RDD_VERIFIER=yes with BYPASS_REASON exits 0" {
    # v4 fail-closed bypass: when SKIP_RDD_VERIFIER=yes AND RDDF_VERIFIER_BYPASS_REASON
    # is set, the verifier logs an audited bypass and returns 0 (no work to verify).
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [{"name": "a", "status": "completed", "tasks_done": 1, "tasks_total": 1}]}
EOF
    SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="Wave X2 test" \
        run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 0 ]
}

@test "skip: empty iteration.json returns 0 (no work to do)" {
    echo '{"changes": []}' > .rddf/state/iteration.json
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
    [ "$status" -eq 0 ]
    [[ "$output" == *"No eligible"* ]]
}

@test "skip: --max-changes 2 limits scan output to 2 changes" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "c1", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "c2", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "c3", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "c4", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "c5", "status": "completed", "tasks_done": 1, "tasks_total": 1}
]}
EOF
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run --max-changes 2
    [ "$status" -eq 0 ]
    # v4 dry-run output: "[dry-run] Would verify N change(s):" then "  - <name>"
    [[ "$output" == *"Would verify 2 change"* ]]
    [[ "$output" == *"  - c1"* ]]
    [[ "$output" == *"  - c2"* ]]
    [[ ! "$output" == *"  - c3"* ]]
    [[ ! "$output" == *"  - c5"* ]]
}

@test "skip: RDDF_VERIFIER_MAX_CHANGES env var honored as default" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "x1", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "x2", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "x3", "status": "completed", "tasks_done": 1, "tasks_total": 1}
]}
EOF
    RDDF_VERIFIER_MAX_CHANGES=2 run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"Would verify 2 change"* ]]
    [[ "$output" == *"  - x1"* ]]
    [[ "$output" == *"  - x2"* ]]
    [[ ! "$output" == *"  - x3"* ]]
}

@test "skip: --max-changes CLI flag overrides env var" {
    cat > .rddf/state/iteration.json <<'EOF'
{"changes": [
  {"name": "y1", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "y2", "status": "completed", "tasks_done": 1, "tasks_total": 1},
  {"name": "y3", "status": "completed", "tasks_done": 1, "tasks_total": 1}
]}
EOF
    RDDF_VERIFIER_MAX_CHANGES=5 run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" \
        --dry-run --max-changes 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"Would verify 1 change"* ]]
    [[ "$output" == *"  - y1"* ]]
    [[ ! "$output" == *"  - y2"* ]]
    [[ ! "$output" == *"  - y3"* ]]
}

@test "skip: --help shows expected flags" {
    run python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--max-changes"* ]]
    [[ "$output" == *"--loop"* ]]
}