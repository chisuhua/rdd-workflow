# skills/_lib — Skill 共享 utilities 入口

> 本文件是 `skills/_lib/` 的**导入面**说明：skill 层只依赖自己层或共享层，不依赖 dispatcher 内部实现。
> 目录规模是 **2026-11-24 的快照**，会随语料漂移 —— 核对时以 `ls` 为准，不要拿本文件的数字当断言。

## §1 Overview

`skills/_lib/` 背后是**两层**结构：

| 层 | 位置 | 内容 | 谁在用 |
|---|---|---|---|
| 真实现层 | 仓库根 `_lib/` | 全部真实逻辑 | dispatcher 与 skill 两侧都 import 它 |
| shim 层 | `skills/_lib/` | bash 转发 + Python identity-merge + 子包 `__path__` 加宽 | skill 层的稳定导入面 |

`skills/_lib/__init__.py` 把 `__path__` 设为三处，让 `import skills._lib.X` 同时命中：

- `skills/_lib/`（shim，本地）
- 仓库根 `_lib/`（真实现）
- `~/.agents/skills/_lib/`（全局安装 fallback）

⇒ 这是**路径加宽**，不是模块复制：Python 侧用 identity-merge（`exec` 真实现源码），
因此 `skills._lib.X is _lib.X` 恒成立 —— 模块级状态（缓存 / 锁 / registry）不会分裂。

## §2 Module Catalog

### §2.1 真实现层（仓库根 `_lib/`）

#### §2.1.1 顶层 Python 模块

