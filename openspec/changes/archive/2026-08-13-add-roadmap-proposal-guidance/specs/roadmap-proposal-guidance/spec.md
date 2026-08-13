# Spec: roadmap-proposal-guidance

> Capability: 让 roadmap 节点声明预期改进主题,guide-design 自动消费并约束 proposal 创建流程。

## ADDED Requirements

### Requirement: Roadmap 分类表支持预期改进方向列

roadmap.md 的 `#### 任务分类` 表格 SHALL 支持第 5 列 "预期改进方向",单元格内容为 `主题1；主题2` 分号分隔的主题列表。表格解析器 SHALL 向后兼容 4 列旧表格 (按"无约束"处理)。

#### Scenario: 5 列表格解析成功
- **WHEN** 用户在 roadmap.md 编辑 `phase-1/arch-design` 行的第 5 列写入 `RBAC权限模型；事件总线契约`
- **THEN** `roadmap_state.py::get_phase_themes("phase-1", "arch-design")` 返回 `["RBAC权限模型", "事件总线契约"]`
- **AND** 第 5 列内容原样保留在 markdown 文件

#### Scenario: 4 列旧表格向后兼容
- **WHEN** 项目升级后保留旧 4 列 `#### 任务分类` 表格
- **THEN** `get_phase_themes()` 返回空列表 (无约束)
- **AND** `roadmap validate/status/advance` 行为零变化
- **AND** 不报 schema 错误

#### Scenario: 空 cell 表示无约束
- **WHEN** 5 列表格的某行第 5 列内容为空字符串
- **THEN** 该分类主题列表返回空数组
- **AND** 在覆盖率计算中按"无主题"跳过,不计入分母

#### Scenario: add_phase 默认模板包含 5 列
- **WHEN** `roadmap add_phase` 创建新 phase
- **THEN** 默认模板的 `#### 任务分类` 表格自动包含第 5 列 "预期改进方向" 表头

### Requirement: Improvement proposal 支持主题字段

`.rddf/improvements/<name>.md` 文件的 front matter SHALL 包含 `**主题**:` 字段,精确记录该提案绑定的 roadmap 主题。可为空字符串或 `不适用`,表示自由模式提案。

#### Scenario: add-improve 自由模式创建
- **WHEN** 用户调用 `skill_use("add-improve")` 无参数调用
- **THEN** 提案 front matter 的 `**主题**:` 字段为空或 `不适用`
- **AND** 当前 OPEN-PROMPT 行为完全不变

#### Scenario: add-improve --from-roadmap 模式创建
- **WHEN** 用户调用 `skill_use("add-improve", "--from-roadmap", "phase-1/arch-design", "--theme", "RBAC权限模型")`
- **THEN** 提案 front matter 的 `**主题**:` 字段为 `RBAC权限模型`
- **AND** `proposal-suggestions.md` 表格中的对应行可选用 `主题` 列记录该值

#### Scenario: brainstorm HARD-GATE 强制用户确认
- **WHEN** 约束模式下 brainstorm Step 4 呈现预填 scaffold
- **THEN** 用户 MUST 在每一段获得确认后才进入下一段
- **AND** 用户拒绝任意段 SHALL 阻止文件创建
- **AND** `proposal-suggestions.md` SHALL 不被修改

### Requirement: add-improve --from-roadmap 模式通过 env-var 传参

`add-improve` 的 `--from-roadmap` 模式 SHALL 通过 env-var 模式传递所有用户输入,禁止 bash string interpolation 直接传入 Python 命令行。env-var 命名 SHALL 使用大写蛇形 (`ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT`)。

#### Scenario: 恶意输入原样写入
- **WHEN** 用户传入包含 `$()`, 反引号, `"; rm -rf #`, 换行符的 rationale 字符串
- **THEN** rationale 原样写入 `.rddf/improvements/<name>.md`
- **AND** 不发生 shell 展开或命令执行

#### Scenario: env-var 命名规范
- **WHEN** add-improve 调用 from_roadmap 子模块
- **THEN** env-var SHALL 命名为 `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT`
- **AND** 调用结束后 SHALL `unset` 这些 env-var 避免污染 shell

#### Scenario: 必填参数校验
- **WHEN** `--from-roadmap` 指定了 phase/category 但 `--theme` 缺失
- **THEN** add-improve SHALL 报错并提示用户补全 theme 参数
- **AND** SHALL 不创建任何文件

### Requirement: guide-design preflight 显示 roadmap 主题覆盖率

`guide-design` Phase 1 preflight SHALL 解析 roadmap.md,显示:
1. 路线图主题总数 M (跨 N 个分类)
2. 当前已映射提案数 X (精确 `**主题**:` 匹配)
3. 未标注主题的旧提案数 K
4. 覆盖率 Y% = X / (M + K)
5. 未覆盖主题清单 (按 phase/category 分组)
6. 已 `~skipped~` 主题数 S (排除出分母)

#### Scenario: 标准覆盖率显示
- **WHEN** 项目有 6 个 roadmap 主题,2 个 proposal 精确匹配, 1 个旧 proposal 无主题字段
- **THEN** preflight 输出:
  ```
  📋 路线图指引: 6 个主题 across 3 分类
  📌 当前提案覆盖: 2/7 (29%) ⚠️
  📌 未覆盖主题:
    - [phase-1/arch-design] 事件总线契约
    - [phase-1/infra-setup] Docker镜像
    - ...
  📌 未标注主题: 1 个旧 proposal (向后兼容)
  ```

