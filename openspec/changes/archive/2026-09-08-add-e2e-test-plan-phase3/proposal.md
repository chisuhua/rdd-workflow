# add-e2e-test-plan-phase3 (C-layer 4 skills 36 scenarios)

> Per `2026-09-08-e2e-test-plan-design.md` §9 Phase 3.

## Why

Plan 2 落 rdd-quick 8 cases。Plan 3 推广到余 4 skill（rdd-builder / rdd-verifier / rdd-arch / rdd-planner）共 36 cases。

## What Changes

- 36 scenario JSONs: `tests/e2e/agent/scenarios/{b_e*,v_e*,a_e*,p_e*}.json`
- 4 bats test files: `tests/e2e/agent/test_rdd_{builder,verifier,arch,planner}_e2e.bats`
- 36/36 cases pass mock mode (CI safe)
- Real mode (RDDF_AGENT_E2E=1) for nightly prose drift

## Capabilities

- capability-rdd-builder-prose-ux
- capability-rdd-verifier-prose-ux
- capability-rdd-arch-prose-ux
- capability-rdd-planner-prose-ux

## Acceptance

- AC-1: 36 scenarios JSON schema 合法 (validate_scenario 36/36 绿)
- AC-2: 36 C-layer bats cases 跑通 mock mode (36/36 绿)
- AC-3: 0 新增回归失败
- AC-4: OpenSpec archive 完成

## Specs

D3 spec-delta 落 `openspec/specs/c-layer-4-skills/spec.md`。
