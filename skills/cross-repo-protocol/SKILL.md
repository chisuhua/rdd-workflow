---
name: cross-repo-protocol
description: MCP (Model Context Protocol) client for Hub-Spoke federation — wraps 4 Hub tools (read/create/update issue, sync contract) with REST fallback and trace logging.
license: MIT
compatibility: Requires Python 3.11+, mcp SDK, requests, GITHUB_TOKEN env var.
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "ADR-0030 Hub-and-Spoke federation Step 3"
  user-invocable: false
---

# Cross-Repo Protocol (MCP Client)

MCP 客户端,封装 4 个 Hub 工具调用。失败时自动 REST 回退到 GitHub API。所有调用 trace 到 `.rddf/state/.mcp-trace.jsonl`。

## 4 个工具

| Tool | 用途 | 必填参数 |
|------|------|----------|
| `hub_read_issue` | 读取 Hub Issue | `issue_number` |
| `hub_create_issue` | 创建 Hub Issue | `title`, `body` (opt), `stakeholders` (opt) |
| `hub_update_status` | 更新 Issue 状态 | `issue_number`, `status`, `comment` (opt) |
| `hub_sync_contract` | 同步契约状态 | `contract_id`, `state` |

## 传输方式

- `stdio` (默认): 通过 `MCP_SERVER_PATH` 启动 MCP Server 子进程
- `http`: 通过 `MCP_SERVER_URL` 连接 Streamable HTTP

## 认证

- `GITHUB_TOKEN` 必须设置(必需)
- REST 回退使用同一 token(`Authorization: Bearer <token>`)

## 回退行为

MCP Server 不可达(`ConnectionRefusedError` / 超时)时,自动 REST 回退。`MCPSuppressFallbackWarning=true` 抑制 stderr 警告。

## Trace 文件

`.rddf/state/.mcp-trace.jsonl`(每行一条 JSON)。结构遵循 `_lib/schemas/mcp_trace_schema.json` v1(SSOT from W2-2)。自动 redact `token` / `secret` / `password` / `api_key` / `authorization` 字段。
