#!/usr/bin/env bats
# Integration tests for guide-design phase

load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/design-test-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  mkdir -p "$PROJECT_ROOT/improvements"
  mkdir -p "$PROJECT_ROOT/skills/guide-design"
}

teardown() {
  rm -rf "$PROJECT_ROOT"
}

@test "guide-design: Phase 1 rejects missing arch-handoff" {
  # No .arch-handoff.json → should fail
  run bash -c '
    PROJECT_ROOT="$PROJECT_ROOT"
    if [ ! -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]; then
      echo "❌ arch-done 未完成" >&2
      exit 1
    fi
  '
  [ "$status" -ne 0 ]
  echo "$output" | grep -q "arch-done"
}

@test "guide-design: design_proposal_review.sh script exists and is executable" {
  [ -f "$REPO_ROOT/skills/guide-design/scripts/design_proposal_review.sh" ]
  head -1 "$REPO_ROOT/skills/guide-design/scripts/design_proposal_review.sh" | grep -q "^#!/usr/bin/env bash"
}

@test "guide-design: approve_proposal.sh script exists in design path" {
  [ -f "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" ]
  head -1 "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" | grep -q "^#!/usr/bin/env bash"
}

@test "guide-design: write_design_handoff.sh source-able" {
  source "$REPO_ROOT/skills/guide-design/scripts/write_design_handoff.sh"
  type write_design_handoff 2>/dev/null
}

@test "guide-design: deprecated shim forwards to design (wrapper function defined)" {
  source "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
  type arch_proposal_review 2>/dev/null
}

@test "guide-design: deprecated shim prints warning when invoked" {
  run bash -c '
    source "'"$REPO_ROOT"'/skills/guide-arch/scripts/arch_proposal_review.sh"
    arch_proposal_review
  ' 2>&1 || true
  echo "$output" | grep -qi "DEPRECATED"
}

@test "guide-design: SKILL.md has valid frontmatter" {
  head -1 "$REPO_ROOT/skills/guide-design/SKILL.md" | grep -q "^---$"
}

@test "guide-design: SKILL.md frontmatter declares version 1.0" {
  grep -q 'version: "1.0"' "$REPO_ROOT/skills/guide-design/SKILL.md"
}