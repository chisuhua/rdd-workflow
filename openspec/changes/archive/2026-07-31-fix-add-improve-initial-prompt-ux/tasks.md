## 1. add-improve/SKILL.md — Phase 0 无参数模式

- [x] 1.1 新增 "Phase 0 — 无参数模式" 章节，强制第一轮纯文本 prompt
- [x] 1.2 标注 <HARD-GATE>: 无参数模式下第一轮不得使用 question 工具
- [x] 1.3 提供 prompt 模板: "请用自然语言描述你想改进的内容（包含: 症状/痛点/期望效果/优先级/是否引用 ADR）"
- [x] 1.4 禁用清单: 不允许把"描述改进"做成多选题

## 2. rdd-workflow-brainstorm/SKILL.md — 第 95 行规则重写

- [x] 2.1 将"首选选择题"改为"初始描述必须开放；后续澄清可选择题"
- [x] 2.2 新增 OPEN-PROMPT 触发条件列表: 无参数调用 / 用户首次表达意图 / 初始需求收集

## 3. guide/SKILL.md — 输入模式判别章节

- [x] 3.1 新增"输入模式判别"章节
- [x] 3.2 列出 question 适用场景: stage 选择 / session 选择 / 固定结构化选项
- [x] 3.3 列出 question 不适用场景: 用户首次描述需求 / 用户主动要求自由输入
- [x] 3.4 提供判别 heuristic (决策树)

## 4. 验证

- [x] 4.1 grep 验证: add-improve/SKILL.md 含 "Phase 0" / "无参数模式" / "open prompt" 关键词
- [x] 4.2 grep 验证: brainstorm/SKILL.md 第 95 行不再含"首选选择题"字面
- [x] 4.3 grep 验证: guide/SKILL.md 含"输入模式判别"章节
- [x] 4.4 现有 bats + pytest 测试全部通过