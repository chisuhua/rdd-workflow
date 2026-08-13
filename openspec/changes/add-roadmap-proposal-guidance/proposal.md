## Why

当前 rdd-workflow 的 roadmap (在 `guide-arch` Phase 4 定义) 只描述 phase + category 结构,不携带"该节点需要哪些改进提案主题"的元数据。`guide-design` 阶段创建提案完全依赖用户手动从 roadmap 推导主题,无法自动消费约束,导致: (a) 提案覆盖率无法计算, (b) 用户容易遗漏某个 roadmap 分类的改进, (c) `add-improve` → `rdd-workflow-brainstorm` 流程对 roadmap 无感知。本提案打通"roadmap → proposal"约束驱动链路,使 roadmap 节点声明预期改进主题后,guide-design 能自动展示覆盖率并提供按主题创建提案的引导模式。

## What Changes

- **roadmap 模板扩展**: `roadmap.md` 的 `#### 任务分类` 表格新增第 5 列"预期改进方向",单元格可写 `主题1；主题2` (分号分隔)。`roadmap_state.py::add_phase()` 默认模板同步更新,新增 `get_phase_themes()` 函数解析该列。解析器向后兼容 4 列旧表格 (无 breaking change)。
- **proposal 模板扩展**: `rdd-workflow-brainstorm` 5 段元数据新增 `**主题**:` 字段,精确记录该提案绑定的 roadmap 主题 (可空 → 自由模式)。覆盖率计算用此字段精确字符串匹配。
- **`add-improve` 新增 `--from-roadmap` 模式**: 通过 env-var 模式传参 (Oracle C1 安全实践),调用 `add-improve` 时预填 theme/category/rationale 上下文,加载 `rdd-workflow-brainstorm` 时进入"约束模式"分支。**不绕过** brainstorm HARD-GATE,用户仍需 Step 4 逐段确认。
- **`rdd-workflow-brainstorm` 约束注入**: 约束模式下 Step 2 一般性澄清改为聚焦范围边界,Step 4 5 段设计预填 scaffold (架构依据由 AI 起草 + 用户确认)。这是 brainstorm 第一次支持参数化调用,需在 SKILL.md 文档化新 env-var 契约。
- **`guide-design` Phase 1 preflight 增强**: 新增显示 roadmap 主题数 + 当前提案覆盖率 + 未覆盖主题清单 (含已 `~skipped~` 豁免的状态)。
- **`guide-design` Phase 2 菜单新增选项**: "🎯 按路线图主题创建提案 (推荐)" — 列出未覆盖主题,用户选主题触发 `add-improve --from-roadmap`。
- **`STRICT_PROPOSAL_COVERAGE` 门控**: design-done Phase 4 新增可选 strict 校验,默认 warning,与现有 `STRICT_*_GATE` 模式对齐。主题状态词汇 `未覆盖 / 已覆盖 / ~skipped~` 三态明确,`~skipped~` 排除出分母。
- **迁移兼容**: 旧项目 v1 handoff + 无主题字段的旧 proposal 不强制补字段,coverage 显示"未标注主题 K 个"独立统计,避免 0/M 假警。

## Capabilities

### New Capabilities

- `roadmap-proposal-guidance`: roadmap 节点携带预期改进主题元数据,guide-design consume-time 直接解析并展示覆盖率,add-improve 支持约束注入模式按主题创建提案。覆盖 In Scope A/B/C/D/E 全部内容。

### Modified Capabilities

无现有 capability 的 REQUIREMENTS 修改 (本提案引入新能力,不改既有 spec 行为)。

## Impact

### 受影响代码

- `skills/roadmap/scripts/roadmap_state.py` — `add_phase()` 模板加 5 列,新增 `get_phase_themes()` 函数
- `skills/roadmap/SKILL.md` — init/edit 模板说明 5 列结构,新增 "预期改进方向" 列文档
- `skills/rdd-workflow-brainstorm/SKILL.md` — 5 段元数据模板加 `**主题**:` 字段,文档化新 env-var 契约
- `skills/add-improve/SKILL.md` — 新增 `--from-roadmap` 模式说明,文档化 env-var 命名
- `skills/add-improve/scripts/` — 新增 env-var 接收 + 约束模式分发逻辑
- `skills/guide-design/SKILL.md` — Phase 1 preflight 增加覆盖率显示,Phase 2 菜单新增选项 2
- `skills/guide-design/scripts/design_preflight.sh` — 新增 theme 解析 + coverage 计算
- `skills/guide-design/scripts/design_proposal_review.sh` — Phase 4 门控加 `STRICT_PROPOSAL_COVERAGE` 分支
- `CHANGELOG.md` — 记录新特性
- `AGENTS.md` — 新增主题状态词汇约定,env-var 命名规范

### 新增依赖

- 无新增外部依赖 (纯内部扩展)
- 新增 `proposal-suggestions.md` 表格可选第 6 列"主题" (向后兼容)

### 向后兼容性

- `roadmap.md` 4 列旧表格 → 按"无约束"处理,行为零变化
- 旧 proposal 无 `**主题**:` 字段 → 不报错,coverage 显示"未标注主题 K 个"
- `add-improve` 无参数调用 → 行为完全不变 (OPEN-PROMPT 自由模式)
- `.arch-handoff.json` schema 不动 (Oracle 关键建议,避免 rdd-doctor CRITICAL)

### 测试影响

- 新增 Python unit: `tests/unit/test_roadmap_state.py::test_get_phase_themes` (≥ 6 case)
- 新增 Python unit: `tests/unit/test_guide_design_preflight_themes.py` (coverage 计算)
- 新增 bats integration: `tests/integration/test_roadmap_5col_parsing.bats`
- 新增 bats integration: `tests/integration/test_add_improve_from_roadmap.bats`
- 现有 bats 测试 (roadmap/guide-design/add-improve/rdd-doctor) 全部回归无破坏