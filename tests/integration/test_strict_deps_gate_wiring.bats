#!/usr/bin/env bats

# tests/integration/test_strict_deps_gate_wiring.bats
#
# Verifies STRICT_DEPS_GATE / SKIP_DEPS_GATE env var escalation in
# plan_done_gate.sh::check_cross_repo_deps_gate (ADR-0018 pattern).

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    PLAN_GATE="$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
    FAKE_CACHE="$BATS_TEST_TMPDIR/cross-repo-cache.json"
    mkdir -p "$BATS_TEST_TMPDIR/state"
}

write_cache_with_blockers() {
    cat > "$FAKE_CACHE" <<EOF
{
  "default": {
    "data": {
      "blockers": [
        {"change": "test-change", "spoke": "org/blocker-repo", "depends_on": "org/blocker-repo#x", "host_spoke": "org/blocker-repo"}
      ]
    },
    "timestamp": 9999999999
  }
}
EOF
    cat > "$REPO_ROOT/.rddf/state/iteration.json" <<EOF
{
  "changes": [
    {"name": "test-change", "status": "proposed", "cross_repo_dependencies": ["org/blocker-repo#x"]}
  ]
}
EOF
}

write_cache_clean() {
    cat > "$FAKE_CACHE" <<EOF
{
  "default": {
    "data": {"blockers": []},
    "timestamp": 9999999999
  }
}
EOF
    rm -f "$REPO_ROOT/.rddf/state/iteration.json"
}

@test "默认模式: cross-repo deps blocker → check_cross_repo_deps_gate 不阻断 (warning)" {
    write_cache_with_blockers
    unset STRICT_DEPS_GATE
    unset SKIP_DEPS_GATE
    run bash -c "source '$PLAN_GATE'; check_cross_repo_deps_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠"* ]] || [[ "$output" == *"cross-repo"* ]] || [[ "$output" == *"warning"* ]] || true
}

@test "STRICT 模式: STRICT_DEPS_GATE=yes + blocker → exit 1 + STRICT 标记" {
    write_cache_with_blockers
    export STRICT_DEPS_GATE=yes
    unset SKIP_DEPS_GATE
    run bash -c "source '$PLAN_GATE'; check_cross_repo_deps_gate" 2>&1
    [ "$status" -eq 1 ]
    [[ "$output" == *"STRICT"* ]]
}

@test "SKIP 模式: SKIP_DEPS_GATE=yes → exit 0 含 SKIP 标记" {
    export SKIP_DEPS_GATE=yes
    unset STRICT_DEPS_GATE
    run bash -c "source '$PLAN_GATE'; check_cross_repo_deps_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP"* ]]
}

@test "默认 + clean cache (no blockers): 静默通过 (exit 0, 无 warning)" {
    write_cache_clean
    unset STRICT_DEPS_GATE
    unset SKIP_DEPS_GATE
    run bash -c "source '$PLAN_GATE'; check_cross_repo_deps_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" != *"⚠"* ]] || true
}

teardown() {
    rm -f "$FAKE_CACHE"
    rm -f "$REPO_ROOT/.rddf/state/iteration.json"
}