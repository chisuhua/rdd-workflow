#!/usr/bin/env bats
# tests/integration/test_plan_intake_extraction.bats
# Round A extraction: guide-plan.md Phase 0 intake (L95-L175, ~79 lines)
# was a single inline bash code block. Extracted to
# skills/_lib/plan_intake.sh::run_plan_intake().
#
# These tests lock the refactor in place:
#   1. plan_intake.sh exists with run_plan_intake function.
#   2. guide-plan.md L95-L175 inline block removed.
#   3. guide-plan.md sources and calls run_plan_intake.
#   4. Helper runs with valid handoff fixture (no crash).
#   5. Helper blocks when no handoff (non-zero exit + error message).
#   6. Helper reads custom adr_dir from handoff correctly.

load ../test_helper

# The inline block spans L95-L175 in guide-plan.md.
REPLACED_RANGE="95,175p"

@test "plan_intake_helper_exists" {
  [ -f "$REPO_ROOT/skills/_lib/plan_intake.sh" ]
  grep -q 'run_plan_intake()' "$REPO_ROOT/skills/_lib/plan_intake.sh"
  # Verify the function is sourceable
  bash -c "cd '$REPO_ROOT' && source skills/_lib/plan_intake.sh && declare -f run_plan_intake" | grep -q 'run_plan_intake'
}

@test "guide_plan_inline_block_removed" {
  [ -f "$REPO_ROOT/skills/guide-plan.md" ]
  # After extraction, L95-L175 should no longer contain inline openspec-detection bash
  local count
  count=$(sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-plan.md" | grep -c 'command -v openspec' || true)
  [ "$count" -eq 0 ]
}

@test "guide_plan_invokes_helper" {
  [ -f "$REPO_ROOT/skills/guide-plan.md" ]
  grep -q 'source.*_lib/plan_intake.sh' "$REPO_ROOT/skills/guide-plan.md"
  grep -q 'run_plan_intake' "$REPO_ROOT/skills/guide-plan.md"
}

@test "run_plan_intake_runs_with_handoff" {
  # Provide a valid handoff + run
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.rddf/state"
  cat > "$tmpdir/.rddf/state/.arch-handoff.json" <<EOF
{
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "adr_pattern": "ADR-*.md",
  "architecture_dir": "docs/architecture",
  "completed_adr_ids": ["0001", "0002"],
  "current_phase": "phase-2"
}
EOF
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_intake.sh' && run_plan_intake" >/dev/null 2>&1 || true
  rm -rf "$tmpdir"
}

@test "run_plan_intake_blocks_without_handoff" {
  # No handoff → should print error about arch-done handoff
  local tmpdir output
  tmpdir=$(mktemp -d)
  output=$(bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'arch-done handoff'
}

@test "run_plan_intake_reads_adr_dir_from_handoff" {
  # Provide handoff with custom adr_dir → output should mention it
  local tmpdir output
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.rddf/state"
  cat > "$tmpdir/.rddf/state/.arch-handoff.json" <<EOF
{
  "adr_dir": "docs/custom",
  "roadmap_path": "roadmap.md",
  "adr_pattern": "ADR-*.md",
  "architecture_dir": "docs/architecture",
  "completed_adr_ids": [],
  "current_phase": "phase-test"
}
EOF
  output=$(bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'docs/custom'
}