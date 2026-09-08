#!/usr/bin/env bats
# tests/e2e/integration/test_rdd_workflow_e2e_coop.bats
# Per Plan 5: rdd-workflow ↔ chisuhua/rdd-workflow-e2e co-op contract
# 3 cases verify compatibility with external testbed reader/parser.

load ../../test_helper

setup() {
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
}

@test "coop: scenario JSON 兼容 — 所有 scenarios/*.json 含 5 必填字段" {
    local missing=0
    local count=0
    for f in "$REPO_ROOT/tests/e2e/agent/scenarios"/*.json; do
        [ -f "$f" ] || continue
        count=$((count + 1))
        for field in scenario_id skill input golden_output isolation; do
            if ! grep -q "\"$field\"" "$f"; then
                echo "MISSING $field in $f" >&2
                missing=$((missing + 1))
            fi
        done
    done
    [ "$missing" -eq 0 ]
    [ "$count" -ge 44 ]  # 8 q + 12 b + 8 v + 8 a + 8 p
}

@test "coop: verdict JSON 兼容 — mock_output 含 6 字段 (per VERDICT_ITEM_SCHEMA v1)" {
    local count=0
    for f in "$REPO_ROOT/tests/e2e/agent/scenarios"/*.json; do
        [ -f "$f" ] || continue
        # If file mentions ac-verdict, check it has all 6 fields somewhere
        if grep -q "ac-verdict" "$f"; then
            count=$((count + 1))
            for field in ac_id description status confidence evidence reasoning; do
                if ! grep -q "$field" "$f"; then
                    echo "verdict file $f missing field: $field" >&2
                    return 1
                fi
            done
        fi
    done
    [ "$count" -ge 1 ]  # at least one file should reference ac-verdict
}

@test "coop: workflow 触发合规 — e2e-nightly.yml + test.yml 含 e2e 步骤 + continue-on-error" {
    # e2e-nightly.yml must have continue-on-error: true for credential-missing skip
    grep -q "continue-on-error: true" "$REPO_ROOT/.github/workflows/e2e-nightly.yml"
    # e2e-nightly.yml must trigger on schedule
    grep -q "schedule:" "$REPO_ROOT/.github/workflows/e2e-nightly.yml"
    grep -q "cron:" "$REPO_ROOT/.github/workflows/e2e-nightly.yml"
    # test.yml must invoke e2e-smoke
    grep -q "\-\-e2e-smoke" "$REPO_ROOT/.github/workflows/test.yml"
    # test.sh must have --e2e-agent and --e2e-smoke modes
    grep -q "e2e-smoke" "$REPO_ROOT/test.sh"
    grep -q "e2e-agent" "$REPO_ROOT/test.sh"
}
