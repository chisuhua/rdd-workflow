# ADR-0058: gap-analysis 实例迁移到 theme doc（multi-project-ai-collaborative-development）

> **状态**: 已采纳
> **日期**: 2026-09-30
> **决策者**: rdd-workflow maintainer
> **取代**: `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`（删除）
> **关联**: ADR-0057（gap-analysis 协议整体删除）、ADR-0030（hub-and-spoke-federation 决策）、ADR-0031（human-in-loop cross-repo）、ADR-0032（hub-federation-deepening）

## Context

ADR-0057（v2.2.0）删除 rdd-arch 的 gap-analysis 工件类型。唯一现存实例 `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`（185 行，2026-08-15 生成）需迁移。

本 ADR 解决两个问题：
1. **§1+§2+§5 的设计叙事**：目标架构（Hub-and-Spoke 联邦）、当前架构（rdd-workflow v4）、参考资料（10 个 ADR + 3 个现有架构文档 + 4 个现有代码模块）需要新归宿——即一个 hub-and-spoke-federation theme doc。
2. **§3+§4 的差距清单与补齐路径**：10 个 gap + Step 1/1.5/2/3/3.5/5/6 的实现步骤，其中 8 个已有对应 `.rddf/improvements/*.md`（已批准或已 complete），2 个部分覆盖。

新 ADR 替代旧 gap-analysis（per ADR-0057 §Out of Scope 与本章 §In Scope "写新 ADR 记录决定"）。

## Decision

**删除旧 gap-analysis 文件；新建 1 个 theme doc 承载叙事；不创建新的 `.rddf/improvements/*.md` 文件（现有 8 个已覆盖）。**

### 影响范围

- **In Scope**:
  - 新建 `docs/architecture/hub-and-spoke-federation.md`（主题文档，承载 §1+§2+§5 叙事）
  - 删除 `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`（git 即归档，无需 `.archive/` 目录）
  - 在 `docs/architecture/README.md` Doc Map 注册新 theme doc
  - 新 theme doc 末尾附"差距 → 实现映射表"，列出 10 个 gap 与对应 `.rddf/improvements/*.md` 状态（用于追溯，但不复制 §3 表的全部字段）
- **Out Scope**:
  - 不修改任何 `.rddf/improvements/*.md`（已存在的不动）
  - 不修改 `docs/adr/ADR-0030/0031/0032` 的 References（这些 ADR 文本引用了 gap-analysis 文件路径，但 link-only 引用，删除文件后 link 失效是 cosmetic，可由后续 doc-drift 清理批次修复）
  - 不创建 `.archive/` 目录（git history 即归档）
  - 不实现 10 个 gap 的任何代码（gap 与 implementation 已在 `.rddf/improvements/*.md` 中独立跟踪）
  - 不修改 `docs/architecture/README.md` 中对 gap-analysis 的历史引用（已迁移为"已删除 per ADR-0057"标注待后续清理批次）

### 备选方案

| 备选 | 理由 |
|------|------|
| **A. 删除 + 新建 1 个 theme doc**（本 ADR）| YAGNI；现有 8 个 improvement 已覆盖；theme doc 是 rdd-arch 的核心工件（per ADR-0057 §Decision） |
| B. 保留 gap-analysis 文件但改名 `*-archived-*.md` | 留作历史参考；但 git history 已永久保留该文件——再保留副本 = clutter，且违反 ADR-0057 §Decision 的"双工件类型"原则 |
| C. 拆分 10 个 gap 为 10 个独立 improvement 文件 | 已有 8 个 improvement 文件；重复创建是浪费；2 个部分覆盖的 gap（#10 rddf-session 联邦化 + #9 L2 上报扩展性）已有相关 improvement（`add-rddf-session-auto-archive-on-entry.md` + `add-rdd-hub-cross-repo-federation.md`）覆盖大部分内容 |
| D. 创建独立决策文件 `rdd-arch-audit-rdd-hub.md` 承担 gap-analysis 内容 | 引入新工件类型；与 ADR-0057 §Decision 的"双工件"原则冲突 |

## Consequences

### 正面

- **rdd-arch 工件类型从 3 减到 2**（per ADR-0057）：现在严格 ADR + theme doc 双工件
- **不创建任何新 improvement 文件**：10 个 gap 中 8 个已有对应文件（已批准/已 complete），避免重复
- **theme doc 是 rdd-arch 的核心叙事载体**：未来读者找 Hub-and-Spoke 联邦设计不再需要依赖被删除的 gap-analysis 文件
- **git 即归档**：删除操作留下 git history，零维护成本；不需要 30 天归档期约定
- **新 theme doc "新归宿 + 映射表"** 既保住了"单文档说完整故事"价值（虽然故事已散落在多文件），又通过映射表提供 traceability

### 负面 / 风险

- **ADR-0030/0031/0032 的 References 链接断链**：这些 ADR 文本引用了旧 gap-analysis 文件路径；删文件后这些 link 失效。cosmetic 问题，可由后续 doc-drift 清理批次修复。**缓解**：本 ADR 顶部明确记录此 ADR 取代旧文件，作为补救参考。
- **新 theme doc 没有 §3 表格的全部字段**：原 §3 有"严重程度/优先级/关联 change"列；新 theme doc 仅保留"gap → 实现状态"映射（丢失"关联 change"列）。**缓解**：原"关联 change"列实际指向的都是 openspec change proposal ID，与已实现的 improvement 无 1:1 关系（很多 improvement 不对应单个 openspec change）；信息保真度损失可接受。
- **读者可能期望 gap-analysis 在 docs/architecture/ 下还能找到**：删除后目录少一个文件，可能短暂困惑。**缓解**：README.md Doc Map 立即注册新 theme doc；arch_audit_check.py 删除了 gap-analysis 引用，不会有"找不到"的运行时警告。
- **`_lib/phase_templates.yaml` 的 `identify_gaps` step 仍引用 `gap_analysis.md`**：这是 Loop 引擎 v2.0 的 5-step pipeline 通用模板，与 rdd-arch 工件类型无关。**缓解**：本 ADR 明确 out-of-scope；如需清理应由独立批次处理。

