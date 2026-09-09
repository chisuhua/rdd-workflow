## Tasks

### Phase A — P0 doc edits (must land)

- [ ] **Task 1: `skills/guide/SKILL.md` (CRITICAL — 30+ sites)**
  - Modify: `skills/guide/SKILL.md` L96, L143-145, L175-177, L188, L194, L199, L225-227, L238, L246-247, L249, L264, L266, L273, L275, L285, L295, L297, L311-312
  - Diff: replace all `guide-design`/`guide-plan`/`guide-ship` → `rdd-planner`/`rdd-builder`/`rdd-builder`; add `rdd-quick` row 5 (per ADR-0047); update stage list 5→4 + bypass
  - Test: AC-1 (grep `skill_use("guide-...")` returns 0 hits)
  - Commit: TBD

- [ ] **Task 2: Create `docs/migration/v3-to-v4.md`**
  - Modify: `docs/migration/v3-to-v4.md` (NEW file)
  - Diff: ≥ 80 lines with 5 H2 sections (阶段数变化 / Skill 重命名映射 / Removed skills / 工作流变更 / 升级步骤) + FAQ + 参考 (ADR-0043/0044/0047)
  - Test: AC-3 (file exists, ≥ 80 lines, contains all 7 required sections)
  - Commit: TBD

### Phase B — P1 doc edits (should land)

- [ ] **Task 3: `skills/rdd-verifier/SKILL.md` (8 sites)**
  - Modify: `skills/rdd-verifier/SKILL.md` L3, L32, L88, L101, L103, L213, L220, L328, L353
  - Diff: routing-context `guide-ship`/`guide-plan` → `rdd-builder`; preserve `evolved-from:` frontmatter
  - Test: AC-2 (sub-skill grep pattern)
  - Commit: TBD

- [ ] **Task 4: `skills/execute/SKILL.md` (3 sites)**
  - Modify: `skills/execute/SKILL.md` L3, L48, L146
  - Diff: description + `$RDDF_EXECUTION_ROOT` routing context
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 5: `skills/status/SKILL.md` (5 sites)**
  - Modify: `skills/status/SKILL.md` L3, L173, L321, L479, L492
  - Diff: description + remove dead link to deleted `guide-ship.md`
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 6: `skills/rddf-session/SKILL.md` (3 sites)**
  - Modify: `skills/rddf-session/SKILL.md` L108, L312, L378
  - Diff: phase routing context
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 7: `skills/rdd-env-check/SKILL.md` (1 site)**
  - Modify: `skills/rdd-env-check/SKILL.md` L3
  - Diff: phase caller list
  - Test: AC-2
  - Commit: TBD

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
