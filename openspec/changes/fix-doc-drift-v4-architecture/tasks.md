## Tasks

### Phase A — P0 doc edits (must land in one PR)

- [x] **Task 1: README.md — "使用流程" sublist (L62-64)**
  - Modify: `README.md` L62-64
  - Diff: split `rdd-builder` Plan 端 into `rdd-planner`; keep `rdd-builder` Ship 端; add `rdd-quick` as bypass row
  - Test: AC-1
  - Commit: TBD

- [x] **Task 2: README.md — v3.0 新特性 section (L105, 110-117)**
  - Modify: `README.md` L105 H3 header (rename v3.0 → v4.0+), L110-117 phase table (4 rows) + skill chain (4 links)
  - Diff: "五阶段" → "四阶段（4 阶段）"; collapse 5-row phase table to 4 rows; skill chain `rdd-arch → rdd-planner → rdd-builder → rdd-verifier`
  - Test: AC-1, AC-2 indirectly
  - Commit: TBD

- [x] **Task 3: README.md — directory tree (L399-406)**
  - Modify: `README.md` L399-406
  - Diff: replace 3× `rdd-builder/SKILL.md` lines with `rdd-planner/SKILL.md` + `rdd-builder/SKILL.md` + `rdd-quick/SKILL.md`; ensure `rdd-quick` row exists
  - Test: AC-1 (directory tree)
  - Commit: TBD

- [x] **Task 4: docs/architecture/overview.md — text + mermaid (L5, 9, 17-22)**
  - Modify: `docs/architecture/overview.md`
  - Diff: "five-phase" → "four-stage" (2 occurrences); "27 user-invocable skills" → "5 stage skills + 22 sub-skills"; mermaid 5-node → 4-node with rdd-quick bypass arrow
  - Test: AC-2
  - Commit: TBD

- [x] **Task 5: docs/architecture/overview.md — phase guides table (L66-70)**
  - Modify: `docs/architecture/overview.md` L66-70
  - Diff: 4 canonical rows (rdd-arch, rdd-planner, rdd-builder, rdd-verifier) + 1 bypass row (rdd-quick); remove `guide-*` rows
  - Test: AC-2
  - Commit: TBD

- [x] **Task 6: docs/architecture/overview.md — inverted rule (L123)**
  - Modify: `docs/architecture/overview.md` L121, L123
  - Diff: L123 read "any doc that still says 'three phases' (the v2.0 model) or 'five phases' (the v3.0 model) is stale; v4 is four stages per ADR-0043"; L121 mention v3 5-phase history
  - Test: AC-5
  - Commit: TBD

- [x] **Task 7: docs/architecture/workflow-phases.md — entire file rewrite**
  - Modify: `docs/architecture/workflow-phases.md` (full file)
  - Diff: 4 stages (arch → planner → builder → verifier) + 1 bypass; rename entry skills to `rdd-*`; merge old "design" + "plan" sections; L110 path `.rdd/state/.rdd-verifier-state.json` → `.rdd/state/verifier/<change>.json`; L117 drop ac-verifier
  - Test: AC-3, AC-10 (no guide-* in docs/architecture/)
  - Commit: TBD

- [x] **Task 8: skills/rdd-arch/SKILL.md — L34 self-reference bug**
  - Modify: `skills/rdd-arch/SKILL.md` L34
  - Diff: "此 skill 从 `rdd-arch` 重命名为 `rdd-arch`" → "此 skill 从 `guide-arch` 重命名为 `rdd-arch`（per D1a 渐进策略）"
  - Test: AC-4
  - Commit: TBD

- [x] **Task 9: skills/rdd-arch/SKILL.md — L40, L64-69, L74-80 (5-stage model)**
  - Modify: `skills/rdd-arch/SKILL.md` L40, L64-69, L74-80
  - Diff: "五阶段架构" → "四阶段架构（v4.0+，per ADR-0043/0044）"; sub-skill table 5 → 4 stage rows + 1 bypass row; workflow diagram 5 nodes → 4 nodes
  - Test: AC-4
  - Commit: TBD

### Phase B — doc-contract test (P0, locks P0 edits)

- [x] **Task 10: New tests/integration/test_v4_doc_drift_contracts.bats**
  - Create: `tests/integration/test_v4_doc_drift_contracts.bats`
  - Contents: 10 @test cases per AC-6 spec (1-10)
  - Includes: pre-patch-fail verification sub-test (stashes 7 files, runs bats, expects 10 fail; un-stashes)
  - Test: AC-6
  - Commit: TBD

