# add-phase-role-model

## Why

本提案建立于以下架构原则和已识别缺口之上：

### 现有架构依据

1. **ADR-0003 三阶段架构（现已扩展为四阶段 arch → design → plan → ship）**：
   - 已定义**人工介入度梯度**（高 → 中 → 中 → 低），但未结构化为可操作的"角色视角"和"职责边界"
   - 现有各 SKILL.md 在"职责边界"段落中已有非形式化的角色描述（如 "需要架构师思考、审查、决策"），但散落且不一致

2. **ADR-0007 Skill frontmatter 规范**：
   - 顶层字段（name / description / license / compatibility）只描述**契约**（CLI 版本、git 版本），不描述**角色语义**
   - `metadata:` 嵌套字段（author / version / evolved-from / user-invocable）只描述**元数据**，不描述**视角/边界**

3. **ADR-0017 rddf-session + ADR-0025 设计阶段独立化**：
   - 工作流已拆分到 4 个独立状态机，但**未配套"角色一致性"约束**
   - 当前 SKILL.md 的"职责边界"段落是叙述性文字，AI 实际行为依赖提示词中的隐性引导

### 识别的缺口（来自本次讨论）

1. **角色一致性缺口**：用户调 `guide-arch` 后进入"自由讨论"模式（`guide` 推荐器层），AI 应该保持"架构师视角"还是降级为"工作流推荐员"？当前**无显式规则**
2. **状态机边界缺口**：guide-arch 阶段 AI 不会自动检查"是否在写 `openspec/changes/<name>/`"——这是边界违规的常见来源
3. **提示词隐性引导缺口**：当前每个 SKILL.md 都有"职责边界"段落但未结构化，AI 行为依赖解读而非强制

### 引用现有惯例

- 现有 SKILL.md 的"职责边界"段落（guide-arch.md §职责边界, guide-design.md §职责边界, guide-plan.md §职责边界, guide-ship.md §职责边界）是**事实来源**
- ADR 模板（`docs/adr/ADR-0000-template.md`）的"决策"和"后果"段落是 ADR-0028 写作格式参考
- 现有 schema 目录：`_lib/schemas/`（项目根，无 `skills/` 前缀，10 个 .json schema），新 schema 沿用此路径

## What Changes

**In Scope**:

- **ADR-0028 创建**：`docs/adr/ADR-0028-role-model-per-phase.md`，记录"角色 = 状态机 + 视角 + 边界"三元组的架构决策
- **SKILL.md frontmatter 扩展（一次性 4 文件）**：4 个 SKILL.md（guide-arch / guide-design / guide-plan / guide-ship）的 YAML frontmatter 添加 `role:` 顶层字段，含：
- `role.title`：人类可读角色名（如 "Architect / Tech Lead / DevOps"）
- `role.perspective`：思考视角（叙述性，1-2 句）
- `role.boundaries.owns`：owns 的文件路径清单
- `role.boundaries.not_owns`：明确禁止 owns 的文件路径清单
- `role.boundaries.human_involvement`：高/中/低（对应 ADR-0003 梯度）
- **SKILL.md 正文同步**：将现有"职责边界"段落改为**引用 frontmatter**而非重复陈述，确保单一事实来源
- **新建 schema**：`_lib/schemas/skill_role_schema.json` 集中定义 `role:` 字段类型与默认值
- **bats 测试覆盖**：1 个综合测试 `tests/integration/test_skill_role_all.bats`，验证 4 个 SKILL.md 的 frontmatter 解析 + 5 个 sub-field 存在性 + schema 合规
- **AGENTS.md 同步更新**：在 `rdd-workflow/AGENTS.md` 关键约定章节引用 ADR-0028，便于未来开发者溯源
- **不修改 AI 提示词自动拼接机制**：LLM 仍按现有方式读取 frontmatter，本提案不写 hook/prompt 注入器
- **不写自动边界检测 linter**：不写 pre-commit / bats hook 检查"AI 是否越权写文件"，仅靠角色一致性 + 现有 reviewer 流程
- **不修改"自由讨论模式"行为**：保留 `guide` 推荐器层的"意图路由规则"，不引入"角色继承到 free discussion"
- **不修改 OpenSpec CLI 行为**：不写 `openspec` 插件
- **不引入子技能角色继承机制**：propose/execute/status 等子技能不继承 guide-plan/guide-ship 角色（除非后续单独提案）
- **不修改现有 ADR-0003 / ADR-0017 / ADR-0025**：本提案是"角色语义补充"，不重定义现有架构
- **AI 实际行为强制约束**：本提案只在 frontmatter 文档化角色，**不强制 LLM 行为**——属 OpenSpec CLI 改造 / AI 框架层独立提案
- **其他子技能（propose/execute/status/deps/roadmap/feature/rddf-session/add-improve/rdd-env-check/rdd-doctor）的角色定义**：属后续提案范围

