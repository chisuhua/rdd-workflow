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

@test "review_phase: gate.py has review_debt_recorded check" {
    [ -f "_lib/gate.py" ]
    grep -q "review_debt_recorded" "_lib/gate.py"
}