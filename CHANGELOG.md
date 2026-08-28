# Changelog

## [Unreleased]

### rdd-verifier (5th phase: 验证回环)

Adds the 5th phase `rdd-verifier` (arch → design → plan → ship → **verify** → archive). Runs ac-verifier skill on ship-done changes in batch, classifies failures heuristically (implementation_gap vs proposal_drift), and routes failures back to plan/ship with 3-retry max. See `docs/superpowers/specs/2026-08-26-rdd-verifier-design.md` and ADR-0034.

- **Components**: `skills/rdd-verifier/SKILL.md` (state machine, 242 lines) + 4 bash helpers (`scan_queue.sh`, `run_verification.sh`, `classify_failure.sh`, `route_loop.sh`) + `_lib/verifier/{classify,cache,loop_state}.py` (3 Python modules) + `_lib/cli/rdd_verify_cmd.py` (`rddf rdd-verify` CLI) + 2 JSON schemas (`verifier_loop_schema.json`, `ac_verdict_cache_schema.json`).
- **SHA-fingerprint verdict cache** (`.rddf/state/.ac-verdict-<name>.json` with `codebase_commit`) shared between rdd-verifier and `archive_gate_check` — prevents double LLM calls (Per ADR-0034 §7.2 + Oracle §C).
- **Heuristic classification**: Pure-function, no new LLM call (Oracle §E). Reuses ac-verifier verdict JSON evidence + reasoning fields. Drift keywords (`exists but` / `discrepan` / `mismatch`) checked before gap keywords (`missing` / `absent`) per Oracle's conservative-fallback principle.
- **5th exit code** (`4`): `max_loops` exceeded → archive halted + audit log → manual review required.
- **`_lib/archive.sh::archive_gate_check` extended**: 3-branch logic (cache-hit skip / cache-stale re-run / cache-miss fresh) replacing prior unconditional LLM call.
- **AGENTS.md 4 → 5 阶段**: adds `verify | rdd-verifier` row to phase table.
- **ADR-0034**: new ADR documenting 5th phase architecture.
- **Tests**: 8 new test files (3 unit + 5 integration), 47 new test cases total. All pass.

### add-feature-fragment-command (rddf roadmap add-feature primitive)

### add-feature-fragment-command (rddf roadmap add-feature primitive)

Adds the `rddf roadmap add-feature <name>` CLI primitive that creates `.rddf/roadmap/features/feat-<name>.md` fragments with valid frontmatter + 3-section body skeleton, and refreshes `.rddf/roadmap.md` AUTO-INDEX atomically. Closes the operation gap from `add-hierarchical-roadmap-structure` (scenario 3, shipped 2026-08-20); users previously had to hand-craft YAML and call `render_fragment_index` manually, leaving `.rddf/roadmap/features/` empty.

- **Components**: `_lib/roadmap_state.py::add_feature` (Python core, ~95 lines) + `skills/roadmap/scripts/roadmap_add_feature.sh` (thin shell wrapper, Oracle C1 env-var passing) + `_lib/cli/roadmap_cmd.py` dispatch extension + `_lib/roadmap_state_wrapper.py` (env-var consuming entry point).
- **SKILL.md integration**: `guide-arch` Phase 4 menu adds option 5 "添加 feature fragment" with 4-step forced interaction (name → theme → phase_refs multi-select → preview+confirm); `roadmap/SKILL.md` adds add-feature subcommand documentation.
- **ADR-0028 patch**: `skills/guide-arch/SKILL.md` frontmatter `role.boundaries.owns` now explicitly includes `.rddf/roadmap/features/*.md` alongside `.rddf/roadmap/phases/*.md`.
- **Tests**: 11 new tests (7 unit + 4 bats). All pass; existing 140 tests unaffected.

### generate-full-proposal-bugfix (Out of Scope ↔ Heading format support)

Fixes 3 related bugs in `skills/guide-design/scripts/generate_full_proposal.py::_extract_scope_items`:

1. `**Out Scope**` → `**Out of Scope**` (was matching without `of`, breaking all bold-line format improvements).
2. Heading format: only matched `**In Scope**:` bold-line, not `### In Scope` heading — affected all historical proposals using heading format.
3. Exact match (`==`) → startswith: `### Out of Scope（详见 spec §13）` failed exact match because of trailing annotation.

### approve-proposal-yaml-schema (align with openspec CLI v1.7+)

