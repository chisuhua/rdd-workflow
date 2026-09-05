# ADR 索引

> rdd-workflow 架构决策记录 (Architecture Decision Records)

> ## 📊 v3.0+ ADR 实施状态（2026-08-28 同步 ADR-0034/0035）
>
> 本索引反映 **v3.0+** 代码现状（含 ADR-0025 引入的四阶段架构 arch → design → plan → ship，及 ADR-0034 扩展为五阶段架构 + `rdd-verifier` 第五阶段）。
> 各 ADR 的实施状态以代码为准 — 见链接的 ADR 文件正文。
>
> | 范围 | ADR |
> |------|-----|
> | 已实施（v2.0.0+） | 0001（双阶段，superseded by 0003）, 0002, 0003, 0004, 0005, 0006, 0007, 0008, 0013, 0023 |
> | 已实施（v2.0.1+） | 0017 |
> | 已实施（v2.0.2+） | 0020 |
> | 已实施（v2.0.8+） | 0018, 0019, 0021, 0022 |
> | 已实施（v2.0.9+） | 0024 |
> | 已实施（v2.0.6+） | 0025, 0026 |
> | 已实施（v2.1.x+） | 0027（拆分至 fix-adr-0027-cleanup / add-issue-reporter-prereqs / add-issue-reporter / add-issue-reporter-tests） |
> | 已实施（v2.0.5+） | 0016 |
> | 已实施（v3.0+） | 0034（rdd-verifier 五阶段）, 0035（verifier-archive-gate 边界） |
> | 部分实施（v2.0 轻量级） | 0010 |
> | 已采纳，未实施（v3.0 候选） | 0009（占位）, 0011, 0012 |
> | 已采纳（设计稿） | 0014, 0015 |

## ADR 列表

