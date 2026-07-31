## Why

`skill_use("add-improve")` 无参数调用时，AI 弹 question 菜单让用户选择改进类型，但 Enter 键的"选中+提交"双重语义导致用户无法自由输入改进描述。根因是 3 处 SKILL.md 缺陷叠加：add-improve 无参数模式未定义 UX 流程、brainstorm 技能"首选选择题"规则被错误套用到初始描述收集场景、guide 技能缺少 question 工具的适用性判别。

## What Changes

- `skills/add-improve/SKILL.md` — 新增 Phase 0 无参数模式章节，强制第一轮纯文本 prompt
- `skills/rdd-workflow-brainstorm/SKILL.md` — 第 95 行"首选选择题"→"初始描述必须开放"
- `skills/guide/SKILL.md` — 新增"输入模式判别"章节
