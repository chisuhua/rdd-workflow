# add-roadmap-proposal-guidance

**优先级**: P1 | **来源**: 用户会话 2026-08-13 — "路线图定义阶段生成的 roadmap 应能约束后续 proposal 创建,减少人工映射成本"
**阶段**: v3.0 | **分类**: arch-design
**类型**: feature

> **设计背景**: 本提案源于用户在 guide-arch Phase 4 (roadmap-define) 后观察到的工作流断点。当前 roadmap 定义了 phase/category 结构,但不携带"该节点需要哪些提案主题"的元数据;guide-design 阶段的提案创建 (`add-improve` → `rdd-workflow-brainstorm`) 完全依赖用户手动从 roadmap 推导主题,无法自动消费任何约束。本提案打通"roadmap → proposal"自动化链路。
>
> **Oracle 审查结论**: 已通过 Oracle (ses_008c936f) 审查,采纳其关键修改建议 — 删除原方案 Layer 2 (handoff v2 schema bump),改为 guide-design 在 consume-time 直接解析 `roadmap.md`;新增 `**主题**:` 字段到 proposal 模板以实现精确覆盖率计算;rationale 在 brainstorm 阶段 AI 起草 + 用户确认。

## 架构依据

### 现状问题

1. **roadmap 与 proposal 之间无结构化连接**:
   - `roadmap.md` 定义 phase + category 树 (例: `phase-1/arch-design`)
   - `proposal-suggestions.md` 列出待创建提案,但不引用任何 roadmap 节点
   - 用户需要"心智映射"两者,深度介入但容易遗漏
   - 无 reconciliation 机制 — 用户可能为某个 roadmap 分类创建 3 个提案,而另一个分类 0 个

2. **add-improve / brainstorm 流程对 roadmap 无感知**:
   - `add-improve/SKILL.md` Phase 1 加载 `rdd-workflow-brainstorm`
   - `rdd-workflow-brainstorm/SKILL.md` Step 1 (探索项目上下文) 把 `roadmap.md` 列为参考输入之一,但**仅作为背景**,不解析 phase/category 列表
   - 无提示 "roadmap phase-1/arch-design 还有哪些分类未覆盖"

3. **覆盖率不可计算**:
   - 用户问"我的 roadmap phase-1 进度如何?"只能数 task checkbox 完成度
   - 无法回答"roadmap 期望的 N 个改进主题,当前已创建几个 proposal?"

### 期望效果

1. roadmap 节点 (category) 可声明"该节点预期哪些改进主题" (抽象意图,非完整提案)
2. guide-design 进入时自动展示 roadmap 覆盖率 + 未覆盖主题清单
3. 用户可选"按路线图主题创建提案"模式,add-improve 自动预填 5 段 scaffold
4. 设计门控可选升级 `STRICT_PROPOSAL_COVERAGE=yes` 强制所有主题有提案

### 关键 ADR 引用

- **ADR-0016** (arch-handoff discovery contract v1) — `guide-design` 已通过 `.arch-handoff.json` 拿到 `roadmap_path`,可直接 consume-time 解析 roadmap.md,**无需 schema bump**
- **ADR-0017** (rddf-session) — 约束注入不破坏现有 session 生命周期
- **ADR-0019** (change-arch-alignment) — change 必须归属 phase + category,本提案在 design 阶段就提前给出 category 锚点

## 范围

### In Scope

**A. roadmap 模板扩展 (guide-arch/roadmap 域)**:
- 现有 `#### 任务分类` 表格从 4 列扩为 5 列,新增"预期改进方向"
- 单元格格式: `主题1（可选补充）；主题2；...` (分号分隔,空 cell = 无约束)
- `roadmap_state.py::add_phase()` 默认模板同步更新,新创建的 phase 自动带第 5 列
- `roadmap_state.py` 新增 `get_phase_themes(phase_id, category_id) -> list[str]` 函数
- 解析器向后兼容 — 旧 4 列表格按"无约束"处理,无 breaking change

**B. proposal 模板扩展 (add-improve/brainstorm 域)**:
- `rdd-workflow-brainstorm/SKILL.md` 5 段元数据模板新增 `**主题**: <theme-name> | 不适用` 字段
- 提案 front matter 新增 `主题:` 字段,精确记录该提案绑定的 roadmap 主题 (可空 → 自由模式提案)
- `proposal-suggestions.md` 表格可选用第 6 列"主题"(向后兼容 — 旧项目缺列时按"未标注"统计)

**C. add-improve 约束注入模式 (add-improve 域)**:
- 新增 CLI 参数 `skill_use("add-improve", "--from-roadmap", "<phase_id>/<category_id>", "--theme", "<theme_name>")`
- 通过 env-var 模式传递 (Oracle C1 安全实践 — 3 文件 split: `.sh` / `.py` / `.env.py`,参考 `write_arch_handoff_env.py`)
- 加载 `rdd-workflow-brainstorm` 时预填 intent context
- **不绕过** brainstorm HARD-GATE (Step 4 逐段确认仍生效,用户可全盘否决)

