# fix-add-improve-initial-prompt-ux

**优先级**: P1 | **来源**: 会话复盘 2026-07-31 — add-improve 无参数模式交互阻塞
**阶段**: default | **分类**: core-impl
**类型**: feature

## 架构依据

- 用户 `skill_use("add-improve")` 调用时未传 `<name>` 参数, 进 add-improve 后 AI 用 `question` 工具弹出多选菜单期望用户从中选择改进类型（代码重构 / 测试 / 工具链 / 我自己描述）。
- 用户实际预期: 直接打字描述改进内容, 然后 AI 收 description 进入 5 段设计。
- 实际体验: 按 Enter 想"先选再打字", 但 Enter 同时承担"选中+提交"双重语义, 直接提交了高亮选项。下一轮 AI 又弹菜单, 用户感觉"回车就结束, AI 就开始说话", 无法进入自由输入。
- 根因（3 处 SKILL.md 缺陷叠加）:
  1. `skills/add-improve/SKILL.md` 的"使用方式"只覆盖带名参数调用 (`skill_use("add-improve fix-login-timeout")`), **完全没规定无参数模式的 UX 流程**。
  2. `skills/rdd-workflow-brainstorm/SKILL.md:95` 写"首选选择题", 被 AI 错误地套用到"收集用户初始描述"这一本应是开放 prompt 的场景。
  3. `skills/guide/SKILL.md:140` 的"自由讨论模式"也需要通过选 "💬 自由讨论" 进入, 所有用户输入都被菜单化, 没有预留"AI 别菜单, 让用户直接打字"的入口。
- 复现路径: `skill_use("add-improve")` → AI 弹 5-12 项菜单 → 用户按 Enter → 提交默认选项 → AI 再次弹菜单 → 循环, 用户无法表达自由文本。
- 影响面: 所有无参数调用 `add-improve` / `guide-design` / `add-proposal-defer-support` 等依赖初始描述收集的 skill; 用户被迫先用 CLI 参数传 name 绕开（违反 convention, 新用户门槛高）。

## 范围

- **In Scope**:
  - `skills/add-improve/SKILL.md` 新增 "Phase 0 — 无参数模式" 章节, 规定:
    - 强制第一轮必须用**纯文本 prompt**(禁用 `question` 工具的多选菜单)
    - 提供 prompt 模板: "请用自然语言描述你想改进的内容（包含: 症状/痛点/期望效果/优先级/是否引用 ADR）"
    - 禁用清单: 不允许把"描述改进"做成多选题; 不允许假设用户会用 <name> CLI 参数
  - `skills/rdd-workflow-brainstorm/SKILL.md` 第 95 行规则重写:
    - "首选选择题" → "**初始描述收集必须开放**; 后续澄清可选择题"
    - 新增 "OPEN-PROMPT 触发条件" 列表: 无参数调用 / 用户首次表达意图 / 初始需求收集
  - `skills/guide/SKILL.md` 新增 "输入模式判别" 章节:
    - `question` 工具适用: stage 选择 / session 选择 / 固定结构化选项
    - `question` 不适用: 用户首次描述需求 / 用户主动要求自由输入时
    - 提供判别 heuristic (决策树)
- **Out Scope**:
  - 不修改 `question` 工具的 OpenCode 平台行为（Enter 双义性问题属平台层, 不在 rdd-workflow 范围）
  - 不修改除上述 3 份外的其它 SKILL.md（如 `guide-ship`、`guide-plan` 等不依赖初始描述收集的 skill）
  - 不引入新的 CLI 参数或工具

## 关键场景

- GIVEN `skill_use("add-improve")` 无参数调用, WHEN AI 加载 add-improve skill, THEN AI 第一轮 prompt 是纯文本"请描述改进内容", 不弹任何 question 菜单
- GIVEN 用户在 add-improve 流程中已描述改进, WHEN AI 询问优先级 / 范围 / 触发原因等子项, THEN AI 可用 question 菜单（选择题适用场景）
- GIVEN 用户在 `guide` 自由讨论模式主动打字"我想改进 X", WHEN AI 识别为初始意图, THEN AI 用文本回应而非菜单
- GIVEN 用户对 question 菜单感到困惑, WHEN AI 检测到用户连续 2 次未选择明确类别, THEN AI 切换到开放 prompt 让用户自由描述

## 技术约束

- MUST `skills/add-improve/SKILL.md` 新增 Phase 0 章节, 并标注 <HARD-GATE>: 无参数模式下第一轮不得使用 `question` 工具
- MUST `skills/rdd-workflow-brainstorm/SKILL.md` 修改第 95 行规则为"初始描述开放, 后续澄清选择"
- MUST `skills/guide/SKILL.md` 新增"输入模式判别"章节, 列出 `question` 适用 / 不适用场景
- MUST NOT 修改 3 份之外任何 SKILL.md
- MUST NOT 引入新的 CLI 参数或外部工具依赖
- SHOULD 在改进 3 份 SKILL.md 后, 同步更新 `/workspace/project/rdd-workflow/skills/_lib/` 下任何引用"选择题优先"的代码注释
- SHOULD 在 PR 描述中附复现视频或 GIF 演示修复前的 UX 阻塞

## 验收标准

- `skills/add-improve/SKILL.md` 含 "Phase 0" / "无参数模式" / "open prompt" 关键词命中（grep 验证）
- `skills/rdd-workflow-brainstorm/SKILL.md` 第 95 行不再含"首选选择题"字面, 改为"初始描述必须开放"
- `skills/guide/SKILL.md` 含新章节 "输入模式判别" 或类似命名
- 端到端测试: 模拟用户 `skill_use("add-improve")` 无参数调用, 验证第一轮 AI 输出不包含 `question` 工具调用
- 端到端测试: 模拟用户在 `guide` 菜单中选"自由讨论"后, 输入"我想改进 X", 验证 AI 不再弹菜单
- 所有现有 bats + pytest 测试通过 (`npm test` + `pytest tests/`)
