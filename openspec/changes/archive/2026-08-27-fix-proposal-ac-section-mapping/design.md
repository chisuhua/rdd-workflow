# fix-proposal-ac-section-mapping — Design

## Context

`skills/guide-design/scripts/generate_full_proposal.py:142` 调用 `_extract_section(improvements_md, "验收标准")`,正则匹配 `^## 验收标准$`。
但实际 `.rddf/improvements/*.md` 文件中,acceptance section 的标题是 **`## 验收`**(2 字),不是 **`## 验收标准`**(4 字)。
后果:

- 所有经 `guide-design` approve 落盘的 `openspec/changes/<name>/proposal.md`,其 `## Acceptance` section 都是 fallback 占位符 `(TBD — 验收标准 from .rddf/improvements 头部未提供)`。

## Goals / Non-Goals

**Goals:**
- `_extract_section` 函数接受多个候选项标题,按顺序尝试匹配。
- `generate_full_proposal.py` 调用时同时传 `["验收", "验收标准"]`,或默认行为兼容两者。
- 新增 unit test 覆盖两种 improvement 标题格式。
- GIVEN 一个 `.rddf/improvements/<name>.md` 文件,header 是 `**优先级**/ **阶段**/ **分类**/ **类型**`,sections 是 `## 架构依据/ ## 范围/ ## 关键场景/ ## 技术约束/ ## 验收`
- GIVEN `generate_full_proposal.py` 对 `sync-package-skills-to-disk` 运行

**Non-Goals:**
- 统一所有现有 `.rddf/improvements/*.md` 的标题(向后兼容,不要 break 历史)。
- 修改 5 段 brainstorming 模板(SKILL.md)。
- 修复已存在的 TBD proposal.md(单独 P 提案)。

## Decisions

### 1. MUST: `_extract_section` 支持多个候选标题(列表输入)

Implementation MUST satisfy this constraint.

### 2. MUST: 优先级 — 优先匹配显式标题,fallback 到常见别名

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `_extract_section(md, ["验收", "验收标准"])` 的便利 API