**D. rdd-workflow-brainstorm 约束注入逻辑 (brainstorm 域)**:
- 新增"约束模式"分支: 检测 `--from-roadmap` env vars,按以下调整 checklist:
  - Step 1 (探索上下文): 重点对照已存在的同主题提案
  - Step 2 (澄清问题): **跳过一般性"你想改什么?"** (theme 已预填),改为聚焦**范围边界**
  - Step 3 (2-3 方案): 主题聚焦,不开放全方向
  - Step 4 (5 段设计): 预填 scaffold — 架构依据 (AI 起草 + 用户确认), 范围 (从 category description 派生), 验收标准 (从 phase completion criteria 派生)
- rationale 来源: **AI 在 Step 1 起草 + Step 4 用户确认** (而非 roadmap cell,避免 roadmap 表格语法过重)
- 文档化 brainstorm **第一次参数化调用**契约 (add-improve → brainstorm 经由 env vars)

**E. guide-design 引导增强 (guide-design 域)**:
- Phase 1 preflight 新增显示:
  ```
  📋 架构上下文:
    - ADR 数量: N 个
    - 路线图阶段: phase-1 (基础架构)
    - 路线图指引: M 个主题 across K 分类
    - 当前提案覆盖: X/M (Y%) ⚠️
  
  📌 未覆盖主题:
    - [phase-1/arch-design] RBAC权限模型
    - [phase-1/infra-setup] Docker镜像
  ```
- Phase 2 菜单新增选项:
  ```
  2. 🎯 按路线图主题创建提案 (推荐)        ← NEW
  ```
- 选项 2 行为: 列出未覆盖主题 (按 phase/category 分组) → 用户选主题 → 触发 `add-improve --from-roadmap` 链
- Phase 4 design-done 门控新增 `STRICT_PROPOSAL_COVERAGE=yes` 校验 (默认 warning, 升级 strict 与现有 `STRICT_*_GATE` 模式对齐)
- 新增主题状态词汇: `未覆盖 / 已覆盖 / ~skipped~` — 跳过主题显式豁免 strict 门控

### Out Scope

- **不修改 arch-handoff schema** (v1 不动, Oracle 关键建议 — 避免 rdd-doctor schema 校验破坏)
- **不修改 rdd-doctor 检查逻辑** (coverage 显示在 guide-design preflight 而非 doctor,doctor 仍是 schema/roadmap-meta 维度)
- **不在 openspec/changes/ 直接落盘时强制主题字段** (proposal-level 字段,openspec artifacts 不感知)
- **不自动 derive rationale 写入 roadmap** (rationale 在 brainstorm 阶段 AI 起草,roadmap 保持简洁)
- **不修改现有 `add-improve` 无参数 OPEN-PROMPT 行为** (`--from-roadmap` 是显式 opt-in, 默认 free-form 模式不变)
- **不引入 `DESIGN_PROPOSAL_AUTO_ACCEPT` 类自动批准机制** (Oracle 警告 — 严禁引入)
- **不修改 proposal.md/design.md OpenSpec 模板** (仅修改 rdd-workflow 自有的 improvement 模板)

## 关键场景

### 场景 1: roadmap 定义时声明预期改进方向

- **GIVEN** 用户在 `guide-arch` Phase 4 选择 "编辑路线图"
- **WHEN** 用户给 `phase-1/arch-design` 分类添加 "预期改进方向": `RBAC权限模型；事件总线契约`
- **THEN** `roadmap.md` 表格第 5 列持久化存储
- **AND** `roadmap_state.py::get_phase_themes("phase-1", "arch-design")` 返回 `["RBAC权限模型", "事件总线契约"]`

### 场景 2: guide-design 显示覆盖率

- **GIVEN** arch-done 完成, roadmap 含 6 个主题 across 3 分类, 已有 2 个 proposal
- **WHEN** 用户调用 `skill_use("guide-design")` 进入 Phase 1 preflight
- **THEN** 输出:
  ```
  📋 路线图指引: 6 个主题 across 3 分类
  📌 当前提案覆盖: 2/6 (33%) ⚠️
  📌 未覆盖主题:
    - [phase-1/arch-design] 事件总线契约
    - [phase-1/infra-setup] Docker镜像
    - [phase-1/infra-setup] GitHub Actions
    - [phase-1/core-impl] (无主题)
  ```
- **AND** Phase 2 菜单新增选项 2 "🎯 按路线图主题创建提案 (推荐)"

### 场景 3: 用户按主题创建提案 (约束模式)

