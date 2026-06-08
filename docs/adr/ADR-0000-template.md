# ADR-0000: <简短决策标题>

> **状态**: <待定 | 已采纳 | 已拒绝 | 已弃用 | 已替代为 ADR-NNN>
> **日期**: YYYY-MM-DD
> **决策者**: <name(s)>

## Context

<描述驱动此决策的上下文：问题、约束、相关方、为什么现在要做这个决策。>

**架构依据**（可引用其他 ADR / 文档）:
- <ADR-NNN §N.M: 标题>
- <docs/path/to/doc.md: 引用段>

## Decision

<用一句祈使句陈述决策（例如"我们采用 X 方案"）。然后展开解释为什么选 X、不选 Y、Z。>

### 影响范围

- **In Scope**: <哪些模块 / 目录 / 工作流被影响>
- **Out Scope**: <明确不涉及的内容>

### 备选方案

| 备选 | 理由 |
|------|------|
| X | 评估结果（接受/拒绝，原因） |
| Y | 评估结果（接受/拒绝，原因） |

## Consequences

### 正面

- <该决策带来的好处>

### 负面 / 风险

- <该决策带来的成本、风险、需要承担的权衡>

### 后续待办

- [ ] <未来需要进一步决策或实现的项，标 `待修复` / `暂不修复` / `未来参考`>

## References

- `docs/proposal-suggestions-format.md` — ADR 引用格式 `ADR-NNN §N.M`
- `skills/propose.md` Phase 1a — `ls docs/adr/ADR-*.md` 扫描入口
- `skills/deps.md` Step 1b — `adr_refs` 提取逻辑
- <其他相关 ADR / 文档链接>