### 关键场景

### 场景 1：arch 阶段防越权

- **GIVEN** AI 已调 `skill_use("guide-arch")` 并完成 Phase 1 setup
- **WHEN** 用户在 arch 阶段中请求"帮我创建一个新 change X"
- **THEN** AI 引用 frontmatter 的 `role.boundaries.not_owns` 字段（"不 owns: openspec/changes/<name>/"），回复：
  > "arch 阶段不直接创建 change。建议先完成 arch-done，然后运行 `guide-design` 走提案批准流程。"
- **AND** AI 不调用 `openspec new` 或 `mkdir openspec/changes/X/`

### 场景 2：自由讨论模式角色一致性

- **GIVEN** 用户调 `skill_use("guide")` 进入"💬 自由讨论"
- **WHEN** 用户问"arch 阶段具体做什么？"
- **THEN** AI **不**直接给架构方案（避免角色升级）
- **AND** AI 引用 `skills/guide-arch/SKILL.md` 的 `role.title` + `role.perspective`，引导用户：
  > "arch 阶段是 Architect 角色，专注于架构治理（ADR/roadmap）。要开始吗？`skill_use('guide-arch')`"
- **WHEN** 用户在 free discussion 中问"该不该用微服务"（具体架构问题）
- **THEN** AI 检测到意图模糊，推荐 `skill_use("guide-arch")` 进入正式阶段，而非自行给方案

### 场景 3：新开发者 onboarding

- **GIVEN** 新开发者打开 `skills/guide-arch/SKILL.md` 阅读 frontmatter
- **WHEN** 看到 `role.title: "Architect (架构治理者)"` + `role.boundaries.owns: [...]`
- **THEN** 立即理解本阶段 AI 行为边界，无需通读全文
- **AND** 通过 git blame `frontmatter` 字段可追溯角色定义历史

### 场景 4：跨阶段切换的角色传递

- **GIVEN** arch-done 已完成（写入 `.rddf/state/.arch-handoff.json`）
- **WHEN** AI 进入 `guide-design` 阶段
- **THEN** AI 引用 `skills/guide-design/SKILL.md` 的 `role.title: "Proposal Manager (提案经理)"` 切换角色视角
- **AND** 不继承 arch 角色的"owns `docs/adr/`" 边界（design 阶段明确不 owns ADR）
- **AND** 现有 rddf-session entry hook（ADR-0017）正常工作，记录角色切换点

**Out of Scope**:

- (TBD)

## Capabilities

- **frontmatter YAML schema 严格**：新增字段必须 snake_case（如 `human_involvement`），类型与默认值在 `_lib/schemas/skill_role_schema.json` 集中定义（注意路径：项目根 `_lib/schemas/`，**不是** `skills/_lib/schemas/`）
- **保持现有 frontmatter 兼容性**：新字段为**可选 + 默认值**，缺字段时 SKILL.md 必须仍可被现有 skill 加载逻辑解析（向后兼容）
- **单一事实来源**：SKILL.md 正文中"职责边界"段落必须引用 frontmatter 字段，禁止重复陈述（避免 drift）
- **边界清单准确性**：`role.boundaries.owns` / `role.boundaries.not_owns` 必须与各 SKILL.md 当前实际行为对齐（不自创边界）
- **bats 测试覆盖**：1 个综合测试 `tests/integration/test_skill_role_all.bats` 验证 4 个 SKILL.md 的 frontmatter 解析 + 5 个 sub-field 存在性 + schema 合规
- **AGENTS.md 同步更新**：在 `rdd-workflow/AGENTS.md` 关键约定章节引用 ADR-0028，便于未来开发者溯源
- **不修改现有 frontmatter 顶层字段**（name / description / license / compatibility）—— 仅扩展
- **不写自动边界检查 hook**（pre-commit / bats pre-merge）—— 角色一致性靠 reviewer 流程
- **不修改 OpenSpec CLI 行为**（不写 openspec 插件）
- **不修改 rddf-session lifecycle**（不引入"角色切换"作为 session kind 的新维度）
- **不引入跨子技能角色继承**（propose/execute/status 等子技能不继承 guide-* 角色）
- **不写 Python 模块**（角色定义在 frontmatter YAML，不引入新 Python 加载器）
- **不拆分 PR**（4 个 SKILL.md 同变更，单 PR 一次性提交）
- **每个 SKILL.md 的 `role.title` 使用中英双语**：方便国际化（参考现有"Architect (架构治理者)"模式）
- **bats 测试复用现有 `load test_helper` + `load_lib skill.bash`**：保持测试基础设施一致
- **ADR-0028 与现有 ADR-0021 (Phase 2 per-skill helper migration) 风格对齐**：标题、章节、决策结构
- **CHANGELOG.md 同步更新**：在 changelog 中标注"skill frontmatter 扩展"为向后兼容变更

