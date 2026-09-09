# docs-v4-sync-followup-v2

> Per Oracle review of `fix-doc-drift-v4-architecture` (2026-09-09).
> Closes the doc-drift sites intentionally deferred from the parent change
> because they require larger rewrites or lie in less-trafficked docs.

## Why

The parent change `fix-doc-drift-v4-architecture` (commit f4d675b) shipped 8 P0/P1 doc edits + 1 doc-contract test covering README.md, USAGE.md, AGENTS.md, CHANGELOG.md, and the 3 docs/architecture/ files most directly tied to the v4 architecture. The Oracle review (ses_f7c586c20ffeAgXx2H9KylZsji) flagged **6 additional doc files with stale v3 / dead-link references** that were intentionally deferred:

| # | File | Stale references | Severity | Why deferred from parent |
|---|------|------------------|----------|---------------------------|
| 1 | `docs/ONBOARDING.md` | **17+ guide-*** | **P0** | `docs/architecture/README.md` explicitly lists ONBOARDING.md as the user entry point; needs wholesale rewrite of phase table + skill lists + "Recommended" line + tree |
| 2 | `docs/architecture/improvement-check-mechanisms.md` | **5 dead links** to `skills/guide-ship/{SKILL.md,scripts/*}` | **P0** | All 5 paths reference Wave-3-deleted skill directory; readers following the links get 404 |
| 3 | `skills/INSTALL.md` | 2 guide-* | P1 | Source-chain line references deleted skill files |
| 4 | `docs/architecture/skills-and-handoff.md` | 4 guide-* | P1 | Discovery path examples list deleted `skills/guide-arch/SKILL.md` paths |
| 5 | `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` | 1 reference | P1 | Cross-project skill table |
| 6 | `docs/architecture/extension-points.md` | 1 reference | P1 | "Write the body" guidance example |

**Why this matters**: ONBOARDING.md is the **new user entry point** (per `docs/architecture/README.md` Update Convention). A new user reading "💡 Recommended: skill_use(\"guide-plan\")" (ONBOARDING.md L194) will hit a non-existent skill and fail. The dead links in improvement-check-mechanisms.md create 404s when contributors follow the cited paths.

**Reference**: Oracle review session `ses_f7c586c20ffeAgXx2H9KylZsji` (subagent kimi-k2.6, score 6/10 fix-or-ship).

## What Changes

### Doc edits (all P0/P1)

1. **`docs/ONBOARDING.md`** (wholesale rewrite of phase sections)
   - L4-6 banner: "v3.0+ 五阶段" → "v4.0+ 四阶段"
   - L25 history paragraph: rewrite to mention v4.0+ as current, v3.0 as historical
   - L42-44 directory tree: replace `guide-arch.md`/`guide-plan.md`/`guide-ship.md` with `rdd-arch.md`/`rdd-planner.md`/`rdd-builder.md`
   - L82 intro: "五阶段" → "四阶段 + 旁路"
   - L88-91 phase skill table: 4 stage rows + 1 bypass row
   - L97-103 skill transition diagram: 4 transitions + 1 bypass arrow
   - L169-176 phase table: 4 rows (drop Design/Plan standalone; merge into Planner + Builder)
   - L194 recommended skill_use: `skill_use("guide-plan")` → `skill_use("rdd-planner")`
   - L210 reference: `guide-ship` Phase 1 → `rdd-builder` P0/P1
   - L225 "五阶段状态机总览": rewrite list with rdd-* names
   - L252-253 skill file size table: rewrite
   - L322-324 directory tree: rdd-* names
   - L373 history paragraph: add v4 line, mark v3 as historical

2. **`docs/architecture/improvement-check-mechanisms.md`** (5 dead link fixes)
   - L45: `skills/guide-ship/SKILL.md:387-475` → `skills/rdd-builder/SKILL.md` (Phase 2.5 review section)
   - L46: `skills/guide-ship/scripts/ship_review.sh` → `skills/rdd-builder/scripts/ship_review.sh`
   - L138: `skills/guide-ship/scripts/ship_archive.sh:239` → `skills/rdd-builder/scripts/ship_archive.sh:239`
   - L465: same as L46
   - L466: same as L138

3. **`skills/INSTALL.md`** (2 line fixes)
   - L34: "被 guide-plan 调用" → "被 rdd-planner 调用"
   - L186: "guide-ship.md (source _lib/archive.sh)" → "rdd-builder.md (source _lib/archive.sh)"

4. **`docs/architecture/skills-and-handoff.md`** (4 line fixes)
   - L33-36: 4 `skills/guide-arch/SKILL.md` discovery paths → `skills/rdd-arch/SKILL.md`

5. **`docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`** (1 line fix)
   - L63: skill column list `guide-arch/guide-design/guide-plan/guide-ship` → `rdd-arch/rdd-planner/rdd-builder`

6. **`docs/architecture/extension-points.md`** (1 line fix)
   - L13: `skills/guide-arch/SKILL.md` → `skills/rdd-arch/SKILL.md`

### Test additions (extends parent's test file)

7. **`tests/integration/test_v4_doc_drift_contracts.bats`** — extend Test 12 scope
   - Currently: checks 3 docs/architecture/ files modified by parent change
   - Update: check ALL docs/architecture/*.md files (catches future drift in unchanged files)
   - Add Test 14: check `docs/ONBOARDING.md` for live `skill_use("guide-*")` invocations
   - Add Test 15: check `skills/INSTALL.md` for guide-* skill name references

### Out of Scope

- No code logic changes
- No skill frontmatter / metadata changes
- No new ADR (parent change's ADR references are sufficient)
- No archived historical mentions — only LIVE references fixed

## Capabilities

- capability-docs-v4-sync-followup-v2

## Acceptance

- AC-1: `docs/ONBOARDING.md` directory tree lists `rdd-arch.md` / `rdd-planner.md` / `rdd-builder.md` (NOT `guide-*`)
- AC-2: `docs/ONBOARDING.md` L194 "💡 Recommended" line uses `skill_use("rdd-planner")` (not `guide-plan`)
- AC-3: `grep -rn "guide-design\|guide-plan\|guide-ship" docs/architecture/` returns 0 hits across ALL `.md` files
- AC-4: `grep -rn "skills/guide-ship" docs/architecture/` returns 0 hits
- AC-5: `grep -rn "skills/guide-arch" docs/architecture/skills-and-handoff.md` returns 0 hits
- AC-6: `grep -rn "guide-design\|guide-plan\|guide-ship" skills/INSTALL.md` returns 0 hits
- AC-7: `grep -rn "skill_use(\"guide-" docs/ONBOARDING.md USAGE.md README.md` returns 0 hits (catches active commands across all 3 user-facing docs)
- AC-8: tests/integration/test_v4_doc_drift_contracts.bats Test 12 extended to all `docs/architecture/*.md`; all 15 tests pass
- AC-9: New Test 14 + Test 15 added; pre-patch fail verification: stash + run + 2+ tests fail
- AC-10: `./test.sh --full --regression` shows no new failures

## Specs

Per D3 spec-delta pattern, spec.md 落 `openspec/changes/docs-v4-sync-followup-v2/specs/docs-v4-sync-scope-followup/spec.md` (path B — change-local).

## Reference

- Parent change: `openspec/changes/fix-doc-drift-v4-architecture/` (commit f4d675b)
- Oracle review session: `ses_f7c586c20ffeAgXx2H9KylZsji`
- ADRs: ADR-0043 (v4 stage-merge), ADR-0044 (Wave 3 hard removal), ADR-0047 (rdd-quick bypass)