<!-- ADR_INDEX_START -->
| ADR | 标题 | 状态 | 日期 |
|-----|------|------|------|
| [ADR-0001](ADR-0001-propose-plan-execute-state-machine.md) | ADR-0001: rdd-workflow 状态机分相（spec 端 / ship 端状态机分离） | 已替代为 ADR-0002 + ADR-0003（已实施） | 2026-06-08 |
| [ADR-0002](ADR-0002-goal-driven-interaction-modes.md) | ADR-0002: 目标驱动接口与交互模式可配置化 | 已采纳 | 2026-06-22 |
| [ADR-0003](ADR-0003-three-phase-architecture.md) | ADR-0003: 三阶段架构重构 (arch → plan → ship) | 已采纳（v2.0 奠基 ADR） | 2026-06-22 |
| [ADR-0004](ADR-0004-loop-engine-core-design.md) | ADR-0004: Loop 引擎核心设计 | 已采纳 | 2026-06-22 |
| [ADR-0005](ADR-0005-human-in-loop-nodes.md) | ADR-0005: Human-in-Loop 节点定义与菜单系统 | 已采纳 | 2026-06-22 |
| [ADR-0006](ADR-0006-state-vector-event-log.md) | ADR-0006: 状态向量与事件流设计 | 已采纳 | 2026-06-22 |
| [ADR-0007](ADR-0007-gate-mechanism.md) | ADR-0007: 门控机制设计 (Gate Mechanism) | 已采纳 | 2026-06-22 |
| [ADR-0008](ADR-0008-tribunal-committee.md) | ADR-0008: 审判委员会设计 (Tribunal Committee) | 已采纳 | 2026-06-22 |
| [ADR-0009](ADR-0009-scheduled-triggers.md) | ADR-0009: 定时循环与事件触发（占位） | 模板（v3.0 候选占位） | 2026-06-22 |
| [ADR-0010](ADR-0010-multi-session-management.md) | ADR-0010: 多会话管理与并行执行 | ✅ 已采纳 + 已实施（v2.0 轻量 + v2.1 完整 + ADR-0017 rddf-session 用户层） | 2026-06-22 |
| [ADR-0011](ADR-0011-phase-step-pipeline-model.md) | ADR-0011: 阶段步骤化执行模型 | 已采纳 | 2026-06-22 |
| [ADR-0012](ADR-0012-flow-customization-layer.md) | ADR-0012: 流程定制层 | 已采纳 | 2026-06-22 |
| [ADR-0013](ADR-0013-extract-scan-state.md) | ADR-0013: Extract scan-state logic from skills/guide.md into skills/_lib/scan-state.sh | 已采纳 | 2026-07-07 |
| [ADR-0014](ADR-0014-review-phase-and-debt-reflow.md) | ADR-0014: Add execute-review phase and debt-reflow mechanism to three-phase workflow | 待定 | 2026-07-08 |
| [ADR-0015](ADR-0015-integrate-openspec-validate-as-plan-critic.md) | ADR-0015: Integrate `openspec validate` as the plan-critic gate for plan_done | 已采纳 | 2026-07-08 |
| [ADR-0016](ADR-0016-arch-artifact-discovery-contract.md) | ADR-0016: Arch 阶段工件发现契约 (Arch Artifact Discovery Contract) | 已采纳 | 2026-07-08 |
| [ADR-0017](ADR-0017-rddf-session.md) | ADR-0017: rddf-session — 用户视角工作流会话 | ✅ 已采纳（已实施） | 2026-07-09 |
| [ADR-0018](ADR-0018-arch-quality-gate.md) | ADR-0018: 架构质量门 — arch 阶段的定性检查 | ✅ 已采纳 | 2026-07-10 |
| [ADR-0019](ADR-0019-change-arch-alignment.md) | ADR-0019: change_arch_alignment — change 提案与架构对齐检查 | ✅ 已采纳 | 2026-07-10 |
| [ADR-0020](ADR-0020-incremental-skeleton-planning.md) | ADR-0020: Incremental Skeleton Planning | 已采纳（v2.0.2 archive 后切换） | 2026-07-08 |
| [ADR-0021](ADR-0021-phase2-per-skill-helper-migration.md) | ADR-0021: Phase 2 Per-Skill Helper Migration Strategy | 已采纳（v2.0.8 archive 后切换） | 2026-07-17 |
| [ADR-0022](ADR-0022-manual-deps-field.md) | ADR-0022: Manual Deps Field for roadmap-meta.yaml | 已采纳 | 2026-07-20 |
| [ADR-0023](ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md) | ADR-0023: v3.0.0 包名重命名 `spec-workflow` → `rdd-workflow` | 已采纳 | 2026-07-22 |
| [ADR-0024](ADR-0024-deps-driven-execution-mode.md) | ADR-0024: deps 阶段驱动执行模式决策 | 已采纳 | 2026-07-24 |
| [ADR-0025](ADR-0025-design-proposal-creation.md) | ADR-0025: design 阶段承担 openspec proposal 创建与内容审查 | 已采纳（v2.1 扩展 ADR） | 2026-08-02 |
| [ADR-0026](ADR-0026-internal-metadata-namespace-convention.md) | ADR-0026: rdd-workflow Internal Metadata Namespace Convention | 已采纳 | 2026-08-11 |
| [ADR-0027](ADR-0027-continuous-evolution-feedback-loop.md) | ADR-0027: 持续演进反馈环（Continuous Evolution Feedback Loop） | 已采纳（v2.1.x 系列 ADR） | 2026-08-12 |
| [ADR-0028](ADR-0028-role-model-per-phase.md) | ADR-0028: Role Model Per Phase | 已采纳（v2.0.8+ 系列） | 2026-08-14 |
| [ADR-0029](ADR-0029-issue-driven-proposal-creation.md) | ADR-0029: Issue-Driven Proposal Creation | 已采纳 | 2026-08-15 |
| [ADR-0030](ADR-0030-hub-and-spoke-federation.md) | ADR-0030: 多项目 AI 协同开发采用 Hub-and-Spoke 联邦架构 | 待定（v2.0.8+ 设计稿） | 2026-08-15 |
| [ADR-0031](ADR-0031-human-in-loop-cross-repo.md) | ADR-0031: 跨项目 RFC 必须人类决策（Human-in-Loop for Cross-Repo） | 已采纳 | 2026-08-15（2026-08-18 经 `fix-adr-0031-safety-gate-substantiation` 实质化后采纳） |
| [ADR-0032](ADR-0032-hub-federation-deepening.md) | ADR-0032: Hub 联邦深化 (Hub Federation Deepening) | 待定 | 2026-08-19 |
| [ADR-0033](ADR-0033-submodule-aware-project-root-resolution.md) | ADR-0033: Submodule-Aware Project Root Resolution | 待定 | 2026-08-25 |
| [ADR-0034](ADR-0034-rdd-verifier-verify-phase-architecture.md) | ADR-0034: rdd-verifier 验证回环阶段架构 | 已采纳 (2026-08-26) | 2026-08-26 |
| [ADR-0035](ADR-0035-verifier-archive-gate-boundary.md) | ADR-0035: rdd-verifier ↔ archive_gate_check 双轨设计边界 | 已采纳 | 2026-08-28 |
| [ADR-0036](ADR-0036-rddf-project-yaml-config.md) | ADR-0036: .rddf/project.yaml 项目级配置源 | 已采纳 (2026-09-02) | 2026-09-02 |
| [ADR-0037](ADR-0037-feedback-contract.md) | ADR-0037: Feedback Contract for `.rddf/improvements/*.md` | 已采纳 (2026-09-03) | 2026-09-03 |
| [ADR-0038](ADR-0038-rdd-planner-crosscutting.md) | ADR-0038: rdd-planner Horizontal Orchestrator (Stage 2) | 已采纳 (2026-09-03) | 2026-09-03 |
| [ADR-0039](ADR-0039-design-handoff-runtime-filter.md) | ADR-0039: design-handoff runtime filter over on-disk cleanup | 已采纳 (2026-09-01) | 2026-09-01 |
| [ADR-0040](ADR-0040-session-metrics.md) | ADR-0040: schema v3 add session metrics opt-in 字段 | 已采纳 (2026-09-01) | 2026-09-01 |
| [ADR-0041](ADR-0041-planner-sprint-lifecycle-and-history.md) | ADR-0041: Planner Sprint Lifecycle and History Storage | 已采纳 (2026-09-03) | 2026-09-03 |
| [ADR-0042](ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md) | ADR-0042: rdd-arch rename + rdd-arch ↔ rdd-planner 双向反馈闭环 | 已采纳 (2026-09-03) | 2026-09-03 |
| [ADR-0043](ADR-0043-rdd-workflow-v4-stage-merge.md) | ADR-0043: rdd-workflow v4 stage-merge architecture | 已采纳 (2026-09-04) | 2026-09-04 |
| [ADR-0044](ADR-0044-v4-stage-merge-wave3-hard-removal.md) | ADR-0044: v4 Stage Merge Wave 3 — Hard Removal of guide-* Skills | 已采纳 (2026-09-04) | 2026-09-04 |
<!-- ADR_INDEX_END -->

