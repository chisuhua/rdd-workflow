# enforce-plan-tdd-5step-new — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`rdd-doctor` plan-tdd check reports 63 WARNING for historical plans lacking TDD 5-step markers. The `execute` skill reads these markers to step through tasks; missing markers cause misexecution. The check itself works correctly — what's missing is a *gate* that prevents new plans from shipping without canonical markers.

This design addresses:
1. New plans may be authored without TDD discipline (no enforcement today)
2. Historical 63 plans are noise (backfill is low-value)
3. Need preventive gate, not retroactive backfill

## Goals / Non-Goals

**Goals:**
- Add `plan-tdd-check` step before Phase 3 archive in `guide-ship`
- Reject archive if plan lacks canonical TDD markers (Write failing test, Run test to verify fail, Write minimal impl, Run test to verify pass, Defer commit)
- `SKIP_PLAN_TDD_CHECK=yes` opt-out with audit log for legacy plans

**Non-Goals:**
- Backfill 63 historical plans (churn vs value tradeoff unfavorable)
- Modify `rdd-workflow-writing-plans` plan template (already canonical)
- Modify rdd-doctor check logic (already correct)

## Decisions

### 1. Gate placement

Insert `plan-tdd-check` step at start of `guide-ship/scripts/ship_plan.sh` (before any other plan processing). This ensures check happens early in ship flow.

### 2. Skip semantics

`SKIP_PLAN_TDD_CHECK=yes`:
- Skips the check
- Writes audit entry to `.rddf/state/.ship-audit.jsonl` with:
  - timestamp
  - change_name
  - reason (env var detection, auto-generated)
  - skip_marker
- Idempotent (multiple calls accumulate audit entries)

### 3. Reuse rdd-doctor check

Direct call to `rddf doctor --category plan-tdd --quiet --json`, parse JSON output, exit 1 if any CRITICAL or ERROR finding exists.

### 4. Skip recommendation heuristic

When plan file's mtime is older than 60 days, the check output suggests setting `SKIP_PLAN_TDD_CHECK=yes` (informational only, no automatic opt-out).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Gate adds friction to all ship flows | Acceptable; legacy opt-out available |
| Users set SKIP_PLAN_TDD_CHECK for all flows (anti-pattern) | Audit log captures every skip; reviewable |
| Test for gate adds complexity to ship pipeline | Integration test in `tests/integration/test_guide_ship_plan_tdd_check.bats` |