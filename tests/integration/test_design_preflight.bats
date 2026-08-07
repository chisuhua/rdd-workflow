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
  [ "$(echo "$output" | jq -r '.arch_handoff_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.adr_count')" = "0" ]
  [ "$(echo "$output" | jq -r '.roadmap_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.session_history_arch_done')" = "false" ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
  [ "$(echo "$output" | jq -r '.arch_handoff_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.adr_count')" = "0" ]
  [ "$(echo "$output" | jq -r '.roadmap_exists')" = "false" ]
  [ "$(echo "$output" | jq -r '.session_history_arch_done')" = "false" ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}
