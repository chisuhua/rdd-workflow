#!/usr/bin/env bash
# tests/_lib/deps-subagent.bash
#
# Test fixture for skills/deps.md Step 3 subagent semantic analysis
# (P2-4 follow-up: replace the 3 TODO/placeholder sites at L345/L499/L566
# with a real subagent call + graceful fallback).
#
# Public API:
#   deps_subagent_call_marker <file>
#       Return 0 if <file> contains `subagent_type=` or `task(` —
#       the two valid call sites for invoking a subagent.
#
#   deps_subagent_fallback_marker <file>
#       Return 0 if <file> contains the string `降级` or `fallback` —
#       the two valid names for the graceful-degradation path.
#
#   deps_md_extract_step3 <file>
#       Print the body of `### Step 3` section (from header to next
#       `### Step 4` or `---`, whichever comes first; excludes both
#       boundary lines).
#
#   deps_md_extract_step5 <file>
#       Print the body of `### Step 5` section (from header to next
#       `---` or end-of-file; excludes both boundary lines).
#
#   deps_subagent_mock_result
#       Print a canned JSON shape that a successful subagent call would
#       produce. Used by tests that exercise the success path.
#
#   deps_subagent_simulate_failure [path]
#       Touch a sentinel file (default `.rddf/state/.deps-subagent-fail-test`)
#       that the runtime fallback test reads to trigger degradation.
#       Returns 0 always (idempotent).
#
# All functions tolerate missing files: print to stderr, return non-zero,
# do not crash the calling test process.
#
# Load via `load_lib deps-subagent` from `tests/test_helper.bash:22-37`.

# deps_subagent_call_marker <file>
#   Returns 0 if <file> contains `subagent_type=` or `task(`.
deps_subagent_call_marker() {
  local f="${1:-}"
  if [[ ! -f "$f" ]]; then
    echo "deps_subagent_call_marker: file not found: $f" >&2
    return 1
  fi
  if grep -qE 'subagent_type=|task\(' "$f"; then
    return 0
  fi
  return 1
}

# deps_subagent_fallback_marker <file>
#   Returns 0 if <file> contains `降级` or `fallback`.
deps_subagent_fallback_marker() {
  local f="${1:-}"
  if [[ ! -f "$f" ]]; then
    echo "deps_subagent_fallback_marker: file not found: $f" >&2
    return 1
  fi
  if grep -qE '降级|fallback' "$f"; then
    return 0
  fi
  return 1
}

# deps_md_extract_step3 <file>
#   Print the body of `### Step 3` up to the next `### Step 4`.
#   Internal `---` separators are NOT treated as section ends (deps.md
#   uses `---` between sub-sections of Step 3, e.g. between 3d and 3e).
deps_md_extract_step3() {
  local f="${1:-}"
  if [[ ! -f "$f" ]]; then
    echo "deps_md_extract_step3: file not found: $f" >&2
    return 1
  fi
  awk '
    /^### Step 3/ { in_step=1; next }
    in_step && /^### Step 4/ { exit }
    in_step { print }
  ' "$f"
}

# deps_md_extract_step5 <file>
#   Print the body of `### Step 5` up to the next `###` (any level)
#   or end-of-file. Stops at any `###` or `##` (next major section).
deps_md_extract_step5() {
  local f="${1:-}"
  if [[ ! -f "$f" ]]; then
    echo "deps_md_extract_step5: file not found: $f" >&2
    return 1
  fi
  awk '
    /^### Step 5/ { in_step=1; next }
    in_step && /^##[[:space:]]/ { exit }
    in_step { print }
  ' "$f"
}

# deps_subagent_mock_result
#   Print a canned JSON shape for the AI subagent success path.
deps_subagent_mock_result() {
  cat <<'JSON'
{
  "ai_deps": [
    {"from": "init-adr-directory", "to": "add-skill-bats-tests", "kind": "soft", "reason": "ADR scaffolding before test refactor"}
  ],
  "suggestions": [
    {"change": "implement-deps-subagent-analysis", "action": "split", "reason": "touches skills/ + tests/ — consider splitting for cleaner review"}
  ],
  "fallback": false
}
JSON
}

# deps_subagent_simulate_failure [path]
#   Touch a sentinel file. Idempotent.
deps_subagent_simulate_failure() {
  local p="${1:-.rddf/state/.deps-subagent-fail-test}"
  mkdir -p "$(dirname "$p")" 2>/dev/null || true
  : > "$p"
  return 0
}
