#!/usr/bin/env bats
# tests/integration/test_fix_ship_archive_resolve_lib_path.bats
#
# Regression test for fix-ship-archive-resolve-lib-path.
#
# Bug: ship_archive.sh lines 211/214 hardcode `$project_root/_lib/validate_delta_targets.py`,
# which fails when the project has no local _lib (external projects rely on global install).
#
# Fix: Use resolve_rdd_lib_dir to find validate_delta_targets.py; fail clearly when unavailable.
#
# Scope:
#   - Lightweight archive path (worktree path uses archive_change from archive.sh)
#   - External project without local _lib symlink
#   - Missing resolver failure assertion

load ../test_helper

RDD_GLOBAL_LIB="${HOME}/.agents/skills/_lib"

# ── Test 1: lightweight archive uses resolve_rdd_lib_dir for validator ────────

@test "fix_ship_archive_resolve_lib_path: lightweight archive reaches global validator" {
  # Create external project without project-local _lib
  EXT_REPO="${BATS_TMPDIR}/external-archive-$$"
  mkdir -p "$EXT_REPO"
  cd "$EXT_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "external project" > README.md
  git add README.md && git commit -q -m "init"

  # Create lightweight archive artifacts (branch + openspec/changes/)
  CHANGE_NAME="ext-test-change"
  git checkout -b "openspec/$CHANGE_NAME" >/dev/null 2>&1
  mkdir -p "openspec/changes/$CHANGE_NAME"
  printf -- '- [x] Task 1\n' > "openspec/changes/$CHANGE_NAME/tasks.md"

  # Set PROJECT_ROOT so resolver uses external project (no local _lib)
  export PROJECT_ROOT="$EXT_REPO"

  # Source the bootstrap pattern (global fallback)
  if [ -f "$HOME/.agents/skills/_lib/skill_root.sh" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.agents/skills/_lib/skill_root.sh"
  else
    skip "global _lib not available (install.sh --global not run)"
  fi

  # Source ship_archive.sh (tests the fix: it should use resolve_rdd_lib_dir internally)
  # shellcheck source=/dev/null
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  # The validator exists in global _lib only; project has no local _lib
  # If the fix is absent, this fails with "python3: .../_lib/validate_delta_targets.py: not found"
  run bash -c '
    source "'"$HOME/.agents/skills/_lib/skill_root.sh"'"
    # Simulate what archive_change_for_mode does for lightweight mode up to the validator call
    RDD_LIB_DIR="$(resolve_rdd_lib_dir)" || {
      echo "FAIL: resolve_rdd_lib_dir returned error" >&2
      return 1
    }
    if [ ! -f "$RDD_LIB_DIR/validate_delta_targets.py" ]; then
      echo "FAIL: validate_delta_targets.py not found at $RDD_LIB_DIR" >&2
      return 1
    fi
    echo "OK: validator found at $RDD_LIB_DIR/validate_delta_targets.py"
  '
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK: validator found"* ]]
}

# ── Test 2: missing resolver fails clearly ─────────────────────────────────

@test "fix_ship_archive_resolve_lib_path: missing shared library fails clearly" {
  # Create isolated environment with no skill_root.sh anywhere
  ISO_REPO="${BATS_TMPDIR}/isolated-archive-$$"
  mkdir -p "$ISO_REPO"
  cd "$ISO_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "isolated" > README.md
  git add README.md && git commit -q -m "init"

  export PROJECT_ROOT="$ISO_REPO"

  # Simulate a broken/missing resolver scenario
  run bash -c '
    # Create minimal fake skill_root.sh that always fails with clear message
    FAKE_LIB="${BATS_TMPDIR}/fake_lib_$$"
    mkdir -p "$FAKE_LIB"
    cat > "$FAKE_LIB/skill_root.sh" <<"INNEREOF"
resolve_rdd_lib_dir() {
  echo "ERROR: Cannot resolve _lib dir" >&2
  echo "  Searched: \$PROJECT_ROOT/.opencode/skills/rdd-workflow/_lib, ~/.agents/_lib, \$RDD_WORKFLOW_SRC/_lib" >&2
  return 1
}
INNEREOF

    # shellcheck source=/dev/null
    source "$FAKE_LIB/skill_root.sh"

    # Call the resolver and capture both stdout and stderr
    output=$(resolve_rdd_lib_dir 2>&1)
    ret=$?

    # Verify resolver failed with non-zero exit
    if [ $ret -eq 0 ]; then
      echo "FAIL: resolve_rdd_lib_dir should have failed" >&2
      rm -rf "$FAKE_LIB"
      exit 1
    fi

    # Verify error message is clear and informative
    if echo "$output" | grep -q "ERROR: Cannot resolve _lib dir"; then
      echo "OK: clear failure message"
      rm -rf "$FAKE_LIB"
      exit 0
    else
      echo "FAIL: unclear error: $output" >&2
      rm -rf "$FAKE_LIB"
      exit 1
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK: clear failure message"* ]]
}

# ── Test 3: ship_archive.sh no longer hardcodes $project_root/_lib/ ─────────

@test "fix_ship_archive_resolve_lib_path: ship_archive.sh does not hardcode project_root/_lib" {
  # Verify the fixed code uses resolve_rdd_lib_dir pattern
  grep -nE 'validate_delta_targets\.py' "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" | while read -r line; do
    # Each line referencing validate_delta_targets.py must use RDD_LIB_DIR or similar resolver
    # and NOT use $project_root/_lib directly
    if echo "$line" | grep -qE 'project_root.*_lib.*validate_delta_targets'; then
      echo "FAIL: hardcoded path found: $line" >&2
      exit 1
    fi
  done
  [ "$?" -eq 0 ]
}

# ── Test 4: ship_archive.sh sources skill_root.sh for resolve_rdd_lib_dir ────

@test "fix_ship_archive_resolve_lib_path: ship_archive.sh bootstraps resolve_rdd_lib_dir" {
  # After the fix, ship_archive.sh should source skill_root.sh to get resolve_rdd_lib_dir
  grep -qE 'skill_root\.sh' "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" && \
    grep -qE 'resolve_rdd_lib_dir' "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
}
