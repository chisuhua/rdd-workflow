# add-mcp-cross-repo-protocol Design

## Context

当前 rdd-workflow 仅使用 GitHub REST API 直接调用（`requests` 库 / `gh` CLI），没有标准 MCP（Model Context Protocol）Server 集成。Hub-and-Spoke 联邦架构（ADR-0030）确立后，Spoke AI 与 Hub 通信必须使用标准协议。ADR-0029 定义了 Issue 驱动提案创建的规范，本提案在该基础上扩展 MCP 协议支持。

本变更实现 MCP Client 端（Spoke 端）基础设施，Hub 端 MCP Server 属于 `rdd-hub` 仓库自身范围（不在 rdd-workflow 仓库内）。

## Goals / Non-Goals

**Goals:**
- 实现 `skills/cross-repo-protocol/mcp_client.py` — MCP Client 库，支持 Stdio 和 Streamable HTTP 双传输
- 实现 4 个 MCP 工具：`hub_read_issue`、`hub_create_issue`、`hub_update_status`、`hub_sync_contract`
- 实现 `.rddf/state/.mcp-trace.jsonl` 追踪每次 MCP 调用（ADR-0030 §可观测性）
- 实现 REST fallback — MCP Server 不可达时自动降级到 GitHub REST API（proposal §错误处理）
- 实现 `install.sh --spoke-init` 子命令，注入 `.cursorrules.cross-repo-hub` 模板到 Spoke 仓库
- 实现 `skills/templates/.cursorrules.cross-repo-hub` 协议规则模板（≥12 条）

**Non-Goals:**
- Hub MCP Server 实现（属于 `rdd-hub` 仓库）
- 替代现有 GitHub REST API（`gh_repo_detect` / `from_issue.sh` 保留）
- 支持非 GitHub MCP Server（多平台支持留待后续 ADR）

## Decisions

### 1. MCP Client Library Structure

**决策**: 将 MCP Client 实现为 `skills/cross-repo-protocol/mcp_client.py`，通过 `mcp` Python 包官方 SDK 与 Hub MCP Server 通信。

**理由**:
- 复用 `skills/_lib/gh_repo_detect.py` 作为底层仓库检测（ADR-0029 §2 复用模式）
- MCP SDK 处理协议握手、心跳、重连等基础设施
- 双传输支持通过 `MCP_TRANSPORT` 环境变量切换

**架构**:
```
mcp_client.py
├── MCPClient class
│   ├── __init__(transport, server_path, token)
│   ├── call_tool(tool_name, args) -> dict
│   ├── _fallback_to_rest(tool_name, args) -> dict
│   └── _log_trace(entry)
├── transport_stdio()
└── transport_http()
```

**Alternatives considered:**
- 直接调用 `mcp-server` CLI subprocess: 放弃复用 MCP SDK，重复造轮子
- 仅支持 Stdio 传输: 不支持 HTTP 远程场景

### 2. Trace Schema Design

**决策**: 使用 JSONL 格式存储在 `.rddf/state/.mcp-trace.jsonl`，每行包含 `timestamp`、`tool_name`、`args`、`result`/`error`、`transport`、`fallback_attempted`、`duration_ms` 字段。

**Schema** (per entry):
```json
{
  "timestamp": "2026-08-16T10:00:00.000Z",
  "tool_name": "hub_read_issue",
  "args": {"issue_number": 42, "owner": "org", "repo": "rdd-hub"},
  "result": {"number": 42, "title": "...", "status": "Open", ...},
  "transport": "stdio",
  "fallback_attempted": false,
  "duration_ms": 127
}
```

**理由**:
- JSONL 适合追加写入，无需锁文件
- 单一文件聚合所有工具调用，便于 `grep` 和 `jq` 分析
- 敏感信息（token）通过 `sanitizer.py` 脱敏写入

### 3. REST Fallback Strategy

**决策**: MCP Client 在连接失败（5s timeout）时自动降级到 `requests` 库直接调用 GitHub REST API，返回相同 JSON Schema。

**触发条件**:
- TCP 连接被拒绝（ConnectionRefusedError）
- DNS 解析失败（gaierror）
- HTTP 连接超时（ConnectTimeout）

**降级流程**:
```
1. 尝试 MCP call
2. 捕获连接异常
3. 记录 fallback_attempted=true
4. 调用 equivalent REST API
5. 返回相同 Schema 的 result
```

**Alternatives considered:**
- 显式配置启用/禁用 fallback: 增加用户心智负担，默认启用符合"持续可用"目标

### 4. Authentication Model

**决策**: 使用 `GITHUB_TOKEN` 环境变量传入 GitHub PAT，token 必须为 fine-grained 类型，scoped 仅到 `rdd-hub` repo。

**理由**:
- 与现有 `gh_repo_detect.py` 环境变量约定一致
- Fine-grained token 符合 proposal §认证：权限边界清晰，避免滥用
- 不在代码中硬编码 token

**安全约束**:
- Token 值在写入 trace 前必须脱敏
- Token 缺失时抛出 `MCPConfigurationError`

### 5. .cursorrules Template Design

**决策**: `.cursorrules.cross-repo-hub` 包含 12 条 Spoke-Hub 协同规则，涵盖：
1. Issue 读取前先查重（避免重复 RFC）
2. 并行创建限速（≥1s 间隔）
3. Status 更新必须附带理由 comment
4. Contract sync 失败必须通知人工
5. Hub MCP Server 不可用时降级 REST 不得静默

**理由**:
- Spoke AI 必须遵守这些规则才能保证 Hub 侧秩序
- 模板化便于复用和版本升级
- 12 条规则覆盖 proposal §关键场景

### 6. Install Integration

**决策**: `install.sh --spoke-init <target-repo>` 复制模板到目标 Spoke 仓库 `.cursorrules`，输出确认信息。

**实现**:
```bash
install.sh --spoke-init /path/to/spoke
# → cp skills/templates/.cursorrules.cross-repo-hub /path/to/spoke/.cursorrules
# → echo "已注入 12 条跨项目协同协议到 /path/to/spoke/.cursorrules"
```

**理由**:
- 非侵入式：不在 Spoke 仓库内创建额外文件
- 幂等：重复执行覆盖，无副作用
- 兼容：`.cursorrules` 是 Cursor/Cline/Continue 等主流 AI 工具的标准提示词文件

## Risks / Trade-offs

**风险 1**: MCP Server 版本不兼容导致握手失败
**缓解**: 协议版本协商，版本不匹配时回退到 REST；日志记录版本信息

**风险 2**: REST fallback 后数据一致性
**缓解**: Fallback 时在 trace 中标注 `fallback_attempted: true`，人工可审计

**风险 3**: Token 泄露到 trace 文件
**缓解**: `sanitizer.py` 强制脱敏，trace 写入前校验敏感字段

**风险 4**: Hub MCP Server 长期不可达导致 Spoke 行为退化
**缓解**: `.cursorrules` 规则要求人工确认后才可降级 REST 为默认行为
