# design-approve-batch-tool

**优先级**: P1 | **来源**: 2026-08-27 ship audit (9 个 audit-fixup proposal 审批时, 每次 approve_proposal.sh 单独调用 + 每次 D1 编排的 y/N 确认, 9 次 round-trip 浪费时间)
**阶段**: phase-2 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 文档与代码一致性审计后续修复

## 架构依据

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

## 范围

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

- MUST: 接受 change name list 作为参数 (`--changes <c1,c2,...>`)
- MUST: 批量生成 proposal.md 草稿到 `/tmp/proposal-drafts/` 一次性 review
- MUST: 用户一次性 y 确认后批量调用 `approve_proposal.sh`
- MUST: 用户 n 时全部跳过 (不破坏任一 change)
- MUST: idempotent — 跳过已 approved 的 change
- SHOULD: 提供 `--strict-yaml` 校验 proposal.md 格式

## Impact

- MUST NOT: 修改 `approve_proposal.sh` (复用, 不修改)
- MUST NOT: 绕过 design-done gate 验证

## Acceptance

- [ ] `rddf design approve-batch <list>` CLI 命令可用
- [ ] 对 9 个 proposal, 1 次 y 确认批量 approve (vs 当前 9 次 round-trip)
- [ ] D1 编排的 y/N 仍由用户决策 (不绕过)
- [ ] 6 个 bats test 全部通过
- [ ] 与现有 `approve_proposal.sh` 兼容
- [ ] `bash tests/scripts/report_regression.sh` 不增加新 failure