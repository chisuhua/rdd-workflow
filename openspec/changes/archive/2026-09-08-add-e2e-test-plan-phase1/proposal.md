# add-e2e-test-plan-phase1

> Per `2026-09-08-e2e-test-plan-design.md` §9 Phase 1 + `2026-09-08-rdd-quick-e2e-scenarios.md` + `2026-09-08-rdd-builder-e2e-scenarios.md`.

## Why

rdd-workflow 现状：281 bats + 2017 pytest，但按流程分布严重不均。`rdd-quick` 和 `rdd-builder` 无真实 e2e 覆盖（契约/结构层而已），导致 prose UX 漂移和 phase 脚本空跑风险。

外部 testbed `chisuhua/rdd-workflow-e2e` 覆盖 4-5 stage 全流程集成，但**不覆盖**本仓单 skill 内部状态机 prose UX、失败回环、隔离契约。

## What Changes

按 `2026-09-08-e2e-test-plan-design.md` §9 Phase 1 实施 A 层基础设施：

- 新增 `tests/e2e/_lib/` 下 3 个 helper：`isolation.bash`（快照/校验零污染）、`script_smoke.bash`（fake project + phase 入口封装）、`golden_compare.bash`（C 层 key-field drift 检测）
- 6 个 `rdd-builder/scripts/phase{0,1,1_5,2,2_5,3}_*.sh` 加 `--auto-approve` flag（CI 非交互入口）
- `rdd-quick/scripts/scaffold_plan.sh` 加 `--no-confirm` flag
- `test.sh` 加 3 个 mode：`--e2e-smoke`（CI 必跑）、`--e2e-agent`（nightly，需 `RDDF_AGENT_E2E=1`）、`--e2e-all`（本地选）
- `tests/e2e/script/` 下 10 A 层 cases：4 rdd-quick（Q-E1/Q-E2/Q-E3/Q-E8 A 层子集）+ 6 rdd-builder（B-E1/B-E3/B-E4/B-E6/B-E8/B-E9 A 层子集）
- 现有 5 planner_feedback_id_uniqueness + 1 test_deps_execution_mode ImportError 加 `KNOWN_FAILURES.txt`（均为 pre-existing，stash baseline 验证）

## Capabilities

- capability-e2e-infrastructure
- capability-ci-non-interactive-phases
- capability-test-runner-extensibility

## Acceptance

- AC-1: `./test.sh --e2e-smoke` 10/10 通过（CI 必跑）
- AC-2: 6 phase 脚本加 `--auto-approve` 后 `bash <script> --auto-approve` 不 TTY hang（status ≠ 124）
- AC-3: `tests/e2e/_lib/isolation.bash` 6 locked paths（.rddf/、openspec/、.rddf/wt/ + 3 state 文件）sha256 锁一致
- AC-4: 现有 `./test.sh --full --regression` 无新增失败（仅 baseline 6 个）
- AC-5: `test.sh --e2e-agent` 无 `RDDF_AGENT_E2E=1` 时 SKIP 退出 0
- AC-6: KNOWN_FAILURES.txt 新增 2 条（planner_feedback 5× 已存在；test_deps_execution_mode 1× 新增）

## Specs

Per D3 spec-delta 协同（`2026-09-08-rdd-quick-e2e-scenarios.md` Q-E1..Q-E8 + `2026-09-08-rdd-builder-e2e-scenarios.md` B-E1..B-E12 描述所有 AC 字段），spec.md 落 `openspec/specs/e2e-test-infrastructure/spec.md`。
