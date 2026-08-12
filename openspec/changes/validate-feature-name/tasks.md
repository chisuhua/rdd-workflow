# Tasks: validate-feature-name

## 1. Test scaffolding (TDD red)

- [ ] 1.1 Create `tests/unit/test_validate_feature_name.py` with 3 failing cases: (a) typo detection warns, (b) correct spelling silent, (c) empty `iteration.json` passes
- [ ] 1.2 Verify tests fail with `pytest tests/unit/test_validate_feature_name.py` — exit code non-zero (helper not yet implemented)

## 2. Helper implementation (TDD green)

- [ ] 2.1 Add `_collect_existing_features(project_root: Path) -> set[str]` helper to `skills/propose/scripts/propose_change.py`: reads `.rddf/state/iteration.json`, collects unique `parent_feature` values, excludes `__ungrouped__`, returns empty set if file missing or empty
- [ ] 2.2 Verify tests pass: `pytest tests/unit/test_validate_feature_name.py` — 3/3 green
- [ ] 2.3 Verify no regression: `pytest tests/unit/test_propose_change*.py` — 43/43 still green

## 3. Wire into propose entry point

- [ ] 3.1 In `skills/propose/scripts/propose_change.py::create_skeleton_change`, call `_collect_existing_features()` before writing `parent_feature` to `iteration.json`; emit WARNING (stderr) if value not in set; respect `STRICT_FEATURE_VALIDATION=yes` env var (exit code != 0)
- [ ] 3.2 Verify warning output contains the existing feature list (truncate to 10 + "and N more")

## 4. Wire into approve entry point (bash)

- [ ] 4.1 In `skills/guide-design/scripts/approve_proposal.sh`, before writing `roadmap-meta.yaml` `parent_feature` field, invoke the same helper via `python3 -c "..."` and emit WARNING with matching format (default non-blocking)
- [ ] 4.2 Verify no regression: `bats tests/integration/test_approve_proposal_*.bats` — 8/9 still green (1 known failure accepted per `tests/KNOWN_FAILURES.txt` baseline)

## 5. Final validation

- [ ] 5.1 Run full Python unit suite: `pytest tests/unit/ -q --tb=short` — all green
- [ ] 5.2 Run full Python integration suite: `pytest tests/integration/ -q --tb=short` — all green
- [ ] 5.3 Run smoke bats: `bats tests/smoke.bats` — all green
- [ ] 5.4 Run `./test.sh --quick` — all green (or only baseline known failures)
- [ ] 5.5 Commit: `feat(propose): add parent_feature validation to propose + approve entry points`