#### Scenario: 旧项目零主题字段不报假警
- **WHEN** 项目升级到本特性版本,所有现有 proposal 无 `**主题**:` 字段
- **THEN** preflight 显示 `未标注主题: K 个 proposal`
- **AND** 退出码 0
- **AND** 不显示 `0/N (0%)` 的虚假报警

#### Scenario: ~skipped~ 主题排除分母
- **WHEN** 用户标记 `phase-1/infra-setup/Docker镜像` 为 `~skipped~`
- **THEN** 该主题不计入分母 M
- **AND** preflight 不再列出该主题为"未覆盖"

### Requirement: guide-design Phase 2 菜单新增按主题创建选项

`guide-design` Phase 2 菜单 SHALL 新增选项 "🎯 按路线图主题创建提案 (推荐)",列出未覆盖主题,用户选主题后触发 `add-improve --from-roadmap` 链路。

#### Scenario: 按主题创建流程
- **WHEN** 用户在 Phase 2 菜单选 2 (按路线图主题创建提案)
- **THEN** 显示未覆盖主题列表 (按 phase/category 分组)
- **WHEN** 用户选主题 `RBAC权限模型` (在 `phase-1/arch-design`)
- **THEN** add-improve 以 `--from-roadmap phase-1/arch-design --theme "RBAC权限模型"` 调用
- **AND** 用户回到 Phase 2 菜单继续处理下一个主题

#### Scenario: 自由模式选项保留
- **WHEN** 用户在 Phase 2 菜单选 1 (创建新提案)
- **THEN** 当前 `skill_use("add-improve")` 无参数行为完全不变
- **AND** OPEN-PROMPT 收集描述流程不被绕过

### Requirement: STRICT_PROPOSAL_COVERAGE 门控

`STRICT_PROPOSAL_COVERAGE=yes` SHALL 升级 design-done Phase 4 门控为严格校验,要求所有未 `~skipped~` 的主题 MUST 至少有一个 proposal 通过 `**主题**:` 字段精确匹配覆盖。默认 OFF (warning only),与现有 `STRICT_*_GATE` 模式对齐。

#### Scenario: 默认行为 (warning only)
- **WHEN** `STRICT_PROPOSAL_COVERAGE` 未设置
- **AND** 有 N 个未覆盖主题
- **THEN** design-done 门控 SHALL 输出 warning 列出未覆盖主题
- **AND** 门控 SHALL 通过 (exit 0)

#### Scenario: 严格模式阻断
- **WHEN** `STRICT_PROPOSAL_COVERAGE=yes` 已设置
- **AND** 有 N 个未覆盖主题 (未 `~skipped~`)
- **THEN** design-done 门控 SHALL 失败 (exit non-zero)
- **AND** 输出未覆盖主题列表 + 建议操作 (补 proposal / 显式 skip / SKIP_PROPOSAL_COVERAGE=yes)

#### Scenario: SKIP_PROPOSAL_COVERAGE 临时绕过
- **WHEN** `SKIP_PROPOSAL_COVERAGE=yes` 已设置
- **THEN** design-done 门控 SHALL 跳过 coverage 校验
- **AND** 输出 "SKIP_PROPOSAL_COVERAGE set, coverage gate skipped" warning

### Requirement: rdd-doctor 不感知主题覆盖率字段

`rdd-doctor` SHALL NOT 将 `**主题**:` 字段纳入 schema 校验,coverage 显示 SHALL 仅在 `guide-design` Phase 1 preflight 中出现,不污染 doctor 报告。

#### Scenario: doctor 不报错
- **WHEN** `rdd-doctor --category state` 在含本特性版本字段的 proposal 上运行
- **THEN** SHALL 输出零 CRITICAL finding
- **AND** SHALL NOT 列出 `**主题**:` 为 schema 问题

#### Scenario: doctor 报告字段范围不变
- **WHEN** 本特性 ship 后运行 `rdd-doctor`
- **THEN** doctor 报告 SHALL 仅包含原有 5 类检查 (state schema / plan TDD / roadmap-meta / proposal table / tasks checkbox)
- **AND** SHALL NOT 新增 coverage 相关检查类别 (除非作为独立 follow-up)

### Requirement: 主题状态词汇 `未覆盖 / 已覆盖 / ~skipped~`

主题 SHALL 处于三态之一:
- `未覆盖` — roadmap 定义但无 proposal 匹配
- `已覆盖` — 至少一个 proposal 的 `**主题**:` 字段精确匹配
- `~skipped~` — 用户显式标记豁免,排除出覆盖率分母

#### Scenario: 三态转换
- **WHEN** 用户创建主题 `RBAC权限模型` 的 proposal 后
- **THEN** 该主题状态从 `未覆盖` → `已覆盖`
- **WHEN** 用户标记 `Docker镜像` 为 `~skipped~`
- **THEN** 该主题从 `未覆盖` → `~skipped~`,不再出现于未覆盖列表

#### Scenario: 跨分类同名独立计数
- **WHEN** `phase-1/arch-design` 和 `phase-2/core-impl` 都包含主题 `事件总线`
- **THEN** 覆盖率 SHALL 按 `(phase, category, theme)` 三元组独立计数
- **AND** 一个分类的覆盖不影响另一个分类