# fix-disk-count-semantic-conflict — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `_count_skill_files()` 改为接受 `include_top_level: bool` 参数 (默认 False)
- [x] Task 2: `test_skill_metadata_consistency.bats` 保持现有语义 (sub-skill only) — no change needed, 已对齐
- [x] Task 3: 提供 `_count_skill_files(include_top_level: bool)` 参数供其他 test 复用
- [x] Task 4: 同步 `tests/unit/test_doc_contracts.py` 的注释和 docstring 解释 INSTALL 计入语义
- [x] Task 5: 新增 unit test 锁定两种 count 行为 (default vs include_top_level) + package.json 一致性
- [x] Task 6: 同步 `tests/integration/test_doc_contracts.py` (如有) — N/A, no such file exists

## 现状验证

- package.json::skills[].length = 27
- sub-skill SKILL.md count = 27
- bats disk count = 27
- _count_skill_files() (default) = 27
- _count_skill_files(include_top_level=True) = 28 (含 INSTALL.md)
- 所有四个来源一致 (含 INSTALL 时为 28, 不含为 27)
