# add-e2e-test-plan-phase1 (e2e-test-plan Phase 1)

> 提案已实施归档。规格见 `docs/superpowers/specs/2026-09-08-e2e-test-plan-design.md`（主策略 doc）+ 5 个 scenario spec。
> 实施 plan 见 `docs/superpowers/plans/2026-09-08-e2e-test-plan-phase1-a-layer.md`（14 tasks TDD 5 步）。
> 归档目录：`openspec/changes/archive/2026-09-08-add-e2e-test-plan-phase1/`。
> D3 spec-delta 落 `openspec/specs/e2e-test-infrastructure/spec.md`（6 Scenarios）。

## 背景

rdd-workflow 现状 281 bats + 2017 pytest，但按流程分布严重不均。`rdd-quick` 和 `rdd-builder` 无真实 e2e 覆盖。Phase 1 实施 A 层基础设施 + 10 A 层 cases（CI 必跑）。

## 实施摘要

- 3 helpers: `tests/e2e/_lib/{isolation,script_smoke,golden_compare}.bash`
- 6 phase scripts: `--auto-approve` flag（CI 非交互入口）
- `scaffold_plan.sh`: `--no-confirm` flag
- `test.sh`: 3 新 mode（`--e2e-smoke`/`--e2e-agent`/`--e2e-all`）
- 10 A 层 cases: `tests/e2e/script/`（4 rdd-quick + 6 rdd-builder）
- KNOWN_FAILURES.txt: 1 新增（test_deps_execution_mode ImportError，pre-existing per stash baseline 2026-09-08）

## 提交链

13 commits on master:
- `81feb93` archive(add-e2e-test-plan-phase1): archive completed
- `2a8b010` feat(plan1): add OpenSpec change artifacts
- `d4a6926` merge: add-e2e-test-plan-phase1 (A-layer e2e infrastructure)
- `607997d` chore(baseline): register test_deps_execution_mode
- `e27d2cc` test(e2e): clean up self-test bats from Task 1-3
- `07bdc3f` test(e2e): add A-layer rdd-builder smoke
- `bd8ecb8` test(e2e): add A-layer rdd-quick smoke
- `58a9536` feat(test.sh): add --e2e-smoke/--e2e-agent/--e2e-all
- `c472633` feat(rdd-quick): add --no-confirm flag
- `a854112` feat(rdd-builder): add --auto-approve to 5 phase scripts
- `ff32bfb` feat(rdd-builder): add --auto-approve to phase0_approval
- `9aa5a88` feat(e2e/_lib): add golden_compare.bash
- `bc74eab` feat(e2e/_lib): add script_smoke.bash
- `a077743` feat(e2e/_lib): add isolation.bash

## 后续 Phase

- Phase 2: C 层基础设施 + rdd-quick 试点（spec §9）
- Phase 3: C 层余 4 skill（rdd-builder/verifier/arch/planner）
- Phase 4: CI 集成（nightly cron + GitHub Actions）
- Phase 5: 外部 testbed 联动文档
