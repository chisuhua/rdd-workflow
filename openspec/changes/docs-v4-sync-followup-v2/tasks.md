## Tasks

### Phase A — P0 ONBOARDING.md (high-impact, new user entry point)

- [ ] **Task 1: ONBOARDING.md L4-6 banner**
  - Modify: `docs/ONBOARDING.md` L4-6
  - Diff: "v3.0+ 五阶段" → "v4.0+ 四阶段"; add rdd-quick mention
  - Test: AC-1 indirectly
  - Commit: TBD

- [ ] **Task 2: ONBOARDING.md L25 history paragraph**
  - Modify: `docs/ONBOARDING.md` L25
  - Diff: rewrite to put v4.0+ as current, v3.0 as historical
  - Commit: TBD

- [ ] **Task 3: ONBOARDING.md L42-44 directory tree**
  - Modify: `docs/ONBOARDING.md` L42-44
  - Diff: `guide-arch.md`/`guide-plan.md`/`guide-ship.md` → `rdd-arch.md`/`rdd-planner.md`/`rdd-builder.md`
  - Test: AC-1
  - Commit: TBD

- [ ] **Task 4: ONBOARDING.md L82 intro**
  - Modify: `docs/ONBOARDING.md` L82
  - Diff: "五阶段" → "四阶段 + 旁路"
  - Commit: TBD

- [ ] **Task 5: ONBOARDING.md L88-91 phase skill table**
  - Modify: `docs/ONBOARDING.md` L88-91
  - Diff: 5 rows (arch/design/plan/ship/verifier) → 4 stage + 1 bypass (arch/planner/builder/verifier + quick)
  - Test: AC-1
  - Commit: TBD

- [ ] **Task 6: ONBOARDING.md L97-103 transition diagram**
  - Modify: `docs/ONBOARDING.md` L97-103
  - Diff: 4 transitions (arch→design→plan→ship→verifier) → 4 stage transitions + 1 bypass
  - Commit: TBD

- [ ] **Task 7: ONBOARDING.md L169-176 phase table**
  - Modify: `docs/ONBOARDING.md` L169-176
  - Diff: rewrite with 4 rows (drop Design/Plan standalone)
  - Commit: TBD

- [ ] **Task 8: ONBOARDING.md L194 "Recommended" line**
  - Modify: `docs/ONBOARDING.md` L194
  - Diff: `skill_use("guide-plan")` → `skill_use("rdd-planner")`
  - Test: AC-2
  - Commit: TBD

- [ ] **Task 9: ONBOARDING.md L210, L225, L252-253, L322-324, L373**
  - Modify: 5 separate sections
  - Diff: guide-* → rdd-*; rewrite size table; update tree
  - Commit: TBD

### Phase B — P0 dead link fixes (improvement-check-mechanisms.md)

- [ ] **Task 10: improvement-check-mechanisms.md L45**
  - Modify: `docs/architecture/improvement-check-mechanisms.md` L45
  - Diff: `skills/guide-ship/SKILL.md:387-475` → `skills/rdd-builder/SKILL.md` Phase 2.5
  - Test: AC-4
  - Commit: TBD

- [ ] **Task 11: improvement-check-mechanisms.md L46, L465 (duplicate)**
  - Modify: same file L46 + L465
  - Diff: `skills/guide-ship/scripts/ship_review.sh` → **`skills/rdd-builder/scripts/phase2_5_review.sh`** (v4 renamed; `ship_review.sh` was deleted in Wave 3 — Oracle P0 catch)
  - Test: AC-4
  - Commit: TBD

- [ ] **Task 12: improvement-check-mechanisms.md L138, L466 (duplicate)**
  - Modify: same file L138 + L466
  - Diff: `skills/guide-ship/scripts/ship_archive.sh:239` → **`skills/rdd-builder/scripts/phase3_archive.sh`** (v4 renamed; `ship_archive.sh` was deleted in Wave 3 — Oracle P0 catch)
  - Test: AC-4
  - Commit: TBD

- [ ] **Task 12b: improvement-check-mechanisms.md L81 (Oracle P1 catch)**
  - Modify: same file L81
  - Diff: `guide-arch/scripts/arch_env_check.sh` → `rdd-arch/scripts/arch_env_check.sh` (inline code reference, no `skills/` prefix)
  - Test: AC-3 (covered by Test 12 3-pattern via `skill_use`/`Entry skill`/`skills/`)
  - Commit: TBD

- [ ] **Task 8b: ONBOARDING.md L105 ac-verifier dead link (Oracle P1 catch)**
  - Modify: `docs/ONBOARDING.md` L105
  - Diff: `ac-verifier.md` → remove (skill was deleted 2026-09-07 per ADR-0045); reword transition line
  - Test: AC-7 indirectly (this is the same drift class)
  - Commit: TBD

- [ ] **Task 8c: ONBOARDING.md L370 `guide-*.md` instruction (Oracle P1 catch)**
  - Modify: `docs/ONBOARDING.md` L370
  - Diff: "更新对应的 `guide-*.md` 文件" → "更新对应的 `rdd-*.md/SKILL.md` 文件" or "更新对应的 skill SKILL.md"
  - Commit: TBD

### Phase C — P1 doc edits

