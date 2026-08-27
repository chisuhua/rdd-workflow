# design-approve-batch-tool

## Why

2026-08-27 design 阶段, AI agent 按 wave 审批 9 个 proposal:
- 每个 wave: `ask_question` → 用户答 "全部批准"
- 每个 proposal: `generate_full_proposal.py` 生成草稿 → `ask_question` y/N → `approve_proposal.sh <name> --auto-accept`
- 9 次草稿生成 + 9 次 y/N 确认 + 9 次 approve_proposal.sh

后果:
- AI agent 的 round-trip 等待开销高 (每次 ~5-10 秒)
- 用户被迫逐个确认草稿 (即使已经 "全部批准" Wave 1 之后)
- approve_proposal.sh 已有 `--auto-accept` (DESIGN_PROPOSAL_AUTO_ACCEPT=yes), 但需手工 export

期望行为: `rddf design approve-batch <list>` 一次调用:
- 批量生成 proposal.md 草稿 (临时目录或 stdout)
- 用户一次性确认 (y/N)
- 批量调用 approve_proposal.sh

## What Changes

**In Scope**:

- 新建 `skills/guide-design/scripts/design_approve_batch.sh`: 批量 approve 入口
- 新建 `skills/guide-design/scripts/design_approve_batch.py`: 批量生成草稿 + 调用 approve_proposal.sh (Python)
- 新建 `tests/integration/test_design_approve_batch.bats`: 6 个 bats test
- 单 change approve-batch
- 多 change approve-batch (3 changes)
- 草稿生成 + 一次性 y 确认
- 草稿生成 + n 拒绝 (全部跳过)
- 已 approved change 跳过 (idempotent)
- 错误处理 (invalid change name)

**Out of Scope**:

- 修改 `approve_proposal.sh` (已正确)
- 修改 `generate_full_proposal.py` (复用, 不修改)
- 新增 wave scheduler (已有 wave_scheduler_hooks.sh, 协调但不重叠)

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] (TBD — 验收标准 from .rddf/improvements 头部未提供)

