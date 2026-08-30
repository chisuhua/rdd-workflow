# phase-3-general-20260829063814

## Why

`ADR-0029` (issue-driven proposal creation) + `ADR-0030` (Hub-Spoke federation) 已建模 issue-driven 流程,但 guide-design 批准后未自动 file Hub RFC,需用户手工执行 `report-issue`。**Why now**: Hub issue backlog 累计,影响 L2 上报契约 (`ADR-0027`)。

## What Changes

**In Scope**:

- **Out Scope**: Hub RFC 状态同步 (留 watch-hub);Hub PR 自动创建

### 关键场景

- GIVEN guide-design 批准 cross-repo-federation 提案
  WHEN approve_proposal.sh 执行
  THEN Hub issue 自动 file,本地状态标记 `pending-hub-approval`
- GIVEN gh CLI 未认证
  WHEN hook触发
  THEN优雅降级,本地状态标记 `hub-failed`,提示用户手工 file

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: report-issue 失败不能阻塞 approve_proposal.sh 主流程 (`|| true`)
- SHOULD: 提供 `rddf hub retry-failed` CLI 重试命令

## Impact

- MUST NOT: 重复 file同一 Hub issue (用本地 hash dedup)

## Acceptance

- 3 个测试用例: cross-repo 提案批准成功 / 本地提案不触发 / gh缺失优雅降级
- 端到端: guide-design approve → Hub issue 自动出现 → 本地状态正确

