# Changelog

## [Unreleased]

### Added

- **rdd-env-check skill**: 环境健康检查外置为独立 skill，`.rddf/state/.env-cache.json` 快照缓存 (TTL 3600s + branch 失效)，arch/design/plan/ship Phase 1 首屏压缩为单行状态 (~600 tokens → ~50 tokens)。共享 `_check_*` 函数提取至 `skills/_lib/env_checks.sh` (DRY)。
- **Execute CHANGE_NAME auto-derivation**: 共享 `skills/execute/scripts/change_name.sh::ensure_change_name` 在 execute Step 1 与辅助脚本入口补齐运行时上下文，保留显式值并对非 `openspec/*` 分支报出明确的修复指引。

## [v3.0.0] — 2026-07-22 (BREAKING)

### Renamed: `spec-workflow` → `rdd-workflow`

**Why**: Align with GitHub repo name `chisuhua/rdd-workflow`.  
**Scope**: Code, docs, ADRs, specs, archive, install paths, skill names, npm package.  
**Compat**: NONE. Hard cut. No backward compatibility shim.

**Action items for users**:
1. Remove old installation: `rm -rf ~/.agents/skills/spec-workflow .opencode/skills/spec-workflow`
2. Reinstall: `git clone https://github.com/chisuhua/rdd-workflow.git ~/.agents/skills/rdd-workflow && bash ~/.agents/skills/rdd-workflow/install.sh --global`
3. Update script calls: `skill_use("spec-workflow/X")` → `skill_use("rdd-workflow/X")`

**Historical note**: Documents authored before v3.0.0 used the name `spec-workflow`. These have been retroactively renamed. Each ADR carries a footnote. See ADR-0023 for the rename decision.

No data migration: `.rddf/state/` content unchanged. Existing rddf-sessions, iterations, deps-analysis continue to work.

## [Unreleased] — v2.0.8

### Changed (skills/ directory reorganization)

**Phase 1** — Per-skill subdirectory skeleton: 12 skills moved to `skills/<name>/SKILL.md`, 53 source paths resolved.

**Phase 2** — Single-skill helper migration: 46 single-skill helpers moved to per-skill `scripts/` directories.

**Phase 3** — `_lib/` reorganization: runtime kernel (6 files) → `_lib/core/`, v2.0 loop engine (15 files) → `_lib/loop/`. Cross-cutting modules stay at top level.

**Phase 4** — Broken path fixes + docs: 3 P0 path fixes (plan_queue_overview state.sh, propose validate_baseline, guide-ship $REPO_ROOT), AGENTS.md state.sh STUB label corrected, directory structure docs updated.

## [Unreleased] — v2.1

### Fixed

- **Scanner fallback**: `skills/guide/scripts/scan-state.sh` and `skills/guide/scripts/guide_entry.sh` now load `skills/_lib/state.sh` from `$PROJECT_ROOT` first, then fall back to `${HOME}/.agents/skills/_lib/state.sh`, with a non-blocking stderr warning if both are missing.
- **Orphaned session archival**: `skills/rddf-session/scripts/rddf_session_pkg/_types.py` now includes `"orphaned"` in `_TERMINAL_STATES`, so `archive_history` archives heartbeat-timeout sessions instead of leaving them in `sessions.json`.

### Added (ADR-0016: Arch Artifact Discovery Contract)

- **JSON Schema**: `skills/_lib/schemas/arch_handoff_schema.json` (v1)
- **Discovery library**: `skills/_lib/discover-arch-artifacts.sh` (4 discover functions + 1 helper)
- **Tests**: 6 schema tests + 10 discover tests + 10 bats integration tests = 26 new tests
- **Handoff fields** (`.arch-handoff.json` v1): `adr_dir`, `roadmap_path`, `architecture_dir`, `adr_pattern`, `discovered`, `version`
- **Env var overrides**: `SPEC_WORKFLOW_ADR_DIR`, `SPEC_WORKFLOW_ROADMAP_PATH`, `SPEC_WORKFLOW_ARCHITECTURE_DIR`, `SPEC_WORKFLOW_ADR_PATTERN`

### Changed

