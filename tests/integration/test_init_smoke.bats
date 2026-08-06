#!/usr/bin/env bats
# tests/integration/test_init_smoke.bats
#
# Smoke regression for `rddf init` after flattening `_lib/` to top-level `_lib/`.
# Covers: target layout, file presence, and post-install Python importability.

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  BASE_TARGET="/tmp/rddf-init-smoke-$$"
  export RDDF_PROJECT_ROOT="$REPO_ROOT"
}

teardown() {
  rm -rf "${BASE_TARGET}"* 2>/dev/null || true
}

@test "init: creates 4 expected files in target .opencode/skills/rdd-workflow/" {
  TEST_TARGET="${BASE_TARGET}-1"
  run --separate-stderr bash "$REPO_ROOT/skills/cli/rddf.sh" init "$TEST_TARGET"
  [ "$status" -eq 0 ] || { echo "stdout: $output"; echo "stderr: $stderr"; false; }
  [ -d "$TEST_TARGET/.opencode/skills/rdd-workflow/skills" ]
  [ -d "$TEST_TARGET/.opencode/skills/rdd-workflow/_lib" ]
  [ -f "$TEST_TARGET/.opencode/skills/rdd-workflow/package.json" ]
  [ -f "$TEST_TARGET/.opencode/skills/rdd-workflow/rddf.sh" ]
}

@test "init: target can import _lib.cli.init_cmd" {
  TEST_TARGET="${BASE_TARGET}-2"
  bash "$REPO_ROOT/skills/cli/rddf.sh" init "$TEST_TARGET"
  run python3 -c "import sys; sys.path.insert(0, '$TEST_TARGET/.opencode/skills/rdd-workflow'); from _lib.cli import init_cmd; print('OK')"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}
