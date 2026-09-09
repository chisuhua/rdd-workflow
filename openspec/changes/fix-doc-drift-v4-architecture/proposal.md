# fix-doc-drift-v4-architecture

> Per ADR-0043 (v4 stage-merge), ADR-0044 (Wave 3 hard removal of guide-*), and ADR-0047 (rdd-quick bypass path).
> Closes the documentation drift surfaced by 2026-09-09 code-vs-doc audit.

## Why

v4 stage-merge (ADR-0043, 2026-09-04) collapsed the 5-phase `arch → design → plan → ship → verify` model into 4 stages (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`) and added `rdd-quick` as a bypass path (ADR-0047). Wave 1–3 (2026-09-04 ~ 2026-09-05) executed the code changes, removed the `guide-*` skills, and migrated skill invocations. **However, ~7 user-facing and architectural documents still describe the pre-v4 model** — a critical drift because the docs are the first entry point for new users and the canonical "current-architecture snapshot" the maintainers rely on.

### Drift inventory (2026-09-09 audit)

| # | File | Severity | Issue |
|---|------|----------|-------|
| 1 | `README.md` L62-64 | P0 | "使用流程" lists `rdd-builder` twice (Plan 端 + Ship 端); Plan 端 should be `rdd-planner` |
| 2 | `README.md` L105, 110-117 | P0 | "v3.0 新特性" section + table still says "五阶段架构 (arch → design → plan → ship → verify)" |
| 3 | `README.md` L399-406 | P0 | Directory tree lists `rdd-builder` 3 times, missing `rdd-planner` and `rdd-quick` |
| 4 | `docs/architecture/overview.md` L5, 9, 17-22 | P0 | "five-phase architecture" + 27 skills (5 phase guides + 22 sub-skills) + mermaid diagram all reference v3 5-phase model |
| 5 | `docs/architecture/overview.md` L66-70 | P0 | Phase guides table lists `guide-arch`/`guide-design`/`guide-plan`/`guide-ship` (all Wave-3 deleted) |
| 6 | `docs/architecture/overview.md` L123 | P0 | **Inverted rule**: "any doc that still says 'three phases' or 'four phases' is stale" — but v4 IS four stages. Misleading future maintainers. |
| 7 | `docs/architecture/workflow-phases.md` (entire file) | P0 | 5-phase model + mermaid + entry skills `guide-arch`/`guide-design`/`guide-plan`/`guide-ship`; L110 wrong state-file path (`.rdd-verifier-state.json` vs canonical `verifier/<change>.json`); L117 references deprecated `ac-verifier` |
| 8 | `skills/rdd-arch/SKILL.md` L34 | P0 | **Bug**: "此 skill 从 `rdd-arch` 重命名为 `rdd-arch`" — self-reference, should be `guide-arch → rdd-arch` |
| 9 | `skills/rdd-arch/SKILL.md` L40, 64-69, 74-80 | P0 | 5-stage model + table + workflow diagram |
| 10 | `docs/architecture/README.md` L17 | P1 | "Five-phase arch → design → plan → ship → verify + handoffs (v3.0+ per ADR-0034)" |
| 11 | `USAGE.md` L19, 26-28, 65-75, 173, 333+ | P1 | 5-stage model + repeated `rdd-builder` for Plan/Ship + `guide-plan`/`guide-ship` in state-file writer column |
| 12 | `CHANGELOG.md` L17-18 | P1 | `[Unreleased]` rdd-verifier entry still says "5th phase" (historical) — leave but clarify v4 placement |
| 13 | `AGENTS.md` (multiple sections) | P1 | Round A/B/C inline-bash extraction sections still reference `guide-design`/`guide-plan`/`guide-ship` (renamed since); "guide-spec 已移除" stale note |

**Why this matters**:

- **New users** reading `README.md` first will see "五阶段" and assume `rdd-builder` runs 3 phases — then look for non-existent `guide-plan` / `guide-ship` skills.
- **Architects / contributors** reading `docs/architecture/overview.md` will see the inverted rule at L123 and possibly add MORE drift.
- **The architectural docs are explicitly self-described as "the current-architecture snapshot"** (per `docs/architecture/README.md` Update Convention) — they MUST be regenerated on every ADR that changes the architecture.

## What Changes

### Doc edits (P0 — must land)

1. **`README.md`** (5 hunks):
   - L62-64 "使用流程" sublist: split Plan 端 to `rdd-planner`, keep Ship 端 as `rdd-builder`
   - L105 H3 header: "v3.0 新特性" → rename to "v4.0+ 当前架构"; change "五阶段" → "四阶段（4 阶段）"
   - L110-113 phase table: collapse to 4 rows (`rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier`)
   - L117 skill chain: `rdd-arch → rdd-planner → rdd-builder → rdd-verifier` (4 links, not 5)
   - L399-406 directory tree: replace 3× `rdd-builder/SKILL.md` lines with `rdd-planner/SKILL.md` + `rdd-builder/SKILL.md` + `rdd-quick/SKILL.md`; add `rdd-quick` row

2. **`docs/architecture/overview.md`** (6 hunks):
   - L5: "five-phase architecture" → "four-stage architecture (v4.0+ per ADR-0043)"
   - L9: "27 user-invocable skills (5 phase guides + 22 sub-skills)" → "5 stage skills (`rdd-arch`/`rdd-planner`/`rdd-builder`/`rdd-verifier`/`rdd-quick` bypass) + 22 sub-skills"
   - L17-22 mermaid: collapse `design` and `plan` into single `rdd-planner` + `rdd-builder` box; add `rdd-quick` as bypass arrow
   - L66-70 phase guides table: 4 canonical entries (rdd-arch, rdd-planner, rdd-builder, rdd-verifier) + 1 bypass entry (rdd-quick); remove all `guide-*` rows
   - L123 inverted rule: rewrite as "any doc that still says 'five phases' (the v3 model) is stale; v4 is four stages per ADR-0043"
   - L121: replace v2.0 3-phase history with v3.0 5-phase → v4.0 4-stage lineage

3. **`docs/architecture/workflow-phases.md`** (rewrite):
   - Title + L3: "five phases" → "four stages (v4.0+, per ADR-0043/0044)"
   - L5-13 mermaid: arch → planner → builder → verifier (4 nodes), with `rdd-quick` bypass arrow from any node
   - L20-127 phase sections: replace `guide-arch`/`guide-design`/`guide-plan`/`guide-ship` with `rdd-arch`/`rdd-planner`/`rdd-builder`/`rdd-verifier`; merge old "design" and "plan" sections under "Stage 2 — planner" + "Stage 3 — builder (6-phase internal)"
   - L110: `.rdd/state/.rdd-verifier-state.json` → canonical `.rdd/state/verifier/<change>.json` (per `rdd-verifier/SKILL.md` State Files Owned table)
   - L117: drop `ac-verifier` reference (deprecated per ADR-0045)
   - L119-127 Phase Recap: 4 rows not 5

4. **`skills/rdd-arch/SKILL.md`** (3 hunks + 1 bug):
   - L34 (bug fix): "此 skill 从 `rdd-arch` 重命名为 `rdd-arch`" → "此 skill 从 `guide-arch` 重命名为 `rdd-arch`"
   - L40: "五阶段架构" → "四阶段架构（v4.0+，per ADR-0043/0044）"
   - L64-69 sub-skill table: 4 stage rows + 1 bypass row; drop `guide-design`/`guide-plan`/`guide-ship` rows
   - L74-80 workflow diagram: 4 stages, not 5

### Doc edits (P1 — should land)

5. **`docs/architecture/README.md`** L17: same fix as #2 first item

6. **`USAGE.md`** (3 hunks):
   - L19 H2: "五阶段架构" → "四阶段架构（v4.0+）"
   - L26-28 phase table: collapse Plan 端 to `rdd-planner`; Ship 端 stays `rdd-builder`
   - L65-75 state-file writer column: replace `guide-plan`/`guide-ship` with `rdd-planner`/`rdd-builder`
   - L173 "Arch 5 + Plan 4 子阶段" → "Arch 5 + Planner 4 + Builder 6 子阶段"

7. **`AGENTS.md`** (Round A/B/C sections + D3 design-pre-created section):
   - Round A/B/C inline-bash extraction sections: rename `rdd-arch.md` / `guide-plan.md` / `guide-ship.md` references to their v4 canonical names
   - "guide-spec 已在 v2.0 移除"段: keep (historical note still valid)
   - "D3 design-pre-created 协同 (v2.2+)"段: clarify `rdd-planner` is the current owner, not `guide-design`

### Doc-contract test (P0 — must land)

8. **New `tests/integration/test_v4_doc_drift_contracts.bats`** (extends `tests/integration/test_doc_contracts.bats` or new file):
   - Test 1: `README.md` does NOT contain "五阶段" or "five-phase" (v3 stale wording)
   - Test 2: `README.md` does contain `rdd-planner` AND `rdd-quick` in directory tree
   - Test 3: `docs/architecture/overview.md` does NOT contain "five-phase" or "5 phases"
   - Test 4: `docs/architecture/overview.md` L123 region does NOT contain the inverted rule (or contains the corrected version)
   - Test 5: `docs/architecture/workflow-phases.md` does NOT contain `guide-arch` / `guide-design` / `guide-plan` / `guide-ship` (as skill names)
   - Test 6: `skills/rdd-arch/SKILL.md` L34 does NOT contain "从 `rdd-arch` 重命名为 `rdd-arch`" (the self-reference bug)
   - Test 7: `skills/rdd-arch/SKILL.md` does NOT contain "五阶段"
   - Test 8: `skills/` directory has exactly 5 `rdd-*` skill subdirs + 0 `guide-*` skill subdirs (excludes `guide/` which is the standalone recommender)
   - Test 9: `docs/architecture/workflow-phases.md` L110 region references `verifier/<change>.json` (canonical) not `.rdd-verifier-state.json`
   - Test 10: `docs/architecture/workflow-phases.md` does NOT contain "ac-verifier" as a non-historical reference

### Out of Scope

- AGENTS.md history sections (Round A/B/C) are P1; can be split into a follow-up `sync-agents-md-round-c-v4` if scope creep
- CHANGELOG.md historical entries are immutable (git blame preservation); only clarify v4 placement in a new `[Unreleased]` sub-section
- Code changes — none, this is documentation-only
- Skill metadata (frontmatter `name`, `version`) — unchanged
- Tests directory (no Python unit tests added; new bats tests only)

## Capabilities

- capability-v4-doc-architecture-sync

## Acceptance

- AC-1: `README.md` "使用流程" sublist shows 4 stage skills (rdd-arch / rdd-planner / rdd-builder / rdd-verifier) + 1 bypass (rdd-quick), with correct phase labels (Arch/Planner/Builder/Verifier) and 0 references to `guide-*` names
- AC-2: `docs/architecture/overview.md` "five-phase" and "5 phases" strings are 0; "four-stage" and "v4.0+" strings are ≥3; phase guides table has exactly 4 canonical entries + 1 bypass entry
- AC-3: `docs/architecture/workflow-phases.md` mermaid diagram has 4 main nodes + 1 bypass arrow; entry-skill column references `rdd-arch`/`rdd-planner`/`rdd-builder`/`rdd-verifier` only
- AC-4: `skills/rdd-arch/SKILL.md` L34 reads "此 skill 从 `guide-arch` 重命名为 `rdd-arch`（per D1a 渐进策略）"; L40-80 describes 4-stage v4 model
- AC-5: `docs/architecture/overview.md` L123 reads: "any doc that still says 'three phases' (the v2.0 model) or 'five phases' (the v3.0 model) is stale; v4 is four stages per ADR-0043"
- AC-6: New `tests/integration/test_v4_doc_drift_contracts.bats` has 10 test cases; all 10 pass on the patched tree; all 10 FAIL on the pre-patch tree (verifies the test is meaningful)
- AC-7: `USAGE.md` (P1) H2 header reads "四阶段架构 (rdd-arch → rdd-planner → rdd-builder → rdd-verifier)"; state-file writer column references rdd-planner / rdd-builder (not guide-plan / guide-ship)
- AC-8: `docs/architecture/README.md` (P1) L17 reads "Four-stage arch → planner → builder → verifier + handoffs (v4.0+ per ADR-0043)"
- AC-9: `./test.sh --full --regression` shows no new failures beyond the existing `KNOWN_FAILURES.txt` baseline
- AC-10: `grep -rn "guide-design\|guide-plan\|guide-ship" docs/architecture/` returns 0 hits (architectural docs are clean)
- AC-11: `grep -rn "guide-design\|guide-plan\|guide-ship" README.md USAGE.md` returns 0 hits (user-facing docs are clean, excluding code blocks that quote historical changelog)

## Specs

Per D3 spec-delta 协同, spec.md 落 `openspec/changes/fix-doc-drift-v4-architecture/specs/doc-architecture-v4-sync/spec.md` (path B — change-local, not `openspec/specs/` archive). 8 Requirement blocks with 18 Scenarios total.