- [ ] **Task 13: INSTALL.md L34**
  - Modify: `skills/INSTALL.md` L34
  - Diff: "被 guide-plan 调用" → "被 rdd-planner 调用"
  - Test: AC-6
  - Commit: TBD

- [ ] **Task 14: INSTALL.md L186**
  - Modify: `skills/INSTALL.md` L186
  - Diff: "guide-ship.md (source _lib/archive.sh)" → "rdd-builder.md (source _lib/archive.sh)"
  - Test: AC-6
  - Commit: TBD

- [ ] **Task 15: skills-and-handoff.md L31 + L33-36 (5 lines, Oracle caught L31 miss)**
  - Modify: `docs/architecture/skills-and-handoff.md` L31 + L33-36
  - Diff:
    - L31: `skill_use("guide-arch")` → `skill_use("rdd-arch")` (live invocation, **Oracle P1 catch — user would 404**)
    - L33-36: 4 `skills/guide-arch/SKILL.md` discovery paths → `skills/rdd-arch/SKILL.md`
  - Test: AC-5
  - Commit: TBD

- [ ] **Task 16: multi-project-ai-collaborative-development-gap-analysis.md L52, L63, L148 (3 lines, Oracle caught 2 misses)**
  - Modify: `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` L52 + L63 + L148
  - Diff:
    - L52: "AI 在 guide-design 阶段" → "AI 在 rdd-planner 阶段" (live prose)
    - L63: skill column list `guide-arch/guide-design/guide-plan/guide-ship` → `rdd-arch/rdd-planner/rdd-builder`
    - L148: "升级 guide-plan deps 阶段" → "升级 rdd-planner deps 阶段" (live prose)
  - Test: AC-3
  - Commit: TBD

- [ ] **Task 17: extension-points.md L13**
  - Modify: `docs/architecture/extension-points.md` L13
  - Diff: `skills/guide-arch/SKILL.md` → `skills/rdd-arch/SKILL.md`
  - Test: AC-3
  - Commit: TBD

### Phase D — Test extensions

- [ ] **Task 18: Extend Test 12 to all docs/architecture/*.md**
  - Modify: `tests/integration/test_v4_doc_drift_contracts.bats` Test 12
  - Diff: change loop from `[docs/architecture/overview.md, workflow-phases.md, README.md]` to `[docs/architecture/*.md]`
  - Test: AC-8
  - Commit: TBD

- [ ] **Task 19: Add Test 14 (ONBOARDING.md live skill_use check)**
  - Modify: same test file
  - Add: new @test case using perl to scan ONBOARDING.md for `skill_use("guide-*")` invocations
  - Test: AC-7, AC-9
  - Commit: TBD

- [ ] **Task 20: Add Test 15 (INSTALL.md guide-* check)**
  - Modify: same test file
  - Add: new @test case grep'ing INSTALL.md for guide-* skill name references
  - Test: AC-6, AC-9
  - Commit: TBD

### Phase E — Verification

- [ ] **Task 21: pre-patch fail verification**
  - Run: `git stash --keep-index` then `bats tests/integration/test_v4_doc_drift_contracts.bats`
  - Expect: ≥2 of Tests 14/15 fail (catches the drift)
  - Commit: not applicable

- [ ] **Task 22: Full regression gate**
  - Run: `./test.sh --full --regression`
  - Expect: no new failures
  - Test: AC-10
  - Commit: not applicable

- [ ] **Task 23: AC-3 grep verification (Test 12 3-pattern with shim exclusion)**
  - Run: `grep -rnE 'skill_use\(\"(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)\"\)|\*\*?Entry skill\*\*?: \`(guide-arch|guide-design|guide-plan|guide-ship)\`|skills/(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)/' docs/architecture/ | grep -v 'shim\|DEPRECATED\|compat'`
  - Expect: 0 hits (after Task 18 extends Test 12 to all docs/architecture/*.md with shim exclusion; shim exclusion is required to avoid false-positive on rdd-arch-rdd-planner-integration.md L337/340 which legitimately document the compat shim)
  - Test: AC-3
  - Commit: not applicable

- [ ] **Task 24: AC-4 grep verification**
  - Run: `grep -rn "skills/guide-ship" docs/architecture/`
  - Expect: 0 hits
  - Test: AC-4
  - Commit: not applicable

- [ ] **Task 25: AC-5 grep verification**
  - Run: `grep -rn "skills/guide-arch" docs/architecture/skills-and-handoff.md`
  - Expect: 0 hits
  - Test: AC-5
  - Commit: not applicable

- [ ] **Task 26: AC-6 grep verification**
  - Run: `grep -rn "guide-design\|guide-plan\|guide-ship" skills/INSTALL.md`
  - Expect: 0 hits
  - Test: AC-6
  - Commit: not applicable

- [ ] **Task 27: AC-7 grep verification**
  - Run: `grep -rn 'skill_use("guide-' docs/ONBOARDING.md USAGE.md README.md`
  - Expect: 0 hits
  - Test: AC-7
  - Commit: not applicable

### Phase F — Archive

- [ ] **Task 28: Archive the change**
  - Run: `openspec archive docs-v4-sync-followup-v2 --yes`
  - Commit: TBD (auto-commit per Archive Auto-Commit convention)
