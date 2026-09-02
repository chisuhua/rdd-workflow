# 架构差距分析: multi-project-ai-collaborative-development

> **生成日期**: 2026-08-15T22:13:18+08:00
> **状态**: 草案
> **关联 ADR**: ADR-0010 (multi-session-management), ADR-0016 (arch-artifact-discovery), ADR-0017 (rddf-session), ADR-0029 (issue-driven-proposal-creation)
> **关联架构文档**: docs/architecture/multi-session.md, docs/architecture/skills-and-handoff.md, docs/architecture/extension-points.md

## 1. 目标架构

构建 **Hub-and-Spoke（中心辐射型）联邦协同架构**，将 rdd-workflow 从"单兵作战利器"升级为"集团军协同指挥系统"，支持企业级多团队、多项目 AI 协同开发。

### 1.1 双层架构

| 层 | 角色 | 职责 |
|---|------|------|
| **Spoke（业务节点）** | 业务仓库（如 repo-frontend, repo-backend, repo-data） | 内部运行 rdd-workflow 的 arch → design → plan → ship 本地状态机 |
| **Hub（协同中枢）** | 独立仓库（如 `rdd-hub` 或 `product-sync`） | 存放跨项目契约、全局决策、协同看板；不存放业务代码 |

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
| `Initiator` | Repository | 发起方仓库（如 org/repo-frontend） |
| `Stakeholders` | Multi-Select | 利益相关方（如 repo-backend, repo-data, repo-infra） |
| `Review-Progress` | Text/Formula | 自动计算（如 "2/3 Approved"） |
| `RDD-Gate` | Single Select | 映射本地门控：Design-Gate / Plan-Gate / Ship-Gate |
| `Contract-Impact` | Single Select | Breaking-Change / Non-Breaking / New-Contract |

### 1.4 多方协同工作流（AI + MCP 驱动）

| 阶段 | Spoke 动作 | Hub 协同 |
|------|-----------|---------|
| **Propose** | AI 在 guide-design 阶段发现提案涉及跨项目契约 | 通过 MCP 在 Hub 创建 `[RFC]` Issue，挂起本地 design 门控 |
| **Review** | 各 Stakeholder 仓库 AI 通过 MCP 监听指派给自己的 RFC | 在 Hub Issue 下发表结构化 `## 🤖 [repo-x] 审查意见` Comment |
| **Resolve** | 等待人类架构师裁决（AI 禁止修改 Status 为 Approved） | 修改 contracts/ 并合并 PR，更新 Status 为 ✅ Approved |
| **Sync-back** | AI 监听 Approved 状态，拉取最新契约 | 解除本地挂起，自动执行 approve_proposal.sh |

## 2. 当前架构

### 2.1 已有能力（rdd-workflow v2.1+）

| 能力 | 实现 | 文件 |
|------|------|------|
| 单仓库 RDD 状态机 | arch → design → plan → ship → verify 五阶段（v3.0+ per ADR-0034） | `skills/guide-arch/`, `guide-design/`, `guide-plan/`, `guide-ship/`, `skills/rdd-verifier/` |
| 全局技能安装 | `install.sh --global` 复制到 `~/.agents/skills/` | `install.sh`, AGENTS.md §全局安装模式 |
| 跨 OpenCode session 恢复 | `rddf-session` skill 5 子命令 | `skills/rddf-session/`, ADR-0017 |
| 工件发现契约 | Arch-handoff 软状态文件 | ADR-0016, `.rddf/state/.arch-handoff.json` |
| GitHub Issue 驱动提案 | `add-improve --from-issue` 路径 | `skills/add-improve/scripts/from_issue.sh`, ADR-0029 |
| L2 上报（单向上报） | `rddf report-issue --no-submit` opt-in | `skills/execute/scripts/execute_step7.py`, README §L2 上报 opt-in |
| 跨项目仓库路径解析 | `detect_gh_repo()` | `skills/_lib/gh_repo_detect.py` |

### 2.2 当前架构限制

