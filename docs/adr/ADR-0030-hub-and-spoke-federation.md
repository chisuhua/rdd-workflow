# ADR-0030: 多项目 AI 协同开发采用 Hub-and-Spoke 联邦架构

> **状态**: 待定
> **日期**: 2026-08-15
> **决策者**: 待确认

## Context

随着 AI 辅助开发从「单兵作战」向「集团军协同」演进，跨项目 / 跨团队的 AI 协同成为企业级落地的关键瓶颈。当前 rdd-workflow（v2.1+）是**单仓库视角的状态机**（arch → design → plan → ship），所有 proposals、iterations、deps-analysis 都在单仓库内闭环。当协同方从 2 个（点对点）扩展到 N 个（如：前端、后端、数据、基础设施、第三方接入）时：

1. **点对点网状模型迅速崩溃**：Source-Repo / Target-Repo 字段无法表达 1↔N / N↔N 协同
2. **跨项目契约没有 SSOT**：OpenAPI / Schema 散落在各业务仓库，难以追踪一致性
3. **审查意见分散**：多方评论散布在各仓库 PR / Issue 中，全局进度不可见
4. **AI 兜底机制不足**：当前 `approve_proposal.sh` 可被 AI 自动批准，跨项目场景下缺乏强制人类决策点

详见：`docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md`（10 项差距 + 6 个补齐 Step）。

**架构依据**:
- `ADR-0003 §3.1`: 三阶段架构按人工介入程度切分（高 → 中 → 低），本 ADR 沿用相同梯度原则
- `ADR-0003 §3.2` → `ADR-0025`: 三阶段扩展为四阶段（arch → design → plan → ship），本 ADR 是 arch 阶段对未来协同层的架构愿景
- `ADR-0034`: v3.0+ 扩展为五阶段（+ rdd-verifier），本 ADR 沿用同一阶段契约（arch-handoff / design-handoff / plan-handoff / archive），不引入第五阶段的跨项目协同维度
- `ADR-0017 §4`: rddf-session 当前是单项目概念，跨项目 session 联邦化是本 ADR 的关键依赖
- `ADR-0029 §3`: Issue 驱动提案创建已支持 `gh_repo` 切换，本 ADR 在此基础上扩展为多仓库协同
- `ADR-0027 §2`: 持续演进反馈环 L2 上报机制，是 Hub-and-Spoke 的前序能力

## Decision

**采用 Hub-and-Spoke（中心辐射型）联邦协同架构**：构建独立的中枢仓库 `rdd-hub` 作为跨项目契约、全局决策和协同看板的 SSOT（Single Source of Truth），各业务仓库（Spoke）保留本地 RDD 状态机自治，通过 GitHub MCP 协议与 Hub 通信。Hub 是「跨项目协同层」，**不侵入单项目的 arch → design → plan → ship → verify 五阶段流程**（v3.0+ 已扩展为五阶段，per ADR-0034）。

### 影响范围

- **In Scope**:
  - 跨项目契约管理（OpenAPI / Protobuf / Schema）通过 `rdd-hub/contracts/` 集中版本化
  - 跨项目 RFC 流程通过 GitHub Projects V2 多维看板管理
  - 跨项目 session 联邦化（在 ADR-0017 rddf-session 基础上扩展）
  - L2 上报通道从「单向上报」升级为「双向协同通道」
  - AI 系统提示词注入机制（`.cursorrules` / `claude.md` 模板）
- **Out Scope**（明确不涉及）:
  - **不修改**单项目的 arch → design → plan → ship → verify 五阶段流程（v3.0+ 已扩展为五阶段，per ADR-0034）
  - **不修改**单项目的状态机契约（arch-handoff / design-handoff / plan-handoff）
  - **不修改**现有 rddf-session 的单项目存储格式
  - **不创建**新的人类介入模式（Human-in-Loop 节点类型不变）
  - **不替代**现有 L2 上报机制（仅作为其扩展通道）

### 实施路径与 canonical 路径

- `rdd-hub` 的真实仓库初始化由 `add-rdd-hub-bootstrap` 负责；其余 Hub 端逻辑必须在该仓库内实现，不得在本仓库创建伪 Hub 运行时代码。
- 根 `_lib/` 是 Python 模块和 JSON Schema 的 canonical 路径；`skills/<name>/scripts/` 是 skill 专属 Bash/Python helper 的 canonical 路径；禁止新增 `skills/_lib/*.py` 作为第二份实现。
- `.rddf/improvements/<name>.md` 的 `**分类**:` 是设计期 SSOT；change 创建时必须复制到 `roadmap-meta.yaml.category`，供 plan/ship 门控读取。
- Design handoff 只有在 `openspec/changes/<name>/proposal.md` 实际存在时才能将 change 名称写入 `changes_pre_created`；否则必须保留为空并由 plan 阶段创建 artifacts。