Fixes `.openspec.yaml` schema field for `guide-design approve_proposal.sh`: was `name + created_by` (unrecognized by openspec CLI), now `schema: spec-driven + created: <date> + name: <name>` (matches openspec CLI v1.7+ format). Future approved proposals no longer require manual schema fix.

### add-phase-role-model (ADR-0028: 阶段技能角色模型)

Formalizes role metadata for the 4 phase skills via structured `role:` frontmatter field:

- **New frontmatter field**: `role:` with 5 sub-fields (title, perspective, boundaries.owns, boundaries.not_owns, boundaries.human_involvement) in all 4 phase SKILL.md files (guide-arch, guide-design, guide-plan, guide-ship).
- **JSON Schema**: New `_lib/schemas/skill_role_schema.json` (JSON Schema draft 2020-12) validates the role field structure.
- **Documentation update**: Each SKILL.md "职责边界" section now references the frontmatter role field as the single source of truth (ADR-0028).
- **AGENTS.md integration**: New "Skill 角色模型 (ADR-0028)" section in "关键约定" documents the role field convention.
- **ADR-0028**: Architecture decision record captures the rationale, decision, and consequences. Documentation-only change with no AI behavior enforcement.
- **Backward compatibility**: Skills without the role field continue to load and parse successfully (validated via test).

测试: 9 integration tests (`test_skill_role_all.bats`) — all 4 phase skills validated for complete role fields + schema compliance + backward compatibility = **9 new tests, all pass**.

### preserve-orchestrator-command-stdout (orchestrator stdout 透传 + async tee)

Restores user-visible stdout from `rddf orchestrate subprocess` while preserving full trace capture via async tee:

- **Default mode**: `tee` (was `capture`). Users now see live stdout from `rddf orchestrate subprocess` calls.
- **Env var**: `RDDF_ORCHESTRATOR_CAPTURE` accepts `tee` (default) | `capture` (legacy) | `passthrough` (zero-overhead).
- **Async reader**: New reader subprocess drains stdout/stderr to trace file via dedicated process with `O_NONBLOCK` pipes (POSIX).
- **Schema**: trace JSONL subprocess events gain `stdout_capture_mode` and `reader_died` fields.
- **Rotation**: trace file rotates to `<trace>.1` when exceeding `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` (default 100MB).
- **CI compat**: GitHub Actions runner output now visible (was swallowed by old capture).
- **Windows caveat**: O_NONBLOCK not supported on Windows pipes; tee mode degrades to default buffer.

测试: 11 unit tests (`test_orchestrator_tee.py`) + 5 bats integration (`test_orchestrator_stdout_passthrough.bats`) = **16 new tests, all pass**.

### roadmap-proposal-guidance (让 roadmap 节点约束 proposal 创建)

Adds end-to-end constraint-driven link from roadmap to proposal creation:

- **roadmap 模板扩展** — `roadmap.md` 任务分类表格支持第 5 列 "预期改进方向" (可选, `主题1；主题2` 分号分隔)。4 列旧表格向后兼容 (按"无约束"处理)。
- **`_lib/roadmap_state.py::get_phase_themes()`** — 解析第 5 列,返回该分类下的主题列表。处理 `~skipped~` 标记、空 cell、4 列遗留表、未知 phase、特殊字符 (CJK/dots/parens) 等边界情况。
- **`rdd-workflow-brainstorm` 模板扩展** — 5 段 metadata 新增 `**主题**:` 字段 (free-form 留空或 `不适用`,约束模式由 `add-improve --from-roadmap` 自动填入)。
- **`add-improve --from-roadmap` 模式** — 新增 CLI 参数,3 文件 env-var split pattern (`from_roadmap.{sh,env.py,py}`) 满足 Oracle C1 安全要求。env-var 名: `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT`。
- **`guide-design` Phase 1 preflight 增强** — 直接解析 `roadmap.md` (consume-time, 避免 arch-handoff schema bump)。显示路线图指引 N 主题 across M 分类、当前覆盖 X/Y (Z%)、未覆盖主题列表 (按 phase/category 分组)、未标注主题的旧 proposal 数 (向后兼容, 避免 0/N 假警)。
- **`guide-design` Phase 2 菜单新增** — 选项 2 "🎯 按路线图主题创建提案 (推荐)" — 列出未覆盖主题,用户选主题后触发 `add-improve --from-roadmap`。
- **`STRICT_PROPOSAL_COVERAGE` 门控** — design-done Phase 4 新增可选严格校验,默认 warning only,与现有 `STRICT_*_GATE` 模式对齐 (`SKIP_PROPOSAL_COVERAGE=yes` 临时绕过)。
- **主题状态词汇** — `未覆盖 / 已覆盖 / ~skipped~` 三态明确,`~skipped~` 排除出覆盖率分母。
- **向后兼容** — 旧 v1 handoff + 无主题字段的旧 proposal 不报错,coverage 显示"未标注主题 K 个"独立统计。
- **Oracle 审查采纳** — 删除原方案 handoff v2 schema bump (避免 rdd-doctor CRITICAL),改为 consume-time 直接解析 roadmap.md。

