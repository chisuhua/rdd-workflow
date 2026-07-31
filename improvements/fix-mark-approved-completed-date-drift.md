# fix-mark-approved-completed-date-drift

**优先级**: P2 | **来源**: 会话复盘 2026-07-31 — 幂等调用 mark_approved_completed 覆盖原完成日期
**阶段**: v2.1 | **分类**: core-impl
**类型**: fix

## 架构依据

- `skills/_lib/state.sh::mark_approved_completed`（L202-275）在 change 归档时把条目从"已批准提案"移到"已实施"表
- 会话复盘 2026-07-31 实测：对已在"已实施"区的 change（如 `fix-scan-state-bats`，原完成日期 `2026-07-23`）再次调用 `mark_approved_completed`，完成日期被改写为调用当天的 `2026-07-31`
- 根因：L220-224 的幂等检查 `if f'[{name}]' in line` 只判断"文件中是否出现 [name]"（未区分所在区），L246-248 删除行 + L250-268 重新插入时**无条件使用当前日期** `date -u +%Y-%m-%d`（L206），未保留原日期
- 影响：重复归档 / 跨 session 重放归档时，历史审计记录的完成日期被篡改，破坏审计追溯

## 范围

- **In Scope**:
  - `skills/_lib/state.sh::mark_approved_completed` — 幂等命中已实施区时保留原完成日期
  - `tests/unit/` 或 `tests/integration/` — 补充幂等日期保留测试
- **Out Scope**:
  - 不修改 `update_proposal_status.py`（另一个归档写入路径，由 fix-update-proposal-status-data-loss 提案覆盖）
  - 不修改 proposal-approved.md 格式
  - 不涉及 priority 提取逻辑（L239-244 已正确提取）

## 关键场景

- GIVEN change 已在"已实施"表（完成日期 2026-07-23）, WHEN 再次调用 mark_approved_completed, THEN 条目保持原日期 2026-07-23（当前：改为调用当天）
- GIVEN change 在"已批准"区, WHEN 首次调用 mark_approved_completed, THEN 条目插入已实施表且日期为调用当天（保持现有行为）
- GIVEN change 不在文件中, WHEN 调用, THEN 返回 1 不修改文件（保持现有行为）

## 技术约束

- MUST 幂等命中已实施区时保留原完成日期（从现有行提取）
- MUST 首次归档（从已批准区移入）时使用调用当天日期（行为不变）
- MUST NOT 改变函数签名 `mark_approved_completed <project_root> <name>`
- MUST 补充测试：幂等调用后日期不变
- SHOULD 与 `fix-update-proposal-status-data-loss` 提案协调——两处归档写入路径的测试可共用 fixture

## 验收标准

- 幂等调用后已实施区条目的完成日期保持原值
- 首次归档行为不变（日期 = 调用当天）
- 新增测试通过，现有 `bats tests/` 与 `python3 -m pytest tests/unit/ -q` 全量回归通过
