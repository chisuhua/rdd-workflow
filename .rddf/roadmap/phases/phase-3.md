---
id: phase-3
kind: phase
status: active
phase_refs: []
主题: 审批后自动发 RFC
主题: 流程定制层
---

## phase-3 概览

Phase 3 覆盖 3 个已实施 ADR / 1 个占位或待定 ADR / 10 个架构文档锚点。按主文档 `## Phase Skeleton` 表格，本阶段包含 2 个并列 theme：

| Theme | ADR 覆盖 | 状态 |
|-------|----------|------|
| 审批后自动发 RFC (C1/C2) | [ADR-0031](../../docs/adr/ADR-0031-human-in-loop-cross-repo.md), [ADR-0032](../../docs/adr/ADR-0032-hub-federation-deepening.md) | 已实施 |
| 流程定制层 | [ADR-0012](../../docs/adr/ADR-0012-flow-customization-layer.md) | 已实施 |

## 已实施能力

- **ADR-0012** — [流程定制层](../../docs/adr/ADR-0012-flow-customization-layer.md)
  - 我们引入 **流程定制层 (Flow Customization Layer)**，允许用户通过配置文件定制步骤模板，采用以下核心设计：

- **ADR-0027** — [持续演进反馈环（Continuous Evolution Feedback Loop）](../../docs/adr/ADR-0027-continuous-evolution-feedback-loop.md)
  - 我们引入**持续演进反馈环（Continuous Evolution Feedback Loop）**，由 5 个环节组成：

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

### ADR-0032 — Hub 联邦深化 (Hub Federation Deepening)

- **状态**：待定
- **关键决策**：**确立"提案生成含跨仓分析 → 审批交互定 RFC 内容 → approve 后自动发 RFC"三阶段闭环**：
- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖
- **后续**：
  1. 更新 ADR 正文，列出具体决策点
  2. 在 `add-improve` 流程中创建对应 implementation change
  3. 经 design-done gate 进入 plan-done 后归档

## 主题注册表映射

主文档 `## Phase Skeleton` 表格中 phase-3 共 2 行（2 个 theme）。本 fragment 是这些 theme 的 **聚合根**，单 fragment 多 theme 模式：

- "审批后自动发 RFC (C1/C2)" → 阅上文 主题相关 ADR 段（已实施或占位）
- "流程定制层" → 阅上文 主题相关 ADR 段（已实施或占位）

## 相关变更历史

- `2026-06-28-v2-multi-session`
- `2026-06-28-v3-roadmap`
- `2026-07-08-add-incremental-skeleton-planning`
- `2026-07-09-add-rddf-session`
- `2026-07-14-rddf-session-binding`

## 下一步

Phase 3 → [phase-4](../phases/phase-4.md)
