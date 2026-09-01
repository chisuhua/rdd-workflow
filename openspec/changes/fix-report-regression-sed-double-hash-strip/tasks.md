# Tasks: fix-report-regression-sed-double-hash-strip

## Implementation Tasks

- [x] Task 1: `tests/unit/test_report_regression_strip.py` 5 个 test PASS
- [x] Task 2: `tests/integration/test_report_regression_descriptions.bats` 3 个 test PASS
- [x] Task 3: 复测 `bash tests/scripts/report_regression.sh` 输出 `✅ 0 新增失败`（现共赢，回归保护）
- [x] Task 4: 显式复测 2 条含 `##` 的 ADR test description 被正确匹配（`every real ADR has a ## 决策 or ## Decision section`）
- [x] Task 5: `./test.sh --full --regression` 在当前 2 个已修复 ADR 场景跑出 0 新增失败（回归门 pass）
- [x] Task 6: 故意引入 1 个 description 含 `##` 的新 test fail → 报告脚本正确报"新增失败：1"且列出完整 description
- [x] Task 7: 与 `fix-specs-auto-generate-in-design-precreated` (P0-1) 无交互：spec 修复不影响 report_regression 解析
- [x] Task 8: `docs/change-quality-guide.md` 加"回归门 description 解析"新段（解释 `##` 陷阱 + 正确格式）
- [x] Task 9: `tests/scripts/report_regression.sh` 头注释加说明"description 处理规则"
- [x] Task 10: 复测当前 KNOWN_FAILURES.txt 132+ 条全量匹配（无新增失败、无 stale）
- [x] Task 11: 复测 pre-existing WIP 条目（`cli_all_subcommands` 等）仍被正确 strip + match
- [x] Task 12: 与 `add-known-failures-baseline` 提案（既有）不冲突：baseline 格式不变
- [x] Task 13: ship 后 30 天观察期：回归门"新增失败"误报率降至 0（历史：因本 bug 误报 1 次，需手工修）
- [x] Task 14: 不引入新的 KNOWN_FAILURES 条目（改动仅在第 3 阶段）
