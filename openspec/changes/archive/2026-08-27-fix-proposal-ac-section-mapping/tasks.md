# fix-proposal-ac-section-mapping — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `_extract_section` 函数接受多个候选项标题, 按顺序尝试匹配 (refactored signature: title: str | list[str])
- [x] Task 2: `generate_full_proposal.py` 调用时同时传 `["验收", "验收标准"]` (line 151 updated)
- [x] Task 3: 新增 unit test `test_proposal_ac_section_mapping.py` 覆盖两种 improvement 标题格式 (7 tests, all pass)
- [x] Task 4: 验证 3 个 P1 docs-consistency change 的 proposal.md 不再显示 TBD (verified: generate_full_proposal now extracts ## 验收 section correctly)
