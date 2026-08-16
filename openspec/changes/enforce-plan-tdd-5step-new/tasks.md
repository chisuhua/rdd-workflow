# enforce-plan-tdd-5step-new — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 Add `plan-tdd-check` function in `guide-ship/scripts/ship_plan.sh`
  - Implement `check_plan_tdd(plan_path)` returning exit 0 (pass) or 1 (fail)
  - Call `rddf doctor --category plan-tdd --quiet --json` and parse for CRITICAL/ERROR findings
- [ ] 1.2 Insert check call at start of `run_ship_phase1` / Phase 2 execute trigger
  - Before plan generation, run `check_plan_tdd "$PLAN_FILE"`
  - Exit 1 with user-facing message if check fails
- [ ] 1.3 Implement `SKIP_PLAN_TDD_CHECK=yes` opt-out
  - Detect env var at check entry
  - If set, write `.rddf/state/.ship-audit.jsonl` line with timestamp + change_name + skip_marker
  - Skip the actual check, return 0
- [ ] 1.4 Add old-plan skip recommendation heuristic
  - If plan file mtime > 60 days, print "consider SKIP_PLAN_TDD_CHECK=yes for legacy plans" message
  - Informational only, no automatic opt-out

## Verification

- [ ] 2.1 Create `tests/integration/test_guide_ship_plan_tdd_check.bats`
  - Test: compliant plan passes check
  - Test: non-compliant plan (missing "Defer commit") fails check
  - Test: `SKIP_PLAN_TDD_CHECK=yes` skips + writes audit
  - Test: old plan (>60 days mtime) suggests skip but doesn't auto-skip
- [ ] 2.2 Run `bats tests/integration/test_guide_ship_plan_tdd_check.bats` — all 4 cases pass
- [ ] 2.3 Run `python3 -m pytest tests/unit/ -q --tb=short` — no regressions
- [ ] 2.4 Run `openspec validate enforce-plan-tdd-5step-new` — passes
- [ ] 2.5 End-to-end: ship a new change with `SKIP_PLAN_TDD_CHECK=yes`, verify audit entry created