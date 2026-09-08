#!/usr/bin/env bats
# tests/integration/test_rdd_quick.bats
# Integration tests for skills/rdd-quick/ skill (per ADR-0047).
#
# Coverage groups:
#  - structural: SKILL.md frontmatter + role.boundaries + P0-P4 markers
#  - scaffold_plan: scaffold_plan.sh contract (TDD markers, ## Acceptance, prefix)
#  - append_history: append_history.py contract (validation, atomic append)
#
# Per design.md D8 zero-pollution: this file NEVER writes to openspec/changes/
# or .rddf/wt/. It also does NOT import skills.rdd-planner or skills.rdd-builder.

load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SKILL_FILE="$PROJECT_ROOT/skills/rdd-quick/SKILL.md"
    SCRIPTS_DIR="$PROJECT_ROOT/skills/rdd-quick/scripts"
    SCAFFOLD="$SCRIPTS_DIR/scaffold_plan.sh"
    APPEND="$SCRIPTS_DIR/append_history.py"
    HISTORY_FILE_DEFAULT="$PROJECT_ROOT/.rddf/state/.quick-history.jsonl"
    WORK_TMP="$(mktemp -d)"
    export RDDF_QUICK_PLAN_DIR="$WORK_TMP/plans"
    export RDDF_QUICK_HISTORY_FILE="$WORK_TMP/.quick-history.jsonl"
}

teardown() {
    rm -rf "$WORK_TMP"
}

# ---------- structural ----------

@test "rdd-quick: SKILL.md exists with required frontmatter fields" {
    [ -f "$SKILL_FILE" ]
    run head -1 "$SKILL_FILE"
    [ "$output" = "---" ]
    # Extract frontmatter (lines between first --- and second ---).
    frontmatter="$(awk 'BEGIN{c=0} /^---$/{c++; next} c==1{print} c==2{exit}' "$SKILL_FILE")"
    for field in name description license compatibility metadata role; do
        echo "$frontmatter" | grep -q "^${field}:"
    done
}

@test "rdd-quick: role.boundaries.owns contains quick-*.md and .quick-history.jsonl" {
    [ -f "$SKILL_FILE" ]
    frontmatter="$(awk 'BEGIN{c=0} /^---$/{c++; next} c==1{print} c==2{exit}' "$SKILL_FILE")"
    echo "$frontmatter" | grep -A 20 "boundaries:" | grep -qE "\.rddf/plans/quick-\*\.md"
    echo "$frontmatter" | grep -A 20 "boundaries:" | grep -q "\.rddf/state/\.quick-history\.jsonl"
}

@test "rdd-quick: role.boundaries.not_owns contains openspec/ + .rddf/wt/ + iteration.json" {
    [ -f "$SKILL_FILE" ]
    frontmatter="$(awk 'BEGIN{c=0} /^---$/{c++; next} c==1{print} c==2{exit}' "$SKILL_FILE")"
    echo "$frontmatter" | grep -A 20 "not_owns:" | grep -q "openspec/changes/<name>/"
    echo "$frontmatter" | grep -A 20 "not_owns:" | grep -q "\.rddf/wt/<name>/"
    echo "$frontmatter" | grep -A 20 "not_owns:" | grep -q "iteration\.json"
}

@test "rdd-quick: SKILL.md body documents P0 P1 P2 P3 P4 phases" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    for phase in "## P0" "## P1" "## P2" "## P3" "## P4"; do
        echo "$body" | grep -qF "$phase"
    done
}

@test "rdd-quick: SKILL.md body explicitly forbids reading proposal.md for AC" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    # Must state AC source is the plan file, NOT proposal.md
    echo "$body" | grep -qiE "(accept.*plan.*file|plan.*accept|## Acceptance.*plan)"
    # Must explicitly NOT read proposal.md for AC extraction
    echo "$body" | grep -qiE "NOT.*proposal\.md|not.*openspec/changes.*proposal"
}

@test "rdd-quick: SKILL.md env var prefix is RDDF_QUICK_" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    echo "$body" | grep -q "RDDF_QUICK_"
    # Must explicitly NOT use the reserved rdd-builder variables
    ! echo "$body" | grep -q "QUICK_FINISH_DETECTED"
    ! echo "$body" | grep -q "SKIP_PROMETHEUS_PLANNING"
}

# ---------- scaffold_plan ----------

@test "rdd-quick: scaffold_plan.sh --name foo writes quick-foo.md (not foo.md)" {
    [ -x "$SCAFFOLD" ]
    run "$SCAFFOLD" --name "test-prefix-isolation" --proposal "fix something small"
    [ "$status" -eq 0 ]
    [ -f "$RDDF_QUICK_PLAN_DIR/quick-test-prefix-isolation.md" ]
    [ ! -f "$RDDF_QUICK_PLAN_DIR/test-prefix-isolation.md" ]
}