- **单仓库视角**：所有 proposals / iterations / deps-analysis 都是单仓库内闭环，没有跨项目可见性
- **L2 上报是单向 / 后置**：仅在执行失败（flow-bug / gate-failure / phase-crash）时上报，**不是协同工具**
- **没有 Hub Repo 概念**：跨项目契约没有 SSOT（Single Source of Truth）
- **MCP 未集成**：当前仅使用 GitHub REST API，没有标准 MCP Server 协议
- **AI 直接决策**：当前 approve_proposal.sh 可被 AI 自动执行，没有强制人类兜底
- **没有 Project V2 集成**：当前 iteration.json 是内部视图，没有外部看板

## 3. 差距清单

| # | 差距项 | 严重程度 | 优先级 | 关联 change |
|---|--------|---------|--------|------------|
| 1 | **缺失 Hub Repo 概念**：没有跨项目契约 / 全局 ADR / 协同看板的 SSOT 仓库 | 高 | P0 | 新增提案 |
| 2 | **Hub Projects V2 看板未接入**：当前只有 iteration.json 内部视图 | 高 | P0 | 新增提案 |
| 3 | **跨项目 RFC 流程缺失**：当前 proposal 是单仓库审批，没有多方审查 | 高 | P0 | 新增提案 |
| 4 | **MCP Server 协议缺失**：当前仅用 REST API，没有标准 MCP 集成 | 中 | P1 | 新增提案 |
| 5 | **AI 兜底机制未强化**：当前 approve_proposal.sh 可被 AI 自动批准 | 高 | P0 | 新增提案（加固 STRICT_DESIGN_GATE） |
| 6 | **跨项目依赖编排缺失**：当前 deps-analysis 是单仓库图，无法表达跨仓库依赖 | 高 | P1 | 新增提案 |
| 7 | **契约校验 CI/CD 缺失**：没有 OpenAPI diff 等自动化契约一致性校验 | 中 | P1 | 新增提案 |
| 8 | **Spoke 系统提示词注入机制缺失**：没有强制注入跨项目协同协议的 .cursorrules / claude.md 模板 | 中 | P1 | 新增提案 |
| 9 | **L2 上报扩展性受限**：当前 `rddf report-issue` 仅支持 flow-bug/gate-failure/phase-crash 三类 | 低 | P2 | 新增提案 |
| 10 | **rddf-session 联邦化**：当前 rddf-session 仅在单仓库内有效，无法跨仓库追踪 | 中 | P2 | 新增提案 |

## 4. 补齐路径

> **注（2026-08-15 修订）**：原版 Step 排序为 1→2→3→4→5→6。基于 Oracle 审查（add-strict-human-approval 风险分析 + 实施依赖），重新排序为 1→1.5→2→3→3.5→5→6：
> - 原 **Step 4「强化人类兜底机制」没有删除**，只是前置重编号为 **Step 1.5**，因为安全门控必须在任何功能扩展之前。
> - 原 **Step 3「MCP 协议 + System Prompt 模板」拆分**为 Step 3（MCP 协议）和 Step 3.5（System Prompt 注入），以便分别验证协议和部署。
> - 因此当前编号没有 Step 4，是有意的迁移和拆分，不是遗漏。
>
> 详见 ADR-0030/0031 后续待办。

### Step 1: 建立 Hub Repo 并初始化契约（最小可行基础）

1. 创建独立仓库 `rdd-hub`，配置 GitHub Projects V2 看板
2. 将跨项目依赖的接口定义（OpenAPI / Schema）从各 Spoke 迁移到 `rdd-hub/contracts/`
3. 配置 Org 级 Project V2 字段（Status / Initiator / Stakeholders / RDD-Gate / Contract-Impact）
4. 落地 6 个新 state 文件 schema 到 `_lib/schemas/`（提案 `add-cross-repo-state-schemas`）

### Step 1.5: 强化人类兜底机制（防 AI 失控）— 安全门控前置

> **优先级最高**：跨项目场景下 AI 误操作代价极高，必须在任何功能扩展之前建立硬阻断。

