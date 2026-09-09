# Design — fix-doc-drift-v4-architecture

## 1. Context

The v4 stage-merge (ADR-0043, 2026-09-04) collapsed 5 phases (arch → design → plan → ship → verify) into 4 stages (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`) and added `rdd-quick` as a small-change bypass path (ADR-0047, 2026-09-07). Wave 1–3 (2026-09-04 ~ 2026-09-05) executed the code migration; Wave 3 hard-removed the `guide-design`/`guide-plan`/`guide-ship` skill directories per ADR-0044.

However, **the user-facing and architectural documentation was not regenerated alongside the code changes**. The `docs/architecture/README.md` self-describes the doc set as "the current-architecture snapshot" with an "Update Convention" requiring regeneration when a new skill / handoff file / ADR is added. This convention was not followed for ADR-0043 / ADR-0044 / ADR-0047, leaving ~7 files describing the pre-v4 5-phase model.

## 2. Problem

A 2026-09-09 code-vs-doc audit (manual review by the author of this proposal) identified 13 drift sites across 7 files, including:

- **README.md L62-64**: New users following the "使用流程" sublist will see `rdd-builder` listed for both Plan 端 and Ship 端 — there is no way to know `rdd-planner` is a separate skill.
- **README.md L105, 117**: The "v3.0 新特性" section header AND the migration chain both say "五阶段" (five phases), directly contradicting the v4 banner at L3 ("四阶段架构").
- **docs/architecture/overview.md L123**: A **reversed rule** warns that "any doc that still says 'three phases' or 'four phases' is stale" — but v4 IS four stages. A future maintainer reading this rule will conclude that v4 itself is wrong, opening the door for v3-style regressions.
- **docs/architecture/workflow-phases.md L110**: References `.rdd/state/.rdd-verifier-state.json`, but the canonical path in `rdd-verifier/SKILL.md` is `.rdd/state/verifier/<change>.json` — a path drift that would send anyone wiring up verifier integration down a dead end.
- **skills/rdd-arch/SKILL.md L34**: Self-reference bug: "此 skill 从 `rdd-arch` 重命名为 `rdd-arch`" — clearly should be `guide-arch → rdd-arch`. The reader cannot recover the rename history.

The drift is not just cosmetic: the 5-phase "5 node" mermaid in `overview.md` and the 5-row phase table in `README.md` are exactly the diagrams and tables used in onboarding decks, blog posts, and the rdd-workflow-e2e external testbed's README. The drift propagates.

## 3. Decision

Adopt a **two-pronged fix**: (a) surgical edits to the 7 drift sites, (b) a doc-contract test that locks the corrected state and fails on regression.

### 3.1 Why surgical edits, not a full architecture doc rewrite

- **Scope discipline**: The drift is 7 files, ~30 specific lines, all expressing the same single fact (the architecture is v4 4-stage, not v3 5-phase). A full rewrite would re-license every section of the docs, increasing review surface and risk of accidental changes.
- **Test-driven verification**: The new doc-contract test pins each drift site to a grep pattern. After the surgical edits land, the test passes; if any drift site regresses, the test fails. This gives us a tighter correctness contract than a free-form rewrite.
- **AGENTS.md history preservation**: `AGENTS.md` contains accurate per-Phase-2-refactor history (Round A/B/C inline-bash extraction sections), where the `guide-*` references are historically correct. A wholesale rewrite would lose this. Instead, only the "当前架构" header section and the 4 "Round *" sub-section summaries need adjustment.

### 3.2 Why a doc-contract test, not just a human review

- **Determinism**: The `overview.md` L123 inverted rule is exactly the kind of bug that survives human review (it reads as a "rule about phase numbers" and a reviewer may not notice the inversion). A grep test on the surrounding context catches it.
- **CI integration**: The existing `tests/integration/test_doc_contracts.bats` already runs in CI per AGENTS.md "CI 在 `.github/workflows/test.yml`" section. Adding 10 cases to that file (or a sibling `test_v4_doc_drift_contracts.bats`) gives us the regression lock for free.
- **Cost**: 10 grep assertions ≈ 60 lines of bats, 0 new dependencies, no fixtures. Fits in P0 budget.

### 3.3 Why AC-6 verifies the test fails on pre-patch tree

A doc-contract test that passes on both pre-patch AND post-patch trees is meaningless (it doesn't verify the fix is applied). AC-6 mandates running the test against a pre-patch snapshot (e.g., `git stash` + `./test.sh --bats tests/integration/test_v4_doc_drift_contracts.bats`) and confirming 10/10 fail. This is a standard "test-the-test" technique that the rdd-workflow test conventions do not currently enforce, so we add it as an explicit AC.

### 3.4 Why split out AGENTS.md (P1) and CHANGELOG.md (out of scope)

- **AGENTS.md**: 13 drift sites identified, but most are in deep history sections (Round A/B/C bash extraction commentary). Touching them in the same change triples review surface for marginal value. Recommend a follow-up `sync-agents-md-round-c-v4` if reviewers want exhaustive AGENTS.md coverage. The current change covers the AGENTS.md **"当前架构" 4-stage banner** and the **D3 design-pre-created** section (which references the now-renamed `rdd-planner` ownership).
- **CHANGELOG.md**: Historical entries are immutable by repo convention (they preserve git blame for shipped changes). The rdd-verifier entry dated 2026-08-26 says "5th phase" because it was correct in the v3 5-phase era. We do NOT edit it. A new `[Unreleased] v4 stage-merge` section can be added in the same change to clarify the v4 placement (rdd-verifier is the 4th stage, not the 5th).

## 4. Scope Boundaries

### In scope (this change)

- README.md, USAGE.md, AGENTS.md (banner sections only), CHANGELOG.md (new entry only)
- docs/architecture/{overview,workflow-phases,README}.md
- skills/rdd-arch/SKILL.md (3 sections + 1 bug fix)
- New `tests/integration/test_v4_doc_drift_contracts.bats` (or extend `test_doc_contracts.bats`)

### Out of scope (deferred to follow-up changes)

- AGENTS.md Round A/B/C inline-bash extraction commentary (P1, large surface, low signal)
- AGENTS.md "guide-spec 已在 v2.0 移除"段 (historical note, technically still correct)
- Per-skill `SKILL.md` files other than `rdd-arch` (rdd-planner, rdd-builder, rdd-verifier, rdd-quick are already correct per 2026-09-09 audit)
- Spec archive (`openspec/specs/`) updates — those are managed by the per-skill path; this change only updates the change-local `specs/doc-architecture-v4-sync/spec.md`
- Architectural decision records (ADR-0043/0044/0047 are already correct; no ADR changes)
- Code logic (this is documentation-only)

## 5. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Surgical edit accidentally rewrites a historically important section (e.g., AGENTS.md Round A history) | Low | Medium | Strict P0/P1 split: AGENTS.md Round sections are P1 (separate change); surgical hunks are 5-15 lines each, fully reviewable in PR |
| Doc-contract test passes on pre-patch tree (test is meaningless) | Low | High | AC-6 mandates pre-patch verification; reviewer runs `git stash` + test manually before approving |
| New `[Unreleased]` CHANGELOG section conflicts with in-flight `remove-ac-verifier-completely` entry | Low | Low | Place the new entry as a sibling paragraph under the existing `[Unreleased]` header; do not edit the existing rdd-verifier entry |
| Mermaid diagram edit breaks the rendered SVG in GitHub | Low | Low | Test render locally before commit; mermaid syntax unchanged (still `graph LR` with `A[label] --> B[label]`) |
| `rdd-planner` description in README.md vs `rdd-planner/SKILL.md` disagrees on stage label (e.g., "Planner" vs "Design") | Low | Medium | Use the canonical label from the skill's own `role.title` field: `rdd-planner`'s role.title is "Planner (路线图 + 提案治理者)" → use "Planner" everywhere |

## 6. Test Strategy

### Doc-contract test (10 cases)

```bash
# Run new test against post-patch tree
bats tests/integration/test_v4_doc_drift_contracts.bats
# Expected: 10 pass

# Run against pre-patch tree (regression lock verification)
git stash
bats tests/integration/test_v4_doc_drift_contracts.bats
# Expected: 10 fail (confirms test detects drift)
git stash pop
```

### Existing test suite

```bash
./test.sh --full --regression
# Expected: no new failures beyond tests/KNOWN_FAILURES.txt baseline
```

If `rdd-doctor --category docs-consistency` (per archived `rdd-doctor-docs-consistency` proposal) is implemented, it should also pass after this change. We do not block on it (it's a follow-up).

## 7. References

- ADR-0043 (v4 stage-merge) — the canonical 4-stage model
- ADR-0044 (Wave 3 hard removal) — the guide-* skill removal
- ADR-0047 (rdd-quick bypass path) — the second path
- `docs/migration-v3-to-v4.md` — the v3→v4 mapping table (already correct)
- `docs/architecture/README.md` "Update Convention" — the convention this change enforces
- `tests/integration/test_doc_contracts.bats` — the existing doc-contract pattern we extend
- Archived `rdd-doctor-docs-consistency.md` proposal — adjacent (but separate) doc-consistency work

## 8. Implementation Order (executor's guide)

1. Land P0 doc edits as 1 commit per file (7 commits, 1-2 lines per hunk on average).
2. Add the doc-contract test (1 commit).
3. Verify AC-6 by stashing the doc edits and running the test (manual).
4. Land P1 doc edits as 1 commit per file (3 commits).
5. Land CHANGELOG.md clarification entry (1 commit).
6. Run `./test.sh --full --regression` to confirm no new failures.
7. Add row to `proposal-approved.md` "## 已实施" table.
8. Archive the change.

Total: ~13 commits, all small, all reviewable in <5 minutes each.
