# add-cross-repo-state-schemas — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 Diff review: Verify 6 schema files in `_lib/schemas/` match proposal specs — output diff report showing field alignment
- [ ] 1.2 Verify each schema has `version` (const) and `$id` unique identifier
- [ ] 1.3 Verify `tests/unit/test_cross_repo_schemas.py` exists with 6 schemas × 3 test cases (valid/invalid/missing-field)
- [ ] 1.4 Run `python3 -m pytest tests/unit/test_cross_repo_schemas.py -v` — confirm all 18+ tests pass
- [ ] 1.5 Verify rdd-doctor `--category state` detects the 6 new schemas — run and confirm CRITICAL/WARNING output
- [ ] 1.6 Verify `docs/schemas/cross-repo-schemas.md` exists with field semantics documentation

## Verification

- [ ] 2.1 Run `openspec validate add-cross-repo-state-schemas` — confirm change is valid
- [ ] 2.2 Run full test suite: `python3 -m pytest tests/unit/ -q --tb=short` — confirm no regressions
