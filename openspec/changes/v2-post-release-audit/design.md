## Context

The v2.0.0-beta release (2026-06-26) shipped code for ADR-0002 through ADR-0008 (state vector, event log, gate, loop engine, detectors, actions, interaction modes, human-in-loop nodes, tribunal, memory, session, agents, sanitizer) along with 169 Python tests. However, the documentation layer was last updated during design phase (mid-June) and was never synchronized with implementation. Separately, the test quality audit found gaps (tautological assertion, untested modules) that should be addressed before the next release.

## Goals / Non-Goals

**Goals:**
- Synchronize all documentation with current v2.0 code reality
- Fix the fictional `spec-workflow` CLI in migration guide
- Fix tautological assertion in test_lock.py
- Add unit tests for modules with zero coverage
- Add CI assertion quality gate
- Promote orphaned spec directories to openspec/specs/

**Non-Goals:**
- Modifying any production Python code (zero behavioral changes)
- Implementing any new features
- Adding integration or bats tests (coverage gap is unit-test level only)
- Implementing the fictional CLI described in migration guide

## Decisions

### Decision 1: One change, not multiple

- **Why**: All fixes are manifestations of the same root cause (v2.0 doc-reality gap + test quality). Tracking them in one change provides coherent closure.
- **Alternative**: Split into v2-doc-truth-sync + v2-test-quality + v2-spec-promotion
- **Rejected**: Over-fragmentation. These are all post-release audit findings from a single review session.

### Decision 2: package.json as single source of truth

- **Why**: INSTALL.md, USAGE.md, README.md all have stale version/skill count. package.json (v2.0.0-beta, 12 skills) is correct. Fix = "sync to package.json", not "choose arbitrary numbers".
- **How**: INSTALL.md's package.json template will read from the actual package.json at install time rather than hardcoding. Other docs reference "see package.json" or match published version.

### Decision 3: Migration guide CLI references → marked "planned, not implemented"

- **Why**: The `spec-workflow migrate/sync/report` CLI was a design aspiration from the ADR phase. Rather than delete (loses the design intent) or implement (scope creep), mark each command as "planned for v2.1" or replace with equivalent manual steps.
- **Risk**: Users may still try the commands. Mitigation: add clear "not yet implemented" warning before each such reference.

### Decision 4: Per-ADR implementation audit, not blanket statement

- **Why**: ADR README currently says "all v2.0 ADRs unimplemented." But some are fully implemented (0004 loop engine, 0006 state vector), some partially (0010 lightweight session), some not at all (0009 scheduled triggers). A blanket fix would be inaccurate.
- **How**: Each ADR's status field gets a per-ADR audit against test files.

### Decision 5: state.sh and archive.sh test coverage via bats, not pytest

- **Why**: These are shell scripts. Adding Python tests would be unnatural. bats tests (which already cover other shell modules) are the right vehicle.
- **Exception**: event_context.py, defaults.py, event_types.py are Python—get pytest unit tests.

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| ADR README blanket "implemented" misses partial gaps | Medium | Per-ADR audit against test files before changing status |
| Migration guide rewrite introduces new inaccuracies | Medium | Ground CLI replacement in actual skill_use() calls, not invented steps |
| Frontmatter consistency test breaks after INSTALL.md change | High | Update test_skill_metadata_consistency.bats in same commit |
| Tautological assertion fix causes real test failure | Low | Verify lock.py release behavior before changing assertion |