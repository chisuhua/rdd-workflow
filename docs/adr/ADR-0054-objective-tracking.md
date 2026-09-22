# ADR-0054: Objective 跟踪工件 (cross-sprint complex targets)

> **状态**: 已采纳
> **日期**: 2026-09-22
> **决策者**: rdd-planner + Oracle 2 轮审查 (session `ses_f37f04c17ffe`)
> **关系**: 接续 ADR-0048 (rdd-planner 独占 roadmap) + ADR-0042 (cross-stage feedback)

## Background

rdd-workflow 现有 roadmap 工件体系 (v2.2+):

| 工件 | 路径 | 维护模式 | 写入方 |
|------|------|----------|--------|
| 主文档 | `.rddf/roadmap.md` | 半自动 (rdd-arch CLI 维护 AUTO 段) | rdd-arch |
| Phase fragment | `.rddf/roadmap/phases/*.md` | 手工 | rdd-arch / rdd-planner |
| Feature fragment | `.rddf/roadmap/features/*.md` | **derived view** (零手工) | CLI 自动派生 |

**真实缺口**: 当一个"复杂目标"需要**多个 sprint + 多个 feature + 多个 openspec change**协同推进时 (例如 `bypass-audit-mechanism + hub-federation governance` 这种跨 sprint deferred objective), 没有对应的"目标级跟踪工件":

- feature fragment 是 derived view, 无法承载 planner 的手工修订意图 (deferral rationale, scope change, go-decision)
- openspec/changes 是单 change 视角, 无法跨 change 给出"目标完成度"全景
- 主文档 `.rddf/roadmap.md` 是状态快照, 无历史轨迹

**借鉴对象**: 外部 `/workspace/project/HydraForge/docs/roadmap/2026-09-16-pdk-chat-demo-evolution-roadmap.md` (984 行 Master Plan)。但其单文档 13 章节模式与 rdd-workflow **分片 + derived-view** 哲学冲突。

**Oracle 2 轮审查结论** (2026-09-22, session `ses_f37f04c17ffe`):

| 维度 | 裁决 |
|------|------|
| 命名 | `objective` (精确对齐用户用语;非 `program`/`track`/`initiative`) |
| 与 feature fragment 区别 | feature = derived view; objective = 手工 source-of-truth |
| 执行链路 | planner→builder→execute→verifier 90% 已存在; 缺 3 读写点 |
| 协作模式 | **串行** (planner 填 → builder 创建 change → execute → verifier → planner 复盘) |
| 写入权 | **rdd-planner 唯一写入** (避免 builder/execute 侵蚀) |
| evidence | v0.1 不开独立目录; §11 带 kind 列台账即可; v0.2 升级触发显式 |
| 依赖图 | 仅允许 §9.5 日期戳快照; 不内嵌 ASCII DAG |

## Decision

### D1: 新增第 4 类工件 `.rddf/roadmap/objectives/*.md`

不修改现有 features/phases 框架。新增目录 `.rddf/roadmap/objectives/` 由 rdd-planner 独占 owns。

### D2: 与 feature fragment 区分 (derived view vs source-of-truth)

| 维度 | feature fragment | objective |
|------|------------------|-----------|
| 维护模式 | derived view (零手工) | 手工 source-of-truth |
| 适用场景 | 跨 phase 聚合当前状态 | 跨 sprint 复杂目标叙事 |
| 时间粒度 | 当前快照 | 跨 sprint 历史轨迹 |
| 写入方 | CLI 自动派生 | rdd-planner |
| 决策规则 | "纯结构聚合用 feature" | "需要跨 sprint 目标叙事用 objective" |

### D3: 写入权归 rdd-planner (per ADR-0028 扩展)

避免 builder/execute 隐式写 objective 侵蚀 rdd-planner 单门控。`planner_stage_exit.sh` 是唯一允许刷新 `AUTO-OBJECTIVES` 哨兵段的入口。