### 备选方案

| 备选 | 理由 |
|------|------|
| **Hub-and-Spoke 联邦**（已采纳） | 单一事实来源；多维看板替代点对点；契约即法律；与 rdd-workflow 单仓库状态机解耦 |
| 全分布式点对点 | 拒绝：状态分散、审查意见不可见、全局进度不可追踪，2 个仓库以上即崩溃 |
| 中央化单体仓库（合并所有业务代码） | 拒绝：违反 rdd-workflow 「按领域拆分」原则；难以扩展；失去本地自治 |
| 现状保持（单仓库视角） | 拒绝：无法支持企业级多团队协同；与 ADR-0027 L2 上报演进方向不一致 |
| GitLab / Jira 替代 GitHub 生态 | 暂缓：保持 GitHub-first；多平台支持留待后续 ADR 评估（详见下方"多平台抽象层"） |

### 多平台抽象层（GitLab / Jira 兼容预留）

虽然本 ADR 现阶段采用 GitHub-first 策略（GitHub Issues / Projects V2 / MCP），但**架构设计必须预留多平台移植路径**。抽象层封装在 `rdd-hub` 仓库内部 + rdd-workflow 客户端，未来可切换实现而不影响业务仓库。

**抽象层组件**：

| 组件 | GitHub 实现 | GitLab 等价 | 抽象接口 |
|------|------------|-----------|---------|
| **跨项目 RFC** | GitHub Issues | GitLab Issues + Epic | `create_rfc(title, body, stakeholders, contract_impact)` |
| **多维看板** | GitHub Projects V2 | GitLab Iterations + Custom Fields | `set_rfc_field(issue_id, field_name, value)` |
| **MCP Server** | `github-mcp-server` | `gitlab-mcp-server` (存在但 schema 不同) | `MCPClient.read_issue(...)` |
| **状态变更事件** | GitHub Webhooks | GitLab Webhooks | `WebhookHandler.on_status_change(...)` |
| **Token 权限模型** | Fine-grained PAT | Project Access Tokens | `TokenScope(repo, actions)` |
| **变更通知** | GitHub Actions | GitLab CI | `notify_spoke_repo(contract_change)` |

**实施策略**（v2.3+ 阶段，非本 ADR 范围）：
- 1. 抽象接口定义在 `skills/cross-repo-protocol/abstract_backend.py`
- 2. GitHub 后端实现现有 `mcp_client.py` 包装
- 3. 引入 `RDDF_HUB_BACKEND=github|gitlab|jira` env var（默认 `github`）
- 4. 单元测试覆盖 3 个后端的 5 个关键接口

**移植成本估算**（v2.3+ 评估）：
- GitHub → GitLab：~30%（主要是 Projects V2 字段映射）
- GitHub → Jira：~50%（Issue 字段语义差异大，需新增 adapter）
- 不变：`_lib/schemas/cross_repo_*.json`（抽象平台无关）

## Consequences

### 正面

- **联邦化扩展**：rdd-workflow 从「单仓库深度状态机」升级为「联邦研发网络」，支持企业级多团队协同
- **契约即代码**：跨项目接口在 `rdd-hub/contracts/` 中版本化，AI 决策有权威全局上下文可参考，降低 AI 幻觉
- **审查意见沉淀**：所有跨项目冲突 / 妥协 / 决策以结构化 Issue + Comment 形式永久沉淀在 Hub 中，成为组织资产
- **解耦清晰**：rdd-workflow 专注单仓库代码质量；rdd-hub 专注跨域路由与多方博弈，互不侵入
- **支持任意复杂度协同**：1↔1 / 1→N / N↔N 联合重构都能通过 Hub-and-Spoke + 多维看板承载

### 负面 / 风险（安全章节）

**S1 - Token 管理（高风险）**：
- Hub Repo 需要 GitHub PAT（fine-grained, scoped to `rdd-hub` repo only）
- Spoke 仓库需要 `HUB_TOKEN` secrets 访问 Hub MCP Server
- **风险**：若 token 泄露，攻击者可读取 / 修改所有跨项目契约
- **缓解**：
  - 文档明确要求使用 GitHub Fine-grained PAT（仅 `Contents: Read` + `Issues: Write`）
  - 严禁将 token 写入代码或 `.rddf/state/*.json`（gitignored 但仍可被 dump）
  - 部署 `git-secrets` / `detect-secrets` pre-commit hook
  - 提供 `rddf token-audit` 命令定期检查 token scope

