# fix-doc-drift-followup-3

> Per 2026-09-09 第 3 轮 doc-vs-code 审计 (`rdd-doctor` + 3 agent 并行扫描).
> Closes the doc-drift sites **intentionally deferred** from both
> `fix-doc-drift-v4-architecture` (f4d675b, 已 archived) and
> `docs-v4-sync-followup-v2` (Oracle-approved, 待归档) — the 12 files / 35 sites
> that none of the first two batches covered.

## Why

Two prior doc-drift changes shipped fixes for the v4 architecture transition (Wave 3 hard removal of `guide-*` skills per ADR-0044, `rdd-quick` bypass per ADR-0047):

- **`fix-doc-drift-v4-architecture`** (f4d675b, 已 archived) — 8 P0/P1 doc edits + 1 doc-contract test covering README.md, USAGE.md, AGENTS.md, CHANGELOG.md, and the 3 most-trafficked `docs/architecture/*.md` files (overview, workflow-phases, README).
- **`docs-v4-sync-followup-v2`** (Oracle-approved `ses_f7c586c20ffeAgXx2H9KylZsji`, 待归档) — 6 additional doc files with stale v3 / dead-link references intentionally deferred from the parent change (ONBOARDING.md, improvement-check-mechanisms.md, INSTALL.md, skills-and-handoff.md, multi-project-*, extension-points.md).

**Gap**: A 2026-09-09 第 3 轮 audit (`rdd-doctor` + 3 parallel explore agents) discovered **12 files / 35 sites** still drift:

| # | File | Sites | Severity | Why NOT covered by prior batches |
|---|------|-------|----------|-----------------------------------|
| 1 | `skills/guide/SKILL.md` | **30+** | **P0 (CRITICAL)** | Recommended-recommender SKILL.md (sub-skill, not `rdd-*`); prior batches only touched `rdd-*` skill descriptions |
| 2 | `skills/rdd-verifier/SKILL.md` | 8 | P1 | Routing context mixes stale `guide-*` with backwards-compat note |
| 3 | `skills/status/SKILL.md` | 5 | P1 | Sub-skill with `guide-ship` refs + dead link to deleted `guide-ship.md` |
| 4 | `skills/execute/SKILL.md` | 4 | P1 | Sub-skill with `guide-ship` / `$RDDF_EXECUTION_ROOT` refs |
| 5 | `skills/rddf-session/SKILL.md` | 3 | P1 | Phase routing mentions `guide-plan` / `guide-ship` |
| 6 | `skills/sync-hub/SKILL.md` | 1 | P2 | `guide-design` in contract refresh context |
| 7 | `skills/add-improve/SKILL.md` | 1 | P2 | Live `skill_use("guide-design")` invocation |
| 8 | `skills/feature/SKILL.md` | 1 | P2 | "run guide-plan once first" |
| 9 | `skills/deps/SKILL.md` | 1 | P2 | "被 guide-plan 在 propose 完成后自动调用" |
| 10 | `skills/openspec-gate/SKILL.md` | 1 | P2 | Live `skill_use("guide-plan")` |
| 11 | `docs/migration/v3-to-v4.md` | **FILE MISSING** | **P0 (HIGH)** | `docs/ONBOARDING.md:375` explicitly references this file as the migration guide; readers get 404 |
| 12 | `README.md` L13-19 | 1 | P2 | npm install commands show v1.x / v2.0-beta while repo is at v4.0.0 |

**Why this matters**:
- **`skills/guide/SKILL.md`** is the **primary user entrypoint** — every AI agent that invokes `skill_use("guide")` reads this file. It currently recommends `skill_use("guide-ship")`, `skill_use("guide-design")`, `skill_use("guide-plan")` — all three skills were **physically deleted** in Wave 3 hard removal (ADR-0044, 2026-09-04). Every workflow entry now errors immediately.
- **`docs/migration/v3-to-v4.md`** is explicitly cited by `docs/ONBOARDING.md:375` as the v3 → v4 migration guide. New users following the onboarding doc get 404.
- The 10 sub-skill SKILL.md files keep misguiding agents about which stage owns which responsibility, leading to wrong `skill_use` invocations even when the right entry point is taken.