- **GIVEN** 用户在 guide-design Phase 2 选 2, 选主题 "RBAC权限模型"
- **WHEN** add-improve 以 `--from-roadmap phase-1/arch-design --theme "RBAC权限模型"` 调用
- **THEN** `rdd-workflow-brainstorm` 进入约束模式:
  - Step 2 跳过一般性澄清
  - Step 4 5 段设计 scaffold 预填 (架构依据: AI 起草 + 用户确认, 范围: 来自 category description)
- **AND** 用户在 Step 4 逐段确认/修改
- **AND** HARD-GATE 强制 — 用户必须批准后才创建文件
- **AND** 生成的 `improvements/<name>.md` 含 `**主题**: RBAC权限模型` 字段

### 场景 4: 自由模式提案 (向后兼容)

- **GIVEN** 用户在 guide-design Phase 2 选 1 (自由模式)
- **WHEN** `skill_use("add-improve")` 无参数调用
- **THEN** 行为与现在完全相同 — OPEN-PROMPT 收集描述, brainstorm 全开放
- **AND** `**主题**:` 字段为空或"不适用"
- **AND** 在 coverage 显示中按"未标注主题"单独统计

### 场景 5: 主题跳过 (~skipped~)

- **GIVEN** 用户判断 `phase-1/infra-setup/Docker镜像` 主题不需要单独提案 (因已合并到其他提案)
- **WHEN** 用户在 Phase 1 preflight 输入 `skip phase-1/infra-setup/Docker镜像`
- **THEN** 该主题标记为 `~skipped~`, 不计入覆盖率分母
- **AND** `STRICT_PROPOSAL_COVERAGE=yes` 门控不会因该主题阻断

### 场景 6: 旧项目无主题字段迁移

- **GIVEN** 升级到本特性版本的现有项目 (v2.0 之前无 `**主题**:` 字段)
- **WHEN** guide-design Phase 1 preflight 运行
- **THEN** 显示 `未标注主题: K 个 proposal` (K = 已有 proposal 数)
- **AND** 覆盖率计算用 `mapped = X`, `denominator = M + K` (避免 0/M 假警)
- **AND** 旧 proposal 不强制补字段 (向前兼容)

### 场景 7: 严格门控

- **GIVEN** `STRICT_PROPOSAL_COVERAGE=yes` 已设置, roadmap 主题 M 个, 未覆盖/未跳过的有 N 个
- **WHEN** design-done Phase 4 门控执行
- **THEN** 若 `N > 0`, 门控失败并列出未覆盖主题
- **AND** 提示用户: 补 proposal / 显式 skip 主题 / 设置 `SKIP_PROPOSAL_COVERAGE=yes` 临时绕过

## 技术约束

### MUST

- **MUST 保持 roadmap.md 表格 4/5 列兼容**: 解析器 (`roadmap_state.py:249/466`) regex 无 EOL anchor,容忍额外列,但**必须测试** 4 列 / 5 列混合的旧项目不破坏
- **MUST 保持 brainstorm HARD-GATE 不被绕过**: 约束模式仍强制 Step 4 逐段用户确认, 自动落盘仅在用户批准后
- **MUST 使用 env-var 模式传参**: `--rationale`, `--theme`, `--from-roadmap` 全部经 `os.environ`, 禁止 `python3 -c "...$VAR..."` 内联插值 (Oracle C1 前例: AGENTS.md Round A/B)
- **MUST 不修改 arch-handoff schema**: v1 不动, 避免 rdd-doctor `state_schema_check.py:60` CRITICAL finding (Oracle C2)
- **MUST 保持 `add-improve` 无参数 OPEN-PROMPT 行为**: `--from-roadmap` 是显式 opt-in, 默认 free-form 模式不变
- **MUST 精确字符串匹配覆盖率**: theme → proposal 的 `**主题**:` 字段严格相等, 不做 fuzzy
- **MUST 主题状态词汇**: `未覆盖 / 已覆盖 / ~skipped~` 三态明确, ~skipped~ 排除出分母
- **MUST env-var 命名规范**: `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT` 等大写蛇形, 不污染用户 shell 环境 (用 `unset` 清理)

### MUST NOT

- **MUST NOT 引入自动批准机制**: 严禁新增类似 `DESIGN_PROPOSAL_AUTO_ACCEPT` 的 env var 自动跳过 HARD-GATE (Oracle Q4 警告)
- **MUST NOT 复制 roadmap 内容到 handoff**: guide-design consume-time 直接解析, 不在 `.arch-handoff.json` 缓存 themes (避免 staleness — Oracle C3)
- **MUST NOT 修改 openspec/changes/ 模板**: proposal-level 字段, 不污染 OpenSpec artifacts
- **MUST NOT 修改 rdd-doctor 逻辑**: coverage 显示在 guide-design preflight, doctor 仍专注 schema/roadmap-meta
- **MUST NOT 把 rationale 写入 roadmap cell**: 保持 roadmap 表格语法简洁 (Oracle C4)
- **MUST NOT 假设每个 theme 必须 1:1 对应一个 proposal**: 多个 proposal 可共享同一 theme, 一个 proposal 可绑定多 theme (用数组)

