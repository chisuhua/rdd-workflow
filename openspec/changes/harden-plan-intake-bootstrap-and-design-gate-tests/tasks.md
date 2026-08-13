# Tasks: harden-plan-intake-bootstrap-and-design-gate-tests

> TDD 5-step structure per `rdd-workflow-writing-plans` skill.
> Each task: Write failing test → Verify fail → Implement → Verify pass → Commit.

## 1. Gap 1: Bootstrap edges tests

- [ ] 1.1 Write failing bats test: missing `.design-handoff.json` → plan_intake exits non-zero with guidance
- [ ] 1.2 Write failing bats test: v2 handoff missing `changes_pre_created` field → v1 fallback
- [ ] 1.3 Write failing bats test: stale `design_complete_at` (>30d) → warning but no block
- [ ] 1.4 Write failing bats test: empty `changes_pre_created: []` → exit non-zero + guidance
- [ ] 1.5 Verify all 4 Gap 1 tests pass (they should — plan_intake already handles these)
- [ ] 1.6 Commit: `test(plan_intake): bootstrap edges coverage (4 cases)`

## 2. Gap 4: Failure semantics tests

- [ ] 2.1 Write failing bats test: interrupted trace (missing `finalize_at`) → warning
- [ ] 2.2 Write failing bats test: abandoned rddf-session → orphan mark + cleanup hint
- [ ] 2.3 Verify Gap 4 tests pass
- [ ] 2.4 Commit: `test(plan_intake): failure semantics coverage (2 cases)`

## 3. Gap 3: Cross-phase integration tests

- [ ] 3.1 Write failing bats test: design v2 happy path with `changes_pre_created` → plan skips propose (Path A)
- [ ] 3.2 Write failing bats test: design v2 sad path (missing `version`) → warning + v1 fallback
- [ ] 3.3 Verify Gap 3 tests pass
- [ ] 3.4 Commit: `test(plan_intake): cross-phase integration (2 cases)`

## 4. Gap 2: Design gate characterization tests

- [ ] 4.1 Write failing pytest test: legitimate improvement (head frontmatter complete + 5 sections + ADR refs ≥1) → lock current `run_design_checks` behavior
- [ ] 4.2 Write failing pytest test: improvement missing `**类型**` head field → lock current behavior
- [ ] 4.3 Write failing pytest test: improvement missing In-Out Scope section → lock current behavior
- [ ] 4.4 Mark all 3 tests with `@pytest.mark.characterization`
- [ ] 4.5 Verify Gap 2 tests pass
- [ ] 4.6 Commit: `test(propose_quality_check): characterization baseline (3 cases)`

## 5. Documentation + zero-impl-check

- [ ] 5.1 Update `tests/README.md` with `characterization tests` section
- [ ] 5.2 Verify `git diff --stat skills/guide-plan/scripts/plan_intake.sh skills/propose/scripts/propose_quality_check.py` returns empty (zero implementation changes)
- [ ] 5.3 Verify `./test.sh --full --regression` all green, no new failures
- [ ] 5.4 Commit: `docs(tests): characterization test marker guide`

## Acceptance criteria

- All TDD tasks above marked complete
- `./test.sh --full --regression` passes
- Single bats file ≤150 lines; single pytest file ≤200 lines
- Zero implementation changes to `plan_intake.sh` or `propose_quality_check.py`
- Characterization tests documented in `tests/README.md`