# Draft: HydraForge Multi-Stage Project Organization Plan

## User's Confirmed Decisions

### Q1: Execution mode
- User asked Oracle for advice; Oracle unavailable → applying Metis+self analysis
- **DECISION: Hybrid B+A** — one umbrella OpenSpec change for Stages 1-2 (cleanup); separate changes for Stages 3, 4, 5
- All amend the existing `tech-debt-cleanup` capability spec (no new base capabilities)

### Q2: Context model
- **DECISION: Implement LayeredContext** (consistent with dsl.md §4.1 and ADR-0008)
- Code → spec alignment, not the other way around
- Stage 3 of the plan

### Q3: engine.h timing
- **DECISION: Last stage, standalone** (Stage 4)
- Touches everything; must follow Context model decision

### Q4: agenticdsl/ subtree
- **DECISION: Promote to sibling `docs/proposals/`**
- Stops semantic confusion between "approved decisions" and "undecided proposals"

## Verified Current State (Jun 12, 2026)

### What's been done (from git log + audits)
- ✅ 2026-06-09 `docs-code-alignment-fixes` archived — 13 ADRs marked deprecated, dead links fixed
- ✅ 2026-06-10 `tech-debt-and-doc-cleanup` archived — log.h facade, 5 orphan lib/ subgraphs deleted, src/modules/prompts.yaml removed, LLMCallNode dead code removed, IExecutionPolicy 3 modes implemented, CostCollector integrated into BudgetController
- ✅ C1 migration (2026-06-08) — IInteractionBus shipped, public headers moved to `include/agenticdsl/`
- ✅ IExecutionPolicy fully implemented (8 methods in headers; 18-21 line .cpp for requires_approval)
- ✅ 13 deprecated ADRs marked in-file but **NOT physically moved to archive**

### What still needs work (consolidated issue list)
1. ADR placeholders 0029/0035 (466B stubs) + missing numbers 0024-0028
2. Phantom ADR references in adr-0030 (→0025) and adr-0031 (→0027)
3. Status vocabulary drift (3 schemes coexist; ADR-0008 contradiction: file says "已批准", README says "❌未实施")
4. Stale `relationships.md` (last updated 2026-05-28, wrong about 0022/0034/placeholders)
5. 13 deprecated ADRs still in active tree (should be in `docs/archive/adr/`)
6. SPECS-ALIGNMENT.md self-admits 3 of 4 "✅已完成" claims are stale
7. Spec triplet duplication: stdlib × 3 (dsl-lib, phase2, stdlib) + memory × 3 (memory, phase2 §memory, dsl §10.3)
8. Context model conflict: flat `unordered_map` (code) vs LayeredContext (dsl.md §4.1) vs ADR-0008 "❌未实施"
9. `engine.h` directly includes 6 module headers (coupling hub)
10. `NodeExecutor` embeds `MarkdownParser` as member (tight coupling)
11. agenticdsl/ subtree semantics mixed with numbered ADRs in same root
12. No `compile_commands.json` / `CMakePresets.json` / CI — manual verification only
13. AGENTS.md stale (some items removed; some items from old `prompts.yaml` era)
14. 6.5 phase-folder inconsistency (Phase 1/4/6/9 lack folders)

## Stage Structure (5 stages, sequenced by hard dependencies)

### Stage 1 — Cleanup Foundation (umbrella OpenSpec change)
**OpenSpec change:** `docs-and-arch-cleanup-foundation` (amends `tech-debt-cleanup/spec.md`)
**Duration:** 3-5 days
**Tasks:**
- 1.1 Delete placeholder ADRs 0029, 0035; add new ADR numbers 0024-0028 to README (or accept gaps)
- 1.2 Fix phantom refs: adr-0030 (→ADR-0025), adr-0031 (→ADR-0027)
- 1.3 Unify status vocabulary to single scheme (6 tags: ✅🟡❌⛔🔍📋)
- 1.4 Reconcile ADR-0008 contradiction (file says 已批准, README says ❌)
- 1.5 Regenerate AGENTS.md from current ground truth
- 1.6 Verify exit: `cmake --build build && ctest` + status vocabulary check

### Stage 2 — Spec Consolidation (part of umbrella change)
**OpenSpec change:** same as Stage 1 (`docs-and-arch-cleanup-foundation`)
**Duration:** 1-2 weeks
**Depends on:** Stage 1 (status vocab unified first)
**Tasks:**
- 2.1 Promote `docs/adr/agenticdsl/` to `docs/proposals/`
- 2.2 Add reverse references from 18 ADRs → proposals
- 2.3 Move 13 deprecated ADRs to `docs/archive/adr/`
- 2.4 Merge 3 stdlib specs → 1 `docs/specs/stdlib-v3.10.md` (drop `phase2-standard-library.md`, fold `stdlib.md` content)
- 2.5 Merge 2 memory specs → 1 (keep `memory.md` content, drop `phase2-standard-library.md` §memory, align with `dsl.md` §10.3 namespace)
- 2.6 Reconcile `layer0.md` vs `architecture.md` 8-layer vs 3-layer model
- 2.7 Update `SPECS-ALIGNMENT.md` §变更追踪 — re-audit and reset all ✅ boxes

