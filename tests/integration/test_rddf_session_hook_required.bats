#!/usr/bin/env bats
load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/rddf-hook-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

@test "rddf_session_hook_entry: fails loud when python3 unavailable" {
  mkdir -p /tmp/rddf-no-python/bin
  for tool in bash cat grep awk tr head wc hostname date stat sed mkdir chmod printf echo ln; do
    ln -sf "$(which "$tool")" "/tmp/rddf-no-python/bin/$tool" 2>/dev/null || true
  done
  run env -i HOME="$HOME" PATH=/tmp/rddf-no-python/bin bash -c "
    source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
    rddf_session_hook_entry stage_design guide-design design-phase design-done /tmp/foo 2>&1 || echo \"exit_code=\$?\"
  "
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE "exit_code=[1-9]|fail"
}

@test "rddf_session_hook_close: fails loud when python3 unavailable" {
  mkdir -p /tmp/rddf-no-python/bin
  for tool in bash cat grep awk tr head wc hostname date stat sed mkdir chmod printf echo ln; do
    ln -sf "$(which "$tool")" "/tmp/rddf-no-python/bin/$tool" 2>/dev/null || true
  done
  run env -i HOME="$HOME" PATH=/tmp/rddf-no-python/bin bash -c "
    source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
    rddf_session_hook_close stage_design design-done guide-design 2>&1 || echo \"exit_code=\$?\"
  "
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE "exit_code=[1-9]|fail"
}

@test "rddf_session_hook_heartbeat: fails loud when python3 unavailable" {
  mkdir -p /tmp/rddf-no-python/bin
  for tool in bash cat grep awk tr head wc hostname date stat sed mkdir chmod printf echo ln; do
    ln -sf "$(which "$tool")" "/tmp/rddf-no-python/bin/$tool" 2>/dev/null || true
  done
  run env -i HOME="$HOME" PATH=/tmp/rddf-no-python/bin bash -c "
    source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
    rddf_session_hook_heartbeat stage_design 2>&1 || echo \"exit_code=\$?\"
  "
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE "exit_code=[1-9]|fail"
}

@test "rddf_session_hook_attach: fails loud when python3 unavailable" {
  mkdir -p /tmp/rddf-no-python/bin
  for tool in bash cat grep awk tr head wc hostname date stat sed mkdir chmod printf echo ln; do
    ln -sf "$(which "$tool")" "/tmp/rddf-no-python/bin/$tool" 2>/dev/null || true
  done
  run env -i HOME="$HOME" PATH=/tmp/rddf-no-python/bin bash -c "
    source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
    rddf_session_hook_attach stage_design some-change 2>&1 || echo \"exit_code=\$?\"
  "
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE "exit_code=[1-9]|fail"
}
