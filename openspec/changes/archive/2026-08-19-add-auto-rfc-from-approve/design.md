## Context

P0 #3 让人类在 approve 前看到"准备发什么"（草稿）。本 change 让 approve 后**自动**调用 `report_issue_rfc.py` 创建 Hub Issue，无需人重跑命令。

## Goals / Non-Goals

**Goals**:

- `approve_proposal.sh --manual --auto-issue` 选项
- 自动调 `report_issue_rfc.py` 并回填 URL 到草稿
- Hub 创建失败时 audit log 写 `decision=fail`，人类可手动重试
- 与现有 `--hub-issue` 选项互斥（二选一）

**Non-Goals**:

- 异步队列提交（同步即可）
- MCP Server 真实调用（仍 REST）

## Technical Decisions

### TD-1: 选项互斥

`--hub-issue <org/repo#N>` 与 `--auto-issue` 不可同时使用，CLI 启动时检测并 exit 2。

### TD-2: 失败回退

Hub 创建失败时：
- audit log 写 `decision=fail` + `hub_state=error` + `error_msg=<msg>`
- 不阻断 approve 已成功的状态
- 人类可手动 `rddf rfc-create --from-draft <name>` 重试

## Implementation Notes

- `RDDF_APPROVE_ACTOR` 复用为 Hub Issue 提交者
- 调用 `report_issue_rfc.py` 用 subprocess + capture_output，避免阻塞

## References

- ADR-0032 §阶段 C
- 依赖 P0 #3 `add-rfc-interview-flow`
