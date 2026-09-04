# ADR-0043: rdd-workflow v4 stage-merge architecture

> **Status**: 已采纳 (2026-09-04)
> **Date**: 2026-09-04
> **决策者**: sisyphus + brainstorming session + Oracle review (session `ses_f74594271ffeqRViAn2Vd85RJ9`) + Metis review

## Context

rdd-workflow 在 v3.0+ 是 5 阶段架构 (arch → design → plan → ship → verify, per ADR-0034)。
阶段治理债过重,用户对"压缩阶段 + planner 升级"提出重构需求(2026-09-04 brainstorming session)。

**Stage 1 之前状态**: Stage 2 (feedback contract + planner status/sync) 已落地,Stage 3 (rdd-arch rename + planner feedback) 已落地。
**本 ADR 范围**: v4 架构总决策 + Wave 1 交付范围 + 3-wave 迁移路径。

详细 spec 见 `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (1003 行, 87 AC items)。

## Decision

采用 v4 4 阶段架构:

```
rdd-arch (slim) → rdd-planner → rdd-builder (6-phase) → rdd-verifier
```

### 1. rdd-arch slim — ADR-0042 v2.1 升级

- 移除 `_lib/gate.py::_check_roadmap_defined` 函数 + arch_done gate 注册
- 移除 `.arch-handoff.json` 3 个字段 (top-level `roadmap_path`/`roadmap_exists`; nested `discovered.roadmap_path`)
- contract v2 → v3 (enum [1, 2, 3])
- v1/v2 backward compat 经 `additionalProperties: true` (top-level + discovered)
- rdd-arch 不再生成 roadmap-related 数据; 这些职责移交给 rdd-planner

### 2. rdd-planner stage promotion — Stage 1/2 lib 包装

- 新增 `skills/rdd-planner/SKILL.md` (Stage 2 入口)
- 新增 `_lib/planner_handoff.py` + `_lib/schemas/planner_handoff_schema.json` (v1)
- 新增 `skills/rdd-planner/scripts/{planner_stage_entry,planner_stage_exit}.sh`
- 既有 `_lib/planner_*.py` (status/sync/feedback/attach/audit/history/advance-sprint) 保持不变
- 双重身份: 顺序阶段(arch → planner) + 横切编排器(任意时刻可调)

### 3. rdd-builder NEW — 6-phase 状态机

```
P0 (approval) → P1 (plan) → P1.5 (deps + exec_mode) → P2 (execute) → P2.5 (review) → P3 (archive)
                                └─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

- **P0** approval: 4-option HARD pause (approve/reject/defer/revise); reject/defer/revise 走 `rddf feedback add` (ADR-0037 single-writer)
- **P1** plan gen: `rdd-workflow-writing-plans` + plan_quality gate + tasks.md scaffolding
- **P1.5** deps + exec_mode: `builder_deps.py::decide_execution_mode` (worktree vs lightweight per ADR-0024); STRICT_DEPS_GATE 阻断; legacy `.plan-handoff.json` fallback 期间
- **P2** execute: COMMIT GATE (per spec §3.4 Q6) + worktree select + TDD 5 步
- **P2.5** review: 4-option HARD pause (merge/revise/abandon/archive); exit 5 for revise/abandon
- **P3** archive: verifier pre-call (5-value exit 0/1/2/3/4 保留 per Oracle H4) + retry loop + back-route 至 P1/P2

**Per-change handoff** (per Oracle H3):
- 单文件 `.rddf/state/.builder-handoff.json` → `.rddf/state/builder/<change>.json` (per-change layout)
- per-file `FileLock` + 字段: `change_name`, `current_phase`, `retry_count`, `retry_history`, `phase_pause_history`, `execution_mode_decision`, `deps_status`, `worktree_path`, `branch`, `archive_status`

**Pause contract** (per spec §5.2 + Oracle M1):
- HARD pause at P0 / P2.5 (mandatory even with `--no-pause`)
- SOFT pause at P1 / P1.5 / verifier back-route (skippable via `--no-pause`)
- `--from-phase N`: resume from arbitrary phase
- `--retry-on-fail`: auto-back-route on verifier verdict

**Exit codes** (per spec §5.2 + Oracle H4 fix):
- 0 = success
- 1 = P0 rejected/deferred
- 2 = plan quality FAIL
- 3 = worktree / COMMIT GATE fail
- 4 = verifier halted
- 5 = review revise/abandon
- 6 = deps gate FAIL
- 7 = archive gate FAIL

### 4. rdd-verifier 保持独立 (per ADR-0034 + 用户 Q2 决策)

不并入 rdd-builder; 保留 5-stage 中的独立阶段; 挂载在 builder.archive 之前的 hook。

### 5. Cross-stage feedback (per spec §3.5 batch 4)