**Reference**:
- Parent change A: `openspec/changes/fix-doc-drift-v4-architecture/` (commit f4d675b, archived `2026-09-08-fix-doc-drift-v4-architecture`)
- Parent change B: `openspec/changes/docs-v4-sync-followup-v2/` (Oracle-approved, awaiting archive)
- ADRs: ADR-0043 (v4 stage-merge), ADR-0044 (Wave 3 hard removal), ADR-0047 (rdd-quick bypass)

## What Changes

### Doc edits (P0 — must land)

1. **`skills/guide/SKILL.md`** (CRITICAL — 30+ sites)
   - Stage list (L96): replace 5-stage menu with 4 stages + bypass
   - Action mapping table (L143-145, L175-177): `guide-design`/`guide-plan`/`guide-ship` → `rdd-planner`/`rdd-builder`/`rdd-builder`
   - WT_ISSUES_JSON check (L199): replace stage labels
   - Skill list (L188, L194): same rename
   - Routing example (L225-227, L246-247, L249, L264, L266, L273, L275, L285, L295, L297, L311-312): all `skill_use("guide-*")` → `skill_use("rdd-*")`
   - Session hook docs (L238): `guide-design.md`/`guide-plan.md`/`guide-ship.md` → `rdd-planner.md`/`rdd-builder.md`
   - Bypass option: add `skill_use("rdd-quick")` as row 5 (per ADR-0047)

2. **`docs/migration/v3-to-v4.md`** (NEW FILE — P0 HIGH)
   - Create with 5 H2 sections: 阶段数变化 / Skill 重命名映射 / Removed skills / 工作流变更 / 升级步骤
   - Plus FAQ + 参考 ADR-0043/0044/0047
   - Min 80 lines; serve as the canonical migration guide for v3 → v4 users

### Doc edits (P1 — should land)

3. **`skills/rdd-verifier/SKILL.md`** (8 sites): routing context `guide-ship`/`guide-plan` → `rdd-builder`; preserve `evolved-from:` frontmatter (legitimate historical)
4. **`skills/execute/SKILL.md`** (L3, 48, 146): description + `$RDDF_EXECUTION_ROOT` context
5. **`skills/status/SKILL.md`** (L3, 173, 321, 479, 492): description + remove dead link to `guide-ship.md`
6. **`skills/rddf-session/SKILL.md`** (L108, 312, 378): phase routing context
7. **`skills/rdd-env-check/SKILL.md`** (L3): phase caller list

### Doc edits (P2 — should land)

8. **`skills/add-improve/SKILL.md`** (L96): `skill_use("guide-design")` → `skill_use("rdd-planner")`
9. **`skills/feature/SKILL.md`** (L5): "run guide-plan once first" → "run rdd-builder once first"
10. **`skills/deps/SKILL.md`** (L3): "被 guide-plan 调用" → "被 rdd-builder 调用"
11. **`skills/sync-hub/SKILL.md`** (L3): "被 guide-design 在 contract refresh 时调用" → "被 rdd-planner 在 contract refresh 时调用"
12. **`skills/openspec-gate/SKILL.md`** (L56): `skill_use("guide-plan")` → `skill_use("rdd-builder")`
13. **`README.md`** (L13-19): npm install commands show `v1.x` and `v2.0-beta`; update to `v4` (latest stable) + main-branch install

### Test additions

