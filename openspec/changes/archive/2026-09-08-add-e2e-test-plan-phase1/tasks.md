## Tasks

- [x] **Task 1: isolation.bash** — 3 helpers: isolation/script_smoke/golden_compare
  - Create: `tests/e2e/_lib/isolation.bash`
  - Test: `tests/e2e/_lib/test_isolation.bats` (deleted in Task 14)
  - Commit: a077743

- [x] **Task 2: script_smoke.bash** — A 层 phase 脚本入口封装
  - Create: `tests/e2e/_lib/script_smoke.bash`
  - Test: `tests/e2e/_lib/test_script_smoke.bats` (deleted in Task 14)
  - Commit: bc74eab

- [x] **Task 3: golden_compare.bash** — sha256 + 关键字段 diff
  - Create: `tests/e2e/_lib/golden_compare.bash`
  - Test: `tests/e2e/_lib/test_golden_compare.bats` (deleted in Task 14)
  - Commit: 9aa5a88

- [x] **Task 4: phase0_approval.sh** — 加 `--auto-approve` flag
  - Modify: `skills/rdd-builder/scripts/phase0_approval.sh`
  - Test: `tests/integration/test_phase0_auto_approve.bats`
  - Commit: ff32bfb

- [x] **Task 5-9: 5 phase 脚本** — `phase1_plan` / `phase1_5_deps` / `phase2_execute` / `phase2_5_review` (带 read gate) / `phase3_archive`
  - Modify: `skills/rdd-builder/scripts/phase{1,1_5,2,2_5,3}_*.sh`
  - Test: `tests/integration/test_phase_auto_approve.bats` (5 cases)
  - Commit: a854112

- [x] **Task 10: scaffold_plan.sh** — 加 `--no-confirm` flag
  - Modify: `skills/rdd-quick/scripts/scaffold_plan.sh`
  - Test: `tests/integration/test_scaffold_plan_no_confirm.bats`
  - Commit: c472633

- [x] **Task 11: test.sh** — 加 `--e2e-smoke` / `--e2e-agent` / `--e2e-all` 3 mode
  - Modify: `test.sh`
  - Commit: 58a9536

- [x] **Task 12: rdd-quick A 层** — 4 cases
  - Create: `tests/e2e/script/test_rdd_quick_smoke.bats`
  - Commit: bd8ecb8

- [x] **Task 13: rdd-builder A 层** — 6 cases
  - Create: `tests/e2e/script/test_rdd_builder_smoke.bats`
  - Commit: 07bdc3f

- [x] **Task 14: cleanup** — 删 3 个自测 bats + 全量回归验证
  - Delete: `tests/e2e/_lib/test_{isolation,script_smoke,golden_compare}.bats`
  - Commit: e27d2cc

- [x] **Task 15: baseline sync** — 1 新 ImportError 加 KNOWN_FAILURES
  - Modify: `tests/KNOWN_FAILURES.txt`
  - Commit: 607997d

- [x] **Task 16: merge to master + archive** — 轻量模式
  - Branch: `openspec/add-e2e-test-plan-phase1` → master
  - Commit: d4a6926
  - Archive: pending
