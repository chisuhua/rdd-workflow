# add-rdd-hub-cross-repo-federation Design

## Context

Hub-and-Spoke 模型确立后（ADR-0030），Hub Repo 作为跨项目契约 / 全局决策 / 协同看板的 SSOT。L2 上报通道从「单向上报」升级为「双向协同通道」，支持：
1. **上行通道**：Spoke → Hub 创建 RFC Issue
2. **下行通道**：Hub → Spoke 拉取最新契约
3. **监听通道**：Hub Issue 状态变化触发本地 design-done 解除挂起

当前 `rddf report-issue` 仅支持 flow-bug/gate-failure/phase-crash 上报。本提案扩展为支持 RFC 类别，并新增 `sync-hub` 和 `watch-hub` 命令。

已有能力复用：
- `skills/execute/scripts/execute_step7.py` — L2 上报执行器
- `skills/_lib/gh_repo_detect.py` — GitHub 仓库自动检测
- README §L2 上报 opt-in — 三重 opt-in 文档

## Goals / Non-Goals

**Goals:**
- 扩展 `rddf report-issue --category=rfc` 在 Hub 创建 `[RFC]` Issue
- 新增 `rddf sync-hub <contract_path>` 从 Hub 拉取契约到本地 `openspec/`
- 新增 `rddf watch-hub --once` 执行一次状态轮询（cron/CI 调度用）
- 扩展 `.rddf/state/.cross-repo-pending.json` 记录挂起的 Hub Issue
- design-done 门控检测 Hub Issue 未 Approved 时硬阻断
- 幂等性、离线模式、速率限制合规

**Non-Goals:**
- 不修改 Hub Repo 自身创建脚本（属于 `add-rdd-hub-bootstrap` 后续提案）
- 不集成 MCP 协议（属于 `add-mcp-cross-repo-protocol` 提案）
- 不实现跨项目依赖编排（属于 `add-cross-repo-deps-orchestration` 提案）
- 不在 CLI 内维护 watch-hub 长驻 daemon

## Decisions

### 1. Command Interface Design

**决策**: 三个独立命令（`report-issue --category=rfc`、`sync-hub`、`watch-hub`）而非统一 `hub` 子命令。

**理由**:
- 职责单一，每个命令可独立调用
- 符合 Unix 工具哲学
- `watch-hub --once` 专为 cron/CI 设计，独立命令便于调度
- 参数组合简单：`sync-hub --contract <path>`、`watch-hub --once --owner=<org/hub> --filter=<expr>`

** Alternatives considered:**
- 统一 `hub` 子命令 with `report/sync/watch` subcommands: 过度工程，一次性轮询不需要 `hub watch` 的完整 daemon 能力

### 2. Pending State Schema

**决策**: 使用 `.rddf/state/.cross-repo-pending.json` 存储挂起的 Hub Issue 链接。

**Schema**:
```json
{
  "entries": [
    {
      "hub_issue_url": "https://github.com/org/rdd-hub/issues/123",
      "contract_path": "auth-v2.yaml",
      "gate_type": "Design-Gate",
      "expected_status": "Approved",
      "created_at": "2026-08-16T10:00:00Z",
      "stakeholders": ["org/repo-backend", "org/repo-data"],
      "title": "[RFC] Auth V2 Proposal",
      "status": "pending"
    }
  ]
}
```

**理由**:
- 与现有 `.rddf/state/` 模式一致（JSON + gitignored）
- 支持多-entry 扩展（未来多 RFC 并行）
- `status` 字段支持: `pending | approved | rejected | superseded`

**Alternatives considered:**
- 使用 SQL/SQLite: 过度复杂，JSON 足够且人类可读
- 追加到 `iteration.json`: 混淆职责，`iteration.json` 是 sprint view

### 3. Watch-Hub Polling Model

**决策**: `--once` 模式，执行一次轮询后退出，由 cron/CI 负责调度。

