## Tasks

### [1/4] Wire openspec validate into guide-plan.md Phase 4

- [x] Read `skills/guide-plan/SKILL.md` Phase 4 (plan-done) and locate insertion point between `run_plan_done_gate` and `write_plan_handoff`
- [x] Read `skills/guide-plan/scripts/plan_done_gate.sh` to confirm helper boundary
- [x] Read `skills/_lib/validate_report.py` to confirm `write_report(project_root, raw_report)` signature
- [x] Verify `openspec validate <change-name> --json` CLI usage (positional arg, not `--change`)
- [x] Add PYEOF block in guide-plan.md Phase 4 that:
  - Guards with `command -v openspec`
  - Loops over `$PROJECT_ROOT/openspec/changes/*/` (skipping `archive/`)
  - Runs `openspec validate <name> --json` per change (non-fatal)
  - Pipes raw JSON to Python via stdin (Oracle C1: no bash string interp)
  - Calls `validate_report.write_report(project_root, raw_report)` to persist to `.rddf/state/openspec-validate.json`
  - Catches all failures as non-fatal warnings
- [x] Mark wiring block with `ADR-0015` comment for grep-ability
- [x] Include TODO comment about long-term merge with gate.py

### [2/4] Update ADR-0015 status

- [x] Read `docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md`
- [x] Change status line from `待定` to `已采纳`
- [x] Append `### 修订记录` section at end of ADR-0015 documenting:
  - Date: 2026-07-20
  - What: guide-plan.md Phase 4 wiring 实装完成
  - Change: `refine-adr-0015-wiring`
  - Status transition: 待定 -> 已采纳
- [x] Read `docs/adr/README.md` ADR index table
- [x] Verify ADR-0015 row in README.md already shows `已采纳` (it does - README was ahead of ADR file)
- [x] No README.md change needed (already correct)

### [3/4] Add integration tests

- [x] Create `tests/integration/test_adr_0015_wiring.bats`
- [x] Add test: `validate_report.py` has `write_report` function (importable)
- [x] Add test: ADR-0015 status is `已采纳`
- [x] Add test: guide-plan.md Phase 4 contains ADR-0015 wiring marker
- [x] Add test: ADR-0015 has 修订记录 section
- [x] Load `test_helper` for `$REPO_ROOT`
- [x] Do NOT modify any existing test files

### [4/4] Verify and commit

- [x] Run `python3 -m pytest tests/unit/ -q --tb=short` - all 57 unit files pass
- [x] Run `bats tests/integration/test_adr_0015_wiring.bats` - all new tests pass
- [x] Run `npm test` (full bats suite) - all 663 existing tests still pass
- [x] Stage changes: ADR-0015, guide-plan/SKILL.md, new test file, change artifacts (proposal/design/tasks)
- [x] Update `.rddf/state/iteration.json`: change status `planned` -> `proposed`
- [x] Commit with message: `feat(adr-0015): wire openspec validate into guide-plan Phase 4 + update ADR status`
