---
id: phase-1
kind: phase
status: active
phase_refs: []
主题: 定时循环与事件触发
---

## phase-1 概览

Phase 1 覆盖 17 个已实施 ADR / 4 个占位或待定 ADR / 10 个架构文档锚点。按主文档 `## Phase Skeleton` 表格，本阶段包含 3 个并列 theme：

| Theme | ADR 覆盖 | 状态 |
|-------|----------|------|
| 完整多会话支持 | [ADR-0010](../../docs/adr/ADR-0010-multi-session-management.md), [ADR-0014](../../docs/adr/ADR-0014-review-phase-and-debt-reflow.md), [ADR-0017](../../docs/adr/ADR-0017-rddf-session.md) +1 | 已实施 |
| 定时循环与事件触发 | [ADR-0004](../../docs/adr/ADR-0004-loop-engine-core-design.md), [ADR-0006](../../docs/adr/ADR-0006-state-vector-event-log.md), [ADR-0009](../../docs/adr/ADR-0009-scheduled-triggers.md) | 已实施 |
| 提案生成阶段 — 自动跨仓分析 (A1/A2/A3) | [ADR-0003](../../docs/adr/ADR-0003-three-phase-architecture.md), [ADR-0007](../../docs/adr/ADR-0007-gate-mechanism.md), [ADR-0010](../../docs/adr/ADR-0010-multi-session-management.md) +10 | 已实施 |

## 已实施能力

- **ADR-0003** — [三阶段架构重构 (arch → plan → ship)](../../docs/adr/ADR-0003-three-phase-architecture.md) *（已实施 v2.0.6+）*
  - 我们将双阶段架构重构为**三阶段架构**（arch → plan → ship），按**人工介入程度**和**职责类型**切分：

- **ADR-0004** — [Loop 引擎核心设计](../../docs/adr/ADR-0004-loop-engine-core-design.md)
  - 我们实现 **Loop 引擎**作为 rdd-workflow v2.x 的核心编排器，采用 **Detector-Action 架构** + **状态向量** + **事件流**：

- **ADR-0005** — [Human-in-Loop 节点定义与菜单系统](../../docs/adr/ADR-0005-human-in-loop-nodes.md)
  - 我们定义 **7 类关键节点**，每类节点有统一的菜单格式、配置项、跳过条件：

- **ADR-0006** — [状态向量与事件流设计](../../docs/adr/ADR-0006-state-vector-event-log.md)
  - 我们引入 **统一状态向量 (State Vector)** + **事件流 (Event Log)** 作为 v2.x 的核心状态管理机制：

- **ADR-0007** — [门控机制设计 (Gate Mechanism)](../../docs/adr/ADR-0007-gate-mechanism.md)
  - 我们实现**门控机制 (Gate Mechanism)** 作为阶段切换的验证层：

- **ADR-0008** — [审判委员会设计 (Tribunal Committee)](../../docs/adr/ADR-0008-tribunal-committee.md)
  - 我们实现**基于 oh-my-opencode 的审判委员会**机制：

- **ADR-0011** — [阶段步骤化执行模型](../../docs/adr/ADR-0011-phase-step-pipeline-model.md)
  - 我们引入 **步骤化执行模型 (Step Pipeline Model)**，将每个阶段从"黑盒"拆分为**可编排的步骤序列**，同时保持与 ADR-0004 的兼容：

- **ADR-0013** — [Extract scan-state logic from skills/guide.md into skills/_lib/scan-state.sh](../../docs/adr/ADR-0013-extract-scan-state.md)
  - Extract the scan logic into a sourced library at `skills/_lib/scan-state.sh`,

- **ADR-0016** — [Arch 阶段工件发现契约 (Arch Artifact Discovery Contract)](../../docs/adr/ADR-0016-arch-artifact-discovery-contract.md)
  - 我们引入 **arch 工件发现契约 (Arch Artifact Discovery Contract)**，在 arch 阶段新增**轻量发现步骤**，将发现的工件路径持久化到现有 `.arch-handoff.json`，下游消费者（plan/ship/Library）优先读 handoff 路径，缺失时回退到硬编码默认。

