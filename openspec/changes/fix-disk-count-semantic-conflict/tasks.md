# fix-disk-count-semantic-conflict — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `_count_skill_files()` 包含 `skills/INSTALL.md`(返回 28 for master)
- [ ] Task 2: `_count_skill_files()` 的 docstring 明确说明计入/排除策略
- [ ] Task 3: 新增 unit test 验证两个 test 用一致的 disk count 语义
- [ ] Task 4: `package.json::skills[]` 确认包含 `INSTALL` 字符串(28 entries)
- [ ] Task 5: 运行 `tests/unit/test_doc_contracts.py` 和 `bats tests/integration/test_skill_metadata_consistency.bats`,两者都 PASS
- [ ] Task 6: CI 跑 `./test.sh --full --regression` 不增加新 failure
- [ ] Task 7: Run `bash tests/scripts/report_regression.sh` to confirm no new failures