### D4: 协作模式串行

每 sprint 收尾由 planner 触发复盘仪式, **不**在 sprint 内增量修订 objective 文件。避开 iteration.json 多 hook 写竞争。

### D5: Status 词汇 4 值 + Kind 词汇 5 值

- **Status** (4 值): `active` / `deferred` / `completed` / `archived`
- **Kind** (5 值, 用于 §11 跟踪台账): `deferral-rationale` / `go-decision` / `sprint-review` / `scope-change` / `adr-amendment`

### D6: frontmatter 9 必填字段

`id` / `status` / `created` / `last_revised` / `review_by` / `owner` (const `rdd-planner`) / `priority` (P0/P1/P2) / `manual_deps` / `theme`

`review_by` 是 **D2 grace 90 天机器可执行锚点**; 缺失则 doctor 标 WARNING。

### D7: section 规则 (手写 vs derived)

**手写段** (planner 必填或条件必填): §1 / §2 (含完成判据) / §3 (条件必有: 有 ADR 必引用) / §5 (可选) / §9 / §10 / §11

**derived 段** (CLI 实时渲染, 不手写): §6 (当前状态) / §7 (关联 features) / §8 (关联 changes) / §9.5 (DAG snapshot)

### D8: "N/A — <理由>" 格式约束 (D9 in design)

deferred objective 的 §10 必填项允许此格式, 但禁止静默留空 (无法区分"不适用"和"忘了填")。`N/A` 必须后接 em-dash + ≥1 字符理由。

### D9: §9.5 DAG snapshot 写入时机

仅 sprint 复盘时由 planner 显式调 `rddf roadmap snapshot-objective <id>`。**禁止自动 hook 重生成** (违反唯一写入点 + 噪音 commit)。

格式强制: 时间戳 + `> Snapshot derived at <date>, regenerate: rddf deps <objective>` + fenced code block。

### D10: rdd-doctor 新增 2 个巡检类别

- `objective-lifecycle`: review_by grace + status 一致性
- `objective-structure`: frontmatter + section + kind enum + N/A 格式

