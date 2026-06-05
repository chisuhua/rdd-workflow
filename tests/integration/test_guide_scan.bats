#!/usr/bin/env bats
#
# Wave 3 / T12: verify guide.md P1-3 and P1-4 fixes.
# See plan checkbox:
#   - [ ] 12. guide.md scan improvements (P1-3 + P1-4)
#
# P1-3: scan must check .zcf/.phase-gate-report.md existence and surface
#       detached worktrees (count via awk $3 ~ /^openspec\//, not grep path).
# P1-4: replace dangerous `grep -q "openspec/"` (matches on path string,
#       false-positive on any openspec/ folder) with strict $3 column match.

load ../test_helper

# Note: spec's original setup() cds to a temp git repo, which would break
# every "skills/..." path-relative assertion below. The T7 test_execute_wt_fix
# pattern is correct: run from spec-workflow repo root, build any temp
# repos inside the test that actually needs one. All 4 tests below are
# pure static-grep assertions on skills/guide.md, so no setup is needed.

# P1-3 ---------------------------------------------------------------------

@test "P1-3: guide.md checks .phase-gate-report.md" {
  [ -f "skills/guide.md" ]
  grep -q ".phase-gate-report.md" skills/guide.md
}

@test "P1-3: guide.md detects detached worktrees" {
  [ -f "skills/guide.md" ]
  grep -q "DETACHED" skills/guide.md
}

# P1-4 ---------------------------------------------------------------------

@test "P1-4: guide.md no longer uses 'grep -q \"openspec/\"' path-match" {
  [ -f "skills/guide.md" ]
  ! grep -qE 'grep -q "openspec/"' skills/guide.md
}

@test "P1-4: guide.md uses awk \$3 ~ /^openspec\//" {
  [ -f "skills/guide.md" ]
  grep -qE "awk.*'\\\$3 ~ /\\^openspec\\\\\\//" skills/guide.md
}
