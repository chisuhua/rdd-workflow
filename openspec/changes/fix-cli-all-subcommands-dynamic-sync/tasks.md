# Tasks: fix-cli-all-subcommands-dynamic-sync

## Implementation Tasks

- [ ] Task 1: `tests/unit/test_cli_all_subcommands.py` 重构为动态 ALL_SUBCOMMANDS
- [ ] Task 2: 5 个单元测试 PASS（含白名单 / alias / 新增命令检测）
- [ ] Task 3: `tests/integration/test_cli_all_subcommands.bats`（如存在）适配新逻辑
- [ ] Task 4: 复现 2026-08-31 场景：临时删掉 ALL_SUBCOMMANDS 中 `hub` → pytest 不再 fail（动态发现自动含）
- [ ] Task 5: 模拟新增 `_cmd.py` → 白名单测试正确 fail（提示显式批准）
- [ ] Task 6: 与 `fix-report-regression-sed-double-hash-strip` (P0-2) 无交互：report_regression 逻辑不变
- [ ] Task 7: `docs/change-quality-guide.md` 加"CLI 子命令白名单"段（新增命令流程）
- [ ] Task 8: `tests/unit/test_cli_all_subcommands.py` 头注释更新说明动态发现机制
- [ ] Task 9: 复测 30 个现有 `_cmd.py` 全部正确发现（无遗漏无多余）
- [ ] Task 10: `rddf --help` 命令列表与 ALL_SUBCOMMANDS 一致
- [ ] Task 11: 与 `hub` / `scheduler` 子命令（2026-08-31 手工加过 tuple）不冲突：动态发现后无需手工维护
- [ ] Task 12: ship 后 30 天观察期：`test_cli_all_subcommands` 无新增失败（历史：添加新命令后必 fail 1 次）
- [ ] Task 13: 不引入新的 KNOWN_FAILURES 条目