### Phase C — P1 doc edits (can split to follow-up if scope creep)

- [x] **Task 11: docs/architecture/README.md (L17)**
  - Modify: `docs/architecture/README.md` L17
  - Diff: "Five-phase arch → design → plan → ship → verify + handoffs (v3.0+ per ADR-0034)" → "Four-stage arch → planner → builder → verifier + handoffs (v4.0+ per ADR-0043)"
  - Test: AC-8
  - Commit: TBD

- [x] **Task 12: USAGE.md — H2 header (L19)**
  - Modify: `USAGE.md` L19
  - Diff: "### 五阶段架构 (arch → design → plan → ship → verify)" → "### 四阶段架构 (rdd-arch → rdd-planner → rdd-builder → rdd-verifier, v4.0+ per ADR-0043)"
  - Test: AC-7
  - Commit: TBD

- [x] **Task 13: USAGE.md — phase table (L26-28)**
  - Modify: `USAGE.md` L26-28
  - Diff: Plan 端 → `rdd-planner`; Ship 端 stays `rdd-builder`
  - Test: AC-7
  - Commit: TBD

- [x] **Task 14: USAGE.md — state-file writer column (L65-75)**
  - Modify: `USAGE.md` L65-75
  - Diff: `guide-plan` → `rdd-planner`; `guide-ship` → `rdd-builder`
  - Test: AC-7
  - Commit: TBD

- [x] **Task 15: USAGE.md — L173 + L333+ phase numbering**
  - Modify: `USAGE.md` L173, L333+
  - Diff: "Arch 5 + Plan 4 子阶段" → "Arch 5 + Planner 4 + Builder 6 子阶段"; Ship 端 phase numbering 1, 1.5, 2, 2.5, 3, 4, 5 → 2, 3 (since these are now rdd-builder internal P0-P3)
  - Test: AC-7
  - Commit: TBD

- [x] **Task 16: AGENTS.md — current-architecture banner (per ADR-0043)**
  - Modify: `AGENTS.md` "## 架构" + "## 关键目录" sections
  - Diff: ensure 4-stage banner is consistent; D3 design-pre-created段 clarify `rdd-planner` is current owner
  - Test: AC-11
  - Commit: TBD

### Phase D — CHANGELOG clarification (P1, non-historical)

- [x] **Task 17: CHANGELOG.md — new [Unreleased] v4 stage-merge sub-section**
  - Modify: `CHANGELOG.md`
  - Diff: add new sub-section under `[Unreleased]`: "### v4 stage-merge (2026-09-04): 四阶段架构 rdd-arch → rdd-planner → rdd-builder → rdd-verifier (per ADR-0043/0044); rdd-quick bypass (per ADR-0047); docs updated per fix-doc-drift-v4-architecture"
  - Test: N/A (CHANGELOG not covered by doc-contract test)
  - Commit: TBD

### Phase E — verification + archive

- [x] **Task 18: AC-6 verification (pre-patch fail check)**
  - Run: `git stash --keep-index` after Tasks 1-9 land, then `bats tests/integration/test_v4_doc_drift_contracts.bats` → expect 10 fail
  - Restore: `git stash pop`
  - Commit: not applicable (manual verification step)
  - Test: AC-6

- [x] **Task 19: Full regression gate**
  - Run: `./test.sh --full --regression`
  - Expect: no new failures beyond `tests/KNOWN_FAILURES.txt` baseline
  - Test: AC-9
  - Commit: not applicable (test run only)

- [x] **Task 20: Update proposal-approved.md "## 已实施" table**
  - Modify: `proposal-approved.md`
  - Diff: add row `[fix-doc-drift-v4-architecture](.rddf/improvements/fix-doc-drift-v4-architecture.md) | P0 | 2026-09-09 | 已实施`
  - Test: N/A
  - Commit: TBD

- [x] **Task 21: Archive the change**
  - Run: `openspec archive fix-doc-drift-v4-architecture --yes`
  - Effect: moves `openspec/changes/fix-doc-drift-v4-architecture/` to `openspec/changes/archive/2026-09-09-fix-doc-drift-v4-architecture/`
  - Test: N/A
  - Commit: TBD (archive auto-commit per AGENTS.md "Archive Auto-Commit")
