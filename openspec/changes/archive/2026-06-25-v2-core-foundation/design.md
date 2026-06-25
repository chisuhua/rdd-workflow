## Context

spec-workflow v1.x represents workflow state across 13 different files: `.zcf/.handoff.json` (spec→ship handoff), `.zcf/.roadmap-state.json`, `.zcf/.deps-output.md`, `proposal-suggestions.md` (with status markers), individual `openspec/changes/<name>/.openspec.yaml` files, and so on. Each phase transition (e.g., spec-done → ship-started) requires ad-hoc validation in the relevant skill. There is no central authority for "what state is the workflow in right now?"

v2.0 (ADR-0006, ADR-0007) commits to a unified state vector and a gate mechanism. The v2 loop engine (ADR-0004) and tribunal (ADR-0008) both require the state vector as their source of truth. This change establishes the foundation those higher-level systems will build on.

## Goals / Non-Goals

**Goals:**
- Provide a single, validated state vector as the authoritative workflow state
- Provide an append-only event log for audit, debugging, and progress reporting
- Provide phase-transition gates with two severity levels (error blocks, warning allows with notice)
- Provide config parser supporting multiple sources with documented priority
- Maintain 100% backward compatibility with v1.x via bidirectional sync

**Non-Goals:**
- Implementing the loop engine itself (that's `v2-loop-engine`)
- Implementing detectors/actions (that's `v2-loop-engine`)
- Implementing human-in-loop nodes (that's `v2-advanced-features`)
- Replacing v1.x skill file formats (sync layer handles compatibility)
- Real-time multi-process coordination beyond file locking (that's `v2-advanced-features` for sessions)

## Decisions

### Decision 1: State vector as single JSON file with file lock

- **Why**: Simple, debuggable, supports manual inspection. File lock (fcntl) provides sufficient serialization for current use cases.
- **Alternative**: SQLite (overkill for ~50KB state), Redis (adds dependency)
- **Rejected**: SQLite adds binary dependency; Redis adds network dependency

### Decision 2: Event log as JSONL, not JSON array

- **Why**: Append-only writes are O(1) vs O(n) for array updates. Concurrent writes are safer (each line is one event).
- **Alternative**: SQLite, single JSON with append
- **Rejected**: SQLite for same reason as above; single JSON has whole-file rewrite cost

### Decision 3: Gate mechanism uses lambda conditions, not string DSL

- **Why**: Python lambdas are type-safe and inspectable. String DSL would require a parser and error handling.
- **Alternative**: YAML/JSON condition definitions
- **Rejected**: Loses type safety and IDE support; debuggability is worse

### Decision 4: Sync layer is bidirectional but state vector wins on conflict

- **Why**: State vector is the v2 source of truth; v1.x files are read-only cache for v1.x code.
- **Alternative**: v1.x files win (would break v2 writes)
- **Rejected**: Defeats the purpose of the unified state

### Decision 5: Config priority is strict order, not merge-by-key

- **Why**: Predictable behavior; users know which source "wins" without reading docs.
- **Alternative**: Deep merge with per-key override
- **Rejected**: Ambiguous behavior when both sources define `interaction.mode` differently

## Risks / Trade-offs

- **Risk**: File lock timeout (10s default) may be too short for slow disks
  - **Mitigation**: Make timeout configurable; log warnings when triggered
- **Risk**: v1.x sync layer may have race conditions with concurrent v1.x and v2 operations
  - **Mitigation**: Detect concurrent modifications via mtime; prefer state vector on conflict; log warnings
- **Risk**: JSON Schema validation overhead on every state write (~5ms per write)
  - **Mitigation**: Acceptable for current throughput; can cache parsed schema
- **Risk**: Plugin-loaded gate checks may have varying quality
  - **Mitigation**: Document plugin API; provide reference implementations
- **Trade-off**: Single state file vs distributed state — chose single for simplicity, accepting that very large states would need splitting
