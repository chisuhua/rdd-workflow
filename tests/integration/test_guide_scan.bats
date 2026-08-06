#!/usr/bin/env bats
#
# Wave 3 / T12: verify scan-state.sh carries the P1-3 and P1-4 fixes.
# Original audit was on skills/guide/SKILL.md; extraction moved the code to
# _lib/scan-state.sh, so this file's assertions follow the code.

load ../test_helper

# P1-3 ---------------------------------------------------------------------

@test "P1-3: phase-gate-report removed from scan-state.sh (v2.0.3)" {
  [ -f "$REPO_ROOT/skills/guide/scripts/scan-state.sh" ]
  ! grep -q "phase-gate-report" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "P1-3: scan-state.sh detects detached worktrees" {
  [ -f "$REPO_ROOT/skills/guide/scripts/scan-state.sh" ]
  grep -q "DETACHED" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

# P1-4 ---------------------------------------------------------------------

@test "P1-4: scan-state.sh no longer uses 'grep -q \"openspec/\"' path-match" {
  [ -f "$REPO_ROOT/skills/guide/scripts/scan-state.sh" ]
  ! grep -qE 'grep -q "openspec/"' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "P1-4: scan-state.sh uses bracket [openspec/ prefix (regression guard)" {
  [ -f "$REPO_ROOT/skills/guide/scripts/scan-state.sh" ]
  # Regression guard: any reference to the bracket form is enough.
  # Originally guide.md used \$3 ~ /^openspec\// (no brackets). The extraction
  # fixed this to anything matching the literal "[openspec/" pattern.
  grep -qE '\[openspec/' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  # And must NOT still have the buggy unbracketed form
  ! grep -qE "awk.*'\\\$3 ~ /\\^openspec\\\\\\//" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}