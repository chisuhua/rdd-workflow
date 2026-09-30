# Hub-and-Spoke Federation

rdd-workflow 的**多项目协同架构**——通过独立 Hub 仓库协调多个 Spoke 仓库（业务项目）的跨项目 RFC / 契约 / 依赖。

> **Migrated from**: `multi-project-ai-collaborative-development-gap-analysis.md`（2026-08-15 生成，2026-09-30 删除）。本文档 §1+§2 由该文件迁移而来（per [ADR-0058](../adr/ADR-0058-gap-analysis-migration-to-theme-doc.md)）；§3+§4 的差距已映射为 `.rddf/improvements/*.md`（见末尾"Gap → 实现状态映射"）。

## 1. 目标架构

构建 **Hub-and-Spoke（中心辐射型）联邦协同架构**，将 rdd-workflow 从"单兵作战利器"升级为"集团军协同指挥系统"，支持企业级多团队、多项目 AI 协同开发。

### 1.1 双层架构

| 层 | 角色 | 职责 |
|---|------|------|
| **Spoke（业务节点）** | 业务仓库（如 `repo-frontend`, `repo-backend`, `repo-data`） | 内部运行 rdd-workflow 的 arch → planner → builder → verifier 本地状态机 |
| **Hub（协同中枢）** | 独立仓库（如 `rdd-hub` 或 `product-sync`） | 存放跨项目契约、全局决策、协同看板；**不存放业务代码** |

### 1.2 Hub Repo 目录结构

```
rdd-hub/
├── contracts/                  # 跨项目契约（OpenAPI / Protobuf / GraphQL Schema / JSON Schema）
│   ├── auth-v2.yaml
│   └── user-profile.json
├── global-adr/                 # 全局架构决策记录（影响多个项目的重大技术选型）
├── .github/
│   └── workflows/              # 自动化流转脚本（契约变更通知、Stale RFC 清理）
│       ├── contract-lint.yml   # 契约 lint + 通知 Spoke
│       └── stale-rfc.yml       # Stale RFC 自动标记
└── docs/
    └── mcp-protocols.md        # Spoke AI 必须遵守的 MCP 交互协议
```

### 1.3 GitHub Projects V2 多维全局看板

在 Hub 仓库创建 `RDD Cross-Repo Sync` Project，配置多维字段替代点对点 Source/Target 模型：

| 字段 | 类型 | 用途 |
|------|------|------|
| `Status` | Single Select | 📝 Draft / 📢 RFC / 🔍 In-Review / ✅ Approved / ❌ Rejected / 🚧 Blocked |
| `Initiator` | Repository | 发起方仓库（如 `org/repo-frontend`） |
| `Stakeholders` | Multi-Select | 利益相关方（如 `repo-backend`, `repo-data`, `repo-infra`） |
| `Review-Progress` | Text/Formula | 自动计算（如 "2/3 Approved"） |
| `RDD-Gate` | Single Select | 映射本地门控：Design-Gate / Plan-Gate / Ship-Gate |
| `Contract-Impact` | Single Select | Breaking-Change / Non-Breaking / New-Contract |

### 1.4 多方协同工作流（AI + MCP 驱动）

| 阶段 | Spoke 动作 | Hub 协同 |
|------|-----------|---------|
| **RFC 起草** | 本地 `rdd-planner` 起草 proposal；`rddf report-issue --category=rfc` 上报 Hub | Hub 自动创建 Issue（per [ADR-0030](../adr/ADR-0030-hub-and-spoke-federation.md)） |
| **多方审查** | Spoke 仓库 stakeholders Review PR；`rddf watch-hub` 监听 Hub Issue 状态 | Hub Projects V2 自动汇总 `Review-Progress` 字段 |
| **人类兜底** | Spoke 端 `approve_proposal.sh` 在 `category=cross-repo` 时**硬阻断 AI 自动批准**（per [ADR-0031](../adr/ADR-0031-human-in-loop-cross-repo.md)） | Hub 端 `STRICT_HUB_APPROVAL=no` 需 PR 审计 |
| **契约同步** | `rddf sync-hub` 拉取 Hub 最新 `contracts/` 到本地 `openspec/` | Hub 端 `contract-lint.yml` 检测 `contracts/` 变更，自动通知 Spoke |
| **跨项目依赖** | `rddf deps cross-repo` 扫描各 Spoke `iteration.json` 生成跨仓库依赖图 | Hub 端创建 `[Dependency]` Issue 指派给上游 Spoke（per `add-cross-repo-deps-orchestration`） |

### 1.5 L2 上报扩展（双向协同通道）

`rddf report-issue` 支持 `category=rfc`（跨项目 RFC 上报）。Phase 1 已有 `flow-bug/gate-failure/phase-crash` 三类；Phase 2+ 增加 `rfc` / `pattern-question` / `tooling-bug` 等类别（per `add-rdd-hub-cross-repo-federation` 的后续扩展）。

