## Tasks

### Phase A — P0 doc edits (must land)

- [x] **Task 1: `skills/guide/SKILL.md` (CRITICAL — 30+ sites)** ✅ 2026-09-09
  - Modified: `skills/guide/SKILL.md` L62, L96, L120, L143-145, L175-177, L188, L194, L199, L222-230, L238, L246-249, L257, L262-266, L273-275, L285, L295, L311-312
  - Diff applied: 11 batch replacements + 14 line edits
  - Added: rdd-verifier + rdd-quick as new stage commands (per ADR-0034 + ADR-0047)
  - Remaining: 3 backward-compat mapping notes (L225-227) — legitimate migration documentation
  - Test: AC-1 ✓ (0 hits for `skill_use("guide-...")`)
  - Commit: pending (consolidated with Task 2)

- [x] **Task 2: Create `docs/migration/v3-to-v4.md`** ✅ 2026-09-09
  - Created: `docs/migration/v3-to-v4.md` (191 lines, 7 H2 sections: 阶段数变化 / Skill 重命名映射 / Removed skills / 工作流变更 / 升级步骤 / FAQ / 参考)
  - Cross-reference: docs/ONBOARDING.md:375 link now resolves (was 404 before)
  - Test: AC-3 ✓ (file exists, ≥ 80 lines, all 7 required sections present)
  - Commit: pending (consolidated with Task 1)

### Phase B — P1 doc edits (should land)

- [x] **Task 3: `skills/rdd-verifier/SKILL.md` (8 sites)** ✅ 2026-09-09
  - Modified: L3, L32, L88, L101, L103, L213, L220, L328, L353 (9 replacements)
  - Diff: routing-context `guide-ship`/`guide-plan` → `rdd-builder`; preserve `evolved-from:`
  - Test: AC-2 ✓ (sub-skill grep pattern)
  - Commit: pending (consolidated with Task 4-7)

- [x] **Task 4: `skills/execute/SKILL.md` (3 sites)** ✅ 2026-09-09
  - Modified: L3, L48, L146 (4 replacements)
  - Diff: description + `$RDDF_EXECUTION_ROOT` routing context
  - Note: L53 contains a filename reference `2026-08-05-guide-ship-execution-contract.md` — pre-existing v3 filename preserved per `Out of Scope` (renaming the spec file would break git blame); explanatory note added
  - Test: AC-2 ✓
  - Commit: pending

- [x] **Task 5: `skills/status/SKILL.md` (5 sites)** ✅ 2026-09-09
  - Modified: L3, L173, L321, L447, L479, L492 (6 replacements)
  - Diff: description + remove dead link to deleted `guide-ship.md`
  - Test: AC-2 ✓
  - Commit: pending

- [x] **Task 6: `skills/rddf-session/SKILL.md` (3 sites)** ✅ 2026-09-09
  - Modified: L108, L312, L378 (3 replacements)
  - Diff: phase routing context
  - Test: AC-2 ✓
  - Commit: pending

- [x] **Task 7: `skills/rdd-env-check/SKILL.md` (1 site)** ✅ 2026-09-09
  - Modified: L3 (1 replacement)
  - Diff: phase caller list
  - Test: AC-2 ✓
  - Commit: pending

### Phase C — P2 doc edits (should land)

- [ ] **Task 8: `skills/add-improve/SKILL.md` (L96)**
  - Modify: L96
  - Diff: `skill_use("guide-design")` → `skill_use("rdd-planner")`
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 9: `skills/feature/SKILL.md` (L5)**
  - Modify: L5
  - Diff: "run guide-plan once first" → "run rdd-builder once first"
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 10: `skills/deps/SKILL.md` (L3)**
  - Modify: L3
  - Diff: "被 guide-plan 调用" → "被 rdd-builder 调用"
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 11: `skills/sync-hub/SKILL.md` (L3)**
  - Modify: L3
  - Diff: "被 guide-design 在 contract refresh 时调用" → "被 rdd-planner 在 contract refresh 时调用"
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 12: `skills/openspec-gate/SKILL.md` (L56)**
  - Modify: L56
  - Diff: `skill_use("guide-plan")` → `skill_use("rdd-builder")`
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 13: `README.md` (L13-19)**
  - Modify: L13-19
  - Diff: replace `v1.x` and `v2.0-beta` install commands with `v4.0.0` (latest stable)
  - Test: AC-4
  - Commit: TBD

### Phase D — Tests (extend parent change's bats)

- [ ] **Task 14: Extend `tests/integration/test_v4_doc_drift_contracts.bats` with Test 16-19**
  - Modify: `tests/integration/test_v4_doc_drift_contracts.bats`
  - Add: Test 16 (guide skill no active `skill_use("guide-*")`), Test 17 (9 sub-skill SKILL.md no `guide-design`/`guide-plan`/`guide-ship`), Test 18 (`docs/migration/v3-to-v4.md` exists and ≥ 80 lines), Test 19 (`README.md` L13-19 npm install section no `v1.x`/`v2.0-beta`)
  - Test: AC-5 (all 19 tests pass); AC-6 (pre-patch-fail verification)
  - Commit: TBD

### Phase E — Final regression gate

- [ ] **Task 15: Regression + Doctor**
  - Run: `./test.sh --full --regression` (no new failures beyond KNOWN_FAILURES baseline)
  - Run: `bash skills/rdd-doctor/scripts/doctor.sh --quiet` (no new CRITICAL beyond current 6)
  - Test: AC-7, AC-8
  - Commit: TBD
