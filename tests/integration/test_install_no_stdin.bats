#!/usr/bin/env bats
#
# Wave 1 / T4: verify INSTALL.md and install.sh are non-interactive (no stdin
# blocking reads) and that dependency checks / path inference are consistent
# between the two files. See plan checkbox:
#   - [ ] 4. INSTALL.md + install.sh environment + path fixes (P0-1, P1-1, P1-2)
#
# P0-1: read -r / read -p must NOT appear in either script
# P1-1: install.sh must use the realpath-based PACKAGE_DIR fallback chain that
#       skills/INSTALL.md already uses (lines 83-84)
# P1-2: skills/INSTALL.md must check all 5 commands:
#       openspec / python3 / jq / git / cmake

load ../test_helper

# P0-1 ---------------------------------------------------------------------

@test "P0-1: INSTALL.md has no stdin-blocking reads (read -p / read -r)" {
  [ -f "skills/INSTALL.md" ]
  # Negative check: any `read -<flag>` (the most common blocking forms)
  ! grep -qE 'read -[pr]' "skills/INSTALL.md"
  # Also block bare `read VAR` (the original bug — line 39 had `read -r confirm`)
  ! grep -qE '^\s*read [a-zA-Z_-]+' "skills/INSTALL.md"
}

@test "P0-1: install.sh has no stdin-blocking reads" {
  [ -f "install.sh" ]
  ! grep -qE 'read -[pr]' "install.sh"
  ! grep -qE '^\s*read [a-zA-Z_-]+' "install.sh"
}

# P1-2 ---------------------------------------------------------------------

@test "P1-2: INSTALL.md checks all 5 commands (openspec/python3/jq/git/cmake)" {
  [ -f "skills/INSTALL.md" ]
  # openspec is checked directly via `command -v openspec`
  grep -qE 'command -v +openspec' "skills/INSTALL.md" || {
    echo "Missing direct env check for: openspec"
    return 1
  }
  # The other 4 are checked via a `for cmd in ...` loop using `command -v "$cmd"`.
  # Verify both that `command -v` is used AND that each cmd is in the loop list.
  grep -qE 'command -v +"\$cmd"' "skills/INSTALL.md" || {
    echo "Missing `command -v \"\$cmd\"` loop"
    return 1
  }
  for cmd in python3 jq git cmake; do
    if ! grep -qE "for cmd in .*\\b${cmd}\\b" "skills/INSTALL.md"; then
      echo "Missing env check for: $cmd (not in for loop)"
      return 1
    fi
  done
}

# Non-interactive escape hatch --------------------------------------------

@test "INSTALL.md / install.sh both honor SKIP_OPENSPEC_PROMPT" {
  # INSTALL.md: must offer the env-var escape for AI environments
  grep -q "SKIP_OPENSPEC_PROMPT" "skills/INSTALL.md"
}

# P1-1 ---------------------------------------------------------------------

@test "P1-1: install.sh and INSTALL.md use consistent path inference" {
  # Both must use the realpath fallback chain for PACKAGE_DIR
  grep -q "realpath" "install.sh"
  grep -q "realpath" "skills/INSTALL.md"
  # And both must assign to PACKAGE_DIR with the same variable name
  grep -qE '^PACKAGE_DIR=' "install.sh"
  grep -qE '^PACKAGE_DIR=' "skills/INSTALL.md"
}
