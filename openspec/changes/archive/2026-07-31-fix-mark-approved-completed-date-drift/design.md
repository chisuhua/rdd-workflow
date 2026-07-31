## Context

`skills/_lib/state.sh::mark_approved_completed`（L202-275）在 change 归档时把条目从"已批准提案"移到"已实施"表。会话复盘 2026-07-31 实测：对已在"已实施"区的 change 再次调用，完成日期被改写为调用当天。根因：幂等检查 `if f'[{name}]' in line` 未区分所在区，删除行 + 重新插入时无条件使用当前日期 `date -u +%Y-%m-%d`（L206），未保留原日期。

## Goals / Non-Goals

**Goals:**
- change 已在"已实施"表时再次调用 `mark_approved_completed`，条目保持原完成日期（当前：改为调用当天）
- 首次归档（从已批准区移入）时使用调用当天日期（行为不变）
- change 不在文件中时返回 1 不修改文件（行为不变）

**Non-Goals:**
- 不修改 `update_proposal_status.py`（另一个归档写入路径，由 fix-update-proposal-status-data-loss 提案覆盖）
- 不修改 proposal-approved.md 格式
- 不涉及 priority 提取逻辑（L239-244 已正确提取）

## Decisions

1. **幂等命中已实施区时保留原日期**：当幂等检查命中"已实施"区的条目时，从现有行提取原完成日期并复用，不重新生成当前日期。
2. **首次归档行为不变**：条目从"已批准"区移入时，日期 = 调用当天（`date -u +%Y-%m-%d`），保持现有语义。
3. **签名不变**：`mark_approved_completed <project_root> <name>` 函数签名不改变。
4. **测试覆盖**：新增幂等日期保留测试——构造已实施区含原日期的 fixture，断言幂等调用后日期不变。与 `fix-update-proposal-status-data-loss` 提案的归档写入路径测试共用 fixture。

## Risks / Trade-offs

- **协调性**：与 `fix-update-proposal-status-data-loss`（`update_proposal_status.py` 路径）是两条独立归档写入路径，本提案只修 `state.sh` 路径，两者测试可共用 fixture。
- **回归验证**：新增测试通过，现有 `bats tests/` 与 `python3 -m pytest tests/unit/ -q` 全量回归通过。
- **低风险**：改动仅限幂等分支的日期处理，不触碰首次归档路径与 priority 提取逻辑。
