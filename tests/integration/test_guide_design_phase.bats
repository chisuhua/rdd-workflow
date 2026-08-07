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

@test "guide-design: Phase 1 invokes preflight before deciding (no evidence)" {
  # No arch-handoff, no ADRs, no roadmap → hard_reject_no_evidence
  run bash -c '
    source "'"$REPO_ROOT"'/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}

@test "guide-design: Phase 1 invokes preflight before deciding (evidence present, handoff missing)" {
  mkdir -p "$PROJECT_ROOT/docs/adr"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/roadmap.md"

  run bash -c '
    source "'"$REPO_ROOT"'/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "soft_prompt_reconstruct" ]
}

@test "guide-design: Phase 1 invokes preflight before deciding (handoff present)" {
  echo '{"version":1,"discovered":{"adr_dir":{"found":true,"created":false,"candidates_tried":1}}}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  run bash -c '
    source "'"$REPO_ROOT"'/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "normal" ]
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