## Context

`skill_use("add-improve")` 无参数调用时，AI 默认使用 question 工具弹出多选菜单让用户选择改进类型。但用户的实际预期是直接自由输入改进描述。Enter 键在 question 工具中同时承担"选中+提交"双重语义，导致用户无法正常进入自由输入模式。

根因是 3 处 SKILL.md 的交互规则缺陷叠加：
1. `add-improve/SKILL.md` 只覆盖了带参数调用（`skill_use("add-improve fix-login-timeout")`），无参数模式的 UX 流程完全未定义
2. `rdd-workflow-brainstorm/SKILL.md:95` 的"首选选择题"规则被 AI 错误套用到初始描述收集场景
3. `guide/SKILL.md` 的 question 菜单使用没有适用性判别，导致所有用户输入都被菜单化

## Goals / Non-Goals

**Goals:**
- 无参数调用 `skill_use("add-improve")` 时，AI 第一轮必须用纯文本 prompt 收集用户描述
- `rdd-workflow-brainstorm` 的初始描述收集必须开放，后续澄清可选择题
- `guide` 技能新增 question 工具适用性判别规则

**Non-Goals:**
- 不修改 question 工具的 OpenCode 平台行为（Enter 双义性问题属平台层）
- 不修改 3 份文件之外的其它 SKILL.md
- 不引入新的 CLI 参数或工具

## Decisions

1. **第一轮强制纯文本 prompt**：`add-improve/SKILL.md` 新增 Phase 0 章节，标注 <HARD-GATE> 禁止第一轮使用 question 工具。提供 prompt 模板："请用自然语言描述你想改进的内容（包含: 症状/痛点/期望效果/优先级/是否引用 ADR）"
2. **初始描述开放原则**：`brainstorm/SKILL.md:95` 的"首选选择题"改为"初始描述必须开放；后续澄清可选择题"。新增 OPEN-PROMPT 触发条件列表：无参数调用 / 用户首次表达意图 / 初始需求收集
3. **question 判别规则**：`guide/SKILL.md` 新增输入模式判别章节，列出 question 适用场景（stage 选择/session 选择/固定结构化选项）和不适用场景（用户首次描述需求/用户主动要求自由输入）
4. **连续困惑检测**：当 AI 检测到用户连续 2 次未选择明确类别时，自动切换到开放 prompt 模式

## Risks / Trade-offs

- [Risk] 纯文本 prompt 可能收集到过于模糊的描述 → Mitigation: prompt 模板提供结构化引导（症状/痛点/期望效果/优先级）
- [Risk] 开发者可能不写 SKILL.md 直接调用 question 工具 → Mitigation: <HARD-GATE> 标注 + 代码审查
- [Trade-off] 增加判别逻辑使 SKILL.md 更复杂 → 但这是必要的 UX 改进，能避免用户困惑