@test "rdd-quick: scaffold_plan.sh output contains all 5 TDD markers" {
    [ -x "$SCAFFOLD" ]
    run "$SCAFFOLD" --name "test-tdd-markers" --proposal "add a helper"
    [ "$status" -eq 0 ]
    out="$RDDF_QUICK_PLAN_DIR/quick-test-tdd-markers.md"
    [ -f "$out" ]
    for marker in "Write the failing test" "Run test to verify it fails" "Write minimal implementation" "Run test to verify it passes" "Defer commit"; do
        grep -qF "$marker" "$out"
    done
}

@test "rdd-quick: scaffold_plan.sh output contains ## Acceptance with at least 1 checkbox" {
    [ -x "$SCAFFOLD" ]
    run "$SCAFFOLD" --name "test-acceptance" --proposal "add a small helper"
    [ "$status" -eq 0 ]
    out="$RDDF_QUICK_PLAN_DIR/quick-test-acceptance.md"
    [ -f "$out" ]
    grep -qF "## Acceptance" "$out"
    grep -qE "^- \[ \]" "$out"
}

@test "rdd-quick: scaffold_plan.sh rejects kebab-invalid names" {
    [ -x "$SCAFFOLD" ]
    run "$SCAFFOLD" --name "Bad_Name!" --proposal "x"
    [ "$status" -ne 0 ]
}

@test "rdd-quick: scaffold_plan.sh refuses to overwrite existing file" {
    [ -x "$SCAFFOLD" ]
    "$SCAFFOLD" --name "test-no-overwrite" --proposal "first"
    run "$SCAFFOLD" --name "test-no-overwrite" --proposal "second"
    [ "$status" -ne 0 ]
}

# ---------- append_history ----------

@test "rdd-quick: append_history.py validates entry against schema (good)" {
    [ -x "$APPEND" ]
    entry='{"name":"quick-test-validate","started_at":"2026-09-07T10:00:00Z","ended_at":"2026-09-07T10:05:00Z","plan_file":".rddf/plans/quick-test-validate.md","complexity":"simple","reviewed_by":[],"verdict_summary":{"total":1,"pass":1,"fail":0},"retry_count":0,"outcome":"completed","commit_sha":"abc1234","upgraded_to_change":null}'
    run "$APPEND" <<< "$entry"
    [ "$status" -eq 0 ]
    [ -f "$RDDF_QUICK_HISTORY_FILE" ]
    lines=$(wc -l < "$RDDF_QUICK_HISTORY_FILE")
    [ "$lines" -eq 1 ]
}

@test "rdd-quick: append_history.py rejects malformed entry (missing fields)" {
    [ -x "$APPEND" ]
    bad='{"name":"quick-bad"}'
    run "$APPEND" <<< "$bad"
    [ "$status" -ne 0 ]
    [ ! -f "$RDDF_QUICK_HISTORY_FILE" ]
}

@test "rdd-quick: append_history.py atomic append preserves prior lines" {
    [ -x "$APPEND" ]
    # Pre-write 2 lines manually.
    mkdir -p "$(dirname "$RDDF_QUICK_HISTORY_FILE")"
    prior_a='{"name":"quick-prior-a","started_at":"2026-09-07T09:00:00Z","ended_at":"2026-09-07T09:01:00Z","plan_file":".rddf/plans/quick-prior-a.md","complexity":"simple","reviewed_by":[],"verdict_summary":{"total":0,"pass":0,"fail":0},"retry_count":0,"outcome":"completed","commit_sha":"deadbe0","upgraded_to_change":null}'
    prior_b='{"name":"quick-prior-b","started_at":"2026-09-07T09:02:00Z","ended_at":"2026-09-07T09:03:00Z","plan_file":".rddf/plans/quick-prior-b.md","complexity":"simple","reviewed_by":[],"verdict_summary":{"total":0,"pass":0,"fail":0},"retry_count":0,"outcome":"completed","commit_sha":"deadbe1","upgraded_to_change":null}'
    printf '%s\n%s\n' "$prior_a" "$prior_b" > "$RDDF_QUICK_HISTORY_FILE"

    # Now append a third.
    new='{"name":"quick-new-c","started_at":"2026-09-07T10:00:00Z","ended_at":"2026-09-07T10:05:00Z","plan_file":".rddf/plans/quick-new-c.md","complexity":"simple","reviewed_by":[],"verdict_summary":{"total":1,"pass":1,"fail":0},"retry_count":0,"outcome":"completed","commit_sha":"abc1234","upgraded_to_change":null}'
    run "$APPEND" <<< "$new"
    [ "$status" -eq 0 ]

    # 3 lines total.
    lines=$(wc -l < "$RDDF_QUICK_HISTORY_FILE")
    [ "$lines" -eq 3 ]

    # First two byte-identical (verify by sha256sum).
    echo "$prior_a" | sha256sum > /tmp/expected_a
    echo "$prior_b" | sha256sum > /tmp/expected_b
    sed -n '1p' "$RDDF_QUICK_HISTORY_FILE" | sha256sum > /tmp/actual_a
    sed -n '2p' "$RDDF_QUICK_HISTORY_FILE" | sha256sum > /tmp/actual_b
    diff /tmp/expected_a /tmp/actual_a
    diff /tmp/expected_b /tmp/actual_b
}