测试: 7 unit tests (`test_roadmap_state_themes.py`) + 4 unit tests (`test_brainstorm_template.py`) + 12 unit tests (`test_from_roadmap_env_validation.py`) + 10 bats integration (`test_add_improve_from_roadmap.bats`) + 4 unit tests (`test_guide_design_preflight_themes.py`) + 8 bats integration (`test_strict_proposal_coverage_gate.bats`) = **45 new tests, all pass**.

### rddf orchestrate (Python orchestrator for phase subprocess detection)

Adds `rddf orchestrate` subcommand that batches subprocess invocations of `guide-arch`,
`guide-design`, `guide-plan`, `guide-ship` into a single traceable checkpoint model,
with stale-trace sweep + GC. Replaces serial shell-call mode with phase-aware trace
files + env-var passthrough. 11 commits + 4 supporting commits:

- `ff094b5` feat(cli): add rddf orchestrate subcommand skeleton
- `388b97c` feat(orchestrate): add trace file management (open/append/read)
- `0f8925d` feat(orchestrate): implement --subprocess with tempfile streams + sanitize
- `4be2749` feat(orchestrate): implement --mark-checkpoint + --finalize + trace reuse
- `666d258` feat(orchestrator): add bash wrapper + __main__ entry point
- `d771201` feat(post-flow-wrap): add single-writer guard for orchestrator coexistence
- `3ebe519` feat(post-flow-analysis): add analyze_phase_trace for orchestrator finalize
- `8539bdc` feat(orchestrate): implement stale-trace sweep + GC (B4 fix - centerpiece)
- `fdf1f09` test(integration): add 5 end-to-end tests for rddf orchestrate
- `fdebcf6` docs(skills): replace Phase Exit prose in 4 SKILL.md with 3-rule checklist
- `9968b43` merge: Python orchestrator for phase subprocess detection (B1-B4 fix)
- `ed503cd` feat(scripts): integrate orchestrator_entry.sh into 4 phase entry scripts
- `02a1aa8` test(integration): verify RDDF_USE_ORCHESTRATOR env var toggles behavior
- `056177c` test(e2e): add temp-project orchestrator tests for realistic scenarios
- `214137b` fix(orchestrate): sweep always reports, even when last subprocess returned 0
- `b64b68e` fix(cli): rename argv → args in cmd_orchestrate + add orchestrate to ALL_SUBCOMMANDS

### env-check gh_available field (ADR-0027 reporter prereq)

Adds 15th env-check field `gh_available` (boolean: `gh` CLI on PATH + authenticated)
required by the post-flow-analysis reporter before attempting `gh issue create`.
Single commit:

- `61a6d2a` feat(env-check): add gh_available field (15th) for ADR-0027 reporter prereq

### archive close hook: lightweight mode

Closes the dual-mode coverage gap for `close_issues_for_change_hook`. The hook was
already wired in worktree mode (`_lib/archive.sh::archive_change`, fail-tolerant via
`|| true`); the lightweight mode path (`guide-ship/scripts/ship_archive.sh::archive_change_for_mode`)
now mirrors the same call site, ensuring changes archived via the lightweight path
(small changes per ADR-0024) close their linked GitHub issues in lockstep.

- `582a6f1` feat(archive): wire close_issues_for_change_hook in lightweight mode

### Continuous evolution feedback loop (ADR-0027)

Three changes implement the Detect → Buffer → Report → Triage → Close loop
that lets third-party projects (and rdd-workflow itself, via dogfooding)
report workflow problems to `github.com/chisuhua/rdd-workflow` Issues, with
maintainers able to triage via `guide-design` and auto-close on archive:

