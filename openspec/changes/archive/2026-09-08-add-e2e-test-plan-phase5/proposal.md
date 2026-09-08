# add-e2e-test-plan-phase5 (外部 testbed 协同契约)

> Per `2026-09-08-e2e-test-plan-design.md` §6 + §9 Phase 5.

## What Changes

- **New**: `docs/superpowers/specs/2026-09-08-rdd-workflow-e2e-coop-contract.md` — 协同契约 spec (职责边界 / 数据交换 / 失败传播 / 版本兼容矩阵)
- **New**: `tests/e2e/integration/test_rdd_workflow_e2e_coop.bats` — 3 契约测试 (scenario JSON 兼容 / verdict JSON 兼容 / workflow 触发合规)
- **Updated**: `README.md` — 引用 co-op spec (per Plan 4 已加)

## Acceptance

- AC-1: 协同契约 spec 落 `docs/superpowers/specs/`
- AC-2: 契约测试 3/3 绿 (scenario / verdict / workflow 兼容)
- AC-3: 0 新增回归失败
- AC-4: OpenSpec archive 完成

## Specs

D3 spec-delta 落 `openspec/specs/external-testbed-coop/spec.md`。
