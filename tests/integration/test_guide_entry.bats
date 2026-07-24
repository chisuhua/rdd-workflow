#!/usr/bin/env bats
#
# tests/integration/test_guide_entry.bats — verifies the v2.1 extraction
# of guide.md's inline bash block into skills/guide/scripts/guide_entry.sh.
#
# Bug class being locked:
#   1. SKILL.md no longer embeds the 64-line bash block (which contained
#      `BASH_SOURCE[0]` that breaks in `bash -c` context).
#   2. SKILL.md no longer has the bare-`then` syntax error.
#   3. guide_entry.sh provides 4-tier path resolution fallback so AI can
#      invoke it via `bash -c` reliably.

load ../test_helper

ENTRY="$REPO_ROOT/skills/guide/scripts/guide_entry.sh"
SKILL_MD="$REPO_ROOT/skills/guide/SKILL.md"

# ===========================================================================
# File presence + structural invariants
# ===========================================================================

@test "guide_entry.sh: file exists and is non-empty" {
  [ -f "$ENTRY" ]
  [ -s "$ENTRY" ]
}

@test "guide_entry.sh: declares guide_entry() function" {
  grep -qE '^guide_entry\(\)' "$ENTRY"
}

@test "guide_entry.sh: exports RECOMMEND/REASON/CONFIDENCE env vars" {
  grep -q 'export RECOMMEND REASON CONFIDENCE' "$ENTRY"
}

@test "guide_entry.sh: has 4-tier _resolve_skill_dir fallback" {
  grep -q '_resolve_skill_dir' "$ENTRY"
  # Tier 1: SKILL_DIR env var
  grep -q 'SKILL_DIR:-' "$ENTRY"
  # Tier 4: walk-up from cwd
  grep -q 'skills/guide/scripts/scan-state.sh' "$ENTRY"
}

@test "guide_entry.sh: handles --json / --no-binding / --help modes" {
  grep -q '\-\-json' "$ENTRY"
  grep -q '\-\-no-binding' "$ENTRY"
  grep -q '\-\-help' "$ENTRY"
}

@test "SKILL.md: frontmatter version bumped to 2.1" {
  grep -qE 'version: "2\.1"' "$SKILL_MD"
}

@test "SKILL.md: frontmatter evolved-from mentions v2.1 extraction" {
  grep -q 'v2.1 extracted entry script' "$SKILL_MD"
}

# ===========================================================================
# Regression guard: the bugs that motivated the extraction
# ===========================================================================

@test "SKILL.md: no BASH_SOURCE[\$0] source path (v2.1 extraction)" {
  ! grep -qE 'BASH_SOURCE\[0\]' "$SKILL_MD"
}

@test "SKILL.md: no inline `source \"\$(dirname ... )/scripts/scan-state.sh\"` block" {
  ! grep -qE 'source "\$\(dirname.*scan-state.sh\)"' "$SKILL_MD"
}

@test "SKILL.md: no inline workflow_synthesizer import" {
  ! grep -qE 'from skills\._lib\.workflow_synthesizer import synthesize' "$SKILL_MD"
}

@test "SKILL.md: no bare `then` after newline (markdown rendering bug)" {
  # The original bug was: line ended with `&& [ -n "$RECO_JSON" ]` and next
  # line started with `  then` (no `if`). Verify the bare pattern is gone.
  ! grep -qE 'RECO_JSON.*&&.*\[ -n' "$SKILL_MD"
}

@test "SKILL.md: line count dropped from 340 baseline (v2.1 reduction)" {
  local lines
  lines=$(wc -l < "$SKILL_MD")
  [ "$lines" -lt 320 ]
}

# ===========================================================================
# Functional tests — 4 invocation modes
# ===========================================================================

@test "guide_entry --help: prints usage to stdout, exits 0" {
  run bash -c "source '$ENTRY' && guide_entry --help"
  [ "$status" -eq 0 ]
  [[ "$output" == *"guide_entry"* ]]
  [[ "$output" == *"--json"* ]]
  [[ "$output" == *"--no-binding"* ]]
}

@test "guide_entry (no args): prints human-readable overview (binding skipped via env)" {
  # redirect stderr to /dev/null because scan_session_binding triggers a
  # pre-existing Python relative-import traceback (out of scope for this PR).
  run bash -c "source '$ENTRY' && guide_entry --no-binding" 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"Workflow Entry"* ]]
  [[ "$output" == *"roadmap.md"* ]]
}

@test "guide_entry --json: appends BEGIN/END JSON block" {
  run bash -c "source '$ENTRY' && guide_entry --json" 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"---BEGIN_RECO_JSON---"* ]]
  [[ "$output" == *"---END_RECO_JSON---"* ]]
  # JSON contains suggested_action field
  [[ "$output" == *"\"suggested_action\""* ]]
}

@test "guide_entry: exports RECOMMEND/REASON/CONFIDENCE env vars" {
  run bash -c "
    source '$ENTRY' && guide_entry --no-binding >/dev/null 2>&1
    echo \"RECOMMEND=\$RECOMMEND\"
    echo \"CONFIDENCE=\$CONFIDENCE\"
  " 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"RECOMMEND=guide-"* ]]
  [[ "$output" == *"CONFIDENCE="* ]]
}

# ===========================================================================
# Critical regression — the bug that triggered this PR
# ===========================================================================

@test "guide_entry: works under bash -c (BASH_SOURCE[0] is empty)" {
  # This is the original failure mode. In `bash -c`, BASH_SOURCE[0] is empty
  # and $0 is "bash", so the old SKILL.md code's
  # `source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/..."` resolved
  # to /usr/bin/scripts/scan-state.sh (does not exist) and failed.
  #
  # The new guide_entry.sh resolves path via SKILL_DIR env var (Tier 1).
  run bash -c "
    SKILL_DIR='$REPO_ROOT/skills/guide' \
      source '$ENTRY' && guide_entry --no-binding
  " 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"Workflow Entry"* ]]
}

@test "guide_entry: Tier 4 walk-up fallback finds SKILL_DIR without env var" {
  # From a subdirectory, _resolve_skill_dir's Tier 4 should walk up to find
  # skills/guide/scripts/scan-state.sh. We cd into tests/_lib/ which is
  # 2 levels deep from repo root.
  run bash -c "
    cd '$REPO_ROOT/tests/_lib'
    source '$ENTRY' && guide_entry --no-binding
  " 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"Workflow Entry"* ]]
}

@test "guide_entry: SKILL_DIR env var overrides Tier 4 walk-up (positive test)" {
  # Explicit SKILL_DIR should be used even if cwd doesn't contain it
  run bash -c "
    SKILL_DIR='$REPO_ROOT/skills/guide' \
      source '$ENTRY' && guide_entry --no-binding
  " 2>/dev/null
  [ "$status" -eq 0 ]
  [[ "$output" == *"Workflow Entry"* ]]
}