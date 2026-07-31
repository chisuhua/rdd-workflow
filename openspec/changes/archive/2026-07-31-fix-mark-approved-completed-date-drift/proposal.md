## Why

会话复盘 2026-07-31 实测：对已在"已实施"区的 change（如 `fix-scan-state-bats`，原完成日期 `2026-07-23`）再次调用 `skills/_lib/state.sh::mark_approved_completed`，完成日期被改写为调用当天的 `2026-07-31`。

根因：L220-224 的幂等检查 `if f'[{name}]' in line` 只判断"文件中是否出现 [name]"（未区分所在区），L246-248 删除行 + L250-268 重新插入时**无条件使用当前日期** `date -u +%Y-%m-%d`（L206），未保留原日期。影响：重复归档 / 跨 session 重放归档时，历史审计记录的完成日期被篡改，破坏审计追溯。

## What Changes

- `skills/_lib/state.sh::mark_approved_completed` — 幂等命中已实施区时保留原完成日期（从现有行提取）。
- `tests/unit/` 或 `tests/integration/` — 补充幂等日期保留测试。

## Capabilities

### New Capabilities
- `mark-approved-completed-date-preservation`: 幂等调用 mark_approved_completed 时保留已实施区条目的原完成日期

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/_lib/state.sh::mark_approved_completed` — 幂等命中已实施区时保留原完成日期
- 新增测试：幂等调用后日期不变

**Out of Scope:**
- 不修改 `update_proposal_status.py`（另一个归档写入路径，由 fix-update-proposal-status-data-loss 提案覆盖）
- 不修改 proposal-approved.md 格式
- 不涉及 priority 提取逻辑（L239-244 已正确提取）