**理由**:
- 符合 12-factor agent 理念（ephemeral process）
- 不需要在 CLI 内维护 daemon/pid 文件
- 便于 CI pipeline 集成
- 调度间隔 ≤5 分钟满足响应时效需求

**Alternatives considered:**
- Long-running daemon with `--watch`: 增加复杂度、需要信号处理、log rotation，且大多数场景只需要 cron 调度

### 4. GraphQL for Batch Polling

**决策**: `watch-hub` 使用 GraphQL 一次查询获取所有 pending Issue 状态。

**理由**:
- 5000 req/hour 速率限制下，N 个 pending entries 用 REST 需要 N 次请求
- GraphQL 一次请求获取所有状态，降低速率消耗
- 与 `gh api graphql` 集成简单

### 5. Offline Behavior

**决策**: Hub 不可达时回退到本地缓存 + 警告，不阻断流程。

**理由**:
- 符合幂等性要求，离线不应挂起开发工作
- `sync-hub` 已有本地缓存可用
- `watch-hub` 只读操作，离线直接返回即可

**门控影响**: `SKIP_HUB_CHECK=true` 环境变量可跳过 design-done 门控的 Hub 检查（紧急情况用）。

### 6. Permission Model

**决策**: `sync-hub`/`watch-hub` 只读 token 即可；`report-issue` 需要写权限。

**理由**:
- 最小权限原则
- sync/watch 大多数场景是只读操作
- report-issue 需要创建 Issue，确实需要写权限

### 7. GitHub Project V2 Integration

**决策**: RFC Issue 创建时自动关联 `RDD Cross-Repo Sync` Project V2。

**Fields**:
| Field | Value |
|-------|-------|
| Status | RFC / Under Review / Approved / Rejected |
| Stakeholders | org/repo pairs |
| Gate | Design-Gate / Test-Gate / Deploy-Gate |
| Contract Impact | Breaking-Change / Non-Breaking |

**理由**:
- Project V2 提供跨 repo 可视化追踪
- 与 Hub 现有看板流程一致

## Implementation Architecture

### New Files

| Path | Purpose |
|------|---------|
| `skills/_lib/gh_hub_client.py` | GitHub Hub API client (GraphQL + REST) |
| `skills/_lib/cross_repo_state.py` | Pending state read/write/validation |
| `skills/_lib/schemas/cross-repo-pending-schema.json` | JSON schema for pending state |
| `skills/report-issue/scripts/report_issue_rfc.py` | RFC Issue creation logic |
| `skills/sync-hub/scripts/sync_hub.py` | sync-hub command implementation |
| `skills/watch-hub/scripts/watch_hub.py` | watch-hub command implementation |
| `scripts/approve_proposal.sh` | Local/manual approval script |

### Modified Files

| Path | Modification |
|------|-------------|
| `skills/execute/scripts/execute_step7.py` | Add `--rfc` mode support |
| `skills/_lib/gh_repo_detect.py` | Add Hub repo detection |
| `.rddf/state/.cross-repo-pending.json` | New state file (gitignored) |
| `README.md` | Add §跨项目协同 documentation |

### Command Entry Points

```
rddf report-issue --category=rfc --title "..." --stakeholders "..." --gate "..." --contract-impact "..."
rddf sync-hub --contract <path> [--dry-run]
rddf watch-hub --once --owner=<org/hub> [--filter <expr>] [--dry-run]
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Hub API rate limit exhaustion | GraphQL batch queries; `--dry-run` 先检查 |
| Offline during critical approval | `SKIP_HUB_CHECK=true` 绕过门控（紧急用） |
| Stale cache misleading | `sync-hub` 每次显示 "using cache" vs "downloaded" |
| Project V2 field mapping changes | Schema 验证 + 清晰的错误消息 |
| Token permission misconfiguration | 幂等性检查 + 权限不足时的清晰错误 |