## Impact

- **frontmatter YAML schema 严格**：新增字段必须 snake_case（如 `human_involvement`），类型与默认值在 `_lib/schemas/skill_role_schema.json` 集中定义（注意路径：项目根 `_lib/schemas/`，**不是** `skills/_lib/schemas/`）
- **保持现有 frontmatter 兼容性**：新字段为**可选 + 默认值**，缺字段时 SKILL.md 必须仍可被现有 skill 加载逻辑解析（向后兼容）
- **单一事实来源**：SKILL.md 正文中"职责边界"段落必须引用 frontmatter 字段，禁止重复陈述（避免 drift）
- **边界清单准确性**：`role.boundaries.owns` / `role.boundaries.not_owns` 必须与各 SKILL.md 当前实际行为对齐（不自创边界）
- **bats 测试覆盖**：1 个综合测试 `tests/integration/test_skill_role_all.bats` 验证 4 个 SKILL.md 的 frontmatter 解析 + 5 个 sub-field 存在性 + schema 合规
- **AGENTS.md 同步更新**：在 `rdd-workflow/AGENTS.md` 关键约定章节引用 ADR-0028，便于未来开发者溯源
- **不修改现有 frontmatter 顶层字段**（name / description / license / compatibility）—— 仅扩展
- **不写自动边界检查 hook**（pre-commit / bats pre-merge）—— 角色一致性靠 reviewer 流程
- **不修改 OpenSpec CLI 行为**（不写 openspec 插件）
- **不修改 rddf-session lifecycle**（不引入"角色切换"作为 session kind 的新维度）
- **不引入跨子技能角色继承**（propose/execute/status 等子技能不继承 guide-* 角色）
- **不写 Python 模块**（角色定义在 frontmatter YAML，不引入新 Python 加载器）
- **不拆分 PR**（4 个 SKILL.md 同变更，单 PR 一次性提交）
- **每个 SKILL.md 的 `role.title` 使用中英双语**：方便国际化（参考现有"Architect (架构治理者)"模式）
- **bats 测试复用现有 `load test_helper` + `load_lib skill.bash`**：保持测试基础设施一致
- **ADR-0028 与现有 ADR-0021 (Phase 2 per-skill helper migration) 风格对齐**：标题、章节、决策结构
- **CHANGELOG.md 同步更新**：在 changelog 中标注"skill frontmatter 扩展"为向后兼容变更

## Acceptance

### 量化指标

- **AC-1（frontmatter 解析）**：4 个 SKILL.md 都能被现有 `load_lib skill.bash` 解析通过，无 YAML 错误（CI 跑 `bats tests/smoke.bats` 验证）
- **AC-2（schema 一致性）**：所有 4 个 SKILL.md 的 `role:` 字段都包含 `title` / `perspective` / `boundaries.owns` / `boundaries.not_owns` / `boundaries.human_involvement` 5 个子字段，无缺漏
- **AC-3（边界准确性）**：每个 SKILL.md 的 `role.boundaries.owns` 字段值与该 SKILL.md "职责边界"段落中的"拥有"清单**完全一致**（人工 review 验证）
- **AC-4（bats 测试覆盖）**：新增 `tests/integration/test_skill_role_all.bats` 综合测试，覆盖 4 个 SKILL.md 的 frontmatter 解析 + 5 个 sub-field 存在性 + schema 合规，全部 pass
- **AC-5（向后兼容）**：删除某个 SKILL.md 的 `role:` 字段后，该 SKILL.md 仍能正常被 `skill_use()` 加载（不引入强依赖）
- **AC-6（ADR 文件存在）**：`docs/adr/ADR-0028-role-model-per-phase.md` 文件存在，编号连续（紧跟 ADR-0027）
- **AC-7（schema 文件存在）**：`_lib/schemas/skill_role_schema.json` 文件存在，定义 `role:` 字段类型与默认值
- **AC-8（AGENTS.md 同步）**：`rdd-workflow/AGENTS.md` "关键约定"章节包含指向 ADR-0028 的引用块

### 验证方法

- `./test.sh --full` 跑全量回归（含 1 个新 bats + 现有 117 个集成测试）
- 手工 review 每个 SKILL.md 的 frontmatter diff，确认字段值准确
- 模拟场景 1-4（关键场景），用真实对话验证 AI 行为是否符合 frontmatter 声明

### 排除（不在本提案验收范围）

- AI 是否**实际遵循** frontmatter 角色定义（属 LLM 行为，不在本提案验证范围内）
- 其他子技能（propose / execute / status / deps / roadmap / feature / rddf-session / add-improve / rdd-env-check / rdd-doctor）的角色定义（属后续提案范围）

