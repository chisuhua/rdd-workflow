# Tasks: add-roadmap-proposal-guidance

## 1. Roadmap 模板与解析器扩展

- [ ] 1.1 修改 `skills/roadmap/scripts/roadmap_state.py::add_phase()` 默认模板,`#### 任务分类` 表格新增第 5 列 "预期改进方向"
- [ ] 1.2 在 `roadmap_state.py` 新增 `get_phase_themes(phase_id, category_id) -> list[str]` 函数,解析第 5 列 cell (分号分隔)
- [ ] 1.3 实现向后兼容: 4 列旧表格返回空列表,不报错
- [ ] 1.4 新增 `tests/unit/test_roadmap_state.py::test_get_phase_themes` (≥ 6 case: 空 cell, 单主题, 多主题分号, 含特殊字符, 跨 phase, 4 列兼容)

## 2. Improvement Proposal 模板扩展

- [ ] 2.1 修改 `skills/rdd-workflow-brainstorm/SKILL.md` 5 段元数据模板,新增 `**主题**: <theme-name> | 不适用` 字段
- [ ] 2.2 在 add-improve 自由模式 (`skill_use("add-improve")` 无参数) 创建的 proposal 中,该字段为空或 `不适用`
- [ ] 2.3 新增 `tests/unit/test_brainstorm_template.py::test_subject_field` 验证模板含新字段

## 3. add-improve --from-roadmap 模式实现 (env-var 传参)

- [ ] 3.1 创建 `skills/add-improve/scripts/from_roadmap.sh` — bash 入口,接收 `--from-roadmap <phase/cat> --theme <name>` 参数,转为 env-var (`ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`) 并调用 from_roadmap.py
- [ ] 3.2 创建 `skills/add-improve/scripts/from_roadmap.py` — Python 主逻辑,接收 env-var,设置 brainstorm 约束模式,创建 proposal front matter 含 `**主题**:` 字段
- [ ] 3.3 创建 `skills/add-improve/scripts/from_roadmap.env.py` — env-var 接收 + 校验 (theme 名禁止 shell 特殊字符,必填校验)
- [ ] 3.4 在 `skills/add-improve/SKILL.md` 文档化 `--from-roadmap` 模式 + env-var 命名规范
- [ ] 3.5 实现调用结束 `unset` env-var 避免污染 shell
- [ ] 3.6 新增 `tests/unit/test_from_roadmap_env_validation.py` (恶意输入测试: `$()`, 反引号, `"; rm -rf #`, 换行符)

## 4. rdd-workflow-brainstorm 约束注入

- [ ] 4.1 在 `rdd-workflow-brainstorm/SKILL.md` 文档化"约束模式"分支 — 检测 `--from-roadmap` env vars 触发
- [ ] 4.2 约束模式下 Step 2 (澄清问题) 跳过一般性"你想改什么?"问题,改为聚焦范围边界
- [ ] 4.3 约束模式下 Step 4 (5 段设计) 预填 scaffold:
  - 架构依据: AI 起草 + 用户确认 (rationale draft 通过 `BRAINSTORM_RATIONALE_DRAFT` env-var 传入)
  - 范围: 从 category description 派生
  - 验收标准: 从 phase completion criteria 派生
- [ ] 4.4 HARD-GATE 验证: 约束模式下用户拒绝某段 → 不创建文件,proposal-suggestions.md 不变
- [ ] 4.5 新增 `tests/integration/test_add_improve_from_roadmap.bats` (覆盖约束模式全流程)

## 5. guide-design preflight 覆盖率显示

- [ ] 5.1 在 `skills/guide-design/scripts/design_preflight.sh` 新增 theme 解析: 调用 `roadmap_state.py::get_phase_themes()` 获取所有 phase/category 主题
- [ ] 5.2 实现 coverage 计算: 扫描 `.rddf/improvements/*.md` front matter,精确匹配 `**主题**:` 字段,统计已映射 X / 未标注 K
- [ ] 5.3 在 preflight 输出覆盖率信息 (路线图指引 M 主题 across N 分类, 当前覆盖 X/M (Y%), 未覆盖主题列表)
- [ ] 5.4 处理 `~skipped~` 主题: 从分母中排除
- [ ] 5.5 修改 `skills/guide-design/SKILL.md` Phase 1 章节,文档化新显示格式
- [ ] 5.6 新增 `tests/unit/test_guide_design_preflight_themes.py` (覆盖率算法测试)

## 6. guide-design Phase 2 菜单新增按主题创建选项

- [ ] 6.1 修改 `skills/guide-design/SKILL.md` Phase 2 菜单,新增选项 2 "🎯 按路线图主题创建提案 (推荐)"
- [ ] 6.2 实现选项 2 行为: 列出未覆盖主题 (按 phase/category 分组),用户选主题后触发 `add-improve --from-roadmap`
- [ ] 6.3 验证现有选项 1 (自由模式) 行为零变化 (OPEN-PROMPT 流程保留)
- [ ] 6.4 新增 `tests/integration/test_guide_design_menu_from_roadmap.bats`

## 7. STRICT_PROPOSAL_COVERAGE 门控

- [ ] 7.1 在 `skills/guide-design/scripts/design_proposal_review.sh` Phase 4 design-done 门控新增 `STRICT_PROPOSAL_COVERAGE` 检查分支
- [ ] 7.2 默认行为 (warning only): 列出未覆盖主题但允许通过
- [ ] 7.3 `STRICT_PROPOSAL_COVERAGE=yes` 严格模式: 有未覆盖主题则阻断,exit non-zero
- [ ] 7.4 `SKIP_PROPOSAL_COVERAGE=yes` 临时绕过支持
- [ ] 7.5 修改 `skills/guide-design/SKILL.md` Phase 4 章节,文档化 env-var
- [ ] 7.6 新增 `tests/integration/test_strict_proposal_coverage_gate.bats`

## 8. 文档与约定更新

- [ ] 8.1 修改 `skills/roadmap/SKILL.md` init/edit 章节,文档化 5 列结构 + 预期改进方向 cell 语法
- [ ] 8.2 在 `skills/add-improve/SKILL.md` 新增 `--from-roadmap` 模式完整说明
- [ ] 8.3 在 `skills/rdd-workflow-brainstorm/SKILL.md` 文档化首次参数化调用契约 (env-var 列表)
- [ ] 8.4 在 `CHANGELOG.md` 记录新特性 (env-var, 主题状态词汇, 覆盖率算法)
- [ ] 8.5 在 `AGENTS.md` 关键约定章节新增: 主题状态词汇 (`未覆盖 / 已覆盖 / ~skipped~`), env-var 命名规范

## 9. 回归测试与端到端验证

- [ ] 9.1 运行 `./test.sh --quick` 确保 smoke + pytest unit 全部通过
- [ ] 9.2 运行 `./test.sh --full --regression` 与 `KNOWN_FAILURES.txt` baseline 比对,无新增失败
- [ ] 9.3 验证关键 bats 通过: `tests/smoke.bats`, `tests/integration/test_*roadmap*`, `tests/integration/test_*guide-design*`, `tests/integration/test_*add-improve*`
- [ ] 9.4 验证 `rdd-doctor --category state` 在含本特性字段的 proposal 上零 CRITICAL finding
- [ ] 9.5 端到端测试: 空 roadmap → 添加 6 个主题 → arch-done → guide-design 显示覆盖率 → 按主题创建提案 → approval → design-done → propose → openspec change 存在
- [ ] 9.6 验证迁移兼容: 旧 v1 handoff 项目 + 无主题字段的旧 proposal → preflight exit 0,显示 "未标注主题 K 个",不报 0/M 假警