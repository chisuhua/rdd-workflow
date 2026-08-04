## 1. Setup

- [x] 1.1 Read `proposal.md`, `design.md`, `improvements/add-skill-registration-checklist.md` and confirm In Scope / Out of Scope boundaries
- [x] 1.2 Inspect `tests/unit/test_doc_contracts.py` current assertions: `_count_skill_files()` (L56-61), `test_install_description_skill_count_matches_disk` (L63), `test_package_json_skills_count_within_delta` (L73, `<= disk + 2` at L76)
- [x] 1.3 Inspect `tests/integration/test_skill_metadata_consistency.bats` hard-coded skill list; count current disk skills (expect 18) and verify alignment with INSTALL.md + package.json before tightening

## 2. Implementation (TDD 5 步)

- [x] 2.1 Write failing tests: add unit cases — package.json exact match (`== disk`, no `+2` tolerance) and INSTALL.md sub-skill table row count == disk SKILL.md count; add bats case asserting metadata-consistency auto-includes new skills via dynamic glob
- [x] 2.2 Verify tests fail (red): confirm current `<= disk + 2` passes when package.json is missing a skill (temporarily assert exact match → fails), and INSTALL.md table-row assertion fails today
- [x] 2.3 Implement change: tighten `test_package_json_skills_count_within_delta` to `len(pkg["skills"]) == disk`; add INSTALL.md sub-skill table row-count assertion (parse table rows, filter non-skill lines); update `tests/integration/test_skill_metadata_consistency.bats` to dynamic glob over `skills/*/SKILL.md` + `skills/*.md`; add "新增 skill 注册 checklist" (5 项, `- [x]` format) to `docs/change-quality-guide.md`
- [x] 2.4 Verify tests pass (green): all test_doc_contracts cases pass with exact match (no drift on current 18 skills); the 2 new cases pass; metadata-consistency bats passes with dynamic glob
- [x] 2.5 Refactor + commit: confirm `_count_skill_files()` logic unchanged, checklist complements (not duplicates) existing bats, diff is proposal-only scope, then commit

## 3. Verification

- [x] 3.1 Run `openspec validate add-skill-registration-checklist --json` — 接受 specs/ 缺失 ERROR (本次 fill 不写 specs/, plan 阶段决策)
- [x] 3.2 Run `python3 -m pytest tests/unit/test_doc_contracts.py -q` (all pass with exact match)
- [x] 3.3 Negative check: temporarily remove one skill from package.json `skills[]` → `== disk` assertion FAILS (proves tolerance no longer masks drift); restore afterward
- [x] 3.4 Run `bats tests/integration/test_skill_metadata_consistency.bats` (passes with dynamic glob)
- [x] 3.5 Run `npm test` full bats regression + `python3 -m pytest tests/unit/ tests/integration/ -q` — zero regression on the ~100 improvement-related tests
- [x] 3.6 Confirm `docs/change-quality-guide.md` contains the 5-item registration checklist in `- [x]` format
- [x] 3.7 Run `git show HEAD:openspec/changes/add-skill-registration-checklist/design.md` (artifact committed)

## 4. Documentation

- [x] 4.1 Add entry to `CHANGELOG.md` (if present)
- [x] 4.2 Confirm no ADR change needed (out of scope per proposal)