- **ADR-0018** — [架构质量门 — arch 阶段的定性检查](../../docs/adr/ADR-0018-arch-quality-gate.md)
  - 我们引入 **`arch_quality_gate`** —— arch-done 阶段的 4 个 warning 级定性检查，默认不阻塞，`STRICT_ARCH_GATE=yes` 环境变量升级为 error（仅 CI 启用）。

- **ADR-0019** — [change_arch_alignment — change 提案与架构对齐检查](../../docs/adr/ADR-0019-change-arch-alignment.md)
  - 我们引入 **`change_arch_alignment`** —— `plan_done` 阶段的 3 个 warning 级检查，默认不阻塞，`STRICT_CHANGE_GATE=yes` 升级为 error（仅 CI 启用）。

- **ADR-0023** — [v3.0.0 包名重命名 `spec-workflow` → `rdd-workflow`](../../docs/adr/ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md) *（已实施 v3.0.0）*
  - 1. **包名统一为 `rdd-workflow`**（用户选择，放弃 `rddf-workflow` 更一致的替代方案）。

- **ADR-0024** — [deps 阶段驱动执行模式决策](../../docs/adr/ADR-0024-deps-driven-execution-mode.md)
  - **在 plan 阶段的 deps 分析时就决定执行模式**，并将决策写入 `.plan-handoff.json`，`guide-ship` 直接读取使用。

- **ADR-0025** — [design 阶段承担 openspec proposal 创建与内容审查](../../docs/adr/ADR-0025-design-proposal-creation.md) *（已实施 v2.0.9+）*
  - 将"创建 + 审查"前移到 design 阶段的批准动作：

- **ADR-0028** — [Role Model Per Phase](../../docs/adr/ADR-0028-role-model-per-phase.md)
  - 在 4 个阶段 SKILL.md 的 YAML frontmatter 中添加 `role:` 顶层字段，包含 5 个子字段：

- **ADR-0029** — [Issue-Driven Proposal Creation](../../docs/adr/ADR-0029-issue-driven-proposal-creation.md)
  - Use a 3-step priority chain. Explicit env override (`RDDF_PROPOSAL_GH_REPO`) is highest priority because it allows fork/override scenarios. `gh repo view` is second because it correctly handles auth s

- **ADR-0031** — [跨项目 RFC 必须人类决策（Human-in-Loop for Cross-Repo）](../../docs/adr/ADR-0031-human-in-loop-cross-repo.md)
  - **确立"跨项目 RFC 必须人类决策"原则**：所有 `**分类**: cross-repo-federation` 的提案，AI **不可自动批准**。必须由**人类维护者**通过交互式 prompt 确认后才能进入下一阶段。

## 架构文档锚点

| 文档 | 与本 phase 关联 |
|------|----------------|
| [Extension Points](../../docs/architecture/extension-points.md) | This doc is for contributors. It captures the **how** for the most common extension operations: adding a skill, a detect... |
| [Gates and Quality](../../docs/architecture/gates-and-quality.md) | Four quality mechanisms, each with a different scope and severity model. |
| [Historical Evolution](../../docs/architecture/historical-evolution.md) | This document records the **architectural** milestones — the points at which the system's structure changed, not every r... |
| [Loop Engine](../../docs/architecture/loop-engine.md) | The Loop engine (ADR-0004) is the runtime that turns a **goal** into a sequence of **plan → execute → verify → adapt** c... |
| [架构差距分析: multi-project-ai-collaborative-development](../../docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md) | 构建 **Hub-and-Spoke（中心辐射型）联邦协同架构**，将 rdd-workflow 从"单兵作战利器"升级为"集团军协同指挥系统"，支持企业级多团队、多项目 AI 协同开发。 |
| [Multi-Session Management](../../docs/architecture/multi-session.md) | A **session** in rdd-workflow is the user's perspective on a single workflow run: which change they're working on, which... |
| [Overview](../../docs/architecture/overview.md) | rdd-workflow is an **OpenSpec-compatible AI development workflow package**. It manages changes via a five-stage lifecycl... |
| [Skills and Handoff Protocol](../../docs/architecture/skills-and-handoff.md) | A **skill** is a `SKILL.md` file with YAML frontmatter that an AI coding assistant can discover and invoke. rdd-workflow... |
| [State and Events](../../docs/architecture/state-and-events.md) | rdd-workflow runs without a database. Instead, state lives in **three distinct layers**, each with a different read/writ... |
| [Workflow Phases](../../docs/architecture/workflow-phases.md) | rdd-workflow v2.1+ runs every change through **four phases** in order: |