## 架构演进

```
v1.0 (2026-06-03)          v1.1 (2026-06-05)          v2.0 (2026-06-22)
─────────────────          ─────────────────          ─────────────────
单文件 guide.md     →      双阶段 spec/ship     →     三阶段 arch/plan/ship
(10 个 phase)              (ADR-0001)                 (ADR-0003)
                                                      +
                                                 Loop 引擎 (ADR-0004)
                                                      +
                                            三种交互模式 (ADR-0002)
                                                      +
                                         Human-in-Loop 节点 (ADR-0005)
                                                      +
                                           状态向量+事件流 (ADR-0006)
                                                      +
                                              门控机制 (ADR-0007)
                                                      +
                                          审判委员会 (ADR-0008)
                                                      +
                                        多会话管理 (ADR-0010)
                                           v2.0: 轻量级

v2.0.5 (2026-07-16)        v2.0.6 (2026-07-21)        v2.0.9+ (2026-08-04+)
─────────────────          ─────────────────          ─────────────────
per-skill scripts/    →    四阶段 arch/design/  →     全局安装 + deps 驱动
迁移 (ADR-0021)             plan/ship (ADR-0025)        执行模式 (ADR-0024)

v3.0+ (2026-08-26)
──────────────────
五阶段 arch/design/plan/ship/verify
(ADR-0034 + ADR-0035)
   ↓
rdd-verifier 第五阶段（批量 AC 验证 + bounded retry）
   ↓
双轨设计边界（rdd-verifier ↔ archive_gate_check，per ADR-0035）
```

## 决策依赖关系（v3.0+ 视角）

```
ADR-0001 (双阶段分离) ─→ ADR-0003 (三阶段重构) ─→ ADR-0025 (扩展为四阶段) ─→ ADR-0034 (扩展为五阶段)
                                                                                  ↓
                                                              ADR-0035 (verifier-archive-gate 边界)
                                                                                  ↓
ADR-0003 ─→ ADR-0002 (交互模式) ─→ ADR-0004 (Loop 引擎) ─→ ADR-0005 (Human-in-Loop)
                                                              ↓
                                                      ADR-0008 (审判委员会)
                                                              ↓
ADR-0006 (状态向量) ─→ ADR-0016 (arch-handoff v1) ─→ ADR-0024 (deps-driven exec mode)
                                                              ↓
                                                      ADR-0017 (rddf-session)
                                                              ↓
ADR-0007 (门控机制) ─→ ADR-0018 (arch_quality_gate) ─→ ADR-0019 (change_alignment)
                                                              ↓
ADR-0021 (per-skill scripts/ 迁移) ─→ ADR-0022 (manual_deps)
                                                              ↓
                                                  ADR-0023 (包名重命名 v3.0)
```

