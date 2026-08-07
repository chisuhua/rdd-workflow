#!/usr/bin/env bats
load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/preflight-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  mkdir -p "$PROJECT_ROOT/docs/adr"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

@test "design_preflight: emits valid JSON with required keys" {
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  echo "$output" | jq -e 'has("arch_handoff_exists")' >/dev/null
  echo "$output" | jq -e 'has("adr_count")' >/dev/null
  echo "$output" | jq -e 'has("roadmap_exists")' >/dev/null
  echo "$output" | jq -e 'has("session_history_arch_done")' >/dev/null
  echo "$output" | jq -e 'has("recommendation")' >/dev/null
  [ "$(echo "$output" | jq -r '.arch_handoff_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.adr_count')" = "0" ]
  [ "$(echo "$output" | jq -r '.roadmap_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.session_history_arch_done')" = "false" ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}

@test "design_preflight: adr_count=0 when adr_dir missing" {
  rm -rf "$PROJECT_ROOT/docs/adr"  # exercise the truly-missing path
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 0 ]
}

@test "design_preflight: adr_count excludes ADR templates" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0000-template.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0002-test.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 2 ]
}

@test "design_preflight: adr_count handles ADR-XXXX prefix correctly" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0022-real.md"
  touch "$PROJECT_ROOT/docs/adr/not-an-adr.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 1 ]
}

@test "design_preflight: recommendation=normal when arch_handoff exists" {
  echo '{"version":1,"discovered":true}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "normal" ]
}

@test "design_preflight: recommendation=soft_prompt_reconstruct when ADRs+roadmap exist but no handoff" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  touch "$PROJECT_ROOT/roadmap.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "soft_prompt_reconstruct" ]
}

@test "design_preflight: recommendation=hard_reject_no_evidence when no evidence at all" {
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}

@test "design_preflight: recommendation=hard_reject_no_evidence when only ADRs (no roadmap)" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}