**S2 - MCP 注入攻击（高风险）**：
- Hub MCP Server 接收 Spoke AI 请求（RFC 发起 / 状态更新）
- **风险**：恶意 Spoke AI 可伪装为其他 Spoke 提交虚假审查意见
- **缓解**：
  - MCP 请求必须携带 Spoke 仓库的 GitHub App JWT（验证来源）
  - `hub_create_issue` 等敏感操作要求 Initiator 字段与 JWT 仓库一致
  - Hub MCP Server 启用 rate limiting（每仓库 100 req/h）
  - 所有 MCP 调用记录到 `.mcp-trace.jsonl`（含 token ID，便于审计）

**S3 - SSRF（服务端请求伪造）（中风险）**：
- Spoke 仓库 `rddf sync-hub <contract_path>` 从 GitHub 拉文件
- **风险**：若 `contract_path` 是 `https://attacker.com/malicious.yaml`，可绕过 SSRF 防护
- **缓解**：
  - 严格校验拉取 URL 必须匹配 `^https://raw.githubusercontent.com/<org>/<repo>/<ref>/contracts/.*` 正则
  - 内容类型校验（必须是 OpenAPI / Protobuf / JSON Schema）
  - 文件大小上限 5 MB
  - 校验和比对（与 Hub 仓库 metadata 的一致性）

**S4 - Hub Repo 沦陷（高风险）**：
- Hub 是 SSOT（Single Source of Truth）——一旦被攻破，所有 Spoke 同步污染
- **风险**：外部攻击者获得 Hub 写权限 → 下发恶意 `contracts/` → 所有 Spoke 集成故障
- **缓解**：
  - Hub Repo 启用 GitHub Branch Protection（main 分支必须 PR + 2 审）
  - 仅 Hub Maintainer Team（≤ 3 人）有写权限
  - 启用 GitHub Secret Scanning + Dependabot
  - 关键变更（`contracts/` 修改）必须有架构师审批
  - Spoke 端 `rddf sync-hub` 必须验证 Hub 仓库的 Webhook 签名

**S5 - 审计日志完整性（中风险）**：
- 三个审计机制分散（`.cross-repo-audit.jsonl` / `.mcp-trace.jsonl` / `.rddf/issues/`）
- **风险**：无统一签名链 → 攻击者可篡改本地审计日志
- **缓解**：
  - 关键决策（Hub Issue Status 变更）记录到 Hub 端 Issue Comment（不可篡改）
  - Spoke 端 audit log 同步到 Hub 的 `audit/` 目录（GitHub 强一致性）
  - 每日 `rddf audit-verify` 校验本地 log 与 Hub 一致性

**S6 - 多租户隔离（未来考虑）**：
- 当前方案假设所有 Spoke 仓库属于同一 Org
- **风险**：未来多 Org 接入可能混淆
- **缓解**：v2.3+ 引入 `RDDF_HUB_OWNER` 强制单 Org 隔离

**架构依据**（安全设计范本）：
- `ADR-0027 §1, §3, §9` — 持续演进反馈环的安全优先设计（680 行参考）
- `ADR-0007 (gate-mechanism)` — 插件式门控（error/warning 两级）

### 风险（架构 / 运营）

- **过早锁定架构**：Hub-and-Spoke 是高层架构愿景，若未来发现不合适，本 ADR 难以回滚
  - 缓解：ADR 状态支持 `已弃用 / 已替代为 ADR-NNN`；本 ADR 在「后续待办」中明确「3 个月内复核」条款
- **GitHub 生态强耦合**：当前方案深度依赖 GitHub Issues / Projects V2 / MCP，迁移到 GitLab / Jira 需重写
  - 缓解：抽象层封装在 `rdd-hub` 仓库内部，未来可替换具体实现
- **AI 兜底机制强化需求**：跨项目场景下 AI 误操作代价更高，需强制人类决策点
  - 缓解：ADR 后续 Step 4 显式升级 `approve_proposal.sh` + `STRICT_DESIGN_GATE` 强制人工确认
- **学习曲线**：Hub Repo + MCP 协议 + Projects V2 字段对团队是新概念
  - 缓解：`docs/mcp-protocols.md` 提供标准交互文档；`install.sh --spoke-init` 自动部署 System Prompt
