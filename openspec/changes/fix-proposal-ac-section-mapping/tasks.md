# fix-proposal-ac-section-mapping — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `_extract_section` 重构为接受 `title_or_titles: str | list[str]`
- [ ] Task 2: `generate_full_proposal.py` 调用改为 `["验收", "验收标准"]`
- [ ] Task 3: 新增 unit test `tests/unit/test_generate_full_proposal.py::test_acceptance_section_extraction`:
- [ ] Task 4: 已存在的 3 个 P1 proposal.md 重新生成:`sync-package-skills-to-disk`, `sync-agents-md-five-stage`, `rdd-doctor-docs-consistency`(用修复后的 script 重跑)
- [ ] Task 5: `rddf ac-verify sync-package-skills-to-disk` 至少返回 1 AC(以前返回 0)
- [ ] Task 6: 现有 `tests/unit/test_doc_contracts.py` 不回归
- [ ] Task 7: Run `bash tests/scripts/report_regression.sh` to confirm no new failures