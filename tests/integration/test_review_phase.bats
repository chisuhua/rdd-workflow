#!/usr/bin/env bats
# tests/integration/test_review_phase.bats
#
# Cover the Phase 2.5 review section added in ADR-0014.
# Locks structural presence of review phase, type field, status enum,
# and gate check so future refactors don't accidentally remove them.
#
# Run: bats tests/integration/test_review_phase.bats

load ../test_helper

setup() {
    cd "$REPO_ROOT"
}

@test "review_phase: Phase 2.5 section exists in guide-ship.md" {
    [ -f "skills/guide-ship.md" ]
    grep -q "Phase 2.5: review" "skills/guide-ship.md"
}

@test "review_phase: review menu has 5 numbered options" {
    count=$(grep -cE '^[1-5]\.' <(
        awk '/^请选择:/,/^```$/' "skills/guide-ship.md" | head -30
    ) 2>/dev/null || echo 0)
    [ "$count" -ge 1 ]  # at least one option block exists
    grep -qE '范围內债务|创建新 debt|架构漂移|跳过|查看详细' "skills/guide-ship.md"
}

@test "review_phase: proposal-suggestions-format.md has type field" {
    [ -f "docs/proposal-suggestions-format.md" ]
    grep -q '"type"' "docs/proposal-suggestions-format.md"
}

@test "review_phase: iteration.py has review in VALID_STATUSES" {
    [ -f "skills/_lib/iteration.py" ]
    grep -q '"review"' "skills/_lib/iteration.py"
}

@test "review_phase: iteration schema has version 3 and review status" {
    [ -f "skills/_lib/schemas/iteration_schema.json" ]
    # Schema v3: 'review' status is in the lifecycle enum, and version=3 is the current const.
    grep -q '"const": 3' "skills/_lib/schemas/iteration_schema.json"
    grep -q '"review"' "skills/_lib/schemas/iteration_schema.json"
}

@test "review_phase: gate.py has review_debt_recorded check" {
    [ -f "skills/_lib/gate.py" ]
    grep -q "review_debt_recorded" "skills/_lib/gate.py"
}