## 主题分类

### 架构设计
- ADR-0003: 三阶段架构重构 → ADR-0025: 扩展为四阶段（+ design）→ ADR-0034: 扩展为五阶段（+ rdd-verifier）→ ADR-0035: 双轨边界
- ADR-0004: Loop 引擎核心设计
- ADR-0011: 阶段步骤化执行模型 (v3.0 候选)

### 用户交互
- ADR-0002: 目标驱动接口与交互模式
- ADR-0005: Human-in-Loop 节点定义

### 状态管理
- ADR-0006: 状态向量与事件流设计（含记忆系统）

### 质量保障
- ADR-0007: 门控机制设计
- ADR-0008: 审判委员会设计（多 agent 交叉验证）
- ADR-0018: arch_quality_gate
- ADR-0019: change_arch_alignment

### 会话管理
- ADR-0010: 多会话管理与并行执行（v2.0 轻量级 + v2.1 完整）
- ADR-0017: rddf-session

### 契约与协议
- ADR-0016: arch-handoff v1 + 工件发现契约
- ADR-0022: manual_deps / manual_blocks 字段
- ADR-0024: deps-driven execution mode（写入 .plan-handoff.json）
- ADR-0025: design-handoff + 两层内容审查
- ADR-0023: 包名重命名（v3.0 BREAKING）

### 工程实践
- ADR-0013: scan-state 提取
- ADR-0020: 增量 skeleton planning
- ADR-0021: per-skill scripts/ 迁移

## 相关文档

- [`../architecture/README.md`](../architecture/README.md) — 当前架构快照（按主题拆分）
- [`../architecture/historical-evolution.md`](../architecture/historical-evolution.md) — 完整演进记录
- `../ONBOARDING.md` — 项目上手
- `../change-quality-guide.md` — change 质量等级
- `../proposal-suggestions-format.md` / `../proposal-approved-format.md` — 提案格式

## 命名规范

```
ADR-NNNN-<slug>.md
```

- `NNNN` 是 4 位零填充编号（`0001` 起递增；`0000` 保留为模板）
- `<slug>` 是 kebab-case 简短描述（建议 ≤ 50 字符）
- 模板永远是 `ADR-0000-template.md`（不要给真实 ADR 分配 0000）

## 状态生命周期

| 状态 | 含义 |
|------|------|
| `待定` | 已起草但尚未正式采纳 |
| `已采纳` | 当前生效 |
| `已拒绝` | 评估后未采纳（保留以记录历史） |
| `已弃用` | 曾生效但已被新决策替代 |
| `已替代为 ADR-NNN` | 显式指向替代者 |
| `已采纳，状态待核实` | 已采纳但代码状态未在本索引中显式核实 |

## 何时写一个 ADR

满足以下任一条件即应考虑：

- 引入新的工具 / 框架 / 库
- 修改工作流的关键路径（如 `propose → plan → execute`）
- 跨多个 skill 的契约变更
- 删除了某项重要功能
- 对安全 / 性能 / 可维护性有长期影响

## 何时**不**写

- 临时性 / 实验性改动（用 TODO 注释或 commit message 即可）
- 实现细节的微调（无架构影响）
- 已被其他 ADR 覆盖的重复决策

## 引用 ADR 的格式

```text
ADR-NNN §N.M
```

- `ADR-NNN` 是 ADR 编号
- `§N.M` 是模板中的小节编号（如 `§3.2` 指第 3 节的 3.2 小节）
- 消费者：`skills/propose.md` Phase 1a（扫描）、`skills/deps.md` Step 1b（提取 `adr_refs`）

## 如何使用 ADR

1. **引用格式**: `ADR-NNN §N.M` (例如: ADR-0003 §2.1)
2. **提案新 ADR**: 复制 `ADR-0000-template.md`，按编号命名
3. **更新状态**: 已采纳 → 已弃用/已替代时更新状态字段
4. **关联决策**: 在 Context 中引用相关 ADR

## 维护者

- 主要决策者: sisyphus
- 上次同步: 2026-09-03 (add-issue-reporter-tests — ADR-0027 完整 3-change 系列落地：prereqs + reporter + tests/docs)
- 下次审查: 新增 ADR 后

## 脚注

[^adr-0027-supersede]: §5 Triage superseded by ADR-0029 (2026-08-24); see clean-adr-0027-section-5-supersede proposal
