#!/usr/bin/env bats
# tests/integration/test_plan_review_phase.bats
#
# Cover the Plan-critic integration introduced in ADR-0015:
# `openspec validate` as the plan_done gate check, plus the
# `plan.review_validation` human-in-loop node, plus the
# `validate_report.py` view module.
#
# Lock structural presence so future refactors don't remove the
# plan-critic integration without breaking tests.
#
# Run: bats tests/integration/test_plan_review_phase.bats

load ../test_helper

setup() {
    cd "$REPO_ROOT"
}

@test "plan_review: ADR-0015 document exists in docs/adr/" {
    [ -f "docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md" ]
    grep -q "openspec validate" "docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md"
}

@test "plan_review: gate.py has _check_openspec_validate function" {
    [ -f "skills/_lib/gate.py" ]
    grep -q "_check_openspec_validate" "skills/_lib/gate.py"
}

@test "plan_review: gate.py registers openspec_validate in plan_done checks" {
    [ -f "skills/_lib/gate.py" ]
    grep -qE 'Check\("openspec_validate"' "skills/_lib/gate.py"
}

@test "plan_review: gate.py _check_deps_analyzed is no longer a no-op (ADR-0015 Decision 3)" {
    [ -f "skills/_lib/gate.py" ]
    # Reject the historic placeholder that always returned (True, "warning")
    ! awk '/def _check_deps_analyzed/,/^$/' "skills/_lib/gate.py" | grep -q 'return (True, "warning")'
}

@test "plan_review: human_nodes.py registers plan.review_validation node" {
    [ -f "skills/_lib/loop/human_nodes.py" ]
    grep -q '"plan.review_validation"' "skills/_lib/loop/human_nodes.py"
}

@test "plan_review: validate_report view module exists with dataclass" {
    [ -f "skills/_lib/validate_report.py" ]
    grep -q "class ValidateReport" "skills/_lib/validate_report.py"
    grep -q "def write_report" "skills/_lib/validate_report.py"
    grep -q "def load_report" "skills/_lib/validate_report.py"
}

@test "plan_review: openspec CLI is available (1.3.1+ declared, runtime must satisfy)" {
    # Required by ADR-0015 Decision 1 — OpenSpec is the plan-critic substrate
    if ! command -v openspec >/dev/null 2>&1; then
        skip "openspec CLI not installed in this environment"
    fi
    run openspec --version
    [ "$status" -eq 0 ]
}

@test "plan_review: validate_report is gitignored (state file lives under .rddf/)" {
    # validate_report writes to .rddf/state/openspec-validate.json
    [ -f ".gitignore" ]
    grep -qE '^\.rddf/state/' ".gitignore" || grep -qE '^\.rddf/' ".gitignore"
}
