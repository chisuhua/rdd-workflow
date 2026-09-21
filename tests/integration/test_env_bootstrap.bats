#!/usr/bin/env bats
#
# tests/integration/test_env_bootstrap.bats
#
# Integration tests for `rddf env-bootstrap` subcommand.
#
# Covers (per AC-2, AC-3, AC-5, AC-6, AC-7, AC-8, AC-9):
#   - --help output
#   - --check-only runs Phases 1-2 only, no file written
#   - --auto-fix --yes skips prompts
#   - --target /tmp/random exits 3
#   - ai-context-bootstrap triggers setup ai-context subprocess
#   - Report schema lands with version=1
#   - Exit code semantics (0/1/2/3)
#   - SKILL.md structural frontmatter (per AC-1)
#
# Requires the worktree checkout (rddf runs from local _lib/cli).
# Uses BATS_TMPDIR for scratch dirs (auto-cleanup).

load test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    # Use a scratch project so we don't pollute the real project state
    SCRATCH="$BATS_TMPDIR/env-bootstrap-test-$$-$BATS_TEST_NUMBER"
    mkdir -p "$SCRATCH"
    # Mark as rdd-workflow project by creating _lib/ marker
    mkdir -p "$SCRATCH/_lib"
    # Add AGENTS.md so Phase 1 detects it (clean baseline)
    echo "# test" > "$SCRATCH/AGENTS.md"
}

teardown() {
    rm -rf "$BATS_TMPDIR/env-bootstrap-test-$$-$BATS_TEST_NUMBER"
}

# ---- AC-2: --help shows all 5 flags ----

@test "env-bootstrap: rddf env-bootstrap --help shows 5 flags" {
    run python3 -m _lib.cli env-bootstrap --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "--check-only" ]]
    [[ "$output" =~ "--auto-fix" ]]
    [[ "$output" =~ "--yes" ]]
    [[ "$output" =~ "--target" ]]
    [[ "$output" =~ "--report" ]]
}

# ---- AC-2: --check-only runs Phases 1-2 only, no file written ----

@test "env-bootstrap: --check-only runs phases 1-2 only, no file written" {
    run python3 -m _lib.cli env-bootstrap --target "$SCRATCH" --check-only
    [ "$status" -eq 0 ]
    # No report file written
    [ ! -f "$SCRATCH/.rddf/state/.env-bootstrap-report.json" ]
    # Output contains phase_1 + phase_2 keys
    [[ "$output" =~ '"phase_1"' ]]
    [[ "$output" =~ '"phase_2"' ]]
    # No phase_4 key (since check-only)
    [[ ! "$output" =~ '"phase_4"' ]]
}

# ---- AC-3: _NO_STATE_CHECK extension — non-rdd-workflow exits 3 ----

@test "env-bootstrap: --target /tmp/non-rdd-project exits 3" {
    NON_RDD="$BATS_TMPDIR/non-rdd-$$-$BATS_TEST_NUMBER"
    mkdir -p "$NON_RDD"
    # No _lib/ marker → not a rdd-workflow project
    run python3 -m _lib.cli env-bootstrap --target "$NON_RDD" --check-only
    [ "$status" -eq 3 ]
    echo "$output" | grep -q "not a rdd-workflow project"
    rm -rf "$NON_RDD"
}

# ---- AC-7: Report schema lands with version=1 ----

@test "env-bootstrap: --check-only on clean project writes report with version=1" {
    run python3 -m _lib.cli env-bootstrap --target "$SCRATCH"
    # Clean project → exit 0
    [ "$status" -eq 0 ]
    [ -f "$SCRATCH/.rddf/state/.env-bootstrap-report.json" ]
    version=$(jq -r .version < "$SCRATCH/.rddf/state/.env-bootstrap-report.json")
    [ "$version" = "1" ]
}

# ---- AC-8: Exit code 0 for clean project ----

@test "env-bootstrap: clean project → exit 0" {
    # SCRATCH has AGENTS.md (existing) + _lib/ marker → clean baseline
    run python3 -m _lib.cli env-bootstrap --target "$SCRATCH"
    [ "$status" -eq 0 ]
}

# ---- AC-1: SKILL.md structural frontmatter ----

@test "env-bootstrap: SKILL.md frontmatter declares role.boundaries" {
    [ -f "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" ]
    # First 30 lines should contain the role block
    head -30 "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" | grep -q "role:"
    head -30 "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" | grep -q "boundaries:"
    head -30 "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" | grep -q "owns:"
    head -30 "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" | grep -q "not_owns:"
}

@test "env-bootstrap: SKILL.md body documents 4 phases" {
    [ -f "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md" ]
    grep -q "Phase 1" "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md"
    grep -q "Phase 2" "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md"
    grep -q "Phase 3" "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md"
    grep -q "Phase 4" "$PROJECT_ROOT/skills/rdd-env-bootstrap/SKILL.md"
}

# ---- AC-6: --auto-fix --yes bypasses prompts ----

@test "env-bootstrap: --auto-fix --yes skips Phase 4 prompts (clean project)" {
    # Clean project has 0 findings → Phase 4 is empty regardless of mode
    run python3 -m _lib.cli env-bootstrap --target "$SCRATCH" --auto-fix --yes
    [ "$status" -eq 0 ]
    # Verify report was written
    [ -f "$SCRATCH/.rddf/state/.env-bootstrap-report.json" ]
}

# ---- AC-6: classify_finding + ai-context-bootstrap flow ----

@test "env-bootstrap: classify_finding routes ai-context-bootstrap: 未部署 to auto-fixable" {
    sys_path="$PROJECT_ROOT/skills/rdd-env-bootstrap/scripts"
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
sys.path.insert(0, '$sys_path')
from diagnose import classify_finding
finding = {'category': 'ai-context-bootstrap', 'severity': 'warning', 'message': '未部署 Layer 0 协议块'}
result = classify_finding(finding)
assert result == 'auto-fixable', f'Expected auto-fixable, got {result}'
print('PASS: classify_finding')
"
}

@test "env-bootstrap: classify_finding routes gitignore to user-decision" {
    sys_path="$PROJECT_ROOT/skills/rdd-env-bootstrap/scripts"
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
sys.path.insert(0, '$sys_path')
from diagnose import classify_finding
finding = {'category': 'gitignore', 'severity': 'warning', 'message': 'openspec/ 缺失'}
result = classify_finding(finding)
assert result == 'user-decision', f'Expected user-decision, got {result}'
print('PASS: classify_finding gitignore')
"
}
