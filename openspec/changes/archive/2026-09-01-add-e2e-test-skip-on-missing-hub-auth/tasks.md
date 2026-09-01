# Tasks: add-e2e-test-skip-on-missing-hub-auth

## Implementation Tasks

- [x] Task 1: `test_cross_repo_e2e_real.bats` setup_file 加 3 个前置检查（gh 存在 / gh auth / Hub 可达）
- [x] Task 2: `test_cross_repo_impact_detection.bats` 加同样前置检查
- [x] Task 3: 模拟无 gh 环境跑 `test_cross_repo_e2e_real.bats` → skip（非 fail）
- [x] Task 4: 模拟无认证跑 → skip
- [x] Task 5: 模拟 Hub 不可达跑 → skip
- [x] Task 6: 正常环境跑 → 13 test PASS（非 skip）
- [x] Task 7: `bats tests/integration/test_cross_repo_e2e_real.bats` 在无 Hub 环境输出 `ok`（skip）而非 `not ok`
- [x] Task 8: `./test.sh --full --regression` 在无 Hub 环境跑出 0 新增失败（不再依赖 KNOWN_FAILURES 标记 setup_file failed）
- [x] Task 9: KNOWN_FAILURES.txt 移除 `setup_file failed` 条目后回归门仍 pass
- [x] Task 10: `docs/change-quality-guide.md` 加"真实 E2E 测试 Skip-not-fail"段
- [x] Task 11: `tests/integration/README.md`（如有）补 E2E 前置条件说明
- [x] Task 12: `tests/KNOWN_FAILURES.txt` 头注释注明 `setup_file failed` 已由 skip 机制取代
- [x] Task 13: 有 Hub 的 CI 环境 E2E 测试全部 PASS（不 skip）
- [x] Task 14: 与 `fix-report-regression-sed-double-hash-strip` (P0-2) 无交互
- [x] Task 15: 与 `add-known-failures-baseline` 提案无冲突
- [x] Task 16: ship 后 30 天观察期：E2E setup_file failed 不再出现（无 Hub 时 skip，有 Hub 时 pass）
- [x] Task 17: KNOWN_FAILURES.txt 规模不因本提案扩大（反而移除 1 条）