### SHOULD

- **SHOULD 在 env-var 传参时同时记录 invocation log**: `improvements/<name>.md` front matter 加 `**来源模式**: from-roadmap | free-form`, 便于审计
- **SHOULD 兼容 4 列 / 5 列混合表格**: 旧 phase 表格保持 4 列 (无主题), 新 phase 表格带 5 列, 共存不报错
- **SHOULD 给旧 proposal 提供 backfill 工具**: `rddf improvements backfill-themes --interactive` 帮助用户补字段 (可选, 非强制)
- **SHOULD coverage 显示附 `proposal-suggestions.md` 直链**: 用户可一键跳转到未覆盖主题对应的提案创建入口

## 验收标准

### 功能验收

- [ ] `roadmap.md` 表格支持 5 列 (含 "预期改进方向"), 4/5 列混合兼容
- [ ] `roadmap_state.py::get_phase_themes()` 函数单元测试 ≥ 6 case (空 cell, 单主题, 多主题分号, 含特殊字符, 跨 phase, 4 列兼容)
- [ ] `rdd-workflow-brainstorm` 5 段模板新增 `**主题**:` 字段, 默认空
- [ ] `add-improve --from-roadmap <phase/cat> --theme <name>` 模式支持, env-var 传参
- [ ] guide-design Phase 1 preflight 显示覆盖率 + 未覆盖主题列表
- [ ] guide-design Phase 2 菜单选项 2 (按路线图主题创建) 可用
- [ ] `~skipped~` 主题状态支持, 排除覆盖率分母
- [ ] `STRICT_PROPOSAL_COVERAGE=yes` 升级 design-done 门控

### 测试验收

- [ ] **解析兼容**: 4 列旧表格 → `roadmap validate/status/advance` 行为零变化
- [ ] **迁移兼容**: 旧 v1 handoff + 无主题字段的旧提案 → preflight exit 0, 显示"未标注主题 K 个", 不报 0/M 假警
- [ ] **HARD-GATE**: `--from-roadmap` 模式下用户拒绝某段 → 无文件创建, `proposal-suggestions.md` 不变
- [ ] **注入测试**: rationale 含 `$()`, 反引号, `"; rm -rf #`, 换行符 → 原样写入, 无 shell 展开
- [ ] **覆盖率算法**: 主题精确匹配; 跨 category 同名独立计数; `~skipped~` 排除
- [ ] **off-roadmap 路径**: 选项 1 自由模式在 `STRICT_PROPOSAL_COVERAGE=yes` 下仍可用, 仅 design-done 门控警告
- [ ] **rdd-doctor**: `--category state` 对 v1 handoff 仍通过 (无 schema 变更)
- [ ] **端到端**: 从空 roadmap → 添加主题 → arch-done → guide-design 显示覆盖率 → 按主题创建提案 → approval → design-done → propose → openspec change 存在

### 文档验收

- [ ] `rdd-workflow-brainstorm/SKILL.md` 文档化**新参数契约** (首次参数化调用, 需明确 env-var 列表)
- [ ] `guide-design/SKILL.md` Phase 1/2 章节同步更新
- [ ] `roadmap/SKILL.md` init/edit 模板说明 5 列结构
- [ ] `add-improve/SKILL.md` 新增 `--from-roadmap` 模式说明
- [ ] `CHANGELOG.md` / `AGENTS.md` 关键约定更新 (主题状态词汇, env-var 命名)

### 性能验收

- [ ] `roadmap_state.py::get_phase_themes()` 解析 ≤ 10ms (单文件 ≤ 100 行)
- [ ] guide-design preflight 增加主题解析后总耗时 ≤ +50ms (现有 preflight ≤ 200ms 基准)
- [ ] `add-improve --from-roadmap` 模式相比自由模式无明显延迟增加 (env-var 传递 < 1ms)

### 回归测试

- [ ] **必跑**: `./test.sh --full --regression` 全绿 (与 `KNOWN_FAILURES.txt` baseline 比对, 无新增失败)
- [ ] **关键 bats**: `tests/smoke.bats`, `tests/integration/test_*roadmap*`, `tests/integration/test_*guide-design*`, `tests/integration/test_*add-improve*` 全部通过
- [ ] **关键 Python unit**: `tests/unit/test_roadmap_state.py`, `tests/unit/test_guide_design_preflight.py` (如无则新建) 全部通过