#!/usr/bin/env bash
# tests/_lib/reflect_hooks_helper.bash
# Helper for reflect hook integration tests.
#
# Provides assertions for verifying that the SKIP_WORKFLOW_REFLECTION
# env var guard and the python3 reflect_engine hook invocations
# exist in the 3 gate scripts.

# Assert that a given gate script file contains the reflect_engine hook.
# Usage: assert_reflect_hook_present <script_path>
assert_reflect_hook_present() {
  local script="$1"
  [[ -f "$script" ]] || { echo "expected file: $script" >&2; return 1; }
  grep -q "reflect_engine" "$script" || {
    echo "expected reflect_engine reference in $script" >&2
    return 1
  }
}

# Assert that a given gate script has the SKIP_WORKFLOW_REFLECTION guard.
# Usage: assert_skip_guard_present <script_path>
assert_skip_guard_present() {
  local script="$1"
  [[ -f "$script" ]] || { echo "expected file: $script" >&2; return 1; }
  grep -q 'SKIP_WORKFLOW_REFLECTION' "$script" || {
    echo "expected SKIP_WORKFLOW_REFLECTION guard in $script" >&2
    return 1
  }
}

# Assert that a given gate script has the non-blocking 2>/dev/null || true suffix.
# Usage: assert_non_blocking <script_path>
assert_non_blocking() {
  local script="$1"
  [[ -f "$script" ]] || { echo "expected file: $script" >&2; return 1; }
  grep -q '2>/dev/null || true' "$script" || {
    echo "expected '2>/dev/null || true' non-blocking suffix in $script" >&2
    return 1
  }
}
