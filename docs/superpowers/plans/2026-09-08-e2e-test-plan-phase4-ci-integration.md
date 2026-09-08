# Plan 4: CI 集成（.github/workflows/e2e-nightly.yml + test.yml 扩展 + README）

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` §5 + §9 Phase 4
> **目标**: 把 Plan 1-3 的 e2e 测试套件接进 GitHub Actions CI
> **承接**: Plan 1-3 已落 53 cases（10 A + 17 C unit + 36 C e2e）

## 1. 现状

`.github/workflows/test.yml` 已存在（CI 必跑），14 steps。需扩 1 step 加 `./test.sh --e2e-smoke`（A 层 CI 必跑）。

缺：`.github/workflows/e2e-nightly.yml`（C 层 nightly 02:00 UTC）。

## 2. 任务清单

### Task 1: 写 Plan 4 doc（本文件）

### Task 2: 创建 `.github/workflows/e2e-nightly.yml`
- Nightly cron: `0 2 * * *` (02:00 UTC)
- Manual trigger: `workflow_dispatch`
- Run: `./test.sh --e2e-agent`
- `continue-on-error: true` for missing LLM credentials

### Task 3: 扩展 `.github/workflows/test.yml`
- 在 PR/push flow 加 step: `./test.sh --e2e-smoke`
- 保持现有 14 steps 不变

### Task 4: 更新 README "测试" 段
- 加 e2e testing strategy（per 2026-09-08-e2e-test-plan-design.md §3）
- 引用 5 spec docs + 4 plan docs
- 引用外部 testbed `chisuhua/rdd-workflow-e2e`

### Task 5: 验证
- `bats tests/smoke.bats` 维持绿
- 新 workflow 文件 YAML schema 合法

### Task 6: OpenSpec artifacts + merge + archive + 索引同步

## 3. CI 矩阵

| Trigger | Workflow | Command | 必须绿? |
|---------|----------|---------|---------|
| PR / push | test.yml | `./test.sh --full --regression` | ✅ |
| PR / push | test.yml | `./test.sh --e2e-smoke` (NEW) | ✅ |
| Nightly cron | e2e-nightly.yml (NEW) | `./test.sh --e2e-agent` | ⚠️ skip-on-missing-credentials |
| Manual | e2e-nightly.yml | `./test.sh --e2e-agent` | developer choice |

## 4. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Nightly C 层无 LLM 凭据 | `continue-on-error: true` + 显式 SKIP 报告 |
| e2e-smoke 慢影响 PR 速度 | 现有 < 90s，可接受 |
| workflow yaml 错误 | 本地 `actionlint` 验证（若可用） |