### 后续待办

- [ ] **rdd-doc-drift batch (Phase B-后)**: 清理 `ADR-0030/0031/0032` 对旧 gap-analysis 文件路径的引用；更新 `workflow-phases.md` / `v4-pipeline-data-flow.md` / `overview.md`（per Oracle 🟡 标记）；更新 `AGENTS.md` / `USAGE.md`
- [ ] **`_lib/phase_templates.yaml` `identify_gaps` step（独立批次）**: 评估是否要删除 `gap_analysis.md` 输出名（避免命名混淆）—out of scope for 本 ADR
- [x] **rdd-planner Phase 0 增强（Phase C）**: 实现 `rdd-planner` Phase 0 读 `.arch-handoff.json::architecture_dir` 并提示 LLM 读 theme docs 作为目标态输入（per Metis 简化建议 C1+C5）—— **已完成 (2026-09-30)**：在 `skills/rdd-planner/SKILL.md` 新增 "Architecture-Aware Planning Guidance（v1.0, per ADR-0058）" 段，镜像 Objective-Aware v1.2 段结构，包含触发/数据源/LLM 推理任务/行为契约/输出格式 5 部分 + 3 个 wording guard（local-only / read-only / stale-fallback）

## 10 Gap 覆盖状态映射（实施证据）

| Gap # | gap 描述（来自旧 §3） | 对应 `.rddf/improvements/` | 状态 |
|-------|---------------------|--------------------------|------|
| 1 | Hub Repo 概念缺失 | `add-rdd-hub-cross-repo-federation.md` + `add-rdd-hub-bootstrap.md` | 已批准 2026-08-15 |
| 2 | Hub Projects V2 看板未接入 | `add-rdd-hub-bootstrap.md`（skill `rdd-hub-bootstrap` 存在） | 已实施 |
| 3 | 跨项目 RFC 流程缺失 | `add-rdd-hub-cross-repo-federation.md` | 已批准（`skills/report-issue/` + `skills/cross-repo-protocol/`） |
| 4 | MCP Server 协议缺失 | `add-mcp-cross-repo-protocol.md` | 已批准（`skills/cross-repo-protocol/` 存在） |
| 5 | AI 兜底机制未强化 | `add-strict-human-approval-for-cross-repo-changes.md` | 已批准 2026-08-15 |
| 6 | 跨项目依赖编排缺失 | `add-cross-repo-deps-orchestration.md` + `complete-add-cross-repo-deps-orchestration.md` | **已 complete** |
| 7 | 契约校验 CI/CD 缺失 | `add-contract-lint-ci-gate.md` + `complete-add-contract-lint-ci-gate.md` | **已 complete** |
| 8 | Spoke 系统提示词注入缺失 | `add-spoke-system-prompt-injection.md` | 已批准（`skills/spoke-system-prompt-injection/` 存在） |
| 9 | L2 上报扩展性受限 | `add-rdd-hub-cross-repo-federation.md` 覆盖（`category=rfc`） | 已批准 |
| 10 | rddf-session 联邦化 | `add-rddf-session-auto-archive-on-entry.md`（部分覆盖） | 进行中（非 blocking） |

**结论**：8 个 gap 已有完整实现，1 个部分覆盖（#10），1 个未覆盖（实质被 #9 涵盖）。无需新建 improvement 文件。

## 迁移来源（provenance）

新 `docs/architecture/hub-and-spoke-federation.md` 末尾将包含一行：
> "本文档 §1+§2 由 `multi-project-2026-08-15-gap-analysis.md` 迁移而来（ADR-0058）；§3+§4 的差距已映射为 `.rddf/improvements/*.md`（见上方表格）。"

## References

- `docs/architecture/hub-and-spoke-federation.md` — 新建 theme doc（本 ADR 实施产物）
- `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` — **已删除**（本 ADR 实施步骤）
- `docs/adr/ADR-0057-rdd-arch-simplify-delete-gap-analysis.md` — 上游决策（删除 gap-analysis 工件类型）
- `docs/adr/ADR-0030-hub-and-spoke-federation.md` — Hub-and-Spoke 决策（gap-analysis 实施依据）
- `docs/adr/ADR-0031-human-in-loop-cross-repo.md` — 跨项目人类决策原则
- `docs/adr/ADR-0032-hub-federation-deepening.md` — Hub 联邦深化
- `.rddf/improvements/add-rdd-hub-cross-repo-federation.md` — Gap #1, #3, #9 实施
- `.rddf/improvements/add-mcp-cross-repo-protocol.md` — Gap #4 实施
- `.rddf/improvements/add-strict-human-approval-for-cross-repo-changes.md` — Gap #5 实施
- `.rddf/improvements/add-cross-repo-deps-orchestration.md` — Gap #6 实施
- `.rddf/improvements/add-contract-lint-ci-gate.md` — Gap #7 实施
- `.rddf/improvements/add-spoke-system-prompt-injection.md` — Gap #8 实施
- `.rddf/improvements/add-rdd-hub-bootstrap.md` — Gap #2 实施
- `skills/rdd-arch/SKILL.md` — rdd-arch 工件类型定义（ADR + theme doc 双工件）
- `skills/rdd-doctor/scripts/checks/arch_audit_check.py` — arch-audit category（第 18 个，新增 per Stage 1）
- `git log --follow docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` — 永久归档（git history 即归档）