## 2. 当前架构

### 2.1 已实施的联邦基础能力

| 能力 | 实现位置 | ADR |
|------|---------|-----|
| Hub Repo 创建 + Projects V2 看板 | `skills/rdd-hub-bootstrap/SKILL.md` | `add-rdd-hub-bootstrap` |
| 跨项目 RFC 上报（`report-issue --category=rfc`） | `skills/report-issue/scripts/` | `add-rdd-hub-cross-repo-federation`（已批准 2026-08-15） |
| Hub Issue 监听（`watch-hub --once`） | `skills/watch-hub/scripts/` | `add-rdd-hub-cross-repo-federation` |
| Hub 契约拉取（`sync-hub --contract`） | `skills/sync-hub/scripts/` | `add-rdd-hub-cross-repo-federation` |
| 跨项目 MCP 协议（Hub-Spoke 标准化交互） | `skills/cross-repo-protocol/SKILL.md` | `add-mcp-cross-repo-protocol`（已批准 2026-08-15） |
| 人类兜底（`category=cross-repo` 硬阻断 AI 批准） | `skills/rdd-builder/scripts/approve_proposal.sh` | `add-strict-human-approval-for-cross-repo-changes`（已批准 2026-08-15）|
| 跨项目依赖编排（`deps cross-repo`） | `_lib/cross_repo_deps.py` | `add-cross-repo-deps-orchestration`（**已 complete**）|
| 契约 lint CI/CD（`contract-check`） | `skills/contract-check/scripts/` | `add-contract-lint-ci-gate`（**已 complete**）|
| Spoke AI 系统提示词注入 | `skills/spoke-system-prompt-injection/scripts/deploy.sh` | `add-spoke-system-prompt-injection`（已批准 2026-08-15）|

### 2.2 联邦相关 ADRs（决策层）

- [ADR-0030](../adr/ADR-0030-hub-and-spoke-federation.md) — Hub-and-Spoke 联邦架构决策（**核心 ADR**）
- [ADR-0031](../adr/ADR-0031-human-in-loop-cross-repo.md) — 跨项目 RFC 必须人类决策（安全约束）
- [ADR-0032](../adr/ADR-0032-hub-federation-deepening.md) — Hub 联邦深化
- [ADR-0029](../adr/ADR-0029-issue-driven-proposal-creation.md) — Issue 驱动提案创建（Hub Issue ↔ proposal 转换机制）
- [ADR-0010](../adr/ADR-0010-multi-session-management.md) — 多会话管理（rddf-session 前身，联邦化基础）
- [ADR-0017](../adr/ADR-0017-rddf-session.md) — rddf-session 数据模型（联邦化延伸路径）

### 2.3 Hub-Spoke 数据流（v1）

```
Spoke A (rdd-planner)
  │   ↓ 起草 proposal + report-issue --category=rfc
  ▼
Hub Projects V2
  │   ↓ watch-hub --once 监听
Spoke A (rdd-builder)
  │   ↓ contract-check 校验
  ▼
openspec/specs/   ← sync-hub 拉取
```

完整 v1 协议见 `skills/cross-repo-protocol/SKILL.md`；MCP Client 实现见 `skills/cross-repo-protocol/mcp_client.py`（Hub 端 MCP Server 未实现，gap #4 部分覆盖；当前 Spoke 端走 REST fallback 协议）。

## 3. Gap → 实现状态映射（per [ADR-0058](../adr/ADR-0058-gap-analysis-migration-to-theme-doc.md)）

| Gap # | gap 描述 | 对应 `.rddf/improvements/*.md` | 状态 |
|-------|---------|---------------------------|------|
| 1 | Hub Repo 概念缺失 | `add-rdd-hub-cross-repo-federation.md` + `add-rdd-hub-bootstrap.md` | 已批准 2026-08-15 |
| 2 | Hub Projects V2 看板未接入 | `add-rdd-hub-bootstrap.md`（skill `rdd-hub-bootstrap`） | 已实施 |
| 3 | 跨项目 RFC 流程缺失 | `add-rdd-hub-cross-repo-federation.md`（`report-issue` + `watch-hub`） | 已批准 |
| 4 | MCP Server 协议缺失 | `add-mcp-cross-repo-protocol.md`（`skills/cross-repo-protocol/`） | 已批准 |
| 5 | AI 兜底机制未强化 | `add-strict-human-approval-for-cross-repo-changes.md` | 已批准 2026-08-15 |
| 6 | 跨项目依赖编排缺失 | `add-cross-repo-deps-orchestration.md` + `complete-add-cross-repo-deps-orchestration.md` | **已 complete** |
| 7 | 契约校验 CI/CD 缺失 | `add-contract-lint-ci-gate.md` + `complete-add-contract-lint-ci-gate.md` | **已 complete** |
| 8 | Spoke 系统提示词注入缺失 | `add-spoke-system-prompt-injection.md` | 已批准 |
| 9 | L2 上报扩展性受限 | `add-rdd-hub-cross-repo-federation.md`（`category=rfc`） | 已批准 |
| 10 | rddf-session 联邦化 | `add-rddf-session-auto-archive-on-entry.md`（部分覆盖） | 进行中 |

