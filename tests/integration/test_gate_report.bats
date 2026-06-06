#!/usr/bin/env bats
#
# Wave 7 / T33: verify .phase-gate-report.md dead-code cleanup (P3-5).
# See plan checkbox:
#   - [ ] 33. .phase-gate-report.md dead code cleanup (P3-5)
#
# P3-5: gate report was written by roadmap.md (gate-report command) but had
#       no documented reader. T12 (P1-3) wired it into guide.md's scan
#       loop so that presence of the file triggers a `status --roadmap`
#       recommendation. T33 documents the writer/reader relationship in
#       .zcf/index.md and locks it in with these tests.
#
# All tests are static-grep assertions on skills/guide.md and
# .zcf/index.md; no temp git repo is needed (matches the convention
# established by test_guide_scan.bats in Wave 3).

load ../test_helper

# Reader link (T12) -------------------------------------------------------

@test "P3-5: guide.md detects .phase-gate-report.md" {
  [ -f "skills/guide.md" ]
  grep -q ".phase-gate-report.md" skills/guide.md
}

@test "P3-5: guide.md recommends status --roadmap on gate report" {
  [ -f "skills/guide.md" ]
  # The scan branch should pair the file with a status --roadmap
  # recommendation. Allow either ordering on the same line.
  grep -qE "phase-gate-report|status --roadmap" skills/guide.md
  # The branch must combine detection and recommendation, not be a
  # dead reference. The `RECOMMEND="status --roadmap"` line is the
  # authoritative wiring added in T12.
  grep -qE 'RECOMMEND="status --roadmap"' skills/guide.md
}

# Index documentation (T33) -----------------------------------------------

@test "P3-5: .zcf/index.md documents guide.md as gate report reader" {
  [ -f ".zcf/index.md" ]
  grep -q "phase-gate-report.md" .zcf/index.md
  # The phase-gate-report entry should now reference guide.md as a reader
  # (not only manual user review). Accept the spec's bilingual wording.
  grep -qE "guide\.md.*扫|guide\.md.*scan|guide\.md.*读取" .zcf/index.md
}

@test "P3-5: .zcf/index.md links gate report to T12 (P1-3)" {
  [ -f ".zcf/index.md" ]
  grep -qE "T12.*P1-3|P1-3.*T12" .zcf/index.md
}