1. 升级 `approve_proposal.sh`：当 `category=cross-repo` 时，**硬阻断 AI 自动批准**
2. 升级 `STRICT_DESIGN_GATE=yes`：当检测到 Hub Issue 未 Approved 时，禁止 design-done
3. 新增 `RDDF_REQUIRE_HUB_APPROVAL=yes` 环境变量（取代 `STRICT_DESIGN_GATE` 单独使用）
4. 落地配套 ADR-0031（人类决策原则）+ 审计 log `.rddf/state/.cross-repo-audit.jsonl`
5. **无 Spoke 端 bypass 路径**（Hub 端 `STRICT_HUB_APPROVAL=no` 需 PR 审计）

### Step 2: 增强 L2 上报为"双向协同"通道

1. 扩展 `rddf report-issue` 增加 `category=rfc` 类型（跨项目 RFC 上报）
2. 新增 `rddf sync-hub` 命令：从 Hub 拉取最新 contracts/ 到本地 openspec/
3. 新增 `rddf watch-hub` 命令：监听 Hub Issue 状态变化

### Step 3: 编写 MCP 跨项目协同协议

1. 新增 `skills/cross-repo-protocol/SKILL.md`，定义标准交互
2. 新增 `skills/cross-repo-protocol/mcp_server.py`（Hub 端）
3. 新增 `skills/cross-repo-protocol/mcp_client.py`（Spoke 端）

### Step 3.5: 部署 System Prompt 注入（配套 Step 3）

1. 新增 `skills/templates/.cursorrules.cross-repo-hub` 模板
2. 新增 `install.sh --spoke-init` 子命令，自动部署到 Spoke 仓库
3. 支持 5 种 AI 工具：Cursor / Cline / Continue / Copilot / Claude Code

### Step 5: 契约校验 CI/CD 守门员

1. 在 Hub 仓库配置 `.github/workflows/contract-lint.yml`：当 contracts/ 变更时，自动通知 Spoke 仓库创建 sync Issue
2. 在 Spoke 仓库 ship 阶段增加 `rddf contract-check`：使用 OpenAPI diff 校验本地实现是否与 Hub 契约一致

### Step 6: 跨项目依赖编排（deps 联邦化）

1. 新增 `rddf deps cross-repo`：扫描各 Spoke 仓库的 iteration.json，生成跨仓库依赖图
2. 新增 `rddf hub issue --deps`：在 Hub 创建 `[Dependency]` Issue，指派给上游 Spoke
3. 升级 `guide-plan` deps 阶段：识别跨仓库强依赖，自动挂起 plan-done 门控

## 5. 参考资料

### 现有 ADR

- **ADR-0010** (`docs/adr/ADR-0010-multi-session-management.md`) — 多会话管理（rddf-session 前身）
- **ADR-0016** (`docs/adr/ADR-0016-arch-artifact-discovery-contract.md`) — Arch Discovery Contract
- **ADR-0017** (`docs/adr/ADR-0017-rddf-session.md`) — rddf-session 数据模型
- **ADR-0029** (`docs/adr/ADR-0029-issue-driven-proposal-creation.md`) — Issue 驱动提案创建

### 现有架构文档

- `docs/architecture/multi-session.md` — rddf-session 生命周期 + 冲突解决器
- `docs/architecture/skills-and-handoff.md` — SKILL.md frontmatter + handoff 契约
- `docs/architecture/extension-points.md` — 扩展点（如何添加 skill / detector / action / CLI）

### 现有代码

- `skills/execute/scripts/execute_step7.py` — L2 上报执行器
- `skills/add-improve/scripts/from_issue.sh` — Issue → Proposal 转换（ADR-0029）
- `skills/_lib/gh_repo_detect.py` — GitHub 仓库自动检测
- `install.sh` — 全局 / 项目安装器

### 外部参考

- GitHub Projects V2 API — https://docs.github.com/en/issues/planning-and-tracking-with-projects
- GitHub MCP Server — https://github.com/modelcontextprotocol/servers/tree/main/src/github
- OpenAPI Diff 工具 — https://github.com/OpenAPITools/openapi-diff

### 拟新增提案（待写入 .rddf/improvements/）

- `add-rdd-hub-cross-repo-federation`
- `add-mcp-cross-repo-protocol`
- `add-strict-human-approval-for-cross-repo-changes`
- `add-cross-repo-deps-orchestration`
- `add-contract-lint-ci-gate`
- `add-spoke-system-prompt-injection`