### Stage 3 — Context Model: Implement LayeredContext
**OpenSpec change:** `layered-context-implementation` (amends `tech-debt-cleanup/spec.md`)
**Duration:** 1-2 weeks
**Depends on:** Stage 1 (vocab fixed), Stage 2 (spec sources unified)
**Tasks:**
- 3.1 Define `LayeredContext` C++ struct in `include/agenticdsl/types/context.h`
- 3.2 Refactor `src/core/types/context.h` to either be a typedef alias or remove
- 3.3 Update all callers (TopoScheduler, NodeExecutor, ToolRegistry, SimpleCognitiveOrchestrator) to use LayeredContext API
- 3.4 Add `tests/test_layered_context.cpp` (≥5 test cases per layer L1-L5)
- 3.5 Update ADR-0008 status to ✅ Implemented
- 3.6 Update dsl.md §4.1 (no content change needed if spec is source of truth)
- 3.7 Verify: `ctest` passes, no flat Context in code, AGENTS.md updated

### Stage 4 — engine.h Decoupling (Interface Inversion)
**OpenSpec change:** `core-interface-inversion` (amends `tech-debt-cleanup/spec.md`)
**Duration:** 2-3 weeks
**Depends on:** Stage 3 (Context model decided)
**Tasks:**
- 4.1 Define `i*` interfaces in `include/agenticdsl/contract/`: IScheduler, IParser, IExecutionPolicy (existing), IInteractionBus (existing)
- 4.2 Add CMake INTERFACE include set so `include/agenticdsl/agenticdsl.h` is a public header
- 4.3 Refactor `TopoScheduler` to inherit `IScheduler`; same for `MarkdownParser` → `IParser`
- 4.4 Refactor `engine.h` to only include `core/agenticdsl.h` + `contract/i*` (no `modules/`)
- 4.5 Refactor `NodeExecutor` to hold `IParser*` (not embed `MarkdownParser` by value)
- 4.6 Verify all 6 examples build + all 24 tests pass
- 4.7 New ADR-0037 (or update ADR-0019 §1.4): mark coupling as resolved

### Stage 5 — Build System & CI
**OpenSpec change:** `build-system-bootstrap` (amends `tech-debt-cleanup/spec.md`)
**Duration:** 1 week
**Depends on:** None of above (orthogonal); can start anytime after Stage 1
**Tasks:**
- 5.1 Add `compile_commands.json` generator hook to root `CMakeLists.txt` (`-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` + symlink)
- 5.2 Add `CMakePresets.json` with debug/release/asan/tsan presets
- 5.3 Add `.github/workflows/ci.yml` with: cmake configure + build + ctest + clang-tidy
- 5.4 Add `tools/adr_lint.py` for ADR frontmatter validation
- 5.5 Add `tools/adr_relationships.py` to auto-generate `relationships.md` from ADR frontmatter
- 5.6 Verify CI green on main; add CI badge to README

## Total Effort: 5-9 weeks
## Critical Path: Stage 1 → Stage 2 → Stage 3 → Stage 4 (Stage 5 parallel)
## Parallelizable: Stage 5 (Build/CI) can run in parallel with Stage 3 or 4

## Hard Dependencies (D-rules)
- D1: Status vocab unified BEFORE any spec consolidation
- D2: Spec consolidation BEFORE Context model code (single source of truth for spec)
- D3: Context model decided BEFORE engine.h decoupling (engine.h exposes Context)
- D4: `i*` interfaces defined BEFORE callers can be refactored
- D5: All stages must end with `cmake --build && ctest` PASS + targeted grep checks
- D6: `examples/` builds must succeed at end of every code-touching stage
- D7: AGENTS.md regeneration is LAST (Stage 1 only regenerates metadata, code changes update it later)

## OpenSpec Structure (Hybrid B+A)

```
openspec/changes/
├── 2026-06-XX-docs-and-arch-cleanup-foundation/    # Stages 1+2
│   ├── proposal.md
│   ├── design.md
│   ├── tasks.md            # 13+ tasks across Stages 1+2
│   └── specs/
│       └── tech-debt-cleanup/
│           └── spec.md     # AMEND existing, not new capability
├── 2026-06-XX-layered-context-implementation/      # Stage 3
├── 2026-06-XX-core-interface-inversion/            # Stage 4
└── 2026-06-XX-build-system-bootstrap/              # Stage 5
```

## Open Questions / Defaults Applied
- Naming of `docs/proposals/` — DEFAULT, override if user wants different
- Whether to keep phase-2/3/5/7/8/ subdirs in `docs/adr/` once 13 ADRs are moved to archive — DEFAULT: keep empty dirs as historical breadcrumbs
- Whether to add `openspec/specs/memory-extension/spec.md` capability when implementing LayeredContext — DEFAULT: extend `tech-debt-cleanup/spec.md`, do not create new capability
