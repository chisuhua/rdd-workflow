# backfill-proposal-approved-col4 — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 Investigate `proposal-approved.md` column distribution
  - `awk -F'|' '{print NF}' proposal-approved.md | sort | uniq -c`
  - Identify rows with column count != 4 (excluding header/separator)
- [ ] 1.2 Fix any actual 3-column or 5-column rows
  - Add missing column or merge extra column based on row context
  - Preserve all existing content (proposal name, priority, date)
- [ ] 1.3 Upgrade rdd-doctor check severity WARNING → CRITICAL
  - Modify `skills/rdd-doctor/scripts/checks/proposal_table_check.py::run()`
  - Return `Finding(severity=Severity.CRITICAL, ...)` when column count != 4
- [ ] 1.4 Add CI gate step in `.github/workflows/test.yml`
  - Insert `rddf doctor --category proposal-table --quiet` in "断言质量门控" section
  - Failure should exit 1 and block merge
- [ ] 1.5 Create `tests/integration/test_proposal_approved_format.bats`
  - Test: all data rows have exactly 4 columns
  - Test: header row has correct column count (5 separator positions)
  - Test: no unescaped pipe character in proposal name field

## Verification

- [ ] 2.1 Run `rddf doctor --category proposal-table --quiet` — exits 0
- [ ] 2.2 Run `python3 -m pytest tests/unit/ -q --tb=short` — no regressions
- [ ] 2.3 Run `openspec validate backfill-proposal-approved-col4` — passes