**不**新增 `objective-evidence-drift` 新鲜度巡检 (避免 doctor 退化为考勤机, 详见 Oracle #5)。

## 工件区分矩阵 (4-class)

| 工件 | 路径 | 维护模式 | 时间粒度 | 写入方 |
|------|------|----------|----------|--------|
| 主文档 | `.rddf/roadmap.md` | 半自动 | 当前状态 | rdd-arch |
| Phase fragment | `.rddf/roadmap/phases/*.md` | 手工 | 当前阶段 | rdd-arch / rdd-planner |
| Feature fragment | `.rddf/roadmap/features/*.md` | **derived view** | 当前快照 | CLI 自动派生 |
| **Objective** | `.rddf/roadmap/objectives/*.md` | **手工 source-of-truth** | **跨 sprint 目标叙事** | **rdd-planner** |
| Openspec change | `openspec/changes/<n>/` | 全自动 | 单 change | rdd-builder |

**决策规则** (写进 AGENTS.md + objective schema 注释):

> "纯结构聚合 → 用 feature fragment (免费、自动、零维护); 需要跨 sprint 目标叙事与复盘记录才建 objective (手工、planner 季度修订)"

## Module Structure

### Production Code (新增)

| 文件 | 行数估算 | 职责 |
|------|----------|------|
| `_lib/schemas/objective_schema.json` | ~30 | JSON Schema v1 |
| `_lib/objective.py` | ~200 | Parser + validator + grace helper + derive stub |
| `_lib/cli/roadmap_cmd.py` | +50 | 7 objective subcommands 注册 |
| `skills/roadmap/scripts/objective_*.sh` | 7 × ~30 = ~210 | Bash wrappers (env-var pattern per Oracle C1) |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | +30 | AUTO-OBJECTIVES refresh hook |
| `skills/rdd-doctor/scripts/checks/objective_lifecycle_check.py` | ~50 | 生命周期 grace check |
| `skills/rdd-doctor/scripts/checks/objective_structure_check.py` | ~60 | 结构 invariant check |

### Documentation (新增/修改)

| 文件 | 行数估算 | 职责 |
|------|----------|------|
| `docs/adr/ADR-0054-objective-tracking.md` | (本文件) | 架构决策 |
| `AGENTS.md` | +30 | objective 工件段 (feature vs objective 决策表) |
| `README.md` | +3 | skill list |
| `.rddf/roadmap/objectives/objective-bypass-audit-hub-governance.md` | ~60 | PoC #1 (deferred) |
| `.rddf/roadmap/objectives/objective-onboard-new-skill.md` | ~40 | PoC #2 (active) |

### Tests (新增)

| 文件 | 用例数 |
|------|--------|
| `tests/unit/test_objective.py` | 31 ✅ ALL PASS |

## Consequences

### 正面

1. **跨 sprint 复杂目标终于有 source-of-truth 工件**: 避免依赖隐式 session 记忆或 git history 重建上下文
2. **planner 季度修订节奏明确**: sprint 收尾仪式化, 降低 cognitive overhead
3. **依赖图快照可审计**: 跨 repo objective 的依赖 (rddf deps 静态分析覆盖不到) 通过人工转录显式化
4. **rdd-planner 治理边界扩展但守住**: 新增 owns 不破坏既有边界, planner 仍是 roadmap 单一门控

### 负面

1. **新工件增加 cognitive load**: AGENTS.md / SKILL.md / CLI 文档都要解释何时建 feature / 何时建 objective
2. **PoC 占用 2 个 objective 文件位**: v0.1 限制 2 个, 验证后扩到 3-5 个常用场景
3. **§9.5 快照有 staleness 风险**: 必须用时间戳 + regenerate 命令强制格式让 reader 知道是派生数据
4. **AGENTS.md AUTO-OBJECTIVES 段会膨胀**: 每个 objective 1 行, 10 个 = 10 行表格; 超 20 个考虑聚合摘要

## Implementation Status

| Component | Status |
|-----------|--------|
| `_lib/objective.py` + schema | ✅ DONE |
| 7 bash wrappers | ✅ DONE |
| rdd-doctor 2 categories wired | ✅ DONE |
| planner_stage_exit AUTO-OBJECTIVES hook | ✅ DONE |
| PoC #1 (deferred) + PoC #2 (active) | ✅ DONE |
| 31 unit tests | ✅ ALL PASS |
| `openspec validate --strict` | ✅ PASS |
| ADR-0054 (本文件) | ⏳ PENDING (本次变更) |
| AGENTS.md objective 段 | ⏳ PENDING |
| README.md skill list row | ⏳ PENDING |

## References

- Oracle session `ses_f37f04c17ffe` (2026-09-22) — 2 轮审查: 命名/D4-D6 论证段/D5 evidence/D6 依赖图/骨架瘦身的全部裁决
- `/workspace/project/HydraForge/docs/roadmap/2026-09-16-pdk-chat-demo-evolution-roadmap.md` (984 行) — 借鉴对象 (单文档 Master Plan)
- ADR-0028 — role-model per phase (写入权归 rdd-planner 的依据)
- ADR-0022 — manual_deps 字段 (objective 的 manual_deps 复用)
- ADR-0042 — rdd-planner ↔ rdd-builder feedback channel (cross-stage)
- ADR-0048 — rdd-planner 独占 roadmap (boundary 强化)
- ADR-0053 — rdd-env-bootstrap orchestrator (同类"治理编排层"参考实现)
- AGENTS.md 关键术语对照表 (improvement vs openspec proposal vs objective 的术语边界)
- `openspec/changes/add-objective-tracking/` — 本 change 完整 proposal + design + tasks
