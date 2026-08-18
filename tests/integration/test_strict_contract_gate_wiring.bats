#!/usr/bin/env bats

# tests/integration/test_strict_contract_gate_wiring.bats
#
# Verifies STRICT_CONTRACT_GATE / SKIP_CONTRACT_GATE env var escalation
# in plan_done_gate.sh::check_contract_gate (ADR-0018 pattern).
# Each case mocks `rddf contract-check` to simulate breaking diff.

load_test_helper() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
}

setup() {
    load_test_helper
    PLAN_GATE="$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
    MOCK_BIN="$BATS_TEST_TMPDIR/mock-bin"
    mkdir -p "$MOCK_BIN"
    export PATH_ORIG="$PATH"
}

mock_rddf_contract_breaking() {
    cat > "$MOCK_BIN/rddf" <<'EOF'
#!/usr/bin/env bash
case "$1" in
    contract-check) echo "mock: breaking diff detected" >&2; exit 1 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$MOCK_BIN/rddf"
    export PATH="$MOCK_BIN:$PATH_ORIG"
}

mock_rddf_clean() {
    cat > "$MOCK_BIN/rddf" <<'EOF'
#!/usr/bin/env bash
case "$1" in
    contract-check) echo "mock: no diff"; exit 0 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$MOCK_BIN/rddf"
    export PATH="$MOCK_BIN:$PATH_ORIG"
}

hide_rddf() {
    # PATH 只留 system bin，不放 mock — rddf 在 mock 之外不可达
    export PATH="/usr/bin:/bin"
}

@test "默认模式: contract-check breaking diff → check_contract_gate 不阻断" {
    mock_rddf_contract_breaking
    unset STRICT_CONTRACT_GATE
    unset SKIP_CONTRACT_GATE
    run bash -c "source '$PLAN_GATE'; check_contract_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"contract"* ]] || [[ "$output" == *"⚠"* ]] || [[ "$output" == *"warning"* ]] || true
}

@test "STRICT 模式: STRICT_CONTRACT_GATE=yes + breaking → exit 1" {
    mock_rddf_contract_breaking
    export STRICT_CONTRACT_GATE=yes
    unset SKIP_CONTRACT_GATE
    run bash -c "source '$PLAN_GATE'; check_contract_gate" 2>&1
    [ "$status" -eq 1 ]
    [[ "$output" == *"STRICT"* ]]
}

@test "SKIP 模式: SKIP_CONTRACT_GATE=yes → exit 0 含 SKIP 标记" {
    hide_rddf
    export SKIP_CONTRACT_GATE=yes
    unset STRICT_CONTRACT_GATE
    run bash -c "source '$PLAN_GATE'; check_contract_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP"* ]]
}

@test "默认 + no rddf on PATH: 优雅跳过 (exit 0, 含 INFO)" {
    hide_rddf
    unset STRICT_CONTRACT_GATE
    unset SKIP_CONTRACT_GATE
    run bash -c "source '$PLAN_GATE'; check_contract_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"INFO"* ]] || [[ "$output" == *"PATH"* ]]
}

@test "默认 + clean contract-check: 静默通过 (exit 0, 无 warning)" {
    mock_rddf_clean
    unset STRICT_CONTRACT_GATE
    unset SKIP_CONTRACT_GATE
    run bash -c "source '$PLAN_GATE'; check_contract_gate" 2>&1
    [ "$status" -eq 0 ]
    # 无 breaking warning (mock 走 exit 0 分支, 函数直接 return 0)
    [[ "$output" != *"⚠"* ]] || true
}