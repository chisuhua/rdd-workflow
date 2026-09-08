# Plan 5: 外部 Testbed 联动文档（README + chisuhua/rdd-workflow-e2e 协同契约）

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` §6 + §9 Phase 5
> **目标**: 落地 rdd-workflow ↔ chisuhua/rdd-workflow-e2e 协同契约
> **承接**: Plan 1-4（53 cases + 2 workflow files）

## 1. 任务清单

### Task 1: 写 Plan 5 doc（本文件）

### Task 2: 协同契约 spec
- `docs/superpowers/specs/2026-09-08-rdd-workflow-e2e-coop-contract.md`
- 定义：
  - 双方职责边界
  - 数据交换格式（scenario JSON / verdict JSON / golden output）
  - 失败传播规则
  - 版本兼容矩阵

### Task 3: 契约测试
- `tests/e2e/integration/test_rdd_workflow_e2e_coop.bats`（3 cases）
- 验证：
  - scenario JSON schema 兼容外部 testbed
  - golden output 格式兼容
  - workflow 文件触发条件合规

### Task 4: README 扩展
- 引用 co-op contract spec
- 加 section "外部 testbed 协同契约"

### Task 5: 验证
- 契约测试 3/3 绿
- workflow yaml 合法

### Task 6: OpenSpec artifacts + merge + archive + 索引同步

## 2. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 外部 testbed 维护方可能不感知契约变更 | 契约 spec 落 `docs/superpowers/specs/` + PR 通知 |
| 双方数据格式漂移 | 契约测试每 PR 必跑 |
| 同步时机不一 | version 字段 + smoke test 入口 |
