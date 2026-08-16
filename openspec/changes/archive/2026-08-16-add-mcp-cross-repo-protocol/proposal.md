# add-mcp-cross-repo-protocol

## Why

**背景**

当前 rdd-workflow 仅使用 GitHub REST API 直接调用（`requests` 库 / `gh` CLI），没有标准 **MCP（Model Context Protocol）** Server 集成。MCP 是 Anthropic 推出的 AI ↔ 工具标准协议，已被 GitHub 官方支持（`github-mcp-server`）。Hub-and-Spoke 联邦架构下，Spoke AI 与 Hub 通信必须使用标准协议，便于：

1. **可替换性**：未来切换到 GitLab MCP / Jira MCP 不需要改 rdd-workflow 代码
2. **互操作性**：第三方 AI 工具（Cline / Cursor / Continue）能直接接入
3. **可审计性**：MCP 协议消息可记录到 `.rddf/state/.mcp-trace.jsonl`
4. **权限边界**：MCP Server 自带 token scope 控制，避免 rdd-workflow 滥用宽权限 token

**已有能力**

- `skills/_lib/gh_repo_detect.py` — GitHub 仓库检测（可复用为 MCP 客户端底层）
- `skills/add-improve/scripts/from_issue.sh` — Issue → Proposal 转换（ADR-0029）

**新增能力**

- 新增 `skills/cross-repo-protocol/SKILL.md` — 定义标准 MCP 交互协议（人类可读）
- 新增 `skills/cross-repo-protocol/mcp_server.py` — Hub 端 MCP Server（提供 read_issue / create_issue / update_status / sync_contract 工具）
- 新增 `skills/cross-repo-protocol/mcp_client.py` — Spoke 端 MCP Client
- 新增 `skills/templates/.cursorrules.cross-repo-hub` — Spoke AI 强制注入协议模板

## What Changes

**In Scope**:

- 在 Spoke 端新增 MCP Client 工具：`hub_read_issue` / `hub_create_issue` / `hub_update_status` / `hub_sync_contract`
- 在 Hub 端（独立仓库 `rdd-hub`）部署 MCP Server
- 新增 `install.sh --spoke-init` 子命令：自动部署 `.cursorrules.cross-repo-hub` 到 Spoke 仓库
- 新增 `skills/cross-repo-protocol/mcp-protocols.md` — 标准交互文档

### 关键场景

### 场景 1：Spoke AI 读取 Hub Issue

```python
# 通过 MCP Client
result = mcp_client.call_tool("hub_read_issue", {
    "issue_number": 42,
    "owner": "org",
    "repo": "rdd-hub"
})
# → 返回标准化的 Issue 对象（含 Status / Stakeholders / RDD-Gate 字段）
```

### 场景 2：Hub AI 创建 Issue 并更新字段

```python
# Hub 端 MCP Server 处理
@mcp_server.tool()
def hub_create_issue(title, body, stakeholders, contract_impact):
    issue = github.create_issue(...)
    project_v2.update_field(issue, "Stakeholders", stakeholders)
    return issue
```

### 场景 3：System Prompt 注入

```bash
# install.sh --spoke-init
$ cp skills/templates/.cursorrules.cross-repo-hub /path/to/spoke/.cursorrules
$ echo "已注入 12 条跨项目协同协议到 /path/to/spoke/.cursorrules"
```

**Out of Scope**:

- **Hub MCP Server 实现细节**：属于 Hub Repo 自身范围（不在 rdd-workflow 仓库内）
- **替代 GitHub REST API**：现有 `gh_repo_detect` / `from_issue.sh` 保留，仅新增 MCP 路径
- **支持非 GitHub MCP**：本提案仅集成 GitHub MCP Server；多平台支持留待后续 ADR

## Capabilities

- **协议版本**：使用 MCP v0.5+（2025-Q2 后稳定版本）
- **传输层**：Stdio + Streamable HTTP 双支持
- **认证**：GitHub PAT（fine-grained，scoped to `rdd-hub` repo only）
- **错误处理**：MCP Server 不可达时回退到 REST API + 警告
- **可观测性**：每次 MCP 调用记录到 `.rddf/state/.mcp-trace.jsonl`

## Impact

- (no items specified)

## Acceptance

- [ ] `mcp_client.hub_read_issue(42)` 返回标准化对象（JSON Schema 校验）
- [ ] `install.sh --spoke-init` 成功部署 `.cursorrules.cross-repo-hub` 到目标仓库
- [ ] MCP Server 不可达时 Spoke 端优雅降级到 REST API
- [ ] `.mcp-trace.jsonl` 记录每次调用的 tool_name / args / result / timestamp
- [ ] `docs/mcp-protocols.md` 提供标准交互示例（≥5 个）
- [ ] 单元测试覆盖 MCP Client/Server 边界（≥10 个）

