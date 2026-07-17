#!/usr/bin/env bats
#
# Wave 8 / fix-debt-audit-2026-07-14 / Wave 2.2: phase-gate-report removal verification.
# v2.0.3 removed the .phase-gate-report.md mechanism entirely (was dead code
# with dot/no-dot filename mismatch — writer wrote `phase-gate-report.md`,
# reader scanned for `.phase-gate-report.md`).
# This file is now: assert absence locks in the removal so it cannot regress.

load ../test_helper

# Removal verification -------------------------------------------------

@test "v2.0.3: phase-gate-report removed from guide.md" {
  [ -f "skills/guide/SKILL.md" ]
  ! grep -q "phase-gate-report" skills/guide/SKILL.md
}

@test "v2.0.3: phase-gate-report removed from scan-state.sh" {
  [ -f "skills/_lib/scan-state.sh" ]
  ! grep -q "phase-gate-report" skills/_lib/scan-state.sh
}

@test "v2.0.3: phase-gate-report removed from roadmap.md" {
  [ -f "skills/roadmap/SKILL.md" ]
  ! grep -q "phase-gate-report" skills/roadmap/SKILL.md
}

@test "v2.0.3: phase-gate-report removed from index.md (or marked historical)" {
  [ -f ".rddf/state/index.md" ]
  # Either removed entirely, or only present in a clearly-marked historical note.
  if grep -q "phase-gate-report" .rddf/state/index.md; then
    # If present, must be in a "removed" or "historical" context
    grep -qiE "removed|historical|已移除|废弃|v2\.0\.3" .rddf/state/index.md
  fi
}