新增通道: `rdd-builder → rdd-arch` (Phase 2 ADR-drift detection → `rddf feedback add --kind ac-fail` → `_lib/builder_feedback_router.py` 路由至 `.planner-feedback.json`)
- Architect 读 advisory via `rddf arch feedback`
- 默认 ON; architect opt-in via `rddf planner feedback --accept-builder-source {yes|no}` (Wave 2 引入)

### 6. 迁移路径 — 3-wave "新并存"

- **Wave 1 (本 ADR + Wave 1 plan)**: 新增 skills + schemas + libs + CLI + tests。旧 skill (guide-design/plan/ship) 完全不动。
- **Wave 2**: 旧 skill 加 DEPRECATED banner + shim routes guide-* CLI 至 rdd-builder + `.shim-usage.jsonl` 埋点 (CI 可见)
- **Wave 3**: 硬删除 guide-design/plan/ship + install.sh cleanup + recommend guide rewrite + ADR 索引同步。trigger: ≥4 weeks + shim 埋点 zero ≥7 days OR `rdd doctor --check stage-merge` 0 users

### 7. D2a → D2b 反转

原 D2a (Stage 1 spec 决策): "no design/plan merge" — 显式否决合并 guide-design + guide-plan,担心 governance gate 与 planning gate 合并会丢失 human-in-loop checkpoints。

新 D2b (本 ADR 反转): design/plan/ship 三者合并为 rdd-builder,理由:
1. Approval gate 是子步骤而非独立阶段
2. Plan quality gate (`evaluate_plan`) 可内嵌 Phase 1
3. 3 个 skill 共享 plumbing 太多
4. rdd-arch slim + planner 正名创建清晰 4-stage 边界

**Checkpoint 损失显式承认 + 缓解**:
- Conceded loss: `rddf builder run` 单次 CLI invocation 执行 P0→P3,失去 3-skill 自然会话边界
- Mitigation: HARD pause at P0 / P2.5 (mandatory); per-phase CLI (`rddf builder phaseN`) 保留完整 checkpoint 粒度

## Consequences

### 正面

- ✅ 5-phase → 4-stage 认知负担降低
- ✅ rdd-arch 与 roadmap 解耦 (per 用户首问)
- ✅ rdd-planner 拥有完整 proposal/feature 生命周期
- ✅ rdd-builder 4-合一消除 plumbing 重复
- ✅ per-change handoff 防止并行 build 串改事故 (per Oracle H3)
- ✅ verifier 5-value exit 语义保留 (per Oracle H4)
- ✅ 跨阶段反馈通道显式化 (per batch 4)
- ✅ D2b 反驳 ADR-0038 (净阶段数 5→4 下降,原拒绝理由在数量上不成立)

### 负面 / 风险

- ⚠️ D2b 反转存在不可逆性 — Wave 3 删除 3 个 skill 后回退成本高
- ⚠️ D2b checkpoint 损失 (3-skill session 边界 → 1-skill run; HARD pause 缓解)
- ⚠️ per-change handoff 强制 FileLock timeout 10s (per Metis Q3 WARN); 不允许 exponential retry
- ⚠️ planner/builder 越界写收敛到 `rddf feedback add` (per Oracle M2)

### 兼容性

- ✅ `.arch-handoff.json` v1/v2 经 `additionalProperties: true` 兼容 (per spec §6.2 batch 2)
- ✅ `.plan-handoff.json::execution_mode_decisions` legacy fallback 在 Wave 1 期间 (per Oracle C2)
- ✅ Legacy `rddf-session` intent (guide-design/plan/ship) 在 Wave 1 保持 literal; shim 推迟 Wave 2 (per Metis Q1)
- ✅ `approve_proposal.sh::generate_spec_delta` 解耦 from guide-design; 用 inline Python helper (per Metis Q1)

## References

- Spec: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (1003 行, 87 AC)
- Plan: `.rddf/plans/v4-stage-merge-wave1.md` (3329 行, 19 tasks, TDD 5 步, 3329 行 ≥69 unit test 目标)
- Oracle review: `ses_f74594271ffeqRViAn2Vd85RJ9` (verdict: defer-pending-changes → 修订完成)
- Metis review: `ses_f9330b34bffeybmxM4J359Yjyq` (verdict: execute-after-fixes → 修订完成)
- Related ADRs: ADR-0037 (feedback), ADR-0038 (planner), ADR-0041 (sprint lifecycle), ADR-0042 (arch rename + planner feedback), ADR-0034 (verifier), ADR-0035 (verifier-archive-gate boundary)

## Implementation

Wave 1 PR 由 `.rddf/plans/v4-stage-merge-wave1.md` 驱动,共 19 tasks。Wave 2/3 另写独立 plan。