# ADR 索引

> rdd-workflow 架构决策记录 (Architecture Decision Records)

> ## 📊 v2.0.9+ ADR 实施状态（2026-08-07 同步 docs-restructure）
>
> 本索引反映 **v2.0.9+** 代码现状（含 ADR-0025 引入的四阶段架构 arch → design → plan → ship）。
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
> | 部分实施（v2.0 轻量级） | 0010 |
> | 已采纳，未实施（v3.0 候选） | 0009（占位）, 0011, 0012 |
> | 已采纳（设计稿） | 0014, 0015 |

## ADR 列表

| ADR | 标题 | 状态 | 关键决策 |
|-----|------|------|---------|
| [ADR-0001](ADR-0001-propose-plan-execute-state-machine.md) | 双阶段状态机分离 (spec/ship) | 已替代为 ADR-0003 | guide 拆分为 guide-spec + guide-ship |
| [ADR-0002](ADR-0002-goal-driven-interaction-modes.md) | 目标驱动接口与交互模式配置 | 已采纳 | 三种交互模式 + 设计先行阶段 |
| [ADR-0003](ADR-0003-three-phase-architecture.md) | 三阶段架构重构 (arch → plan → ship) | 已采纳 | 按人工介入程度切分三阶段（v2.0.6+ 由 ADR-0025 扩展为四阶段） |
| [ADR-0004](ADR-0004-loop-engine-core-design.md) | Loop 引擎核心设计 | 已采纳 | 5 大构建块 + 多 Agent 协作 |
| [ADR-0005](ADR-0005-human-in-loop-nodes.md) | Human-in-Loop 节点定义 | 已采纳 | 三种验证模式 + 节点策略 |
| [ADR-0006](ADR-0006-state-vector-event-log.md) | 状态向量与事件流设计 | 已采纳 | 统一状态向量 + 记忆系统 |
| [ADR-0007](ADR-0007-gate-mechanism.md) | 门控机制设计 | 已采纳 | error/warning 两级 + 插件扩展 |
| [ADR-0008](ADR-0008-tribunal-committee.md) | 审判委员会设计 | 已采纳 | 多 agent 交叉验证 + 数据脱敏 |
| [ADR-0009](ADR-0009-scheduled-triggers.md) | 定时循环与事件触发（占位） | 已采纳（v3.0 候选） | 编号占位，v3.0 候选 |
| [ADR-0010](ADR-0010-multi-session-management.md) | 多会话管理与并行执行 | 已采纳（v2.0 轻量级） | v2.0 轻量级 + v2.1 完整实现 |
| [ADR-0011](ADR-0011-phase-step-pipeline-model.md) | 阶段步骤化执行模型 | 已采纳（v3.0 候选） | 模板+触发器 + 步骤引擎 + 中断恢复 |
| [ADR-0012](ADR-0012-flow-customization-layer.md) | 流程定制层 | 已采纳（v3.0 候选） | 增量覆盖 + 条件触发 + 自定义技能 |
| [ADR-0013](ADR-0013-extract-scan-state.md) | scan-state 提取 | 已采纳 | 拆分 scan-state.sh → `_lib/scan-state.sh` |
| [ADR-0014](ADR-0014-review-phase-and-debt-reflow.md) | Review 阶段债务回流机制 | 已采纳（设计稿） | 债务回流 4 选项 + 文件冲突驱动 deps |
| [ADR-0015](ADR-0015-integrate-openspec-validate-as-plan-critic.md) | openspec validate 集成为 plan-critic | 已采纳（设计稿） | 把 openspec validate 接入 plan-done 门控 |
| [ADR-0016](ADR-0016-arch-artifact-discovery-contract.md) | Arch 阶段工件发现契约 | 已采纳 | 扩展 `.arch-handoff.json` v1 + 替换 14+ 处硬编码路径 |
| [ADR-0017](ADR-0017-rddf-session.md) | rddf-session 用户视角工作流会话 | 已采纳 | 项目级 `sessions.json` 持久化 + 4 选项软提示冲突处理 + 跨 OpenCode session 恢复 |
| [ADR-0018](ADR-0018-arch-quality-gate.md) | 架构质量门 — arch 阶段的定性检查 | 已采纳 | 4 个 warning 级检查 (alignment/debt/clarity/actionable) + `STRICT_ARCH_GATE=yes` CI 升级 |
| [ADR-0019](ADR-0019-change-arch-alignment.md) | change_arch_alignment — change 提案与架构对齐检查 | 已采纳 | 3 个 warning 级检查 (refs_valid/no_contradiction/task_traceability) + `STRICT_CHANGE_GATE=yes` 独立 env var |
| [ADR-0020](ADR-0020-incremental-skeleton-planning.md) | 增量 skeleton planning | 已采纳 | 引入 `planned` 状态 + 6 个关键子决策 |
| [ADR-0021](ADR-0021-phase2-per-skill-helper-migration.md) | Phase 2 per-skill helper migration | 已采纳 | Per-skill scripts/ 目录迁移 |
| [ADR-0022](ADR-0022-manual-deps-field.md) | manual_deps 人工依赖声明 | 已采纳 | `manual_deps`/`manual_blocks` 字段 |
| [ADR-0023](ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md) | v3.0.0 包名重命名 | 已采纳 | `spec-workflow` → `rdd-workflow` (BREAKING) |
| [ADR-0024](ADR-0024-deps-driven-execution-mode.md) | deps 阶段驱动执行模式决策 | 已采纳 | 执行模式在 plan 阶段决定并写入 handoff |
| [ADR-0025](ADR-0025-design-proposal-creation.md) | design 阶段提案创建 + 内容审查 | 已采纳 | 设计管理独立成阶段 + 两层内容审查 |
| [ADR-0026](ADR-0026-internal-metadata-namespace-convention.md) | 内部元数据命名空间约定 | 已采纳 | `>` blockquote 元数据命名规范 |
| [ADR-0027](ADR-0027-continuous-evolution-feedback-loop.md) | 持续演进反馈环 | 已采纳 | Detect→Buffer→Report→Triage→Close 五环 + 复用 `_lib/config.py` + 三重 opt-in + 幂等 close + Oracle 复核 8/8/7 |
| [ADR-0029](ADR-0029-issue-driven-proposal-creation.md) | Issue-Driven Proposal Creation | 已采纳 | 新增 `add-improve --from-issue` 模式 + repo-neutral `close_issues.py` 修复 |
| [ADR-0030](ADR-0030-hub-and-spoke-federation.md) | Hub-and-Spoke 联邦协同架构 | 待定 | 多项目 AI 协同开发采用 Hub 仓库 + L2 升级双向协同通道 + 6 项安全风险 + 3 个月复核 |
| [ADR-0031](ADR-0031-human-in-loop-cross-repo.md) | 跨项目 RFC 必须人类决策 | 已采纳 | 跨项目提案 AI 不可自动批准 + `RDDF_REQUIRE_HUB_APPROVAL` 强制门控 + 审计 log + 无 Spoke 端 bypass |
| [ADR-0032](ADR-0032-hub-federation-deepening.md) | Hub 联邦深化 | 待定 | 4 个 P0 change (跨仓分析/RFC 草稿/审批交互/自动发 RFC) + 9 change 总览 + 3 个月复核窗口 2026-11-15 |

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
```

## 决策依赖关系（v2.0.9+ 视角）

```
ADR-0001 (双阶段分离) ─→ ADR-0003 (三阶段重构) ─→ ADR-0025 (扩展为四阶段)
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
- ADR-0003: 三阶段架构重构 → ADR-0025: 扩展为四阶段
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
- 上次同步: 2026-08-12 (add-issue-reporter-tests — ADR-0027 完整 3-change 系列落地：prereqs + reporter + tests/docs)
- 下次审查: 新增 ADR 后
