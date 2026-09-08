# Plan 3: C 层余 4 skill（rdd-builder 12 + rdd-verifier 8 + rdd-arch 8 + rdd-planner 8 = 36 cases）

> **日期**: 2026-09-08
> **所属**: `2026-09-08-e2e-test-plan-design.md` §9 Phase 3
> **目标**: Plan 2 落 rdd-quick 8 cases；本 Plan 推广到余 4 skill，36 cases
> **承接**: Plan 2（agent_runner.bash 三模式 + scenario JSON schema 已建）

## 1. 任务清单

### Task 1: 写 Plan 3 doc（本文件）
- 创 branch openspec/add-e2e-test-plan-phase3
- 落本 plan doc

### Task 2: 12 rdd-builder scenarios (B-E1..B-E12)
- `tests/e2e/agent/scenarios/b_e{1..12}.json`
- 覆盖 P0 approval / P1 plan / P1.5 deps / P2 execute / P2.5 review / P3 archive / verifier 回环 / 隔离
- 每 scenario 含 mock_output（pre-recorded agent response）

### Task 3: 8 rdd-verifier scenarios (V-E1..V-E8)
- `tests/e2e/agent/scenarios/v_e{1..8}.json`
- 覆盖 AC 提取 / verdict 6 字段 / pass / fail-gap / fail-drift / partial / retry 上限 / skip 凭据

### Task 4: 8 rdd-arch scenarios (A-E1..A-E8)
- `tests/e2e/agent/scenarios/a_e{1..8}.json`
- 覆盖 setup discovery / ADR 创建 / 差距分析 / roadmap / arch-done gate / 0 ADR 阻断 / stale / 隔离

### Task 5: 8 rdd-planner scenarios (P-E1..P-E8)
- `tests/e2e/agent/scenarios/p_e{1..8}.json`
- 覆盖 stage entry / intake / propose / brainstorm / approve / reject / 横切 / stage exit

### Task 6: 4 bats test files (36 cases)
- `tests/e2e/agent/test_rdd_builder_e2e.bats` (12 cases)
- `tests/e2e/agent/test_rdd_verifier_e2e.bats` (8 cases)
- `tests/e2e/agent/test_rdd_arch_e2e.bats` (8 cases)
- `tests/e2e/agent/test_rdd_planner_e2e.bats` (8 cases)

### Task 7: 验证 36/36 绿
- `./test.sh --e2e-agent` 跑 C-layer
- 36 cases 全部 mock mode 通过
- 0 新增回归失败

### Task 8: OpenSpec artifacts + merge + archive + 索引同步

## 2. 验收标准

- AC-1: 36 scenarios JSON schema 合法 (validate_scenario 36/36 绿)
- AC-2: 36 C-layer bats cases 跑通 mock 模式 (36/36 绿)
- AC-3: 0 新增回归失败
- AC-4: OpenSpec archive 完成

## 3. 复用

- `tests/e2e/_lib/agent_runner.bash` (Plan 2) — 直接复用
- `tests/e2e/_lib/isolation.bash` (Plan 1) — sha256 锁
- `tests/e2e/_lib/script_smoke.bash` (Plan 1) — fake project setup
- Plan 2 rdd-quick bats 模板 — 复制改 scenario_id

## 4. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 36 cases 总量大 | 紧凑 JSON 模板 + 共享 test 函数 |
| Mock output 与真实 agent drift | golden_output 仅断言"关键字段"而非全文 sha256 |
| rdd-builder B-E6/B-E7 (worktree vs lightweight) | mock mode 仅断言 mode 决策字段，不真 worktree |
| 隔离契约失败 | 每个 bats 都 setup_fake_project + isolation::snapshot |
