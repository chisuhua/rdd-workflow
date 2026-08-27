# fix-proposal-ac-section-mapping

**优先级**: P1 | **来源**: 2026-08-27 ship audit (generate_full_proposal.py D1 编排 `_extract_section(md, "验收标准")` 不匹配 improvement 文件的 `## 验收` 标题,导致 proposal.md 的 Acceptance 是 TBD 占位符, rdd-verifier ac-verify 永远 parse 出 0 ACs)
**阶段**: phase-2 | **分类**: governance
**类型**: bugfix

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

`skills/guide-design/scripts/generate_full_proposal.py:142` 调用 `_extract_section(improvements_md, "验收标准")`,正则匹配 `^## 验收标准$`。但实际 `.rddf/improvements/*.md` 文件中,acceptance section 的标题是 **`## 验收`**(2 字),不是 **`## 验收标准`**(4 字)。

后果:

- 所有经 `guide-design` approve 落盘的 `openspec/changes/<name>/proposal.md`,其 `## Acceptance` section 都是 fallback 占位符 `(TBD — 验收标准 from .rddf/improvements 头部未提供)`。
- 2026-08-27 的 3 个 P1 docs-consistency change 都受此影响: proposal.md 显示 TBD,但 `.rddf/improvements/*.md` 实际有 7-8 条 acceptance checkboxes。
- `rddf ac-verify` 在 parse_acs 时返回 0 ACs(因为 proposal.md 只有 TBD),LLM 验证退化为空。
- rdd-verifier 的 AC 验证流程实际上从未真正跑过。

期望行为: `_extract_section` 应同时匹配 `## 验收` 和 `## 验收标准` 两种标题风格。

## 范围

**In Scope**:

- `_extract_section` 函数接受多个候选项标题,按顺序尝试匹配。
- `generate_full_proposal.py` 调用时同时传 `["验收", "验收标准"]`,或默认行为兼容两者。
- 新增 unit test 覆盖两种 improvement 标题格式。

**Out of Scope**:

- 统一所有现有 `.rddf/improvements/*.md` 的标题(向后兼容,不要 break 历史)。
- 修改 5 段 brainstorming 模板(SKILL.md)。
- 修复已存在的 TBD proposal.md(单独 P 提案)。

## 关键场景

- GIVEN 一个 `.rddf/improvements/<name>.md` 文件,header 是 `**优先级**/ **阶段**/ **分类**/ **类型**`,sections 是 `## 架构依据/ ## 范围/ ## 关键场景/ ## 技术约束/ ## 验收`
  WHEN `_extract_section(md, "验收")` 调用
  THEN 返回 `## 验收` section 的内容(包含所有 `- [ ]` checkboxes)

- GIVEN `generate_full_proposal.py` 对 `sync-package-skills-to-disk` 运行
  WHEN 生成的 `proposal.md` 落盘
  THEN `## Acceptance` section 包含 7 条具体 AC,而不是 `(TBD)` 占位符

## 技术约束

- MUST: `_extract_section` 支持多个候选标题(列表输入)
- MUST: 优先级 — 优先匹配显式标题,fallback 到常见别名
- MUST NOT: 改变 5 段标准结构(架构依据/范围/关键场景/技术约束/验收)
- SHOULD: 提供 `_extract_section(md, ["验收", "验收标准"])` 的便利 API

## 验收标准

- [ ] `_extract_section` 重构为接受 `title_or_titles: str | list[str]`
- [ ] `generate_full_proposal.py` 调用改为 `["验收", "验收标准"]`
- [ ] 新增 unit test `tests/unit/test_generate_full_proposal.py::test_acceptance_section_extraction`:
  - 验证 `## 验收` 标题被正确解析
  - 验证 `## 验收标准` 标题仍工作(向后兼容)
- [ ] 已存在的 3 个 P1 proposal.md 重新生成:`sync-package-skills-to-disk`, `sync-agents-md-five-stage`, `rdd-doctor-docs-consistency`(用修复后的 script 重跑)
- [ ] `rddf ac-verify sync-package-skills-to-disk` 至少返回 1 AC(以前返回 0)
- [ ] 现有 `tests/unit/test_doc_contracts.py` 不回归

## 相关

- 关联: `generate_full_proposal.py` D1 编排(guide-design 的 proposal 落盘阶段)
- 来源: 2026-08-27 全链路工作流审计
- 关联: ADR-0034 rdd-verifier — 此 bug 阻断 AC 验证
