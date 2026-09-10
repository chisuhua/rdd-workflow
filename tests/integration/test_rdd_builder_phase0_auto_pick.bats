#!/usr/bin/env bats
# tests/integration/test_rdd_builder_phase0_auto_pick.bats
# Integration tests for rdd-builder Phase 0 auto-pick mode (per 用户 UX 需求 2026-09-10).
#
# Coverage:
#  - Default mode (no flag) auto-picks case 5 when advisory=simple + AC ≤ 2
#  - Default mode auto-picks case 1 when advisory=simple + AC > 2
#  - Default mode auto-picks case 1 when advisory=complex (any AC)
#  - Default mode falls back to RDDF_REQUIRE_USER_CONFIRM logic when advisory=unknown
#  - RDDF_REQUIRE_USER_CONFIRM=yes forces user input (asks user)
#  - RDDF_REQUIRE_USER_CONFIRM=no (default) auto-picks without prompting
#  - --auto-approve CLI flag → case 1 (override auto-pick)
#  - --dispatch-quick CLI flag → case 5 (override auto-pick, still hard-validates)
#  - --require-confirm CLI flag → ask user
#  - AC count fallback: improvement file used when proposal.md absent (per ADR-0049)

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    PHASE0="$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh"
    WORK_TMP="$(mktemp -d)"
    cd "$WORK_TMP"
    git init -q .
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md
    mkdir -p .rddf/state/builder
    mkdir -p .rddf/improvements
    cat > .rddf/improvements/test-change.md <<'IMPROVE_EOF'
---
name: test-change
priority: P3
---

## Why
fix typo

## What
docs/README.md

## How
edit

## Acceptance
- [ ] typo fixed

## Capabilities
MUST: fix typo
MUST NOT: change behavior
IMPROVE_EOF
}

teardown() {
    rm -rf "$WORK_TMP"
}

# Helper: run phase0 with default auto-pick mode (no RDDF_REQUIRE_USER_CONFIRM)
run_auto() {
    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        env -u RDDF_REQUIRE_USER_CONFIRM \
        bash "$PHASE0" "$@"
}

# Helper: run phase0 with RDDF_REQUIRE_USER_CONFIRM=yes (ask user)
run_require_confirm() {
    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        RDDF_REQUIRE_USER_CONFIRM=yes \
        bash "$PHASE0" "$@"
}

# Helper: write planner-handoff.json with given recommended_route
write_planner_handoff() {
    local route="$1"
    cat > .rddf/state/.planner-handoff.json <<EOF
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "recommended_route": "$route"
}
EOF
}

# Helper: write proposal.md with N AC checkboxes
write_proposal_ac_count() {
    local n="$1"
    {
        echo "# proposal"
        for ((i=1; i<=n; i++)); do
            echo "- [ ] AC-$i"
        done
    } > openspec/changes/test-change/proposal.md
}


# --- DEFAULT MODE: auto-pick case 5 (advisory=simple + AC ≤ 2) ---

@test "auto-pick default: advisory=simple + AC=1 → auto-picks case 5 dispatch-quick" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-pick (default): option 5 (dispatch-quick)"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
    [[ "$output" != *"Choose [1-5]"* ]]  # should NOT prompt user
}

@test "auto-pick default: advisory=simple + AC=2 → auto-picks case 5 dispatch-quick" {
    write_planner_handoff "simple"
    write_proposal_ac_count 2

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"option 5 (dispatch-quick)"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}

@test "auto-pick default: advisory=simple + AC=3 → auto-picks case 1 approve" {
    write_planner_handoff "simple"
    write_proposal_ac_count 3

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-pick (default): option 1 (approve)"* ]]
    # Should write builder-handoff with approval_status=approved
    [ -f .rddf/state/builder/test-change.json ]
    run python3 -c "
import json
with open('.rddf/state/builder/test-change.json') as f:
    d = json.load(f)
assert d['approval_status'] == 'approved', f'got {d}'
print('OK: approval_status = approved')
"
    [ "$status" -eq 0 ]
}

@test "auto-pick default: advisory=simple + AC=10 → auto-picks case 1 approve" {
    write_planner_handoff "simple"
    write_proposal_ac_count 10

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"option 1 (approve)"* ]]
}

@test "auto-pick default: advisory=complex + AC=1 → auto-picks case 1 approve" {
    write_planner_handoff "complex"
    write_proposal_ac_count 1

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"option 1 (approve)"* ]]
    [[ "$output" != *"DISPATCH_TO_QUICK=1"* ]]  # case 1 doesn't emit dispatch marker
}

@test "auto-pick default: advisory=complex + AC=10 → auto-picks case 1 approve" {
    write_planner_handoff "complex"
    write_proposal_ac_count 10

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"option 1 (approve)"* ]]
}

@test "auto-pick default: no planner-handoff.json (advisory=unknown) + AC=1 → auto-picks case 1 approve (conservative)" {
    # No planner-handoff.json → PLANNER_ROUTE=unknown → conservative case 1
    write_proposal_ac_count 1

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"Planner advisory: recommended_route = unknown"* ]]
    [[ "$output" == *"option 1 (approve)"* ]]
}

