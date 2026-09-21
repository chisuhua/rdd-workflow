# JSON Schema 索引

> rdd-workflow 项目所有结构化数据的 JSON Schema 集中索引。
> Schema 真实落点在仓库根 `_lib/schemas/`（canonical，29 个文件）；
> `skills/_lib/schemas/` 是向后兼容 shim 层（per P1-1b flatten layout, 2026-08-25）。
> 改 schema **必须 bump `version` 字段**；schema 消费者拒绝 `version=0` payload。

---

## 总览

| 分组 | 数量 | 用途 |
|------|------|------|
| [核心运行时](#核心运行时-core) | 1 | 状态向量原子持久化 |
| [配置与扩展](#配置与扩展-config) | 4 | 配置 / 插件 / 角色 / 触发器 |
| [阶段 handoff](#阶段-handoff-stage-handoff) | 7 | 跨阶段交接契约 |
| [视图与状态](#视图与状态-view) | 6 | 派生视图与多 hook 写入的 state 文件 |
| [跨 repo / hub](#跨-repo--hub-cross-repo) | 6 | Hub-and-Spoke 联邦通道 |
| [verifier / quick](#verifier--quick-verification) | 5 | 验证回环 + 旁路审计 |
| [env-bootstrap](#env-bootstrap) | 1 | 4-phase 环境编排报告 |
| **合计** | **30** | 截至 2026-09-22 |

---

## 核心运行时 (core)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`state_vector_schema.json`](../../_lib/schemas/state_vector_schema.json) | v1 | `.rddf/state/.state-vector.json` | `state_vector.py::atomic_write` | 全部 detector/action |

---

## 配置与扩展 (config)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`config_schema.json`](../../_lib/schemas/config_schema.json) | v1 | `.rddf/config.json` | `config.py::load` | loop 引擎 |
| [`plugin_manifest_schema.json`](../../_lib/schemas/plugin_manifest_schema.json) | v1 | `plugins/*/manifest.yaml` | plugin loader | loop 引擎 plugin 注册 |
| [`skill_role_schema.json`](../../_lib/schemas/skill_role_schema.json) | v1 | inline in `skills/*/SKILL.md` frontmatter `role:` | SKILL.md 编辑 | rdd-arch/planner/builder/verifier 边界校验 (per ADR-0028) |
| [`trigger_schema.json`](../../_lib/schemas/trigger_schema.json) | v1 | `.rddf/triggers/*.yaml` | trigger_registry | trigger_engine |

---

## 阶段 handoff (stage handoff)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`arch_handoff_schema.json`](../../_lib/schemas/arch_handoff_schema.json) | v1 | `.rddf/state/.arch-handoff.json` | `rdd-arch` arch-done | `rdd-planner` stage entry + propose/roadmap/gate/detectors/actions/scan-state |
| [`design_handoff_schema.json`](../../_lib/schemas/design_handoff_schema.json) | v1 | `.rddf/state/.design-handoff.json` | `rdd-planner`（legacy design-done, per ADR-0044 RETIRE） | legacy fallback |
| [`plan_handoff_schema.json`](../../_lib/schemas/plan_handoff_schema.json) | v1 | `.rddf/state/.plan-handoff.json` | `rdd-planner`（legacy plan-done, per ADR-0044 RETIRE） | legacy fallback |
| [`planner_handoff_schema.json`](../../_lib/schemas/planner_handoff_schema.json) | **v1.1** | `.rddf/state/.planner-handoff.json` | `rdd-planner` stage exit (per ADR-0048 §Decision 2) | `rdd-builder` P0 dispatch-quick (REQUIRED `recommended_route`) |
| [`planner_state_schema.json`](../../_lib/schemas/planner_state_schema.json) | v1 | `.rddf/state/.planner-state.json` | `rdd-planner` | planner advisor |
| [`builder_handoff_schema.json`](../../_lib/schemas/builder_handoff_schema.json) | v1 | `.rddf/state/builder/<change>.json` | `rdd-builder` P0-P3 | `rdd-builder` 内 P0/P1/P1.5/P2/P2.5/P3 流转 |
| [`builder_retry_schema.json`](../../_lib/schemas/builder_retry_schema.json) | v1 | `.rddf/state/builder/<change>.retry.json` | `rdd-verifier` 失败回路由 | `rdd-builder` P1/P2 重试 |

> ⚠️ **ADR-0044 Wave 3 hard removal**：`design_handoff` 和 `plan_handoff` 已 RETIRE，v4 现写 `.planner-handoff.json`（schema v1.1）+ `.rddf/state/builder/<change>.json`。Wave 1 共存期内保留 legacy schema 读取作为 fallback。

---

## 视图与状态 (view)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`iteration_schema.json`](../../_lib/schemas/iteration_schema.json) | v1 | `.rddf/state/iteration.json` | `propose` / `rdd-builder` / `execute` / `deps` / `archive` 多 hook | `feature` / `status` / `guide` 扫描器 |
| [`feature_view_schema.json`](../../_lib/schemas/feature_view_schema.json) | v1 | `.rddf/state/feature-view.json` | `feature` 子技能 | `feature graph/status/order` |
| [`sessions_schema.json`](../../_lib/schemas/sessions_schema.json) | v1 | `.rddf/state/sessions.json` | `rddf-session` 5 子命令 | `guide` binding scan |
| [`deps_analysis_schema.json`](../../_lib/schemas/deps_analysis_schema.json) | v1 | `.rddf/state/deps-analysis.json` | `deps` Step 5b | `rdd-builder` P1.5 execution_mode 决策 |
| [`feedback_entry_schema.json`](../../_lib/schemas/feedback_entry_schema.json) | v1 | `.rddf/state/.planner-feedback.json` | `rdd-builder` Phase 2 ADR-drift → `_lib/builder_feedback_router.py` | `rdd-planner` advisory feedback |
| [`improvement_frontmatter_schema.json`](../../_lib/schemas/improvement_frontmatter_schema.json) | v1 | `.rddf/improvements/*.md` frontmatter | `add-improve` | `rdd-builder` P0 pre-flight |

---

## 跨 repo / hub (cross-repo)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`cross_repo_pending_schema.json`](../../_lib/schemas/cross_repo_pending_schema.json) | v1 | `.rddf/state/.cross-repo-pending.json` | `rddf report-issue` | `sync-hub` / `watch-hub` |
| [`cross_repo_deps_cache_schema.json`](../../_lib/schemas/cross_repo_deps_cache_schema.json) | v1 | `.rddf/state/.cross-repo-deps-cache.json` | `cross_repo_deps.py` (24h TTL) | `cross_repo_gate` |
| [`cross_repo_audit_schema.json`](../../_lib/schemas/cross_repo_audit_schema.json) | v1 | `.rddf/state/.cross-repo-audit.jsonl` | `cross_repo_audit.py` | `cross-repo-protocol` MCP |
| [`contract_cache_schema.json`](../../_lib/schemas/contract_cache_schema.json) | v1 | `.rddf/state/.contract-cache.json` | `sync-hub` | `contract-check` |
| [`hub_metrics_schema.json`](../../_lib/schemas/hub_metrics_schema.json) | v1 | `.rddf/state/hub-metrics.json` | `watch-hub` | dashboard |
| [`mcp_trace_schema.json`](../../_lib/schemas/mcp_trace_schema.json) | v1 | `.rddf/state/mcp-trace.jsonl` | `cross-repo-protocol` MCP client | `report-issue` |

> 完整跨 repo 协议说明见 [`cross-repo-schemas.md`](cross-repo-schemas.md)。

---

## verifier / quick (verification)

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`ac_verdict_cache_schema.json`](../../_lib/schemas/ac_verdict_cache_schema.json) | v2 | `.rddf/state/.ac-verdict-<change>.json` | `rdd-verifier` Step 5 (SHA-fingerprint cache) | archive_gate_check |
| [`verifier_audit_schema.json`](../../_lib/schemas/verifier_audit_schema.json) | v1 | `.rddf/state/.ac-verification.jsonl` | `rdd-verifier` Step 5 (append-only) | `rdd-doctor --category plan-tdd` |
| [`verifier_loop_schema.json`](../../_lib/schemas/verifier_loop_schema.json) | v2 | `.rddf/state/verifier/<change>.json` | `rdd-verifier` route_loop.sh | `rdd-builder` retry 决策 |
| [`quick_history_schema.json`](../../_lib/schemas/quick_history_schema.json) | v1 | `.rddf/state/.quick-history.jsonl` | `rdd-quick` 审计 | `rdd-doctor --category bypass-audit` |
| [`rdd_quick_context_schema.json`](../../_lib/schemas/rdd_quick_context_schema.json) | v1 | `.rddf/state/rdd-quick-context.json` | `rdd-builder` P0 case 5 dispatch-quick | `rdd-quick` entry (per ADR-0048 amendment) |

> ⚠️ `ac_verdict_cache_schema.json` 已从 v1 → v2（per `verifier-v2-hardening` closure）。如果 `.rddf/state/` 残留 v1 文件，`rdd-doctor --category state` 会报警。

---

## env-bootstrap

| Schema | Version | 路径 | 写入方 | 消费者 |
|---|---|---|---|---|
| [`env_bootstrap_report_schema.json`](../../_lib/schemas/env_bootstrap_report_schema.json) | v1 | `.rddf/state/.env-bootstrap-report.json` | `rddf env-bootstrap` (4-phase orchestrator) | `rdd-doctor --category state` |

---

## 维护约定

### 命名规范

`<domain>_<noun>_schema.json` — domain 为功能域（arch / planner / builder / verifier / quick / cross_repo 等），noun 为对象类型（handoff / state / view / cache / audit 等）。

### 修改流程

1. **必须 bump `version` 字段**（v1 → v2 → v3 ...）
2. **更新本 README 对应行**（确保 SSOT）
3. **写 migration 指南**（如果 breaking change）
4. **跑 `rdd-doctor --category state`** 验证无残留旧 version
5. **CI `tests/unit/test_*_schema.py`** 锁定 schema 字段不变（每 schema ≥ 1 test）

### 双路由（per AGENTS.md 25 段）

- **canonical 路径**：仓库根 `_lib/schemas/`
- **shim 路径**：`skills/_lib/schemas/`（P1-1b flatten layout, 2026-08-25；向后兼容历史 import）

新增代码 **必须 import `_lib.X`**（canonical），历史 `skills._lib.X` 调用继续兼容。

---

## See Also

- [`../adr/ADR-0016-arch-artifact-discovery-contract.md`](../adr/ADR-0016-arch-artifact-discovery-contract.md) — arch 发现契约
- [`../adr/ADR-0018-arch-quality-gate.md`](../adr/ADR-0018-arch-quality-gate.md) — arch 质量门（含 schema validation）
- [`../adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md`](../adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md) — planner feedback schema
- [`../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md`](../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md) — legacy handoff RETIRE
- [`../adr/ADR-0048-v4-stage-merge-revision.md`](../adr/ADR-0048-v4-stage-merge-revision.md) — `.planner-handoff.json` v1.1 schema 新增 `recommended_route`
- [`../adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md`](../adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md) — ac_verdict_cache v2
- `cross-repo-schemas.md` — 跨 repo 协议补充说明