- **额外维护成本**：Hub 仓库需要独立 CI/CD、契约 lint、Stale RFC 清理等自动化
  - 缓解：Hub 内置 `.github/workflows/contract-lint.yml` + `stale-rfc.yml` 自治
- **MCP 标准尚未完全稳定**：GitHub MCP Server 当前在演进中，API 可能变化
  - 缓解：抽象层封装在 `skills/cross-repo-protocol/SKILL.md`，未来可切换实现

### 后续待办

- [ ] **3 个月内复核（2026-11-15 截止）**：检查 Hub-and-Spoke 假设是否仍成立
  - **触发条件**（任一即触发早期复核）：
    1. 超过 2 个 Spoke 仓库接入 Hub（生产环境运行）
    2. 跨项目 RFC 平均决策时间 > 7 天
    3. `.cross-repo-audit.jsonl` 出现 ≥ 3 次 `decision=block` 异常
    4. 收到 1 个以上 GitHub Issue 反对当前架构
  - **负责人**：rdd-workflow 维护者团队（ARCHITECTURE 邮箱）
  - **决策路径**：
    1. 维护者创建 PR 评估当前状态（链接 `.rddf/state/.hub-metrics.json`）
    2. 在 Hub Repo 创建 `RFC: Hub-and-Spoke 3-month review` Issue
    3. 公开评论期 14 天（Stakeholders 必须 respond）
    4. 决策：保留 `已采纳` / 改为 `已弃用` / 拆分为 `已替代为 ADR-NNNN`
  - **决策产物**：
    - 保留 → 更新"后续待办"清单，刷新复核截止日期
    - 弃用 → 拆仓库 `rdd-hub` + 退化为 ADR-0027 L2 上报
    - 替代 → 启动新 ADR 起草（参考 ADR-0025 设计提案创建模式）
- [ ] 创建独立 `rdd-hub` 仓库骨架 — 提案 `add-rdd-hub-bootstrap` (P0, Step 1)
- [ ] 强化跨项目 RFC 人类兜底机制 — 提案 `add-strict-human-approval-for-cross-repo-changes` (P1, Step 1.5)
- [ ] 升级 L2 上报为双向协同通道 — 提案 `add-rdd-hub-cross-repo-federation` (P1, Step 2)
- [ ] 实现 MCP 跨项目协同协议 — 提案 `add-mcp-cross-repo-protocol` (P1, Step 3)
- [ ] 部署 Spoke System Prompt 注入 — 提案 `add-spoke-system-prompt-injection` (P1, Step 3.5)
- [ ] 部署契约校验 CI/CD 守门员 — 提案 `add-contract-lint-ci-gate` (P1, Step 5)
- [ ] 实现跨项目依赖编排 — 提案 `add-cross-repo-deps-orchestration` (P1, Step 6)
- [ ] 6 个新 state 文件 schema 落地 — 提案 `add-cross-repo-state-schemas`（待创建, MEDIUM #12）

## References

- `docs/architecture/multi-project-ai-collaborative-development-gap-analysis.md` — 完整差距分析 + 6 Step 补齐路径
- `docs/architecture/multi-session.md` — rddf-session 当前实现（跨项目联邦化的基线）
- `docs/architecture/extension-points.md` — 扩展点（Hub-and-Spoke 涉及的 skill / detector / CLI 扩展）
- `skills/execute/scripts/execute_step7.py` — 当前 L2 上报实现（升级目标）
- `skills/add-improve/scripts/from_issue.sh` — Issue → Proposal 转换（ADR-0029，Hub RFC 的基础能力）
- `_lib/gh_repo_detect.py` — GitHub 仓库自动检测（多仓库识别的基础；根 `_lib/` 为 Python canonical 路径）
- [GitHub Projects V2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects) — 多维看板字段定义
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github) — Spoke-Hub 通信协议
- [OpenAPI Diff](https://github.com/OpenAPITools/openapi-diff) — 契约一致性校验工具

---

## 演进（Evolution）

> **状态**: 待定（v2.0.8+ 设计稿）
> **演进路径**: 本 ADR 在 v2.0/v2.1 四阶段架构上下文中起草。v3.0+ 扩展为五阶段（+ rdd-verifier，per ADR-0034）后，本 ADR 的"不侵入单项目阶段流程"承诺保持不变 —— Hub-and-Spoke 联邦化是横向（cross-project）维度，不增加第五阶段的跨项目协同能力（rdd-verifier 默认仅在单项目内运行）。
> **如需查看当前架构**, 见 [ADR-0034](ADR-0034-rdd-verifier-verify-phase-architecture.md)。
