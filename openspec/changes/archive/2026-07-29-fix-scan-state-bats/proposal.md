# fix-scan-state-bats

**优先级**: P2 | **阶段**: v2.0 | **分类**: infra-setup

## 问题描述

`plan-handoff.json` 与实际目录存在差异，导致 `scan_state` 的 bats 测试失败。scan_state 的 handoff 读取逻辑需要修复。

## 范围

- **In Scope**:
  - 排查 plan-handoff.json 与实际目录的差异
  - 修复 scan_state 的 handoff 读取逻辑
  - 更新或归档已完成的 changes
- **Out Scope**:
  - 不修改 guide 推荐逻辑

## 验收标准

- 所有 scan_state bats 测试通过
- handoff 读取逻辑与目录状态一致
