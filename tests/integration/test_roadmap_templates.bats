#!/usr/bin/env bats
#
# Wave 3 / T15: roadmap.md templates 3 & 4 implementation (P1-5).
# See plan checkbox:
#   - [ ] 15. roadmap.md templates 3 & 4 implementation (P1-5)
#
# Locks three properties of skills/roadmap.md:
#   1. Template 3 (Blank) logic exists, uses ROADMAP_PHASE_COUNT env var
#      (AI-environment compatible — no stdin blocking reads).
#   2. Template 4 (ADR-based) logic exists, scans docs/adr/ for ADR-*.md
#      and reports ADR_COUNT.
#   3. Menu at lines 66-72 marks template 2 (Web) as 即将推出 (coming soon).

load ../test_helper

# P1-5: Template 3 implemented --------------------------------------------

@test "P1-5: template 3 (blank) implemented in roadmap.md" {
  [ -f "skills/roadmap.md" ]
  # The roadmap should have a branch for TEMPLATE=3 with the blank template body
  grep -qE 'TEMPLATE.*=.*"3"|TEMPLATE.*3' "skills/roadmap.md"
}

@test "P1-5: template 3 (blank) uses ROADMAP_PHASE_COUNT env var" {
  [ -f "skills/roadmap.md" ]
  # Blank template must use env var (not stdin read) for phase count
  grep -q "ROADMAP_PHASE_COUNT" "skills/roadmap.md"
}

# P1-5: Template 4 implemented --------------------------------------------

@test "P1-5: template 4 (ADR-based) implemented in roadmap.md" {
  [ -f "skills/roadmap.md" ]
  # Should scan docs/adr/ directory
  grep -qE "docs/adr/|ADR_COUNT" "skills/roadmap.md"
}

@test "P1-5: template 4 generates adr-impl category" {
  [ -f "skills/roadmap.md" ]
  # The generated category for ADR-based template
  grep -q "adr-impl" "skills/roadmap.md"
}

# P1-5: Template 2 menu marking -------------------------------------------

@test "P1-5: template 2 (Web) marked as coming soon in menu" {
  [ -f "skills/roadmap.md" ]
  # Menu line for template 2 must contain either 即将推出 (Chinese) or
  # "coming soon" (English fallback) somewhere on the line.
  grep -qE "Web.*即将推出|Web.*coming soon" "skills/roadmap.md"
}
