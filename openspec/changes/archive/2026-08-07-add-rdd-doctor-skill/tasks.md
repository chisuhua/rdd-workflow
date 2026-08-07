## 1. Renderer contract (locks M1 milestone)

- [x] 1.1 Write `skills/rdd-doctor/scripts/doctor_render.py` with severity→exit-code mapping (0/1/2/3) and `--json` payload schema (timestamp, categories_checked, findings[], summary{critical,warning,info})
- [x] 1.2 Write `tests/unit/test_doctor_render.py` with ≥6 tests: severity mapping, JSON schema validation, exit-code matrix
- [x] 1.3 Decide on SHOULD items: include top-level `next_step` field in JSON; confirm cat-2 loose matching vs strict

## 2. Path resolver + state-schema-check (M2 critical path)

- [x] 2.1 Write `skills/rdd-doctor/scripts/path_resolver.py` that returns the real `_lib/` location (NEVER resolves via `skills/_lib/` shim)
- [x] 2.2 Write `skills/rdd-doctor/scripts/checks/state_schema_check.py` — validates `.rddf/state/{state_vector,sessions,iteration,deps_analysis}.json` against existing `_lib/schemas/*_schema.json`
- [x] 2.3 Write `tests/integration/test_state_schema_check.bats` — covers S2 root cause (iteration.json missing required field) + degraded fixture

## 3. Roadmap-meta-check (M2 critical path, S4 root cause)

- [x] 3.1 Write `skills/rdd-doctor/scripts/checks/roadmap_meta_check.py` — validates `openspec/changes/*/roadmap-meta.yaml` field completeness + `manual_deps`/`manual_blocks` are arrays (not strings)
- [x] 3.2 Write `tests/integration/test_roadmap_meta_check.bats` — covers S4 root cause (`manual_deps: "x,y"` string) with assertion that finding hint contains literal "silently ignore"

## 4. Proposal-table-check (uses existing parser, avoids drift)

- [x] 4.1 Extend `_lib/parse_approved.py` to expose a `validate_table_format(path) -> list[Finding]` API (instead of writing a new parser)
- [x] 4.2 Write `skills/rdd-doctor/scripts/checks/proposal_table_check.py` — calls the extended parser for both `proposal-suggestions.md` and `proposal-approved.md`
- [x] 4.3 Write `tests/integration/test_proposal_table_check.bats` — covers S5 root cause (column count drift, missing date column)

## 5. Tasks-checkbox-check (degraded path)

- [x] 5.1 Write `skills/rdd-doctor/scripts/checks/tasks_checkbox_check.py` — counts `- [ ]` / `- [x]` in `openspec/changes/*/tasks.md`, verifies file existence
- [x] 5.2 Add degraded-path branch: detect `openspec` on `$PATH`; if missing, emit INFO `openspec status unavailable, skipping cross-check`; do NOT raise as checker exception
- [x] 5.3 Write `tests/integration/test_tasks_checkbox_check.bats` — covers S6 root cause (checkbox count = 0 with active change) + degraded-path test (`PATH=$BATS_TMPDIR/empty_bin:$PATH`)

## 6. Plan-TDD-structure-check (loose matching, WARNING-only)

- [x] 6.1 Write `skills/rdd-doctor/scripts/checks/plan_tdd_check.py` — verifies `.rddf/plans/*.md` contains the 5 step markers (Write failing test / Verify fail / Implement / Verify pass / Commit); loose string-presence check
- [x] 6.2 Run against real corpus `tests/fixtures/` and the repo's own `.rddf/plans/*.md` to tune false-positive rate; emit WARNING only on missing markers
- [x] 6.3 Write `tests/integration/test_plan_tdd_check.bats` — covers S3 root cause (Step 3 missing)

## 7. Bash dispatcher + flags

- [x] 7.1 Write `skills/rdd-doctor/scripts/doctor.sh` — dispatches to single Python process (`doctor_render.py`) importing all 5 checkers; passes `--category`, `--quiet`, `--json` flags
- [x] 7.2 Add `--help` / `--version` flags
- [x] 7.3 Add `SKIP_DOCTOR=yes` and `DRY_RUN_DOCTOR=yes` env-var bypasses (per SHOULD #2-3)
- [x] 7.4 Write `tests/integration/test_rdd_doctor_cli.bats` — covers default / `--json` / `--category` / `--quiet` / `--help` modes

## 8. SKILL.md + smoke registration

- [x] 8.1 Write `skills/rdd-doctor/SKILL.md` (~50 lines, mirrors `rdd-env-check/SKILL.md` style) with full frontmatter (name/description/license/compatibility + metadata.author/version/user-invocable)
- [x] 8.2 Add `rdd-doctor` registration to `tests/smoke.bats` with description test line (AC6)
- [x] 8.3 Verify `bats tests/smoke.bats` passes including new entry

## 9. Diseased-fixture repo (for AC3 root-cause tests)

- [x] 9.1 Create `tests/fixtures/diseased-repo/` with all 5 category defects planted via named mutation helpers (`plant_manual_deps_string_drift`, `drop_plan_step3`, `drop_table_column`, etc.)
- [x] 9.2 Create `tests/fixtures/healthy-repo/` (empty / clean baseline)
- [x] 9.3 Add fixture-using tests across all 5 checker test files

## 10. Documentation sync

- [x] 10.1 Add "rdd-doctor" section to `AGENTS.md` (~15 lines, list 3 example scenarios)
- [x] 10.2 Add 1-line entry to `tests/README.md`
- [x] 10.3 Run `openspec validate add-rdd-doctor-skill --strict` and ensure no errors

## 11. Read-only enforcement + integration smoke

- [x] 11.1 Add `find ... -newer <marker>` + `git status --porcelain` diff tests (AC4)
- [x] 11.2 Run `rdd-doctor` against the real rdd-workflow repo as an integration smoke
- [x] 11.3 Run `./test.sh --full --regression` to confirm zero new failures

## 12. Archive pre-flight

- [x] 12.1 Confirm all 12 task groups above are complete; `tasks.md` checkboxes all checked
- [x] 12.2 `./test.sh --full --regression` → all green
- [x] 12.3 Commit change in worktree with conventional `feat(rdd-doctor):` prefix
- [x] 12.4 `guide-ship` archive flow (auto-detect mode: lightweight since single change)