- 10 files updated to read handoff paths with fallback defaults (no breaking changes for v2.0 users)
- 14+ hardcoded `docs/adr/` / `roadmap.md` references replaced with handoff-aware readers
- `guide-arch.md` Phase 1 (setup) + Phase 2/3/4 (write paths) + Phase 5 (handoff writer) all consume discovered paths
- `guide-plan.md` Phase 0, `propose.md` Phase 1a, `roadmap.md` (header + Template 4), `scan-state.sh` line 154 — all handoff-aware
- `gate.py` `_check_adr_exists` / `_check_roadmap_defined`, `detectors.py` `detect_adr_status`, `actions.py` `action_create_adr` — handoff-aware

### Added (guide-design Phase: 四阶段架构 arch → design → plan → ship)

- **New skill**: `skills/guide-design/SKILL.md` — design phase state machine (Phase 1-5: setup, proposal intake, review, gate, exit)
- **New handoff**: `.rddf/state/.design-handoff.json` (v1 schema, 4 fields: `design_complete_at`, `proposals_reviewed`, `all_proposals_have_decision`, `version`)
- **New schema**: `skills/_lib/schemas/design_handoff_schema.json`
- **New rddf-session kind**: `stage_design` (parent=stage_arch, aliased to `guide-design`)
- **New scripts**:
  - `skills/guide-design/scripts/design_proposal_review.sh` (搬移自 arch_proposal_review.sh + 重命名)
  - `skills/guide-design/scripts/approve_proposal.sh` (搬移自 arch/)
  - `skills/guide-design/scripts/write_design_handoff.{sh,py}` (env-var 模式, Oracle C1 合规)
- **Tests**: 9 Python unit + 12 bats integration (新增 guide-design 阶段 + shim 行为验证)

### Changed (4-state 重构)

- **guide-arch**: Phase 5.5 删除, 顶部插入 deprecation notice; Phase 6 输出不再含提案计数, 改为 `💡 Next: guide-design`
- **guide-plan**: `plan_intake.sh` 新增 `check_design_handoff()` 硬门控 (SKIP_ARCH_HANDOFF=yes 同时跳过两门控; direct-create fallback 豁免)
- **双扫描器**: `guide_cmd.py` + `scan-state.sh` 同步升级为 4-state 优先级阶梯, 两入口推荐一致
- **sessions schema**: `kind` 枚举追加 `stage_design`, `goal.intent` 追加 `guide-design` (additive, version 保持 1)
- **rddf-session**: `_VALID_KINDS` + `_KIND_ALIAS` 增加 `stage_design`/`guide-design`; `parent_kind_map` 增加 `stage_design: stage_arch`, `stage_plan` parent 改为 `stage_design`
- **guide SKILL.md**: 菜单增加 `guide-design` 条目, 顺序在 arch 之后 plan 之前
- **add-improve SKILL.md**: 批准引用从 `guide-arch Phase 5.5` 改为 `guide-design`

### Deprecated
- `guide-arch` Phase 5.5 脚本路径替换为 deprecated shim (包装函数转发到 `guide-design/scripts/`), v2.2.0 移除

### Docs
- `README.md` / `AGENTS.md` 顶部 banner 新增四阶段说明; `README.md` 架构表改为四阶段; `proposal-suggestions.md` 头注释更新
- `INSTALL.md` 子技能计数更新为 14

- **JSON Schema**: `skills/_lib/schemas/arch_handoff_schema.json` (v1)
- **Discovery library**: `skills/_lib/discover-arch-artifacts.sh` (4 discover functions + 1 helper)
- **Tests**: 6 schema tests + 10 discover tests + 10 bats integration tests = 26 new tests
- **Handoff fields** (`.arch-handoff.json` v1): `adr_dir`, `roadmap_path`, `architecture_dir`, `adr_pattern`, `discovered`, `version`
- **Env var overrides**: `SPEC_WORKFLOW_ADR_DIR`, `SPEC_WORKFLOW_ROADMAP_PATH`, `SPEC_WORKFLOW_ARCHITECTURE_DIR`, `SPEC_WORKFLOW_ADR_PATTERN`

### Changed

- 10 files updated to read handoff paths with fallback defaults (no breaking changes for v2.0 users)
- 14+ hardcoded `docs/adr/` / `roadmap.md` references replaced with handoff-aware readers
- `guide-arch.md` Phase 1 (setup) + Phase 2/3/4 (write paths) + Phase 5 (handoff writer) all consume discovered paths
- `guide-plan.md` Phase 0, `propose.md` Phase 1a, `roadmap.md` (header + Template 4), `scan-state.sh` line 154 — all handoff-aware
- `gate.py` `_check_adr_exists` / `_check_roadmap_defined`, `detectors.py` `detect_adr_status`, `actions.py` `action_create_adr` — handoff-aware