14. **Extend `tests/integration/test_v4_doc_drift_contracts.bats`** (currently 10 tests from parent change) — add Test 16-19:
    - **Test 16**: `skills/guide/SKILL.md` does NOT contain active `skill_use("guide-*")` invocations
    - **Test 17**: 9 sub-skill SKILL.md files (execute/status/deps/add-improve/feature/sync-hub/rddf-session/openspec-gate/rdd-env-check) do NOT contain `guide-design`/`guide-plan`/`guide-ship` outside legitimate `evolved-from:` frontmatter
    - **Test 18**: `docs/migration/v3-to-v4.md` exists and has ≥ 80 lines
    - **Test 19**: `README.md` L13-19 npm install section does NOT contain `v1.x` or `v2.0-beta`

### Out of Scope

- README.md / USAGE.md / AGENTS.md / CHANGELOG.md — already covered by `fix-doc-drift-v4-architecture`
- docs/ONBOARDING.md + 5 other `docs/architecture/*.md` — already covered by `docs-v4-sync-followup-v2`
- Historical prose mentions in archived `openspec/specs/*.md` (e.g., `three-phase-skills/spec.md`, `archive-gate-verification/spec.md`) — intentionally retained as v3 evolution record
- `_lib/` code docstrings referencing `guide-ship/scripts/ship_*.sh` paths — out of scope per "no code logic changes" rule; tracked as future `code-docstring-cleanup-v4-rename` proposal
- USAGE.md 14 prose guide-* mentions (non-active `skill_use` calls) — already deferred in `docs-v4-sync-followup-v2` Out of Scope

## Capabilities

- capability-fix-doc-drift-followup-3

## Acceptance

- AC-1: `grep -nE 'skill_use\("(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)"\)' skills/guide/SKILL.md` returns 0 hits
- AC-2: `grep -nE 'skill_use\("guide-' skills/execute/SKILL.md skills/status/SKILL.md skills/deps/SKILL.md skills/add-improve/SKILL.md skills/feature/SKILL.md skills/sync-hub/SKILL.md skills/rddf-session/SKILL.md skills/openspec-gate/SKILL.md skills/rdd-env-check/SKILL.md` returns 0 hits (excludes legitimate `evolved-from:` frontmatter)
- AC-3: `docs/migration/v3-to-v4.md` exists, has ≥ 80 lines, contains 5 H2 sections (阶段数变化 / Skill 重命名 / Removed skills / 工作流变更 / 升级步骤) + FAQ + 参考
- AC-4: `README.md` L13-19 npm install section does NOT contain `v1.x` or `v2.0-beta`, labels `latest stable = v4.0.0`
- AC-5: `tests/integration/test_v4_doc_drift_contracts.bats` extended with Test 16-19; all 19 tests pass
- AC-6: pre-patch-fail verification: `git stash` 12 modified files → run bats → Test 16/17/18/19 fail → `git stash pop`
- AC-7: `./test.sh --full --regression` does not introduce new failures beyond `tests/KNOWN_FAILURES.txt` baseline
- AC-8: `bash skills/rdd-doctor/scripts/doctor.sh` does not add new CRITICAL findings (current: 6 CRITICAL; post-completion: ≤ 6)

## Specs

Per D3 spec-delta 协同 (per ADR-0025), spec.md 落 `openspec/changes/fix-doc-drift-followup-3/specs/doc-drift-followup-3/spec.md` (path B — change-local). 8 Requirement blocks with 18 Scenarios total mirroring the 8 AC.

## Reference

- Parent change A: `openspec/changes/fix-doc-drift-v4-architecture/` (f4d675b, archived 2026-09-08)
- Parent change B: `openspec/changes/docs-v4-sync-followup-v2/` (Oracle-approved, awaiting archive)
- ADRs: [ADR-0043](docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md) (v4 stage-merge), [ADR-0044](docs/adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md) (Wave 3 hard removal), [ADR-0047](docs/adr/ADR-0047-rdd-quick-bypass-path.md) (rdd-quick bypass)
- Feature fragment: `.rddf/roadmap/features/feat-fix-archive-gaps-v2.md` (this change's phase-4)
- Improvement draft: `.rddf/improvements/fix-doc-drift-followup-3.md`
- Doctor report: `.rddf/state/.doctor-report.json` (snapshot at 2026-09-09)
