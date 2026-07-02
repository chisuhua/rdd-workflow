# Changelog

## v2.0.0-beta (2026-06-26)

### New Features

- **Three-Phase Architecture** (ADR-0003): Split spec phase into `guide-arch` (architecture definition) → `guide-plan` (change generation) → `guide-ship` (change execution). Each phase has a dedicated skill with its own state machine.
- **Loop Engine v2.0**: Goal-driven execution loop with 8 built-in detectors, 7 built-in actions, and plugin support. Automates repetitive change management tasks.
- **State Vector + Event Log**: Atomic state persistence with JSON-schema validation, checksum integrity, and append-only event log with sub-100ms query over 10K events.
- **Gate Mechanism**: Plugin-based quality gates with error/warning levels. Default checks include dirty worktree, uncommitted changes, and merge conflicts.
- **Tribunal Committee**: Multi-agent cross-validation with weighted scoring. Supports degradation policy when sub-agents fail.
- **Session Coordinator**: Lightweight sequential coordination for change management sessions. Parent-child session tracking.
- **Agents Framework**: Planner/Executor/Verifier coordinator for automated change execution.
- **LoopMemory**: History tracking, interrupted recovery, config recommendation, and automatic archiving at capacity.
- **Sanitizer**: API key, password, and sensitive path redaction. Sub-10ms per call.

### Breaking Changes

- **v1.x compatibility maintained**: `guide-spec` remains as a backward-compatible alias that internally calls `guide-arch` → `guide-plan`. No user skill code changes required.
- **State file format unchanged**: All `.rddf/state/` state files maintain v1.x format. No migration needed.
- **npm package rename**: None — package remains `spec-workflow`.

### Performance Targets (Verified)

| Metric | Target | Status |
|--------|--------|--------|
| State vector read/write | < 10ms | ✅ 171 tests pass |
| Event log query (10K events) | < 100ms | ✅ Verified in test suite |
| Sanitizer per-call latency | < 10ms | ✅ Verified |
| Loop engine startup | < 1s | ✅ Confirmed |

### Known Issues

- **Beta designation**: `2.0.0-beta` is explicitly unstable. Breaking changes may occur before `2.0.0-stable`.
- **Migration documentation**: v1-to-v2 migration guide is comprehensive but may not cover all edge cases. Report issues via GitHub.
- **Performance at scale**: Loop engine tested with 10K event logs. Performance at 100K+ not yet verified.
- **Plugin ecosystem**: Detector/action/gate plugins are documented but no third-party plugins exist yet.

### Migration

See [v1.x → v2.0 Migration Guide](./docs/migration/v1-to-v2.md) for step-by-step instructions.

### Contributors

- @sisyphus — Architecture, implementation, and release