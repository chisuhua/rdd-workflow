# add-e2e-test-plan-phase2 (C-layer agent_runner + rdd-quick 8 scenarios)

> 提案已实施归档。规格见 `docs/superpowers/specs/2026-09-08-e2e-test-plan-design.md` §9 Phase 2 + `2026-09-08-rdd-quick-e2e-scenarios.md`。
> 实施 plan 见 `docs/superpowers/plans/2026-09-08-e2e-test-plan-phase2-c-layer-rdd-quick.md`。
> 归档目录：`openspec/changes/archive/2026-09-08-add-e2e-test-plan-phase2/`。
> D3 spec-delta 落 `openspec/specs/c-layer-agent-runner/spec.md`（7 Scenarios）。

## 实施摘要

- 1 framework: `tests/e2e/_lib/agent_runner.bash`（validate/mock/real 三模式）
- 8 scenarios: `tests/e2e/agent/scenarios/q_e{1..8}.json`（rdd-quick P0-P4 + 隔离契约）
- 9 unit cases: `tests/e2e/agent/test_agent_runner_{validate,mock,real}.bats`
- 8 C-layer cases: `tests/e2e/agent/test_rdd_quick_e2e.bats`（mock mode 100% pass）

## 提交链

3 commits on master:
- `merged`: agent_runner + tests + scenarios (3e1aa1a + 3897dad + 6a29b19)
- `archive`: c-layer-agent-runner spec-delta 落

## 后续 Phase

- Plan 3: C-layer 余 4 skill（rdd-builder 12 + rdd-verifier 8 + rdd-arch 8 + rdd-planner 8 = 36 cases）
- Plan 4: CI 集成（.github/workflows/e2e-nightly.yml）
- Plan 5: 外部 testbed 联动文档
