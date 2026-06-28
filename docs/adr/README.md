# ADR 索引

> spec-workflow 架构决策记录 (Architecture Decision Records)

> ## 📊 v2.0 ADR 实施状态（2026-06-28）
>
> | ADR | 标题 | 实施状态 | 目标版本 |
> |-----|------|---------|---------|
> | [ADR-0001](ADR-0001-propose-plan-execute-state-machine.md) | 双阶段状态机分离 (spec/ship) | ✅ 已实施（v1.x） | 已完成（v1.x） |
> | [ADR-0002](ADR-0002-goal-driven-interaction-modes.md) | 目标驱动接口与交互模式 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0003](ADR-0003-three-phase-architecture.md) | 三阶段架构重构 (arch → plan → ship) | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0004](ADR-0004-loop-engine-core-design.md) | Loop 引擎核心设计 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0005](ADR-0005-human-in-loop-nodes.md) | Human-in-Loop 节点 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0006](ADR-0006-state-vector-event-log.md) | 状态向量与事件流 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0007](ADR-0007-gate-mechanism.md) | 门控机制 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0008](ADR-0008-tribunal-committee.md) | 审判委员会 | ✅ 已实施 | 已完成（v2.0） |
> | [ADR-0009](ADR-0009-scheduled-triggers.md) | 定时循环与事件触发 | ❌ 未实施（v2.1 候选） | **v3.0** |
> | [ADR-0010](ADR-0010-multi-session-management.md) | 多会话管理 | ⚠️ 部分实施（v2.0 轻量级） | **v2.1（完整版）** |
> | [ADR-0011](ADR-0011-phase-step-pipeline-model.md) | 阶段步骤化执行模型 | ❌ 未实施（设计已采纳） | **v3.0** |
> | [ADR-0012](ADR-0012-flow-customization-layer.md) | 流程定制层 | ❌ 未实施（设计已采纳） | **v3.0** |
>
> **图例**：✅ 已实施 | ⚠️ 部分实施 | ❌ 未实施
> **目标版本**：未来 ADR 的实施版本；已完成 ADR 显示实际发布的版本。

## ADR 列表

| ADR | 标题 | 状态 | 日期 | 关键决策 |
|-----|------|------|------|---------|
| [ADR-0000](ADR-0000-template.md) | ADR 模板 | 模板 | - | ADR 格式规范 |
| [ADR-0001](ADR-0001-propose-plan-execute-state-machine.md) | 双阶段状态机分离 (spec/ship) | 已替代为 ADR-0002+0003 | 2026-06-08 | guide 拆分为 guide-spec + guide-ship |
| [ADR-0002](ADR-0002-goal-driven-interaction-modes.md) | 目标驱动接口与交互模式配置 | 已采纳 (修订) | 2026-06-22 | 三种交互模式 + 设计先行阶段 |
| [ADR-0003](ADR-0003-three-phase-architecture.md) | 三阶段架构重构 (arch → plan → ship) | 已采纳 | 2026-06-22 | 按人工介入程度切分三阶段 |
| [ADR-0004](ADR-0004-loop-engine-core-design.md) | Loop 引擎核心设计 | 已采纳 (修订) | 2026-06-22 | 5 大构建块 + 多 Agent 协作 |
| [ADR-0005](ADR-0005-human-in-loop-nodes.md) | Human-in-Loop 节点定义 | 已采纳 (修订) | 2026-06-22 | 三种验证模式 + 节点策略 |
| [ADR-0006](ADR-0006-state-vector-event-log.md) | 状态向量与事件流设计 | 已采纳 (修订) | 2026-06-22 | 统一状态向量 + 记忆系统 |
| [ADR-0007](ADR-0007-gate-mechanism.md) | 门控机制设计 | 已采纳 | 2026-06-22 | error/warning 两级 + 插件扩展 |
| [ADR-0008](ADR-0008-tribunal-committee.md) | 审判委员会设计 | 已采纳 | 2026-06-22 | 多 agent 交叉验证 + 数据脱敏 |
| [ADR-0009](ADR-0009-scheduled-triggers.md) | 定时循环与事件触发（占位） | 待定（v2.1 候选） | 2026-06-22 | 编号占位，v2.1 候选 |
| [ADR-0010](ADR-0010-multi-session-management.md) | 多会话管理与并行执行 | 已采纳（分阶段） | 2026-06-22 | v2.0 轻量级 + v2.1 完整实现 |
| [ADR-0011](ADR-0011-phase-step-pipeline-model.md) | 阶段步骤化执行模型 | 已采纳 | 2026-06-22 | 模板+触发器 + 步骤引擎 + 中断恢复 |
| [ADR-0012](ADR-0012-flow-customization-layer.md) | 流程定制层 | 已采纳 | 2026-06-22 | 增量覆盖 + 条件触发 + 自定义技能 |

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

v2.1 (候选)
─────────────────
完整会话管理 (ADR-0010)
  - 真正并行（多进程）
  - 依赖图调度器
  - 动态负载均衡

声明式流程 DSL (v2.1 候选)
  - 完全自定义流程编排
  - 条件分支 + 并行步骤
  - 基于 ADR-0011 + ADR-0012 升级
```

## 决策依赖关系

```
ADR-0001 (双阶段分离)
    ↓
ADR-0003 (三阶段重构) ──→ ADR-0002 (交互模式)
    ↓                        ↓
ADR-0004 (Loop 引擎) ←───────┘
    ↓
ADR-0005 (Human-in-Loop) ──→ ADR-0008 (审判委员会)
    ↓                            ↓
ADR-0006 (状态向量) ←────────────┘
    ↓
ADR-0007 (门控机制)
    ↓
ADR-0010 (多会话管理)
  v2.0: 轻量级
  v2.1: 完整实现

## 主题分类

### 架构设计
- ADR-0001: 双阶段状态机分离
- ADR-0003: 三阶段架构重构
- ADR-0004: Loop 引擎核心设计
- ADR-0007: 门控机制设计

### 用户交互
- ADR-0002: 目标驱动接口与交互模式
- ADR-0005: Human-in-Loop 节点定义

### 状态管理
- ADR-0006: 状态向量与事件流设计（含记忆系统）

### 质量保障
- ADR-0008: 审判委员会设计（多 agent 交叉验证）

### 会话管理
- ADR-0010: 多会话管理与并行执行（v2.0 轻量级 + v2.1 完整）

### 工程实践
- ADR-0000: ADR 模板

## 相关文档

- `docs/audit/2026-06-05-workflow-audit.md` — v1.1 审计报告（38 个问题）
- `README.md` — 项目概览和使用指南
- `USAGE.md` — 完整工作流说明
- `skills/` — 技能文件目录
- `openspec/` — OpenSpec 变更管理目录

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

从 `proposal-suggestions.md` 的 `source` 字段引用 ADR 时：

```json
"source": "ADR-NNN §N.M"
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
- 审计日期: 2026-06-22
- 下次审查: v2.0 发布前