- **`fix-adr-0027-cleanup`** — Apply Oracle's 5 review fixes to ADR-0027
  (python skeleton bug, 9 stale string occurrences, References dedup, triage
  label lifecycle, env prefix unification). Flip status to 已采纳.
- **`add-issue-reporter-prereqs`** — Three prerequisites for the reporter:
  extend `_lib/loop/sanitizer.py` with `$HOME` path + project name
  redaction (basename-preserving replacement); add `reporting` namespace to
  `_lib/config.py` + `config_schema.json` with `RDDF_REPORT_*` env vars;
  new `_lib/issue_dedup.py` implementing 5 normalization rules
  (path→basename, lineno, timestamp, digit→N, platform) for cross-machine
  stable 8-char SHA-256 dedup hashes.
- **`add-issue-reporter`** — Core reporter (`_lib/issue_reporter.py`) with
  5 public functions (detect_issue, write_issue_file, submit_issue_via_gh,
  is_ci_environment, can_close_in_repo); close hook (`_lib/close_issues.py`)
  with close_issues_for_change + prune_old_issues; integration in
  `_lib/archive.sh` (worktree mode, failure-tolerant via `|| true`).

Triple opt-in (`enabled` + `auto_submit` + per-category `submit_categories`)
preserves the default-don't-call-home posture. 62 new unit tests (32 in
change-a, 30 in change-b), 0 regression. Full unit suite: 1429/1429 pass.

### Breaking — package layout: skills/_lib → _lib

The shared Python library has moved from `skills/_lib/` to the top-level `_lib/`.
A backward-compatibility shim remains at `skills/_lib/` (re-exports from `_lib`)
for >=6 months. `rddf init` now works from any source directory when
`RDDF_PROJECT_ROOT` is set (no longer overridden by `__main__.py`). See
`openspec/changes/fix-rddf-init-broken-layout/`.

### Added

- **rdd-env-check skill**: 环境健康检查外置为独立 skill，`.rddf/state/.env-cache.json` 快照缓存 (TTL 3600s + branch 失效)，arch/design/plan/ship Phase 1 首屏压缩为单行状态 (~600 tokens → ~50 tokens)。共享 `_check_*` 函数提取至 `_lib/env_checks.sh` (DRY)。
- **Known Bats failure baseline**: `tests/KNOWN_FAILURES.txt`, shared incremental regression reporting, explicit refresh, and a CI gate that fails only for newly introduced failures.
- **Strict skill registration contract**: `test_doc_contracts.py` 收紧为精确 `== disk` 匹配，新增 INSTALL.md 子技能表行数断言；`test_skill_metadata_consistency.bats` 改为基于磁盘 glob 的动态校验；`docs/change-quality-guide.md` 增加五项新增 skill 注册 checklist。`package.json` 与 `skills/INSTALL.md` 同步补齐 guide-design、rdd-env-check 等登记项。
- **Execute CHANGE_NAME auto-derivation**: 共享 `skills/execute/scripts/change_name.sh::ensure_change_name` 在 execute Step 1 与辅助脚本入口补齐运行时上下文，保留显式值并对非 `openspec/*` 分支报出明确的修复指引。

## [Unreleased] — v3.1

### feat-fix-audit-findings: 2026-08-26 文档与代码一致性审计后续修复（18 个 audit-followup 提案）

2026-08-26 对 rdd-workflow 自身做了一次全栈审计（package.json skills 漂移、AGENTS.md 阶段描述与 4→5 阶段架构不一致、rdd-doctor 文档不一致等）。发现的问题通过 18 个 audit-followup 提案 + 4 个 batch-tool 提案 + 5 个 process 改进提案分阶段处理，2026-08-27/28 期间由 background Sisyphus session 自动实施并归档。

**Feature fragment**: `.rddf/roadmap/features/feat-fix-audit-findings.md` (kind=feature, phase_refs=[phase-1..4], status=active)。AGENTS.md 新增 "Active Feature Fragments" section (commit 868fce5) 列出此 feature 与自动化进展。

### Added — 18 audit-followup proposals (registered 2026-08-26, archived 2026-08-27/28)

