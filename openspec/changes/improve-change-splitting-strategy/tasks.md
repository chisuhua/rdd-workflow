# improve-change-splitting-strategy — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `guide-design` Phase 2 增加检测 — 新建 `change_split_detect.sh` 在 `skills/guide-design/scripts/`
- [x] Task 2: 检测基于 `.rddf/improvements/*.md` 的 ## 范围 节 (backtick-quoted file paths)
- [x] Task 3: 检测结果作为 WARNING 输出, 不阻断 ship (默认 severity=warn)
- [x] Task 4: 提供 `--json` flag 输出结构化 conflict 列表
- [x] Task 5: 提供 `--strict-change-split` flag (out of scope — 留待后续 P2 提案)
- [x] Task 6: 新增 bats 测试 `test_change_split_detect.bats` (6 cases, all pass)
