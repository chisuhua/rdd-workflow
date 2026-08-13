#!/usr/bin/env bats
# tests/integration/test_plan_intake_extraction.bats
# Round A extraction: guide-plan.md Phase 0 intake (L95-L175, ~79 lines)
# was a single inline bash code block. Extracted to
# _lib/plan_intake.sh::run_plan_intake().
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

# plan_intake.sh's bootstrap uses ${RDDF_PROJECT_ROOT:-...} to find
# orchestrator_entry.sh. When cwd is a non-git tmpdir, without this
# export the bootstrap silently fails and orchestrator_run is undefined.
# Centralized here so all tests in this file inherit the fix.
setup() {
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
}

@test "plan_intake_helper_exists" {
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh" ]
  grep -q 'run_plan_intake()' "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh"
  # Verify the function is sourceable
  bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_intake.sh && declare -f run_plan_intake" | grep -q 'run_plan_intake'
}

@test "guide_plan_inline_block_removed" {
  [ -f "$REPO_ROOT/skills/guide-plan/SKILL.md" ]
  # After extraction, L95-L175 should no longer contain inline openspec-detection bash
  local count
  count=$(sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-plan/SKILL.md" | grep -c 'command -v openspec' || true)
  [ "$count" -eq 0 ]
}

@test "guide_plan_invokes_helper" {
  [ -f "$REPO_ROOT/skills/guide-plan/SKILL.md" ]
  grep -q 'source.*scripts/plan_intake.sh' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'run_plan_intake' "$REPO_ROOT/skills/guide-plan/SKILL.md"
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
  # SKIP_DESIGN_HANDOFF=yes: this test focuses on arch-handoff behavior,
  # not design-handoff (added in v2.1). run_plan_intake requires design-done
  # post-v2.1 unless explicitly skipped.
  SKIP_DESIGN_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" >/dev/null 2>&1
  rm -rf "$tmpdir"
}

@test "run_plan_intake_blocks_without_handoff" {
  # No handoff → should print error about arch-done handoff
  local tmpdir output
  tmpdir=$(mktemp -d)
  output=$(SKIP_DESIGN_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
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
  output=$(SKIP_DESIGN_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'docs/custom'
}

@test "run_plan_intake_respects_skip_arch_handoff_env" {
  # No handoff file — should still succeed with SKIP_ARCH_HANDOFF=yes
  local tmpdir output
  tmpdir=$(mktemp -d)
  output=$(SKIP_ARCH_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'SKIP_ARCH_HANDOFF=yes'
}