@test "auto-pick default: no proposal.md + improvement file with 1 AC → AC count from improvement (per ADR-0049)" {
    write_planner_handoff "simple"
    rm openspec/changes/test-change/proposal.md

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"AC count: 1"* ]]
    [[ "$output" == *"from .rddf/improvements"* ]]
    [[ "$output" == *"option 5 (dispatch-quick)"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}


# --- RDDF_REQUIRE_USER_CONFIRM=yes mode: forces user input ---

@test "require-confirm: RDDF_REQUIRE_USER_CONFIRM=yes asks user (case 5 prompt)" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    # Provide "5" as stdin to simulate user input
    run_require_confirm test-change <<< "5"
    [ "$status" -eq 0 ]
    [[ "$output" == *"RDDF_REQUIRE_USER_CONFIRM=yes — asking user"* ]]
    # read -r -p prompt is sent to stderr (not captured by `run`), but we verify
    # that user input was accepted (case 5 path runs → DISPATCH_TO_QUICK emitted)
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}

@test "require-confirm: user picks 1 (approve) when prompted" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run_require_confirm test-change <<< "1"
    [ "$status" -eq 0 ]
    [[ "$output" == *"option 1 (approve)"* ]] || [[ "$output" == *"approved"* ]]
}

@test "require-confirm: user picks invalid input exits 2" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run_require_confirm test-change <<< "9"
    [ "$status" -eq 2 ]
}


# --- CLI flag overrides ---

@test "CLI --auto-approve: overrides auto-pick, always case 1" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    # Even when advisory=simple + AC=1, --auto-approve forces case 1
    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        env -u RDDF_REQUIRE_USER_CONFIRM \
        bash "$PHASE0" test-change --auto-approve
    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-pick (--auto-approve CLI): option 1 (approve)"* ]]
    [[ "$output" != *"DISPATCH_TO_QUICK=1"* ]]
}

@test "CLI --dispatch-quick: overrides auto-pick, always case 5 (with simple hard-validate)" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        env -u RDDF_REQUIRE_USER_CONFIRM \
        bash "$PHASE0" test-change --dispatch-quick
    [ "$status" -eq 0 ]
    [[ "$output" == *"Auto-pick (--dispatch-quick CLI): option 5 (dispatch-quick)"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}

@test "CLI --dispatch-quick: hard-validates recommended_route=simple (advisory=complex fails)" {
    write_planner_handoff "complex"
    write_proposal_ac_count 1

    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        env -u RDDF_REQUIRE_USER_CONFIRM \
        bash "$PHASE0" test-change --dispatch-quick
    [ "$status" -eq 2 ]
    [[ "$output" == *"requires recommended_route=simple"* ]]
}

@test "CLI --require-confirm: forces user input" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" \
        env -u RDDF_REQUIRE_USER_CONFIRM \
        bash "$PHASE0" test-change --require-confirm <<< "5"
    [ "$status" -eq 0 ]
    # User picked 5 → case 5 path runs → DISPATCH marker emitted
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}


# --- UX: auto-pick doesn't ask user by default ---

@test "UX: default mode never prompts user (no 'Choose [1-5]' line in output)" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run_auto test-change
    [ "$status" -eq 0 ]
    # Ensure no interactive prompt was shown
    [[ "$output" != *"Choose [1-5]"* ]]
}

@test "UX: auto-pick output includes reasoning prose for human review" {
    write_planner_handoff "simple"
    write_proposal_ac_count 1

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"🤖 Auto-pick (default): option 5"* ]]
    [[ "$output" == *"理由: advisory=simple + AC ≤ 2"* ]]
    [[ "$output" == *"如需用户介入, 设 RDDF_REQUIRE_USER_CONFIRM=yes"* ]]
}

@test "UX: auto-pick case 1 includes reasoning prose" {
    write_planner_handoff "complex"
    write_proposal_ac_count 5

    run_auto test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"🤖 Auto-pick (default): option 1"* ]]
    [[ "$output" == *"理由: advisory=complex, AC=5"* ]]
}


# --- SKILL.md documentation ---

@test "SKILL.md documents 阶段 0.0.5 全自动决策逻辑" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    run grep -c "阶段 0.0.5 — 全自动决策逻辑" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "SKILL.md auto-pick decision table has 9 rows" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    export SKILL_FILE
    run awk '/^## 阶段 0\.0\.5/,/^---$/' "$SKILL_FILE"
    [ "$status" -eq 0 ]
    # Count pipe-table rows in section
    count=$(echo "$output" | grep -cE "^\| .*\|")
    [ "$count" -ge 9 ]
}

@test "SKILL.md documents RDDF_REQUIRE_USER_CONFIRM env var" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    run grep -c "RDDF_REQUIRE_USER_CONFIRM" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "SKILL.md documents user-intervention triggers (低置信度场景)" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    run grep -c "用户介入门控\|用户介入的条件" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "SKILL.md case 5 section notes 全自动 (no user input)" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    run bash -c "
        awk '/## 阶段 0\\.3 — Case 5/,/^---$/' '$SKILL_FILE' | grep -c '全自动 note'
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "SKILL.md case 2/3/4 section notes 全自动 (no user input)" {
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    run bash -c "
        awk '/## 阶段 0\\.2 — Case 2\\/3\\/4/,/^---$/' '$SKILL_FILE' | grep -c '全自动 note'
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