## 占位 / 未实施

### ADR-0009 — 定时循环与事件触发（占位）

- **状态**：模板（v3.0 候选占位）
- **关键决策**：**当前决策**：编号占位（v2.0 发布前保持编号序列稳定），不实施任何具体功能。
- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖
- **后续**：
  1. 更新 ADR 正文，列出具体决策点
  2. 在 `add-improve` 流程中创建对应 implementation change
  3. 经 design-done gate 进入 plan-done 后归档

### ADR-0014 — Add execute-review phase and debt-reflow mechanism to three-phase workflow

- **状态**：待定
- **关键决策**：我们在 `guide-ship` Phase 2 (execute) 和 Phase 3 (archive) 之间插入 **Phase 2.5: review** 阶段，并提供完整的债务回流机制。
- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖
- **后续**：
  1. 更新 ADR 正文，列出具体决策点
  2. 在 `add-improve` 流程中创建对应 implementation change
  3. 经 design-done gate 进入 plan-done 后归档

### ADR-0030 — 多项目 AI 协同开发采用 Hub-and-Spoke 联邦架构

- **状态**：待定
- **关键决策**：**采用 Hub-and-Spoke（中心辐射型）联邦协同架构**：构建独立的中枢仓库 `rdd-hub` 作为跨项目契约、全局决策和协同看板的 SSOT（Single Source of Truth），各业务仓库（Spoke）保留本地 RDD 状态机自治，通过 GitHub MCP 协议与 Hub 通信。Hub 是「跨项目协同层」，**不侵入单项目的 arch → design → plan →
- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖
- **后续**：
  1. 更新 ADR 正文，列出具体决策点
  2. 在 `add-improve` 流程中创建对应 implementation change
  3. 经 design-done gate 进入 plan-done 后归档

### ADR-0032 — Hub 联邦深化 (Hub Federation Deepening)

- **状态**：待定
- **关键决策**：**确立"提案生成含跨仓分析 → 审批交互定 RFC 内容 → approve 后自动发 RFC"三阶段闭环**：
- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖
- **后续**：
  1. 更新 ADR 正文，列出具体决策点
  2. 在 `add-improve` 流程中创建对应 implementation change
  3. 经 design-done gate 进入 plan-done 后归档

## 主题注册表映射

主文档 `## Phase Skeleton` 表格中 phase-1 共 3 行（3 个 theme）。本 fragment 是这些 theme 的 **聚合根**，单 fragment 多 theme 模式：

- "完整多会话支持" → 阅上文 主题相关 ADR 段（已实施或占位）
- "定时循环与事件触发" → 阅上文 主题相关 ADR 段（已实施或占位）
- "提案生成阶段 — 自动跨仓分析 (A1/A2/A3)" → 阅上文 主题相关 ADR 段（已实施或占位）

## 相关变更历史

- `2026-06-28-v2-multi-session`
- `2026-06-28-v3-roadmap`
- `2026-07-08-add-incremental-skeleton-planning`
- `2026-07-09-add-rddf-session`
- `2026-07-14-rddf-session-binding`

## 下一步

Phase 1 → [phase-2](../phases/phase-2.md)
