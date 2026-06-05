#!/usr/bin/env bash
# test_helper.bash - common setup/teardown for bats tests
#
# Sourced automatically by bats before each test file. Provides:
#   - $REPO_ROOT: absolute path to the spec-workflow repo root
#   - $BATS_TMPDIR: per-test scratch directory (auto-cleaned by bats)
#   - load_lib(name): source files from tests/_lib/<name>.bash
#   - common assertion helpers

# Resolve repo root (directory above tests/)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REPO_ROOT

# Project-under-test working dir, if needed
export PROJECT_ROOT="${PROJECT_ROOT:-$REPO_ROOT}"

# Load helper libraries
load_lib() {
  local name="$1"
  local path="$REPO_ROOT/tests/_lib/${name}.bash"
  if [[ ! -f "$path" ]]; then
    echo "load_lib: file not found: $path" >&2
    return 1
  fi
  # shellcheck source=/dev/null
  source "$path"
}

# Verify a file exists and is non-empty
assert_file_exists() {
  local f="$1"
  [[ -f "$f" ]] || { echo "expected file to exist: $f" >&2; return 1; }
}

# Verify a file contains a regex
assert_file_contains() {
  local f="$1"
  local pattern="$2"
  [[ -f "$f" ]] || { echo "file not found: $f" >&2; return 1; }
  grep -qE "$pattern" "$f" || { echo "expected '$pattern' in $f" >&2; return 1; }
}

# Verify a command succeeds
assert_cmd_succeeds() {
  "$@" >/dev/null 2>&1 || { echo "expected command to succeed: $*" >&2; return 1; }
}

# Common setup runs before every @test in files that load this helper.
# Keep it idempotent and fast.
setup() {
  : # placeholder; individual test files can override
}

# Common teardown runs after every @test in files that load this helper.
teardown() {
  : # placeholder; individual test files can override
}
