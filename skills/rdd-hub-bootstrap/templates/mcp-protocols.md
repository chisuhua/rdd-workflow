# MCP Protocol — rdd-hub Cross-Repo Coordination

## Overview

本协议定义 Spoke ↔ Hub 之间的 Model Context Protocol 消息格式。

## Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `rfc_propose` | Spoke → Hub | 发起跨项目 RFC |
| `rfc_status` | Hub → Spoke | 返回 RFC 状态变更 |
| `contract_sync` | Bidirectional | 契约增量同步 |

## Cross-Repo Flow

```
Spoke                    Hub
  |--- rfc_propose ------>|
  |<-- rfc_status (queued) -|
  |                        | (RFC 在看板更新)
  |<-- rfc_status (merged) -|
  |--- contract_sync ------>|
  |<-- contract_sync ack ---|
```

## Error Handling

- 401 Unauthorized: token 过期,触发 `gh auth refresh`
- 403 Forbidden: 权限不足,日志记录组织成员资格
- 429 Rate Limited: 指数退避(1s, 2s, 4s, 8s)
- 5xx Server Error: 重试 3 次后上报到 `.rddf/issues/`