| Module | Purpose | ADR |
|---|---|---|
| `_python_resolve_project_root.py` | Skill-layer Python wrapper for project_root resolution | ADR-0033 |
| `adr_catalog.py` | Shared ADR catalog scanner | — |
| `adr_index_generator.py` | ADR Index Generator — the ONLY generator for the docs/adr index table | — |
| `approval_matrix.py` | Multi-stakeholder approval gate (per phase-4-general-20260829063814) | — |
| `arch_quality_gate.py` | Architecture quality gate — qualitative checks for arch_done transition (ADR-0018) | ADR-0060 |
| `archive_helper.py` | Helper for archive operations with change_type awareness | — |
| `builder_deps.py` | Phase 1.5 deps + execution_mode decision (per spec §3.4, Oracle C2) | — |
| `builder_feedback_router.py` | Builder feedback routing to .planner-feedback.json (per spec §3.5.2, batch 4) | — |
| `builder_handoff.py` | builder-handoff per-change file r/w + FileLock (per spec §6.3 + Oracle H3) | ADR-0049 |
| `builder_retry.py` | Verifier verdict → Phase routing + retry counter (per spec §3.4, Oracle C1) | — |
| `change_alignment.py` | Change alignment gate — qualitative checks for plan_done transition (ADR-0019) | — |
| `cleanup_plan_handoff.py` | Plan-handoff cleanup with final-state convergence semantics | — |
| `close_issues.py` | Close hook for ADR-0027: close linked GitHub issues on change archive | ADR-0027 |
| `config.py` | Multi-source configuration parser with strict priority order | — |
| `contract_diff.py` | Contract diff engine: compare Hub OpenAPI contracts vs Spoke implementations | — |
| `cross_repo_audit.py` | Cross-repo audit log (JSONL append with validation) | — |
| `cross_repo_deps.py` | Cross-repo dependencies orchestration (Step 6 of Hub-and-Spoke federation) | ADR-0030 |
| `cross_repo_deps_cache.py` | TTL cache for cross_repo_deps (24h default) | — |
| `cross_repo_gate.py` | Cross-repo dependencies gate (ADR-0018 escalation pattern) | — |
| `cross_repo_state.py` | Pending RFC state manager (CRUD + schema validation + atomic write) | ADR-0030 |
| `dependency_scheduler.py` | DependencyScheduler — build dependency graphs, topological sort (Kahn), gate execution | ADR-0024 |
| `discover_ship_changes.py` | Unified read-model for guide-ship change discovery | — |
| `docs_consistency.py` | docs-consistency doctor category: 6 类文档与代码一致性校验 | — |
| `env_bootstrap_report.py` | Data layer for env-bootstrap reports | — |
| `event_context.py` | Event context — reads the current state vector to populate event `context` fields | — |
| `feedback_appender.py` | Append-only feedback writer for .rddf/improvements/*.md files | — |
| `feedback_resolver.py` | Read-only resolution of proposal name → OpenSpec change name | — |
| `gate.py` | Gate mechanism — phase-transition validator with two severity levels | ADR-0007 |
| `gh_hub_client.py` | GitHub Hub API client (REST + GraphQL via gh CLI) | ADR-0030 |
| `gh_repo_detect.py` | 3-step GitHub repo detection chain for `add-improve --from-issue` | — |
| `hook_whitelist.py` | Hook comment whitelist for developer experience observability | — |
| `hub_dedup.py` | Hub auto-file dedup (per phase-3-general-20260829063814) | — |
| `hub_issue.py` | Hub Issue CRUD wrapper (uses existing gh_hub_client) | ADR-0030 |
| `issue_dedup.py` | Dedup hash computation for ADR-0027 issue reporter | — |
| `issue_reporter.py` | Issue reporter core for ADR-0027 | ADR-0027 |
| `loop_engine.py` | LoopEngine — the AI-native execution engine for rdd-workflow v2.0 | ADR-0003 |
| `migrate_proposals.py` | Migrate legacy JSON improvement-suggestions.md to individual .rddf/improvements/*.md… | — |
| `objective.py` | Parser + validator + grace helper for objective files | — |
| `objective_parser.py` | Collect active/deferred objectives as JSON for LLM handoff payloads | — |
| `openspec_quota.py` | OpenSpec change quota (KPI slot) — the single implementation | — |
| `parallel_executor.py` | Parallel wave execution helper | — |
| `parse_approved.py` | Centralized parser for improvement-approved.md | — |
| `plan_quality.py` | Plan quality validation module | — |
| `planner_attach.py` | Validated, single-file proposal attach | — |
| `planner_audit.py` | Read-only audit of unmapped proposals | — |
| `planner_deprecation.py` | Skill frontmatter deprecation scanner | — |
| `planner_feedback.py` | Stage 3 Change 2: persistent planner review-task storage | — |
| `planner_handoff.py` | planner-handoff.json v1 read/write/validate (per spec §3.3 + §6.1 + ADR-0048) | — |
| `planner_history.py` | Append-only JSONL history storage for planner sprints | — |
| `planner_state.py` | Planner state I/O — atomic read/write of .rddf/state/.planner-state.json | — |
| `planner_sync.py` | Planner sync — discover improvements, render state, delegate roadmap write | — |
| `plugin_manifest.py` | Plugin manifest validator (per phase-3-general-20260829063801) | — |
| `populate_lib.py` | populate-roadmap-from-arch: Python helpers (Step 1-3: catalog / classify /… | — |
| `post_flow_analysis.py` | Post-flow-analysis classifier for ADR-0027 §1.2 | — |
| `proposal_review.py` | skills/_lib/proposal_review.py — HOW-leakage warning detector (D4) | — |
| `proposal_review_config.py` | skills/_lib/proposal_review_config.py — HOW-leakage threshold configuration | — |
| `propose_cross_repo_hooks.py` | Propose-phase auto cross-repo detection | — |
| `quick_history.py` | Audit-log data layer for rdd-quick (ADR-0047) | ADR-0047 |
| `rate_limiter.py` | TokenBucket rate limiter with persistence support for v3-scheduled-triggers | — |
| `rdd_arch_status.py` | Stage 3 Change 4: rdd-arch status aggregator | — |
| `recommender.py` | Single source of truth for the stage recommendation ladder | ADR-0062 |
| `reflect_cooldown.py` | 24h fingerprint-based cooldown manager for reflect_engine | — |
| `reflect_dedup.py` | Fuzzy dedup matching for reflect_engine | — |
| `reflect_engine.py` | Workflow reflection engine - analyzes failures and proposes GitHub issues | ADR-0027 |
| `review_debt_checker.py` | Phase 2.5 pre-commit review debt checker | — |
| `rfc_ambiguity.py` | Static ambiguity detection for RFC proposals (no LLM, fast, deterministic) | — |
| `rfc_interview_state.py` | RFC interview checkpoint state (resume support, per phase-2-general-20260829063814… | — |
| `roadmap_md_integrity.py` | Pure parsing helpers for `.rddf/roadmap.md` integrity checks | — |
| `roadmap_sprint.py` | Roadmap AUTO-SPRINT section renderer | — |
| `roadmap_state.py` | Roadmap long-term state management | — |
| `roadmap_state_wrapper.py` | Thin env-var consuming wrapper for roadmap_state CLI invocations | — |
| `roadmap_validate.py` | validate_fragment_refs: 8 rules R1-R8 for roadmap fragment integrity | — |
| `session.py` | SessionCoordinator — lightweight v2.0 sequential session coordination | — |
| `session_base.py` | Shared session infrastructure for v2.0 and v2.1 session managers | — |
| `session_manager.py` | SessionManager — parallel session execution (ADR-0010 v2.1) | ADR-0010 |
| `session_stats.py` | Session stats tracking for developer experience observability | — |
| `state_reader.py` | Shared read-only data layer for all CLI subcommands | — |
| `subagent_strategy.py` | Subagent orchestrator execution strategy | — |
| `sync_usage_banner.py` | CHANGELOG ↔ USAGE.md sync check | — |
| `tasks_count.py` | Canonical checkbox counter for tasks.md (fix-iteration-tasks-total) | — |
| `trigger_engine.py` | TriggerEngine — flow.yaml trigger condition evaluator (ADR-0012) | ADR-0012 |
| `trigger_registry.py` | TriggerRegistry — persistent storage for triggers in .rddf/state/triggers.json | ADR-0012 |
| `triggers.py` | Trigger data model and manager for the v3-scheduled-triggers change | ADR-0012 |
| `validate_delta_targets.py` | validate_delta_targets.py - Verify spec.md MODIFIED/RENAMED targets exist | — |
| `validate_report.py` | Structured `openspec validate` output (ADR-0015) | ADR-0015 |
| `wave_compute.py` | Wave DAG computation from deps-analysis.json | ADR-0024 |
| `wave_scheduler.py` | WaveScheduler - auto-detect when blocked changes become unblocked | — |
| `workflow_synthesizer.py` | Read-only workflow state synthesizer for the guide recommender | — |

#### §2.1.2 顶层 Bash helper

| Module | Purpose |
|---|---|
| `archive.sh` | Archive helpers（status.md Mode C / guide-ship Phase 3 抽出） |
| `bypass_audit.sh` | SKIP_* 旁路的统一审计日志写入器 |
| `check_project_setup.sh` | rdd-workflow 运行时项目配置校验 |
| `discover-arch-artifacts.sh` | ADR / theme-doc 发现（arch 阶段） |
| `discover_roadmap_fragments.sh` | Roadmap feature-fragment 发现 |
| `discover_ship_changes.sh` | change 发现统一读模型（Python 版薄封装） |
| `env_checks.sh` | 共享环境健康检查函数库 |
| `orchestrator_entry.sh` | orchestrator 入口 + _resolve_project_root |
| `parallel_throttle.sh` | 并发执行限流器 |
| `post_archive_cleanup.sh` | 归档后清理（plan 文件 / 状态） |
| `post_flow_wrap.sh` | 流程后输出包装（tee / capture） |
| `project_config.sh` | project.yaml 配置加载 |
| `resolve_skill_name.sh` | 短 skill 名 → 全名解析 |
| `sessions_count.sh` | 只读：孤儿 rddf-session 计数 |
| `ship_execution_mode.sh` | 轻量 / worktree 执行模式判定 |
| `ship_parallel.sh` | 并行 change 执行（含限流） |
| `skill_root.sh` | rdd-workflow skill 双根路径解析 |
| `state.sh` | 经 python3 做安全 JSON / YAML 读写的 shell helper |
| `wave_scheduler_hooks.sh` | WaveScheduler 的 bash 封装 |
| `worktree.sh` | Git worktree helper（从 guide/status/execute 抽出） |

#### §2.1.3 子包（Python package）

| Package | Purpose |
|---|---|
| `_lib/cli/` | `rddf` CLI 子命令实现（各 skill 的命令行入口） |
| `_lib/core/` | 底层原子件：文件锁、原子写 |
| `_lib/dashboard/` | 看板 / 状态汇总的读模型 |
| `_lib/iteration/` | iteration 状态读写、渲染、归档后处理 |
| `_lib/loop/` | Loop Engine：detector / action / 插件加载 |
| `_lib/plugins/` | 插件清单与注册 |
| `_lib/schedulers/` | cron / fs-watch / git-hook / webhook 调度器 |
| `_lib/schemas/` | JSON Schema 定义（harness / config / iteration 等） |
| `_lib/templates/` | 模板（layer0 使用说明等） |
| `_lib/verifier/` | verdict cache / audit log / discovery（ADR-0034） |

### §2.2 shim 层（`skills/_lib/`）

#### §2.2.1 Bash 转发（每个转发到同名真实现）

| Module | 转发目标 |
|---|---|
| `skills/_lib/archive.sh` | `_lib/archive.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/check_project_setup.sh` | `_lib/check_project_setup.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/discover-arch-artifacts.sh` | `_lib/discover-arch-artifacts.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/discover_ship_changes.sh` | `_lib/discover_ship_changes.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/env_checks.sh` | `_lib/env_checks.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/orchestrator_entry.sh` | `_lib/orchestrator_entry.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/parallel_throttle.sh` | `_lib/parallel_throttle.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/post_flow_wrap.sh` | `_lib/post_flow_wrap.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/resolve_skill_name.sh` | `_lib/resolve_skill_name.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/sessions_count.sh` | `_lib/sessions_count.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/ship_execution_mode.sh` | `_lib/ship_execution_mode.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/ship_parallel.sh` | `_lib/ship_parallel.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/skill_root.sh` | `_lib/skill_root.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/state.sh` | `_lib/state.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/wave_scheduler_hooks.sh` | `_lib/wave_scheduler_hooks.sh`（回退 `~/.agents/skills/_lib/`） |
| `skills/_lib/worktree.sh` | `_lib/worktree.sh`（回退 `~/.agents/skills/_lib/`） |

#### §2.2.2 Python identity-merge

| Module | 说明 |
|---|---|
| `skills/_lib/__init__.py` | 包入口：把 __path__ 指向 shim / 真实现 / 全局 fallback 三处 |
| `skills/_lib/_python_resolve_project_root.py` | skill 层 project_root wrapper（identity-merge 到真实现） |
| `skills/_lib/adr_catalog.py` | identity-merge 到 `_lib/adr_catalog.py` |
| `skills/_lib/arch_quality_gate.py` | identity-merge 到 `_lib/arch_quality_gate.py` |
| `skills/_lib/cleanup_plan_handoff.py` | identity-merge 到 `_lib/cleanup_plan_handoff.py` |
| `skills/_lib/contract_diff.py` | identity-merge 到 `_lib/contract_diff.py` |
| `skills/_lib/cross_repo_audit.py` | identity-merge 到 `_lib/cross_repo_audit.py` |
| `skills/_lib/cross_repo_deps.py` | identity-merge 到 `_lib/cross_repo_deps.py` |
| `skills/_lib/cross_repo_deps_cache.py` | identity-merge 到 `_lib/cross_repo_deps_cache.py` |
| `skills/_lib/cross_repo_gate.py` | identity-merge 到 `_lib/cross_repo_gate.py` |
| `skills/_lib/cross_repo_state.py` | identity-merge 到 `_lib/cross_repo_state.py` |
| `skills/_lib/gh_hub_client.py` | identity-merge 到 `_lib/gh_hub_client.py` |
| `skills/_lib/gh_repo_detect.py` | identity-merge 到 `_lib/gh_repo_detect.py` |
| `skills/_lib/hub_issue.py` | identity-merge 到 `_lib/hub_issue.py` |
| `skills/_lib/loop_engine.py` | identity-merge 到 `_lib/loop_engine.py` |
| `skills/_lib/parse_approved.py` | identity-merge 到 `_lib/parse_approved.py` |
| `skills/_lib/planner_feedback.py` | identity-merge 到 `_lib/planner_feedback.py` |
| `skills/_lib/state_reader.py` | identity-merge 到 `_lib/state_reader.py` |
| `skills/_lib/tasks_count.py` | identity-merge 到 `_lib/tasks_count.py` |

#### §2.2.3 子包 `__path__` 加宽

| Package | 说明 |
|---|---|
| `skills/_lib/cli/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |
| `skills/_lib/core/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |
| `skills/_lib/dashboard/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |
| `skills/_lib/iteration/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |
| `skills/_lib/loop/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |
| `skills/_lib/schedulers/` | 只有一个 `__init__.py`：把 `__path__` 加宽到真实现包并 re-export 其公开 API |

## §3 Helper Entry Points — project_root resolution

同一件事有三种调用形态，行为必须一致（见 §6）：

| Layer | 调用方式 | 用在哪 |
|---|---|---|
| Bash | `source` `_lib/orchestrator_entry.sh` 后调用 `_resolve_project_root` | bash 脚本 |
| Python（skill wrapper） | `from skills._lib._python_resolve_project_root import resolve_project_root` | skill 侧脚本 |
| Python（CLI dispatcher） | `from _lib.cli.__main__ import resolve_project_root` | `rddf` CLI |

**契约文件**：`_lib/_resolve_project_root_contract.yaml`（canonical）。
`skills/_lib/_resolve_project_root_contract.yaml` 只是指向它的兼容指针，**勿**在两处分别维护内容。

**已知语义边界**：`resolve_project_root` 返回 **canonical root**（worktree 场景下归一到主仓），
不是裸 `git rev-parse --show-toplevel`。依赖 toplevel 语义的新代码请先读契约文件。

## §4 ADR References

| ADR | 主题 | 与本目录的关系 |
|---|---|---|
| `ADR-0033` | submodule-aware project root resolution | project_root 三层解析 + canonical root 语义 |
| `ADR-0030` | hub-and-spoke federation | cross-repo 依赖 / 状态 / Hub 客户端 |
| `ADR-0007` | gate mechanism | 阶段门的两档 severity 与判定入口 |
| `ADR-0060` | ADR shape contract | ADR 形态检查（`arch_quality_gate.py`） |
| `ADR-0027` | continuous evolution feedback loop | issue 上报 / reflect 引擎 |
| `ADR-0010` | multi-session management | 并行会话管理 |
| `ADR-0012` | flow customization layer | trigger 引擎与注册表 |
| `ADR-0015` | integrate openspec validate as plan critic | 结构化 validate 输出 |
| `ADR-0062` | recommender single implementation | 阶段推荐阶梯唯一实现 |

## §5 Onboarding Guide — 如何新增一个 helper

1. **先确定层**：bash helper / Python 核心模块 / 跨仓模块 / skill wrapper？先在 §2 里找有没有同类可复用。
2. **在真实现层落地**：逻辑写在仓库根 `_lib/`（不是 `skills/_lib/`）—— shim 层只是转发面。
3. **遵守该层约定**：bash 用 `set -euo pipefail` 且优先 `source` 共享 helper；Python 核心模块带类型注解 + docstring；
   wrapper 用 lazy import + shim 形态（参照 `_python_resolve_project_root.py`）。
4. **补 shim**：需要在 skill 层可见时，在 `skills/_lib/` 加同名转发（bash）/ identity-merge（Python）；
   子包则由其 `__init__.py` 加宽 `__path__`。
5. **补契约测试**：跨层行为必须有一致性断言（参照 §6 的两个契约测试文件）。
6. **回填本文件 §2**：新模块登记进对应层的表格；目录规模变了就更新 §1 的快照日期。

## §6 Cross-Layer Consistency

bash 与 Python 两侧的同名 helper 必须行为一致，漂移由这两个契约测试盯住：

- `tests/unit/test_resolve_project_root_contract_bash.sh`
- `tests/unit/test_resolve_project_root_contract_python.py`

任一层需要偏离契约时：改**契约文件**并升版本号，同时写 ADR 说明偏离理由 —— 不要只在某一层打补丁。

## See Also

- `skills/_lib/INDEX.md` — 一页速查表
- `_lib/_resolve_project_root_contract.yaml` — project_root 解析契约
- `docs/adr/README.md` — ADR 索引（由 `_lib/adr_index_generator.py` 生成）
- `AGENTS.md` — 仓库级工作流约定与快速命令
