# add-auto-rfc-from-approve

## Why

当前 `approve_proposal.sh --manual --hub-issue <org/repo#N>` 强制人工先有 Hub Issue 才能 approve。但 approve 流程本应自动创建 Hub Issue（基于已审批的草稿），让人类无需重跑 `rddf rfc-create`。

依赖 Phase 2 `add-rfc-interview-flow` 提供的草稿机制 + schema 校验。

## What Changes

**In Scope**:

- `approve_proposal.sh` 新增 `--auto-issue` 选项：approve 后自动调 `report_issue_rfc.py`
- 本地 `--hub-issue` 占位 → 自动捕获新建的 Issue URL 并回填
- `RDDF_APPROVE_ACTOR` 复用为 Hub Issue 提交者
- 失败回退：Hub 创建失败时 audit log 写 `decision=fail`，人类手动跑 `rddf rfc-create --from-draft`
- bats + unit test

**Out of Scope**:

- 异步队列提交（同步即可）
- MCP Server 真实调用（仍 REST）

## Impact

- **能力**: approve → 自动发 RFC，无需人重跑
- **兼容**: 不破坏现有 `--hub-issue` 用法（强制 vs 自动二选一）
- **风险**: 中. 增加失败点（Hub 网络）需配套 audit trail + 手动 fallback

## Acceptance

- AC-1: `approve_proposal.sh <name> --manual --auto-issue` 在草稿存在时自动创建 Hub Issue 并回填 URL
- AC-2: Hub 创建失败时 audit log 写 `decision=fail`，错误信息可见
- AC-3: 与现有 `--hub-issue` 选项互斥（二选一）
- AC-4: bats + unit test 全绿（含失败路径）
- AC-5: `./test.sh --full --regression` 不新增失败
- AC-6: e2e 测试 `test_cross_repo_e2e_real.bats` 新增 ≥ 2 case 覆盖 auto-issue 路径

## Manual Deps

依赖 `add-rfc-interview-flow`（Phase 2）。
