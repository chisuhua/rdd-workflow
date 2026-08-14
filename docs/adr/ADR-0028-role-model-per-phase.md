# ADR-0028: Role Model Per Phase

> **状态**: 已采纳
> **日期**: 2026-08-14
> **决策者**: sisyphus

## 问题

rdd-workflow v2.1 的 4 个阶段技能 (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) 的"职责边界"段落是叙述性文字，缺乏结构化的角色元数据。这导致：
1. 新开发者无法在 frontmatter 快速理解角色边界
2. AI 代理可能意外跨阶段边界（如 arch 阶段写 openspec/changes/）
3. 角色一致性依赖提示词隐性引导而非显式约束

## 决策

在 4 个阶段 SKILL.md 的 YAML frontmatter 中添加 `role:` 顶层字段，包含 5 个子字段：

```yaml
role:
  title: "Architect (架构治理者)"  # 双语角色名
  perspective: "..."  # 思考视角（1-2 句）
  boundaries:
    owns: [...]  # 文件路径清单
    not_owns: [...]  # 明确禁止的文件路径
    human_involvement: "high"  # 高/中/低（ADR-0003 梯度）
```

新建 JSON Schema (`_lib/schemas/skill_role_schema.json`) 定义字段类型。

SKILL.md 正文的"职责边界"段落改为引用 frontmatter 字段（单一事实来源）。

## 后果

**正面**：
- 新开发者在 frontmatter 即可了解角色边界
- git blame frontmatter 可追溯角色定义历史
- 角色一致性有显式文档基础（虽未强制 AI 行为）

**负面**：
- 新字段增加 frontmatter 解析负担（向后兼容：缺字段时仍可加载）
- 文档化角色不自动强制 AI 行为（需独立提案）

**中立**：
- 不修改现有 ADR-0003 / ADR-0017 / ADR-0025
- 不引入子技能角色继承（propose/execute/status 等留后续）

## 参考

- ADR-0003: 三阶段架构（现为四阶段）
- ADR-0007: Skill frontmatter 规范
- ADR-0017: rddf-session
- ADR-0025: 设计阶段独立化
