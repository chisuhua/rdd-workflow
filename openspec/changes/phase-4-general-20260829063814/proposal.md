# phase-4-general-20260829063814

## Why

`ADR-0031` (human-in-loop cross-repo) + `ADR-0035` (verifier-archive-gate boundary) 已建立多 stakeholder 边界,但当前 archive 仅本地 verify-pass即可,无对称 multi-party check。**Why now**: archive 后全量回归门控 (per add-full-regression-gate proposal) 已强制但分散在 shell/test.sh,需统一到 design阶段契约。

## What Changes

**In Scope**:

- **Out Scope**: 多方投票 UI;回归预测

### 关键场景

- GIVEN 2 stakeholder (本地 owner + Hub approver) 都需 approve
  WHEN guide-ship 准备 archive
  THEN 等待双方 approval,缺一阻塞 archive
- GIVEN KNOWN_FAILURES.txt 包含 3 个 baseline 失败
  WHEN 测试运行后新失败 = 0
  THEN archive 允许 (含 baseline 失败)

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: 回归基线版本控制 (KNOWN_FAILURES.txt 跟随 git)
- SHOULD: 提供 `rddf regression diff` CLI 对比 baseline vs 当前

## Impact

- MUST NOT: 删除 KNOWN_FAILURES 条目来 "通过" 测试

## Acceptance

- 3 stakeholder 场景测试 (1 owner + 2 hub) 全流程
- baseline 管理: 新增/移除/失效 3 个测试
- 对称 verify: 本地 + Hub 失败分别正确处理

