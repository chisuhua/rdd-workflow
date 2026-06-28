#!/usr/bin/env bats
# tests/_lib/test_state.bats
#
# Smoke tests for skills/_lib/state.sh.
#
# As of general-harden-doc-consistency, state.sh is intentionally a stub
# (the safe Python JSON/YAML helpers were removed; no production callers
# remain — consumers use jq/python3 inline). These tests pin that contract:
# the file must exist, source without error, and not define any state_*
# helpers (the absence is the point — it would catch a regression that
# re-introduced a broken helper).
#
# Run: bats tests/_lib/test_state.bats

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "state.sh exists and is readable" {
  [ -f "$REPO_ROOT/skills/_lib/state.sh" ]
  [ -r "$REPO_ROOT/skills/_lib/state.sh" ]
}

@test "state.sh sources without error" {
  run bash -c "source '$REPO_ROOT/skills/_lib/state.sh' && echo 'loaded'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"loaded"* ]]
}

@test "state.sh does not define any state_* helper functions" {
  # Sourcing state.sh must not introduce state_* functions — the stub is
  # intentionally empty. A regression that re-adds a broken helper would
  # be caught here (and would force the test author to consciously update
  # the contract).
  run bash -c "source '$REPO_ROOT/skills/_lib/state.sh' && declare -F | awk '{print \$3}' | grep -E '^state_' || true"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}