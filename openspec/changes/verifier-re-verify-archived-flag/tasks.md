# verifier-re-verify-archived-flag — Implementation Tasks

## Implementation Tasks

- [x] Task 1: argparse 添加 --re-verify-archived + --archived-since flag
- [x] Task 2: discover_archived() 枚举 archive/ 含日期提取
- [x] Task 3: --re-verify-archived 支持 dry-run 模式
- [x] Task 4: 默认 rdd-verify 行为不变 (向后兼容)
- [x] Task 5: 9 个 unit test 全部通过
- [x] Task 6: `bash tests/scripts/report_regression.sh` 不增加新 failure