### Migration

Zero migration needed. Existing v2.0 projects with `docs/adr/` and `roadmap.md` work unchanged via fallback defaults. Custom layouts (e.g. `doc/adr/`, `planning/roadmap.md`, `DEC-*.md`) now discoverable via env vars or handoff.

## [2.0.7] — 2026-07-17

### Changed (Round A: 6 inline bash extractions)

- **guide-arch.md**: 962 → 671 lines (-30%) via 3 new `_lib/` helpers (`arch_env_check.sh`, `write_arch_handoff.{sh,py,env.py}`)
- **guide-plan.md**: 886 → 564 lines (-36%) via 3 new helpers (`plan_intake.sh`, `plan_done_gate.{sh,py,env.py}`)
- **guide-ship.md**: 1361 → 751 lines (-45%, P3-2 + P3-3 partial) via 1 new helper (`ship_monitor.sh`)
- **execute.md**: 516 → 265 lines (-49%) via 1 new helper (`select_worktree.sh`)
- **status.md**: 566 → 531 lines (-6%) (minor — Round B only)
- 10 new `_lib/` helpers + 66 new tests

### Changed (Round B: 10 inline bash extractions)

- **guide-arch.md**: 671 → 602 lines (gap analysis + dual gate + quality report)
- **guide-plan.md**: 564 → 514 lines (deps-candidates + queue overview + feature progress)
- **execute.md**: 265 → 251 lines (tasks writeback + roadmap progress + step 7 report)
- **status.md**: 531 → 525 lines (mode A render)
- + 11 new `_lib/` helpers, ~480 lines removed from 4 skill files
- 2 SEC fixes: `python3 -c` with bash `$VAR` interpolation eliminated
- 1 real bug fix: `awk sub()` regex issue in tasks.md writeback
- 68 new tests

### Changed (Round C: feature.md refactor)

- **feature.md**: 183 → 77 lines (-58%) via 4 per-subcommand helpers
- 1 new `_lib/feature_cli.py` + 4 thin bash wrappers
- 16 new bats tests
- DRY: 60 lines of duplicated heredoc boilerplate eliminated via `_load_feature_view()`

### Changed (Guide-ship extraction — v2.0.5 holdover)

- **guide-ship.md**: 1361 → 751 lines (-45%) via 3 `_lib/ship_*.sh` scripts
- Extracted Phase 1 (plan), Phase 2.5 (review), Phase 3 (archive) into dedicated modules
- 9 bats integration tests lock contract

### Changed (Deps + Propose extraction — v2.0.6 holdover)

- **deps.md**: 786 → 637 lines (-19%) via `deps_output.py::render_markdown_report` + `deps_render_report.sh`
- **propose.md**: 942 → 686 lines (-27%) via `propose_change.{sh,py}` (5 Python functions)
- 17 Python unit + 9 bats (deps); 21 Python unit + 9 bats (propose)

### Bug Fixes

- **SECURITY (B3, B8)**: Eliminated `python3 -c "..."` with bash `$VAR` string interpolation (Oracle C1 risk) in plan deps-candidates and execute roadmap-progress writers. Now use env-var passing.
- **Tasks writeback (B7)**: `awk sub()` was interpreting `[ ]` as regex character class, causing silent zero-match failure. Replaced with `awk index()` + `substr()` for literal match.
- **SKIP_ARCH_HANDOFF** (Round A): Was dead code (error message told users to set env var but code never read it). Now wired.
- **roadmap_exists** (Round A final review): Was always `false` because env var didn't propagate between markdown code blocks. Now computed from filesystem.
- **commit gate (#7)**: Fixed `e3f466c commit` writing artifacts missed intermediate staging.
- **Plan Gate 0 skip semantics**: `exit 0` terminated entire plan-done block (preventing handoff write) → fixed with `PLAN_GATE_0_SKIPPED` sentinel.

### Total Stats

- 37 commits across master
- ~1,800 lines of inline bash extracted from skill files
- 25+ new `_lib/` helpers (bash wrappers + Python modules)
- ~150 new tests (19 Python unit + 131 bats integration)
- All 819 Python test cases passing (57 unit + 10 integration files), full bats regression green

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
- **npm package rename**: None — package remains `rdd-workflow`.

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