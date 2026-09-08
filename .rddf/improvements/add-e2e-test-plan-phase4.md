# add-e2e-test-plan-phase4 (CI integration)

> 提案已实施归档。规格见 `2026-09-08-e2e-test-plan-design.md` §5 + §9 Phase 4。
> 实施 plan: `docs/superpowers/plans/2026-09-08-e2e-test-plan-phase4-ci-integration.md`。
> 归档: `openspec/changes/archive/2026-09-08-add-e2e-test-plan-phase4/`。
> D3 spec-delta: `openspec/specs/ci-e2e-integration/spec.md`（3 Scenarios）。

## 实施摘要

- 新建 `.github/workflows/e2e-nightly.yml`（nightly cron + workflow_dispatch）
- 扩展 `.github/workflows/test.yml` 加 e2e-smoke step
- 更新 README "测试" 段描述分层 e2e 策略
