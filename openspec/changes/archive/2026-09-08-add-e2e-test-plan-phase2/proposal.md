# add-e2e-test-plan-phase2 (C-layer agent_runner + rdd-quick 8 scenarios)

> Per `2026-09-08-e2e-test-plan-design.md` §9 Phase 2 + `2026-09-08-rdd-quick-e2e-scenarios.md`.

## Why

Plan 1 落 A-layer（CI 必跑，10 cases），验证 phase 脚本的机械正确性。但 prose UX（agent 真读 SKILL.md 走状态机）未覆盖。

本 Plan 引入 C-layer 框架：agent_runner.bash 调度 + 8 scenarios（rdd-quick P0-P4 全链路）+ 8 bats cases。验证 prose UX 真跑通 rdd-quick，再 Plan 3 推广到 4 skill。

## What Changes

- `tests/e2e/_lib/agent_runner.bash` (~170 行) — 三模式 (validate / mock / real) 调度框架
- `tests/e2e/agent/scenarios/q_e{1..8}.json` — 8 个 scenario，per-scenario mock_output
- `tests/e2e/agent/test_agent_runner_{validate,mock,real}.bats` — 9 cases 验 framework plumbing
- `tests/e2e/agent/test_rdd_quick_e2e.bats` — 8 cases 验 rdd-quick P0-P4 + 零污染契约

## Capabilities

- capability-c-layer-agent-runner
- capability-rdd-quick-prose-ux
- capability-scenario-driven-testing

## Acceptance

- AC-1: agent_runner.bash 三模式 (validate/mock/real) 全实现，9 unit cases 绿
- AC-2: 8 scenarios JSON schema 合法 (validate_scenario 8/8 绿)
- AC-3: 8 test_rdd_quick_e2e cases 跑通 mock 模式，8/8 绿
- AC-4: test.sh --e2e-agent 缺 RDDF_AGENT_E2E=1 时 SKIP + exit 0
- AC-5: 0 新增回归失败（A-layer + C-layer 维护 baseline）

## Specs

Per D3 spec-delta 协同，spec.md 落 `openspec/specs/c-layer-agent-runner/spec.md`。
