# ADR-0031: 跨项目 RFC 必须人类决策（Human-in-Loop for Cross-Repo）

> **状态**: 待定
> **日期**: 2026-08-15
> **决策者**: 待确认
> **父 ADR**: ADR-0030 (Hub-and-Spoke 联邦协同架构)
> **落地提案**: `add-strict-human-approval-for-cross-repo-changes` (P1, Step 1.5)

## Context

ADR-0030 确立 Hub-and-Spoke 联邦协同架构后，跨项目变更流程的风险显著高于单仓库场景：

1. **错误传播范围扩大**：一个错误的 RFC 批准可能导致多个 Spoke 仓库同步污染
2. **决策影响不可逆**：跨项目接口变更一旦合并，回滚成本高
3. **AI 误判代价高**：AI 误判 Hub Issue Status 或契约影响可能导致下游连锁失败

当前 rdd-workflow 的 `approve_proposal.sh` **可被 AI 自动执行**（当未启用 `STRICT_DESIGN_GATE` 或显式标记 `SKIP_DESIGN_HANDOFF` 时），缺乏强制人类决策点。

**本 ADR 确立**：跨项目 RFC（提案 `**分类**: cross-repo-federation`）**必须由人类决策**，AI 不可绕过此限制。

**架构依据**：
- `ADR-0030 §Decision` — Hub-and-Spoke 联邦架构的一部分
- `ADR-0030 §S4 (Hub Repo 沦陷)` — 安全风险贯穿人类决策
- `ADR-0025 §D1` — design 阶段两层内容审查的反模式参考
- `ADR-0027 §1, §3, §9` — 持续演进反馈环的安全优先设计范本
- `ADR-0005 (Human-in-Loop 节点定义)` — 人类介入模式

## Decision

**确立"跨项目 RFC 必须人类决策"原则**：所有 `**分类**: cross-repo-federation` 的提案，AI **不可自动批准**。必须由**人类维护者**通过交互式 prompt 确认后才能进入下一阶段。

### 实现细节

1. **升级 `approve_proposal.sh`**：检测 `**分类**: cross-repo-federation` 时，**硬阻断 AI 自动批准**（exit code 3）
2. **新增 `RDDF_REQUIRE_HUB_APPROVAL=yes`**：跨项目强制门控（独立 env var，与 `STRICT_DESIGN_GATE` 并列）
3. **交互式 prompt**：`--manual` 模式要求 stdin 输入 GitHub username（避免 process listing 泄露）
4. **审计日志**：所有 cross-repo 决策记录到 `.rddf/state/.cross-repo-audit.jsonl`
5. **Hub Issue 状态主动校验**：本地批准前必须重新拉取 Hub Issue 状态（防 race condition）

### 影响范围

- **In Scope**:
  - `skills/guide-design/scripts/approve_proposal.sh` 升级（detect cross-repo + 硬阻断）
  - 新增 `RDDF_REQUIRE_HUB_APPROVAL` env var
  - 新增 `_lib/cross_repo_audit.py`（审计 log 写入；根 `_lib/` 是 Python 模块 canonical 路径）
  - 升级 `skills/guide-design/scripts/design_content_review.sh`（cross-repo 类别审查）
  - 升级 `.openspec.yaml` schema：新增 `cross_repo_review.required` 字段

**分类传递契约**：

- 来源 SSOT：`.rddf/improvements/<name>.md` 中精确的 `**分类**: <value>` 元数据行
- Change 创建时：必须将该值复制到 `openspec/changes/<name>/roadmap-meta.yaml` 的 `category` 字段
- Plan/ship 阶段：门控只读取 `roadmap-meta.yaml.category`，不得依赖 `proposal-approved.md`（索引不携带分类）
- 允许值：`cross-repo-federation`；缺失或未知分类时 fail-closed，不得静默按单仓库流程放行
- **Out Scope**:
  - **不修改** 单仓库 proposal 审批流程（保持现有 `y/N` 交互）
  - **不创建** 新的交互模式（Human-in-Loop 节点类型不变）
  - **不实现** Hub 端人类兜底（属于 Hub Repo 自身）

### 备选方案

| 备选 | 理由 |
|------|------|
| **强制人类决策**（已采纳） | 跨项目变更影响范围大，AI 误判代价不可接受；与人类兜底原则一致 |
| AI 自动批准 + 审计 | 拒绝：审计是事后追溯，不可阻止错误发生；违反"防 AI 失控"原则 |
| AI 自动批准 + 24h 冷静期 | 拒绝：仍有自动通过风险；与硬阻断语义不同 |
| 完全阻断跨项目变更 | 拒绝：过度保守，会阻碍联邦架构演进 |

## Consequences

### 正面

- **降低 AI 误判代价**：跨项目错误变更被前置硬阻断
- **审计可追溯**：所有决策有 `actor` + `timestamp` + `reason` 记录
- **与现有安全设计一致**：遵循 ADR-0027 §3 三重 opt-in 哲学
- **人类决策点明确**：交互式 prompt 强制人类参与

### 负面 / 风险

- **决策延迟**：跨项目 RFC 平均决策时间增加 1-3 天（需人工确认）
  - 缓解：Hub Issue 状态变更触发本地通知（`rddf watch-hub`）
- **AI 工作流受阻**：AI 助手在跨项目场景下需等待人类介入
  - 缓解：明确"AI 不能跨项目自动批准"原则写入 system prompt（`add-spoke-system-prompt-injection`）
- **逃生口缺失**：无 `SKIP_CROSS_REPO_GATE` 强制门控（Hub 端 `STRICT_HUB_APPROVAL=no` 需 PR 审计）
  - 缓解：紧急场景通过 Hub 端 PR 临时关闭（Hub 维护者团队 ≤ 3 人）

### 后续待办

- [ ] 升级 `approve_proposal.sh` 检测跨项目分类
- [ ] 新增 `RDDF_REQUIRE_HUB_APPROVAL` env var 支持
- [ ] 新增 `_lib/cross_repo_audit.py` 审计模块
- [ ] 单元测试覆盖 5 个关键路径（auto-block / gate-detect / manual-confirm / audit-write / hub-state-recheck）
- [ ] README §跨项目协同 章节明确"AI 不能跨项目自动批准"原则
- [ ] `docs/strict-gate-boundary.md` 已包含 `RDDF_REQUIRE_HUB_APPROVAL` 边界说明

## References

- `ADR-0030` (`docs/adr/ADR-0030-hub-and-spoke-federation.md`) — Hub-and-Spoke 联邦协同架构（父 ADR）
- `ADR-0025` (`docs/adr/ADR-0025-design-proposal-creation.md`) — design 阶段提案创建 + 内容审查
- `ADR-0027` (`docs/adr/ADR-0027-continuous-evolution-feedback-loop.md`) — 持续演进反馈环（安全设计范本）
- `ADR-0005` (`docs/adr/ADR-0005-human-in-loop-nodes.md`) — Human-in-Loop 节点定义
- `docs/strict-gate-boundary.md` — STRICT_*_GATE 与 RDDF_REQUIRE_* 边界澄清
- `.rddf/improvements/add-strict-human-approval-for-cross-repo-changes.md` — 落地提案
- `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` — 差距分析 §3 差距 #5