**结论**：8 个 gap 已完整实现，1 个部分覆盖（#10），1 个被 #9 涵盖。无需新建 improvement 文件（per ADR-0058 §Decision Option A）。

## 4. 已知约束与未来扩展

### 4.1 当前边界

- **rdd-planner 不读取 Hub 文档**（per ADR-0028 role.boundaries.owns）：Spoke planner 只读本地 `.arch-handoff.json`，Hub Issue 通过 `report-issue --category=rfc` 推送而非拉取
- **MCP 协议 v1 仅覆盖 RFC 起草 + 审查 + 契约同步**，未覆盖实施编排（gap #10）
- **rddf-session 联邦化**（gap #10）当前是 partial implementation（`auto-archive-on-entry` 单独项），完整联邦化需要 Hub 端状态机接入

### 4.2 后续方向

| 优先级 | 方向 | 触发条件 |
|--------|------|---------|
| P1 | rddf-session 完整联邦化 | Hub Issue API 提供 session state sync endpoint（需 Hub 端支持） |
| P2 | 跨项目 AC 验证（verifier 联邦化） | 多个 Spoke 仓库共享同一 RFC，需要 AC 跨仓库验证 |
| P2 | Hub Projects V2 → rdd-builder P0 自动接入 | Hub Issue 状态变化自动触发 Spoke build phase |
| P3 | Spoke 自描述协议（每个 Spoke 声明其能力） | Hub 需要路由 RFC 到合适的 Spoke 仓库 |

## References

### 现有 ADR

- [ADR-0030](../adr/ADR-0030-hub-and-spoke-federation.md) — Hub-and-Spoke 联邦架构决策
- [ADR-0031](../adr/ADR-0031-human-in-loop-cross-repo.md) — 跨项目 RFC 必须人类决策
- [ADR-0032](../adr/ADR-0032-hub-federation-deepening.md) — Hub 联邦深化
- [ADR-0029](../adr/ADR-0029-issue-driven-proposal-creation.md) — Issue 驱动提案创建
- [ADR-0057](../adr/ADR-0057-rdd-arch-simplify-delete-gap-analysis.md) — gap-analysis 工件类型删除（本文档上游决策）
- [ADR-0058](../adr/ADR-0058-gap-analysis-migration-to-theme-doc.md) — gap-analysis 实例迁移决策（本文档迁移来源）

### 现有架构文档

- `docs/architecture/multi-session.md` — rddf-session 生命周期 + 冲突解决器
- `docs/architecture/skills-and-handoff.md` — SKILL.md frontmatter + handoff 契约
- `docs/architecture/extension-points.md` — 扩展点（如何添加 skill / detector / action / CLI）
- `docs/architecture/gates-and-quality.md` — 联邦相关 gate（cross-repo-federation, strict-human-approval）

### 现有 skills

- `skills/rdd-hub-bootstrap/` — Hub 仓库初始化
- `skills/report-issue/` — L2 上报（含 `category=rfc`）
- `skills/watch-hub/` — Hub Issue 监听
- `skills/sync-hub/` — Hub 契约拉取
- `skills/cross-repo-protocol/` — MCP 跨项目协议
- `skills/spoke-system-prompt-injection/` — Spoke AI 提示词注入
- `skills/contract-check/` — 契约校验 CI/CD

### 现有 `.rddf/improvements/*.md`

- `add-rdd-hub-cross-repo-federation.md` — Gap #1, #3, #9
- `add-mcp-cross-repo-protocol.md` — Gap #4
- `add-strict-human-approval-for-cross-repo-changes.md` — Gap #5
- `add-cross-repo-deps-orchestration.md` — Gap #6
- `add-contract-lint-ci-gate.md` — Gap #7
- `add-spoke-system-prompt-injection.md` — Gap #8
- `add-rdd-hub-bootstrap.md` — Gap #2

### 迁移来源

本文档由 `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`（2026-08-15 生成，2026-09-30 删除 per ADR-0058）迁移而来：
- §1 目标架构 → §1 本文档
- §2 当前架构 → §2 本文档
- §3 差距清单 → §3 Gap → 实现状态映射（精简）
- §4 补齐路径 → §4.2 后续方向 + `.rddf/improvements/*.md` 实施
- §5 参考资料 → §References 本文档

Git 历史保留完整文件作为归档（`git log --follow docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`）。