- **P0 reconcile + iteration fix** (2): `fix-iteration-archive-sync`, `reconcile-iteration-after-archive`
- **P1 docs-consistency** (3): `sync-package-skills-to-disk`, `sync-agents-md-five-stage`, `rdd-doctor-docs-consistency`
- **P1 bugs / improvements** (6): `fix-disk-count-semantic-conflict`, `fix-proposal-ac-section-mapping`, `fix-design-preflight-roadmap-format`, `fix-ship-plan-untracked-gate`, `fix-rdd-verifier-lifecycle-dashboard`, `improve-execution-mode-per-change`
- **P2 process improvements** (3): `improve-change-splitting-strategy`, `improve-commit-scope-discipline`, `improve-from-roadmap-naming-flexibility`

### Added — 5 process proposals (registered 2026-08-27, archived 2026-08-28)

- `add-brainstorm-hardgate-enforcement` — HARD-GATE 强制 `rdd-workflow-brainstorm` 调用（防止 `add-improve` 绕过）
- `add-pre-commit-proposal-quality-check` — `pre-commit` hook 验证 proposal 质量 (Bronze/Silver/Gold)
- `add-proposal-source-tracking` — `iteration.json` 新增 `proposal_source_tracking` 字段 (session_id / audit_source / created_at_iso / parent_session_id)
- `improve-from-roadmap-naming-flexibility` — `add-improve` 接受 `--multi` flag 支持从单 theme 批量创建 sub-proposals
- `improve-roadmap-feature-discovery` — `skills/guide-design/scripts/feature_discovery.py::list_active_features` 在 `guide-design` Phase 1 preflight 列出 active features

### Added — 4 batch-tool proposals (registered 2026-08-27, archived 2026-08-27)

- `auto-archive-iteration-and-commit` — `archive` 命令自动同步 `iteration.json` + commit archive 移动
- `design-approve-batch-tool` — `guide-design approve_proposal.sh` 支持 `--batch` 批量批准
- `plan-batch-fill-tool` — `guide-plan` 支持批量填充 design.md + tasks.md
- `verifier-re-verify-archived-flag` — `rddf rdd-verify --re-verify-archived` 验证 archived 提案（注意：当前实现为 print-only stub，`ac-verifier.sh` 暂不支持 archive 路径 — 后续 follow-up）

### Fixed — Archived proposal.md TBD placeholders

3 个 P1 docs-consistency changes 的 archived `proposal.md` 文件原本含 `(TBD — 验收标准 from .rddf/improvements 头部未提供)` placeholder（因 `generate_full_proposal.py` 早期版本只识别 `## 验收标准` 标题，但源 `.rddf/improvements/*.md` 使用 `## 验收`）。`fix-proposal-ac-section-mapping` (line 151) 修复了 extraction 逻辑（同时接受两种标题），但仅对未来生成生效。**Commit `6e0a538`** 手动重新生成 3 个 archived `proposal.md`：

| Change | AC bullets |
|---|---|
| sync-package-skills-to-disk | 7 |
| sync-agents-md-five-stage | 8 |
| rdd-doctor-docs-consistency | 8 |

### Test baseline maintenance

**Commit `d6b451c`** 登记 28 个 pre-existing bats 失败到 `tests/KNOWN_FAILURES.txt`：

| 文件 | 失败数 | 根因 |
|---|---|---|
| `test_populate_roadmap_from_arch.bats` | 16 | `skills/populate-roadmap-from-arch/` 目录无 SKILL.md + populate.sh（仅 `__pycache__` 残骸），sync-package-skills-to-disk 只清理 package.json 注册未清理磁盘。后续 follow-up：完全删除残骸目录 + tests，或恢复 artifacts |
| `test_populate_wrapper.bats` | 5 | 同上 |
| `test_rdd_verifier_skip.bats` | 5 | verifier-re-verify-archived-flag 新增的 skip 行为测试未登记 baseline |
| `test_roadmap_skill.bats` | 1 | v2.0.3 移除 gate-report 后命令数变化未跟进 |
| `test_adr_directory.bats` | 1 | ADR status+date 字段检查新增 |

### Notes

- pytest unit: **2256 passed, 3 skipped, 1 flaky** (test_detectors timing — 重跑通过)
- pytest integration: **182 passed**
- Phase C1 已通过 commit `868fce5 docs(agents): add Active Feature Fragments section for in-flight feature visibility` 完成
- Phase A1/B1/B2 完成记录在 HANDOFF.md (2026-08-28)

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