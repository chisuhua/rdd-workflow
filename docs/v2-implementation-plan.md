# spec-workflow v2.0 实施计划

> **版本**: 2.0.0-beta  
> **日期**: 2026-06-24（更新: 2026-06-28）  
> **状态**: ✅ 已完成（v2.0.0-beta 已于 2026-06-26 发布）  
> **决策者**: sisyphus  
> **基于**: ADR-0001 ~ ADR-0012, v2-architecture-refactor-plan.md

> ## ✅ v2.0.0-beta 实施完成
>
> 本文档最初为 v2.0 的**设计计划**。以下 5 个 Phase 已全部实施并归档：
>
> | Phase | 对应 Change | 状态 |
> |------|------------|------|
> | Phase 1: 核心基础 | `v2-core-foundation` | ✅ 完成（2026-06-25） |
> | Phase 2: Loop 引擎 | `v2-loop-engine` | ✅ 完成（2026-06-25） |
> | Phase 3: 高级特性 | `v2-advanced-features` | ✅ 完成（2026-06-26） |
> | Phase 4: 迁移与测试 | `v2-migration-and-tests` | ✅ 完成（2026-06-26） |
> | Phase 5: Beta 发布 | `v2-beta-release` | ✅ 完成（2026-06-26） |
>
> **当前实现状态**（2026-06-28）：
> - ✅ `skills/guide-arch.md` / `guide-plan.md` / `guide-ship.md` — 三阶段架构已实施
> - ✅ `skills/loop_engine.py` — Loop 引擎已实施（含 8 个探测器、7 个动作）
> - ✅ `skills/_lib/state_vector.py` / `event_log.py` / `gate.py` / `tribunal.py` 等 22 个 Python 模块已实现
> - ✅ 145 个 Python 测试 + 257 个 bats 测试通过
> - ✅ ADR-0002 ~ ADR-0008 已实施；ADR-0009~0012 为 v3.0 候选
>
> **本文档保留为历史设计记录**。后续开发见 `roadmap.md` 或新的 openspec change。

---

## 📋 执行摘要

本文档定义了 spec-workflow v2.0 的完整实施计划，从**状态机驱动**升级到 **Loop 驱动 + Human-in-Loop** 的 AI 编程范式。

### 核心变更概览

| 维度 | v1.x (当前) | v2.0 (目标) |
|------|------------|------------|
| **架构** | 双阶段 (spec/ship) | 三阶段 (arch → plan → ship) |
| **驱动方式** | 菜单驱动 | Loop 驱动 + 可配置交互模式 |
| **状态管理** | 13 个分散文件 | 统一状态向量 + 事件流 |
| **Human-in-Loop** | 所有决策点 | 7 类关键节点 (可配置) |
| **质量保障** | 简单验证 | 门控机制 + 审判委员会 |
| **记忆系统** | 无 | 中断恢复、配置推荐、失败学习 |

### 实施统计

- **总工作量**: 45-55 人天
- **预计周期**: 8-10 周（单开发者）
- **Phase 数量**: 4 个主要阶段 + 1 个 Beta 阶段
- **新增文件**: ~25 个 Python 模块 + 3 个 skill 文件
- **测试覆盖目标**: ≥ 80%

---

## 📚 文档依赖

本实施计划基于以下 ADR 和文档：

| 文档 | 状态 | 关键决策 |
|------|------|---------|
| [ADR-0002](adr/ADR-0002-goal-driven-interaction-modes.md) | 已采纳 | 三种交互模式 + 设计先行 + 便携规范 |
| [ADR-0003](adr/ADR-0003-three-phase-architecture.md) | 已采纳 | 三阶段架构 (arch → plan → ship) |
| [ADR-0004](adr/ADR-0004-loop-engine-core-design.md) | 已采纳 | Loop 引擎 5 大构建块 |
| [ADR-0005](adr/ADR-0005-human-in-loop-nodes.md) | 已采纳 | 三种验证模式 + 节点策略 |
| [ADR-0006](adr/ADR-0006-state-vector-event-log.md) | 已采纳 | 状态向量 + 事件流 + 记忆系统 |
| [ADR-0007](adr/ADR-0007-gate-mechanism.md) | 已采纳 | 门控机制 (error/warning 两级) |
| [ADR-0008](adr/ADR-0008-tribunal-committee.md) | 已采纳 | 审判委员会 + 数据脱敏 |
| [ADR-0010](adr/ADR-0010-multi-session-management.md) | 已采纳 | 轻量级会话管理 (v2.0) |

---

## 🏗️ 实施路线图

### 总体时间线

```
Week 1-2    Week 3-4    Week 5-7    Week 8-9    Week 10
  │           │           │           │           │
  ├─ Phase 1 ─┤           │           │           │
  │ 核心基础  │           │           │           │
  │           ├─ Phase 2 ─┤           │           │
  │           │ Loop 引擎 │           │           │
  │           │           ├─ Phase 3 ─┤           │
  │           │           │ 高级特性  │           │
  │           │           │           ├─ Phase 4 ─┤
  │           │           │           │ 迁移测试  │
  │           │           │           │           ├─ Beta
  │           │           │           │           │ 发布
```

### 关键路径

```
状态向量 → 事件流 → 门控机制 → Loop 引擎 → 三种模式 → 审判委员会 → 记忆系统 → 测试
    ↑          ↑          ↑          ↑          ↑           ↑           ↑         ↑
  P0-1       P0-2       P0-3       P1-1       P1-2        P2-1        P2-2      P3
```

**关键路径**: 状态向量 → 门控机制 → Loop 引擎 → 测试（任何延迟将直接影响发布日期）

---

## ✅ Phase 1: 核心基础 ✅已实施

**目标**: 实现核心基础设施，向后兼容 v1.x

**对应 ADR**: ADR-0006, ADR-0007, ADR-0002

### 任务清单

#### P1-T1: 实现状态向量 (State Vector)

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: 无
- **对应 ADR**: ADR-0006

**任务详情**:

1. **创建 StateVector 类** (`skills/_lib/state_vector.py`)
   - 实现 `load()` / `save()` 方法（带文件锁）
   - 实现 `update_field()` 支持嵌套字段更新
   - 实现 `validate()` 使用 JSON Schema 验证
   - 实现 `create_default()` 创建默认状态向量
   - 实现 `reset()` 重置状态向量

2. **定义状态向量 Schema** (`skills/_lib/schemas/state_vector_schema.json`)
   - 定义完整 JSON Schema（goal, arch_side, plan_side, ship_side, loop_state, memory, metadata）
   - 添加字段验证规则（类型、枚举、必填）
   - 添加自定义验证器（checksum 计算）

3. **实现文件锁机制** (`skills/_lib/lock.py`)
   - 实现 `FileLock` 类（基于 fcntl）
   - 支持超时控制（默认 10 秒）
   - 支持上下文管理器（with 语句）

4. **创建默认状态向量模板**
   - 定义空状态向量结构
   - 添加版本字段 (`version: "2.0"`)
   - 添加 metadata 字段（spec_workflow_version, git_commit）

**验收标准**:

- [ ] `StateVector` 类可通过单元测试
- [ ] 并发读写测试通过（2 个进程同时写入不冲突）
- [ ] Schema 验证拒绝非法状态（缺少必填字段、类型错误）
- [ ] 状态向量文件大小 < 50KB（空状态）
- [ ] 读写延迟 < 10ms（本地文件系统）

**交付文件**:

```
skills/_lib/
├── state_vector.py          # 状态向量核心类
├── lock.py                  # 文件锁机制
└── schemas/
    └── state_vector_schema.json  # JSON Schema 定义
```

---

#### P1-T2: 实现事件流 (Event Log)

- **优先级**: P0
- **工作量**: 2 人天
- **依赖**: P1-T1（状态向量）
- **对应 ADR**: ADR-0006

**任务详情**:

1. **创建 EventLog 类** (`skills/_lib/event_log.py`)
   - 实现 `record()` 方法（追加写入 JSONL）
   - 实现 `query()` 方法（支持事件类型、严重度、时间范围过滤）
   - 实现 `get_progress_report()` 生成进度报告
   - 实现 `generate_id()` 生成事件 ID（格式: `evt_YYYYMMDD_HHMMSS_NNN`）

2. **定义事件类型枚举** (`skills/_lib/event_types.py`)
   - 定义 17 种事件类型（loop_started, scan_completed, plan_generated, ...）
   - 定义严重度枚举（debug, info, warn, error）

3. **实现上下文获取** (`skills/_lib/event_context.py`)
   - 从状态向量读取当前上下文（goal, active_changes, worktrees）
   - 附加到每个事件

**验收标准**:

- [ ] 事件写入后立即可查询（无缓冲延迟）
- [ ] 查询性能: 10,000 条事件中过滤 < 100ms
- [ ] 进度报告包含正确统计（迭代次数、完成单元数、错误数）
- [ ] 事件 ID 唯一性（同一秒内不重复）

**交付文件**:

```
skills/_lib/
├── event_log.py             # 事件流核心类
├── event_types.py           # 事件类型定义
└── event_context.py         # 事件上下文获取
```

---

#### P1-T3: 实现门控机制 (Gate Mechanism)

- **优先级**: P0
- **工作量**: 2-3 人天
- **依赖**: P1-T1（状态向量）
- **对应 ADR**: ADR-0007

**任务详情**:

1. **创建 GateMechanism 类** (`skills/_lib/gate.py`)
   - 定义内置检查清单（arch_done, plan_done, ship_done）
   - 实现 `verify_transition()` 验证阶段切换
   - 实现 `handle_gate_failure()` 处理失败（返回/查看/强制/中止）
   - 实现 `get_suggestion()` 提供修复建议

2. **实现 Check 类** (`skills/_lib/gate.py`)
   - 定义 `name`, `condition`, `message`, `severity` 字段
   - 支持 lambda 条件函数
   - 支持严重度分级（error/warning）

3. **实现插件注册机制**
   - 实现 `register_gate_check()` API
   - 支持从 `.spec-workflow/plugins/` 加载自定义检查

4. **定义默认门控检查清单**
   - arch_done: adr_exists (error), roadmap_defined (error), gap_analysis_complete (warning)
   - plan_done: changes_committed (error), artifacts_complete (error), deps_analyzed (warning)
   - ship_done: worktrees_empty (error), archive_empty (error), tests_pass (error)

**验收标准**:

- [ ] 门控验证拒绝非法切换（缺少 ADR 时 arch → plan）
- [ ] Warning 检查失败时允许继续（但显示警告）
- [ ] 强制切换记录到事件流（force_transition 事件）
- [ ] 自定义插件可注册并生效
- [ ] 修复建议清晰可操作（包含具体命令）

**交付文件**:

```
skills/_lib/
├── gate.py                  # 门控机制核心
└── plugins/                 # 插件目录（可选）
    └── README.md            # 插件开发指南
```

---

#### P1-T4: 实现配置解析器 (Config Parser)

- **优先级**: P0
- **工作量**: 1-2 人天
- **依赖**: 无
- **对应 ADR**: ADR-0002

**任务详情**:

1. **创建 ConfigParser 类** (`skills/_lib/config.py`)
   - 实现 `.rddf.json` 解析
   - 实现 `loop.yaml` 解析（需要 PyYAML）
   - 实现配置优先级合并（运行时参数 > loop.yaml > .rddf.json > 环境变量 > 默认值）

2. **定义默认配置** (`skills/_lib/defaults.py`)
   - 定义默认交互模式（hybrid）
   - 定义默认 Loop 参数（max_iterations=100, max_retries=3）
   - 定义默认 Human-in-Loop 节点列表

3. **实现环境变量支持**
   - 读取 `RDDF_MODE`, `RDDF_MAX_ITERATIONS` 等
   - 类型转换（字符串 → 整数/布尔）

4. **实现配置验证**
   - 验证必需字段存在
   - 验证枚举值合法（mode: loop/menu/hybrid）
   - 验证数值范围（max_iterations > 0）

**验收标准**:

- [ ] 最小配置可解析（仅 `{"version": "2.0", "interaction": {"mode": "hybrid"}}`）
- [ ] 配置优先级正确（运行时参数覆盖文件配置）
- [ ] 非法配置被拒绝并显示清晰错误消息
- [ ] 环境变量可覆盖文件配置

**交付文件**:

```
skills/_lib/
├── config.py                # 配置解析器
└── defaults.py              # 默认配置定义
```

---

#### P1-T5: 实现 v1.x 同步层 (Sync Layer)

- **优先级**: P1
- **工作量**: 2 人天
- **依赖**: P1-T1（状态向量）
- **对应 ADR**: ADR-0006

**任务详情**:

1. **创建同步脚本** (`skills/_lib/sync_state.py`)
   - 实现 `sync_state_vector_to_legacy()`: 状态向量 → v1.x 文件
   - 实现 `sync_legacy_to_state_vector()`: v1.x 文件 → 状态向量
   - 实现双向同步（检测冲突，优先状态向量）

2. **同步目标文件**
   - `.rddf/state/roadmap-state.json` (roadmap 状态)
   - `proposal-suggestions.md` (proposal 建议)
   - `openspec/changes/<name>/.openspec.yaml` (change 状态)

3. **实现冲突解决**
   - 检测时间戳差异
   - 优先使用状态向量（权威来源）
   - 记录冲突到事件流

**验收标准**:

- [ ] 状态向量更新后，v1.x 文件自动同步
- [ ] v1.x 文件变更后，状态向量自动更新
- [ ] 同步延迟 < 50ms
- [ ] 冲突解决策略正确（状态向量优先）

**交付文件**:

```
skills/_lib/
└── sync_state.py            # v1.x 同步层
```

---

### Phase 1 里程碑

| 里程碑 | 验收标准 | 预计日期 |
|--------|---------|---------|
| **M1.1**: 状态向量可运行 | 通过单元测试 + 并发测试 | Week 1 结束 |
| **M1.2**: 事件流可运行 | 通过写入/查询测试 | Week 1 结束 |
| **M1.3**: 门控机制可运行 | 通过阶段切换测试 | Week 2 结束 |
| **M1.4**: Phase 1 集成测试通过 | 所有组件协同工作 | Week 2 结束 |

---

## ✅ Phase 2: Loop 引擎核心 ✅已实施

**目标**: 实现 Loop 引擎 5 大构建块 + 三种交互模式

**对应 ADR**: ADR-0004, ADR-0002

### 任务清单

#### P2-T1: 实现 Loop 引擎核心循环

- **优先级**: P0
- **工作量**: 5 人天
- **依赖**: P1-T1, P1-T2, P1-T3（状态向量、事件流、门控）
- **对应 ADR**: ADR-0004

**任务详情**:

1. **创建 LoopEngine 类** (`skills/loop-engine.py`)
   - 实现主循环 `run()`: while not goal_achieved()
   - 实现 5 大构建块方法：
     - `verify_goal()`: 检查目标是否达成
     - `scan_state()`: 运行所有 detectors
     - `generate_plan()`: 生成执行计划
     - `execute_plan()`: 执行 actions
     - `verify_results()`: 验证执行结果 + 门控检查
     - `update_state()`: 更新状态向量
     - `adapt()`: 自适应调整（错误恢复）

2. **实现安全机制**
   - 最大迭代次数检查（默认 100）
   - 最大重试次数检查（默认 3）
   - 状态震荡检测（最近 5 次 ≤ 2 种状态）
   - 超时控制（每个 action 最大 30 分钟）
   - 断路器（连续失败 3 次触发）

3. **实现目标达成判定**
   - 支持多种目标类型（"complete all changes", "create worktrees", ...）
   - 从配置文件读取成功标准（success_criteria）

4. **实现计划生成逻辑**
   - 匹配 detectors → actions
   - 支持优先级排序
   - 支持依赖分析（先创建 worktree，再执行）

**验收标准**:

- [ ] Loop 引擎可执行完整循环（scan → plan → execute → verify → adapt）
- [ ] 安全机制触发正确（超过最大迭代次数时报错）
- [ ] 状态震荡检测有效（5 次相同状态时中止）
- [ ] 目标达成判定准确（active_changes=0, worktrees=0）
- [ ] 事件流记录完整（每个步骤都有对应事件）

**交付文件**:

```
skills/
└── loop-engine.py           # Loop 引擎核心
```

---

#### P2-T2: 实现 Detectors（状态检测器）

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: P2-T1（Loop 引擎）
- **对应 ADR**: ADR-0004

**任务详情**:

1. **创建 Detectors 模块** (`skills/_lib/detectors.py`)
   - 实现 8 个内置 detectors：
     - `detect_worktrees()`: 检测活跃 worktrees
     - `detect_pending_changes()`: 检测待处理 changes
     - `detect_archived_changes()`: 检测已归档 changes
     - `detect_roadmap_state()`: 检测 roadmap 状态
     - `detect_adr_status()`: 检测 ADR 文档状态
     - `detect_health_issues()`: 检测环境问题
     - `detect_test_gaps()`: 检测测试覆盖缺口
     - `detect_stale_branches()`: 检测过期分支

2. **实现 Detector 基类**
   - 定义 `detect()` 接口
   - 返回 `DetectionResult` 对象（type, data, message）

3. **实现注册机制**
   - 支持从 `.spec-workflow/detectors/` 加载自定义 detectors
   - 支持配置文件注册

**验收标准**:

- [ ] 所有 8 个 detectors 返回结构化结果
- [ ] 检测性能: 全部运行 < 500ms
- [ ] 自定义 detectors 可注册并生效
- [ ] 检测结果写入状态向量

**交付文件**:

```
skills/_lib/
└── detectors.py             # 状态检测器集合
```

---

#### P2-T3: 实现 Actions（执行动作）

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: P2-T1（Loop 引擎）
- **对应 ADR**: ADR-0004

**任务详情**:

1. **创建 Actions 模块** (`skills/_lib/actions.py`)
   - 实现 7 个内置 actions：
     - `action_create_worktree()`: 创建 worktree + branch
     - `action_generate_plan()`: 生成 Prometheus 计划
     - `action_execute_worktree()`: 执行 work units
     - `action_archive_change()`: merge + archive + cleanup
     - `action_cleanup_stale()`: 清理过期 worktrees/branches
     - `action_update_roadmap()`: 更新 roadmap 进度
     - `action_create_adr()`: 创建 ADR 文档

2. **实现 Action 基类**
   - 定义 `execute()` 接口
   - 返回 `ActionResult` 对象（success, data, error）

3. **实现 subprocess 调用**
   - 调用现有 skill 文件（bash scripts）
   - 捕获 stdout/stderr
   - 处理超时（30 分钟）

4. **实现 Action 注册机制**
   - 支持从 `.spec-workflow/actions/` 加载自定义 actions
   - 支持配置文件注册

**验收标准**:

- [ ] 所有 7 个 actions 可执行（subprocess 调用成功）
- [ ] 错误处理正确（失败时返回 ActionResult(success=False)）
- [ ] 超时控制有效（超过 30 分钟自动中止）
- [ ] 执行结果记录到事件流

**交付文件**:

```
skills/_lib/
└── actions.py               # 执行动作集合
```

---

#### P2-T4: 实现三种交互模式

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: P2-T1（Loop 引擎）
- **对应 ADR**: ADR-0002

**任务详情**:

1. **实现 Loop 模式**（全自动）
   - 跳过所有 Human-in-Loop 节点
   - 仅在错误时暂停
   - 适合 CI/CD

2. **实现 Menu 模式**（全手动）
   - 每个决策点显示菜单
   - 用户完全控制流程
   - 适合学习和调试

3. **实现 Hybrid 模式**（半自动）
   - 自动执行常规操作
   - 关键节点显示菜单（Human-in-Loop）
   - 平衡效率和安全性

4. **实现 Human-in-Loop 节点管理**
   - 从配置文件读取节点列表
   - 支持三种验证模式（human/multi_model/script）
   - 实现菜单系统（选择/跳过/修改/中止）

**验收标准**:

- [ ] Loop 模式全自动运行（无需人工干预）
- [ ] Menu 模式每个决策点显示菜单
- [ ] Hybrid 模式关键节点暂停等待确认
- [ ] 模式切换可配置（运行时参数覆盖）

**交付文件**:

```
skills/_lib/
├── interaction_modes.py     # 三种交互模式实现
└── human_nodes.py           # Human-in-Loop 节点管理
```

---

#### P2-T5: 实现设计先行阶段

- **优先级**: P1
- **工作量**: 1-2 人天
- **依赖**: P2-T4（交互模式）
- **对应 ADR**: ADR-0002

**任务详情**:

1. **实现目标设计** (Goal Design)
   - 明确产出物和完成标准
   - 显示给用户确认

2. **实现验证设计** (Verification Design)
   - 确定检查机制（human/multi_model/script）
   - 配置 Executor/Reviewer agents

3. **实现控制设计** (Control Design)
   - 设置刹车机制（最大迭代、断路器、震荡检测）
   - 显示给用户确认

**验收标准**:

- [ ] 设计先行阶段在 Loop 启动前执行
- [ ] 用户可修改设计参数
- [ ] 设计结果保存到状态向量

**交付文件**:

```
skills/_lib/
└── design_phase.py          # 设计先行阶段
```

---

#### P2-T6: 实现可视化流程图生成

- **优先级**: P2
- **工作量**: 1 人天
- **依赖**: P2-T1（Loop 引擎）
- **对应 ADR**: ADR-0004

**任务详情**:

1. **创建流程图生成器** (`skills/_lib/flowchart.py`)
   - 读取事件流和状态向量
   - 生成 ASCII 流程图
   - 显示当前阶段、门控状态、进度

2. **实现实时进度显示**
   - 显示当前迭代次数
   - 显示各阶段进度
   - 显示错误/警告

**验收标准**:

- [ ] 流程图格式清晰（ASCII 艺术）
- [ ] 实时更新（每次迭代后刷新）
- [ ] 包含关键信息（阶段、门控、进度、错误）

**交付文件**:

```
skills/_lib/
└── flowchart.py             # 可视化流程图生成
```

---

### Phase 2 里程碑

| 里程碑 | 验收标准 | 预计日期 |
|--------|---------|---------|
| **M2.1**: Loop 引擎核心可运行 | 通过单元测试 + 集成测试 | Week 4 结束 |
| **M2.2**: 三种模式可运行 | Loop/Menu/Hybrid 均通过测试 | Week 5 结束 |
| **M2.3**: Detectors/Actions 可运行 | 8 detectors + 7 actions 全部通过测试 | Week 6 结束 |
| **M2.4**: Phase 2 集成测试通过 | 完整 Loop 流程可运行 | Week 6 结束 |

---

## ✅ Phase 3: 高级特性 ✅已实施

**目标**: 实现审判委员会、记忆系统、会话管理

**对应 ADR**: ADR-0008, ADR-0006, ADR-0010, ADR-0005

### 任务清单

#### P3-T1: 实现 Human-in-Loop 节点管理

- **优先级**: P1
- **工作量**: 2 人天
- **依赖**: P2-T4（交互模式）
- **对应 ADR**: ADR-0005

**任务详情**:

1. **完善 Human-in-Loop 节点**
   - 实现 7 类关键节点：
     - `arch.adr_create`: ADR 创建
     - `arch.roadmap_define`: Roadmap 定义
     - `plan.change_select`: Change 选择
     - `plan.propose_confirm`: Proposal 确认
     - `ship.archive_confirm`: 归档确认
     - `ship.cleanup_confirm`: 清理确认
     - `ship.execute_error`: 错误处理

2. **实现三种验证模式**
   - `human`: 人工审核（显示菜单，等待输入）
   - `multi_model`: 多 agent 交叉验证（调用审判委员会）
   - `script`: 脚本验证（运行 Python 脚本）

3. **实现节点策略**
   - `fixed`: 固定验证模式（adr_create、execute_error 必须是 human）
   - `configurable`: 用户可配置（archive_confirm、change_select 等）

**验收标准**:

- [ ] 7 类关键节点全部可配置
- [ ] 三种验证模式工作正常
- [ ] 固定策略不可覆盖（adr_create 必须 human）
- [ ] 节点跳过条件生效（skip_if 配置）

**交付文件**:

```
skills/_lib/
└── human_nodes.py           # Human-in-Loop 节点管理（扩展）
```

---

#### P3-T2: 实现审判委员会 (Tribunal Committee)

- **优先级**: P1
- **工作量**: 4-5 人天
- **依赖**: P3-T1（Human-in-Loop 节点）
- **对应 ADR**: ADR-0008

**任务详情**:

1. **创建 Tribunal 类** (`skills/_lib/tribunal.py`)
   - 实现 `execute_verification()`: 调用 Executor agent
   - 实现 `review_verification()`: 调用 Reviewer agent
   - 实现 `judge()`: 综合判定算法
     - `final_score = exec_score * 0.4 + review_score * 0.6`
     - `passed = final_score >= 0.8 AND 双方都通过 AND 分歧 < 0.4`

2. **实现 oh-my-opencode agent 调用**
   - 配置 executor_agent 和 reviewer_agent（必须不同）
   - 通过 subprocess 调用 oh-my-opencode CLI
   - 传递验证上下文（change 名称、验证标准）

3. **实现数据脱敏** (`skills/_lib/sanitizer.py`)
   - 自动检测敏感信息（API Keys、密码、路径）
   - 替换为占位符（`<REDACTED>`）
   - 支持白名单（允许传输的路径）

4. **实现判定结果记录**
   - 记录到事件流（verification_completed 事件）
   - 包含双方分数、分歧、最终判定

**验收标准**:

- [ ] Executor/Reviewer 返回独立分数
- [ ] 判定算法正确（权重 0.4/0.6，阈值 0.8）
- [ ] 分歧过大时警告（> 0.4）
- [ ] 数据脱敏有效（API Keys 不传输）
- [ ] 同 agent 警告但允许（用户确认）

**交付文件**:

```
skills/_lib/
├── tribunal.py              # 审判委员会核心
└── sanitizer.py             # 数据脱敏
```

---

#### P3-T3: 实现记忆系统 (Memory System)

- **优先级**: P1
- **工作量**: 3-4 人天
- **依赖**: P1-T1（状态向量）
- **对应 ADR**: ADR-0006

**任务详情**:

1. **创建 LoopMemory 类** (`skills/_lib/memory.py`)
   - 实现 `record_execution()`: 记录执行痕迹
   - 实现 `get_execution_history()`: 查询历史执行
   - 实现 `get_insights_for_change()`: 获取洞察
   - 实现 `suggest_config()`: 推荐配置

2. **实现中断恢复**
   - 读取历史执行记录
   - 显示恢复上下文（上次执行时间、结果、失败原因）
   - 推荐配置（基于历史成功执行）

3. **实现重复失败警告**
   - 检测失败模式（同一 change 失败 ≥ 3 次）
   - 分析失败原因（错误类型统计）
   - 显示警告和建议

4. **实现配置推荐**
   - 查找相似目标的历史执行
   - 分析成功执行的配置参数
   - 推荐配置（max_iterations, max_retries, parallel_limit）

5. **实现统计更新**
   - 更新总执行次数、成功率
   - 更新平均迭代次数、重试次数
   - 更新常见错误统计

**验收标准**:

- [ ] 中断恢复显示完整上下文
- [ ] 重复失败警告触发（失败 ≥ 3 次）
- [ ] 配置推荐基于历史数据（非硬编码
- [ ] 统计数据准确（成功率、平均迭代）
- [ ] 记忆数据永久保留（提供归档命令）

**交付文件**:

```
skills/_lib/
└── memory.py                # 记忆系统核心
```

---

#### P3-T4: 实现轻量级会话管理

- **优先级**: P2
- **工作量**: 2 人天
- **依赖**: P1-T1（状态向量）
- **对应 ADR**: ADR-0010

**任务详情**:

1. **扩展状态向量**
   - 添加 `session_info` 字段（session_id, parent_session_id, started_at）
   - 添加 `sub_sessions` 字段（子会话列表）

2. **创建 SessionCoordinator 类** (`skills/_lib/session.py`)
   - 实现 `create_session()`: 创建新会话
   - 实现 `find_session()`: 查找会话（按 session_id）
   - 实现 `update_session_status()`: 更新会话状态
   - 实现 `list_sessions()`: 列出所有会话

3. **实现父子会话协作**
   - 父会话创建子会话（用于并行任务）
   - 子会话通过状态向量隐式协调
   - 不支持真正并行（轮流执行）

4. **实现会话状态管理**
   - 会话状态枚举（active, paused, completed, failed）
   - 会话状态转换（active → paused → active）

**验收标准**:

- [ ] 会话信息正确写入状态向量
- [ ] 父子会话关系可追踪
- [ ] 会话状态转换正确
- [ ] 不支持真正并行（文档明确说明）

**交付文件**:

```
skills/_lib/
└── session.py               # 轻量级会话管理
```

---

#### P3-T5: 实现多 Agent 协作

- **优先级**: P2
- **工作量**: 2-3 人天
- **依赖**: P3-T2（审判委员会）
- **对应 ADR**: ADR-0004

**任务详情**:

1. **创建 Agent 协作框架** (`skills/_lib/agents.py`)
   - 定义 Agent 角色（Planner, Executor, Verifier）
   - 实现 Agent 通信机制（通过状态向量传递数据）

2. **实现 Planner Agent**
   - 分析当前状态
   - 生成执行计划
   - 定义成功标准

3. **实现 Executor Agent**
   - 执行计划中的 actions
   - 报告执行结果
   - 处理错误

4. **实现 Verifier Agent**
   - 验证执行结果
   - 计算质量分数
   - 报告问题

**验收标准**:

- [ ] 三个 Agent 可独立运行
- [ ] Agent 间通过状态向量通信
- [ ] 协作流程完整（Planner → Executor → Verifier）
- [ ] 验证结果记录到事件流

**交付文件**:

```
skills/_lib/
└── agents.py                # 多 Agent 协作框架
```

---

### Phase 3 里程碑

| 里程碑 | 验收标准 | 预计日期 |
|--------|---------|---------|
| **M3.1**: Human-in-Loop 节点可运行 | 7 类节点 + 3 种验证模式通过测试 | Week 7 结束 |
| **M3.2**: 审判委员会可运行 | 多 agent 验证 + 数据脱敏通过测试 | Week 8 结束 |
| **M3.3**: 记忆系统可运行 | 中断恢复 + 配置推荐通过测试 | Week 8 结束 |
| **M3.4**: Phase 3 集成测试通过 | 所有高级特性协同工作 | Week 8 结束 |

---

## ✅ Phase 4: 迁移与测试 ✅已实施

**目标**: 三阶段拆分、v1.x 迁移、测试套件

**对应 ADR**: ADR-0003, ADR-0006

### 任务清单

#### P4-T1: 实现三阶段拆分

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: P2-T1, P2-T4（Loop 引擎、交互模式）
- **对应 ADR**: ADR-0003

**任务详情**:

1. **创建 `skills/guide-arch.md`** (架构定义阶段)
   - 实现 5 个子阶段：setup, adr-create, architecture, roadmap-define, arch-done
   - 集成门控机制（arch_done 检查）
   - 生成交接文件（`.rddf/state/arch-handoff.json`）

2. **创建 `skills/guide-plan.md`** (变更生成阶段)
   - 从 `guide-spec.md` 拆分（移除 roadmap 相关逻辑）
   - 实现 4 个子阶段：scan, propose, deps, plan-done
   - 集成门控机制（plan_done 检查）
   - 生成交接文件（`.rddf/state/plan-handoff.json`）

3. **更新 `skills/guide.md`** (推荐器)
   - 支持三阶段扫描（arch, plan, ship）
   - 自动推荐下一阶段
   - 显示阶段间切换建议

4. **实现阶段间交接文件**
   - `.rddf/state/arch-handoff.json`: ADR 数量、roadmap 状态、差距分析
   - `.rddf/state/plan-handoff.json`: active changes、artifacts 状态、依赖分析

**验收标准**:

- [ ] `guide-arch` 可独立运行（创建 ADR、定义 roadmap）
- [ ] `guide-plan` 可独立运行（生成 changes、依赖分析）
- [ ] `guide-ship` 保持不变（向后兼容）
- [ ] 阶段间切换通过门控验证
- [ ] `guide-spec` 作为别名保留（内部调用 arch → plan）

**交付文件**:

```
skills/
├── guide-arch.md            # 架构定义阶段（新增）
├── guide-plan.md            # 变更生成阶段（从 guide-spec 拆分）
└── guide.md                 # 推荐器（更新支持三阶段）
```

---

#### P4-T2: 编写单元测试

- **优先级**: P0
- **工作量**: 3 人天
- **依赖**: P1, P2, P3 所有任务
- **对应 ADR**: 部

**任务详情**:

1. **创建测试目录结构**
   ```
   tests/
   ├── unit/
   │   ├── test_state_vector.py
   │   ├── test_event_log.py
   │   ├── test_gate.py
   │   ├── test_config.py
   │   ├── test_loop_engine.py
   │   ├── test_detectors.py
   │   ├── test_actions.py
   │   ├── test_tribunal.py
   │   ├── test_memory.py
   │   └── test_session.py
   └── integration/
       ├── test_loop_flow.py
       ├── test_gate_transition.py
       └── test_phase_switch.py
   ```

2. **编写核心组件测试**
   - StateVector: 读写、并发、验证、重置
   - EventLog: 写入、查询、进度报告
   - Gate: 检查清单、失败处理、插件
   - Config: 解析、优先级、验证
   - LoopEngine: 主循环、安全机制、目标判定
   - Detectors: 8 个 detectors 独立测试
   - Actions: 7 个 actions 独立测试
   - Tribunal: 判定算法、数据脱敏
   - Memory: 中断恢复、配置推荐、失败警告
   - Session: 会话创建、状态转换

3. **编写集成测试**
   - 完整 Loop 流程（scan → plan → execute → verify → adapt）
   - 阶段切换（arch → plan → ship）
   - 门控验证（通过/失败/强制）
   - 三种交互模式（loop/menu/hybrid）

**验收标准**:

- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 所有测试通过（0 failures, 0 errors）
- [ ] 测试执行时间 < 5 分钟
- [ ] 集成测试覆盖核心场景

**交付文件**:

```
tests/
├── unit/                  # 单元测试（10 个文件）
└── integration/           # 集成测试（3 个文件）
```

---

#### P4-T3: 编写迁移指南

- **优先级**: P1
- **工作量**: 1-2 人天
- **依赖**: P4-T1（三阶段拆分）
- **对应 ADR**: ADR-0003, ADR-0006

**任务详情**:

1. **创建 `docs/migration/v1-to-v2.md`**
   - 解释 v1.x → v2.0 架构变更
   - 提供迁移步骤（安装、配置、测试）
   - 列出向后兼容承诺
   - 提供常见问题解答

2. **更新 `README.md`**
   - 添加 v2.0 特性列表
   - 更新工作流图（三阶段）
   - 添加快速开始指南

3. **更新 `USAGE.md`**
   - 更新技能列表（guide-arch, guide-plan, guide-ship）
   - 添加 Loop 引擎使用示例
   - 添加配置示例

**验收标准**:

- [ ] 迁移指南清晰可操作（v1.x 用户可跟随）
- [ ] README/USAGE 反映 v2.0 架构
- [ ] 向后兼容承诺明确（guide-spec 别名、同步层）

**交付文件**:

```
docs/
├── migration/
│   └── v1-to-v2.md        # 迁移指南（新增）
README.md                  # 更新
USAGE.md                   # 更新
```

---

#### P4-T4: 编写完整文档

- **优先级**: P1
- **工作量**: 1-2 人天
- **依赖**: P1, P2, P3 所有任务

**任务详情**:

1. **编写 Loop 引擎教程**
   - 快速开始指南
   - 配置详解
   - 最佳实践
   - 故障排查

2. **编写开发者指南**（已存在，更新）
   - 扩展 Detectors/Actions/Gates
   - 自定义 Human-in-Loop 节点
   - 测试指南

3. **编写 API 参考文档**
   - StateVector API
   - EventLog API
   - GateMechanism API
   - LoopEngine API
   - Tribunal API
   - Memory API

**验收标准**:

- [ ] 教程完整（快速开始 → 高级用法）
- [ ] API 参考文档覆盖所有公共接口
- [ ] 开发者指南可指导扩展开发

**交付文件**:

```
docs/
├── v2-loop-engine-tutorial.md   # Loop 引擎教程（新增）
├── v2-api-reference.md          # API 参考（更新）
└── v2-developer-guide.md        # 开发者指南（更新）
```

---

### Phase 4 里程碑

| 里程碑 | 验收标准 | 预计日期 |
|--------|---------|---------|
| **M4.1**: 三阶段拆分完成 | guide-arch/guide-plan/guide-ship 可独立运行 | Week 9 结束 |
| **M4.2**: 测试覆盖率达标 | 单元测试 ≥ 80%，集成测试覆盖核心场景 | Week 9 结束 |
| **M4.3**: 迁移指南完成 | v1.x 用户可跟随迁移 | Week 10 结束 |
| **M4.4**: 文档完整 | 教程、API 参考、开发者指南齐全 | Week 10 结束 |

---

## ✅ Phase 5: Beta 发布 ✅已实施

**目标**: Beta 发布，收集反馈，修复关键问题

### 任务清单

#### P5-T1: Beta 发布准备

- **优先级**: P0
- **工作量**: 2 人天

**任务详情**:

1. **版本号更新**
   - `package.json` 版本改为 `2.0.0-beta`
   - 添加 skills 列表（guide-arch, guide-plan, guide-ship, loop）

2. **发布说明**
   - 编写 CHANGELOG.md
   - 列出新特性、破坏性变更、已知问题
   - 提供迁移指南链接

3. **性能优化**
   - 状态向量缓存（减少重复读取）
   - 事件流批量写入（减少 I/O）
   - 优化检测器/动作执行时间

**验收标准**:

- [ ] `npm install spec-workflow@2.0.0-beta` 成功
- [ ] 发布说明完整
- [ ] 性能指标达标（读写延迟 < 10ms）

---

#### P5-T2: 收集用户反馈

- **优先级**: P1
- **工作量**: 1 人天

**任务详情**:

1. **创建反馈渠道**
   - GitHub Issues 模板（Bug 报告、特性请求）
   - 反馈表单（使用体验、问题、建议）

2. **监控关键指标**
   - 安装成功率
   - 首次运行成功率
   - 错误报告频率

3. **收集性能数据**
   - Loop 引擎执行时间
   - 状态向量读写延迟
   - 事件流查询性能

---

#### P5-T3: 修复关键问题

- **优先级**: P0
- **工作量**: 1 人天

**任务详情**:

1. **优先级排序**
   - P0: 阻塞性问题（崩溃、数据丢失）
   - P1: 功能缺陷（门控不生效、记忆不工作）
   - P2: 用户体验（错误消息不清、文档缺失）

2. **快速修复流程**
   - 复现问题
   - 编写测试
   - 修复 + 回归测试
   - 发布补丁

---

### Phase 5 里程碑

| 里程碑 | 验收标准 | 预计日期 |
|--------|---------|---------|
| **M5.1**: Beta 发布 | v2.0.0-beta 发布到 npm | Week 10 结束 |
| **M5.2**: 反馈收集 | ≥ 5 个用户反馈 | Week 11 结束 |
| **M5.3**: 关键问题修复 | 所有 P0 问题修复 | Week 11 结束 |

---

## 📊 工作量汇总

### 按 Phase 汇总

| Phase | 工作量（人天） | 预计周期 | 关键交付物 |
|-------|---------------|---------|-----------|
| **Phase 1**: 核心基础 | 8-10 | 2 周 | StateVector, EventLog, Gate, ConfigParser, SyncLayer |
| **Phase 2**: Loop 引擎 | 12-15 | 3 周 | LoopEngine, Detectors, Actions, 三种模式, 设计先行 |
| **Phase 3**: 高级特性 | 10-12 | 2-3 周 | Human-in-Loop, Tribunal, Memory, Session, Agents |
| **Phase 4**: 迁移测试 | 8-10 | 2 周 | 三阶段拆分, 测试套件, 迁移指南, 文档 |
| **Phase 5**: Beta 发布 | 3-4 | 1 周 | Beta 发布, 反馈收集, 问题修复 |
| **总计** | **41-51** | **8-10 周** | **v2.0.0-beta** |

### 按模块汇总

| 模块 | 工作量（人天） | 对应 ADR | 文件数 |
|------|---------------|---------|--------|
| 状态管理（StateVector + EventLog + Sync） | 7 | ADR-0006 | 5 |
| 门控机制（Gate） | 2-3 | ADR-0007 | 1 |
| 配置系统（ConfigParser） | 1-2 | ADR-0002 | 2 |
| Loop 引擎（LoopEngine + Detectors + Actions） | 11 | ADR-0004 | 3 |
| 交互模式（三种模式 + Human-in-Loop） | 5 | ADR-0002, ADR-0005 | 2 |
| 审判委员会（Tribunal + Sanitizer） | 4-5 | ADR-0008 | 2 |
| 记忆系统（Memory） | 3-4 | ADR-0006 | 1 |
| 会话管理（Session） | 2 | ADR-0010 | 1 |
| 多 Agent 协作（Agents） | 2-3 | ADR-0004 | 1 |
| 三阶段拆分（guide-arch/plan） | 3 | ADR-0003 | 3 |
| 测试 + 文档 | 10-12 | 全部 | 15+ |

---

## 🗂️ 代码结构

### 最终目录结构

```
spec-workflow/
├── skills/
│   ├── _lib/                      # Python 核心库（新增）
│   │   ├── state_vector.py        # 状态向量
│   │   ├── event_log.py           # 事件流
│   │   ├── event_types.py         # 事件类型定义
│   │   ├── event_context.py       # 事件上下文
│   │   ├── lock.py                # 文件锁
│   │   ├── gate.py                # 门控机制
│   │   ├── config.py              # 配置解析器
│   │   ├── defaults.py            # 默认配置
│   │   ├── sync_state.py          # v1.x 同步层
│   │   ├── detectors.py           # 状态检测器
│   │   ├── actions.py             # 执行动作
│   │   ├── interaction_modes.py   # 三种交互模式
│   │   ├── human_nodes.py         # Human-in-Loop 节点
│   │   ├── design_phase.py        # 设计先行阶段
│   │   ├── flowchart.py           # 可视化流程图
│   │   ├── tribunal.py            # 审判委员会
│   │   ├── sanitizer.py           # 数据脱敏
│   │   ├── memory.py              # 记忆系统
│   │   ├── session.py             # 会话管理
│   │   ├── agents.py              # 多 Agent 协作
│   │   └── schemas/               # JSON Schema 定义
│   │       └── state_vector_schema.json
│   │
│   ├── loop-engine.py             # Loop 引擎核心（新增）
│   ├── guide-arch.md              # 架构定义阶段（新增）
│   ├── guide-plan.md              # 变更生成阶段（从 guide-spec 拆分）
│   ├── guide-ship.md              # 变更执行阶段（保持不变）
│   ├── guide.md                   # 推荐器（更新）
│   ├── propose.md                 # 保持不变
│   ├── execute.md                 # 保持不变
│   ├── status.md                  # 保持不变
│   ├── roadmap.md                 # 保持不变
│   ├── deps.md                    # 保持不变
│   └── prometheus-planning.md     # 保持不变
│
├── tests/
│   ├── unit/                      # 单元测试（新增）
│   │   ├── test_state_vector.py
│   │   ├── test_event_log.py
│   │   ├── test_gate.py
│   │   ├── test_config.py
│   │   ├── test_loop_engine.py
│   │   ├── test_detectors.py
│   │   ├── test_actions.py
│   │   ├── test_tribunal.py
│   │   ├── test_memory.py
│   │   └── test_session.py
│   ├── integration/               # 集成测试（新增）
│   │   ├── test_loop_flow.py
│   │   ├── test_gate_transition.py
│   │   └── test_phase_switch.py
│   └── ...                        # 现有测试保持不变
│
├── docs/
│   ├── adr/                       # ADR 文档（已存在）
│   ├── migration/
│   │   └── v1-to-v2.md            # 迁移指（新增）
│   ├── v2-implementation-plan.md  # 本文档
│   ├── v2-architecture-refactor-plan.md  # 已存在
│   ├── v2-adr-summary.md          # 已存在
│   ├── v2-developer-guide.md      # 已存在（更新）
│   ├── v2-loop-engine-guide.md    # 已存在
│   ├── v2-config-schema.md        # 已存在
│   ├── v2-api-reference.md        # 已存在（更新）
│   └── v2-loop-engine-tutorial.md # 教程（新增）
│
├── .spec-workflow/                # 项目配置目录（可选）
│   ├── detectors/                 # 自定义 detectors
│   ├── actions/                   # 自定义 actions
│   ├── gates/                     # 自定义 gates
│   ├── verifiers/                 # 验证脚本
│   ├── human_nodes/               # 自定义 human nodes
│   ├── plugins/                   # 门控插件
│   └── loops/                     # loop.yaml 配置
│
├── package.json                   # 更新（version: 2.0.0-beta）
├── README.md                      # 更新
├── USAGE.md                       # 更新
└── CHANGELOG.md                   # 新增
```

### 核心文件清单

| 文件 | 类型 | 行数预估 | 对应 ADR |
|------|------|---------|---------|
| `skills/_lib/state_vector.py` | Python | ~300 | ADR-0006 |
| `skills/_lib/event_log.py` | Python | ~250 | ADR-0006 |
| `skills/_lib/gate.py` | Python | ~300 | ADR-0007 |
| `skills/_lib/config.py` | Python | ~200 | ADR-0002 |
| `skills/_lib/sync_state.py` | Python | ~200 | ADR-0006 |
| `skills/_lib/lock.py` | Python | ~100 | ADR-0006 |
| `skills/loop-engine.py` | Python | ~500 | ADR-0004 |
| `skills/_lib/detectors.py` | Python | ~400 | ADR-0004 |
| `skills/_lib/actions.py` | Python | ~350 | ADR-0004 |
| `skills/_lib/interaction_modes.py` | Python | ~250 | ADR-0002 |
| `skills/_lib/human_nodes.py` | Python | ~300 | ADR-0005 |
| `skills/_lib/tribunal.py` | Python | ~250 | ADR-0008 |
| `skills/_lib/sanitizer.py` | Python | ~150 | ADR-0008 |
| `skills/_lib/memory.py` | Python | ~300 | ADR-0006 |
| `skills/_lib/session.py` | Python | ~200 | ADR-0010 |
| `skills/_lib/agents.py` | Python | ~250 | ADR-0004 |
| `skills/guide-arch.md` | Markdown | ~200 | ADR-0003 |
| `skills/guide-plan.md` | Markdown | ~150 | ADR-0003 |

**新增代码总量**: ~5,000 行 Python + ~350 行 Markdown

---

## ⚠️ 风险与缓解策略

### 风险矩阵

| 风险 | 影响 | 概率 | 缓解策略 | 负责人 |
|------|------|------|---------|--------|
| **范围蔓延** | 高 | 中 | 严格限制 v2.0 核心功能，v2.1 再添加增强功能 | sisyphus |
| **向后兼容破坏** | 高 | 低 | 同步层 + alias + v2.x 期间不移除旧接口 | sisyphus |
| **Loop 死循环** | 高 | 低 | 四重安全机制（迭代限制、重试限制、震荡检测、超时） | sisyphus |
| **状态不一致** | 中 | 中 | 同步层 + 校验 + 文件锁 | sisyphus |
| **性能下降** | 低 | 低 | 缓存 + 批量写入 + 异步事件流 | sisyphus |
| **测试覆盖率不足** | 中 | 中 | 编写测试优先（TDD），覆盖率 ≥ 80% 目标 | sisyphus |
| **文档不完整** | 中 | 中 | 每个 Phase 结束时更新文档 | sisyphus |
| **学习成本高** | 中 | 高 | 提供教程、默认配置、迁移指南 | sisyphus |
| **oh-my-opencode 集成失败** | 高 | 低 | 提供降级方案（单 agent 验证） | sisyphus |

### 风险缓解计划

#### 1. 范围蔓延控制

**策略**:
- 明确 v2.0 核心功能清单（本文档定义）
- 每周审查进度，确保不偏离计划
- v2.1 候选功能严格隔离（定时循环、完整会话管理）

**检查点**:
- Phase 1 结束: 确认核心基础完成，不添加额外功能
- Phase 2 结束: 确认 Loop 引擎完成，不添加增强功能
- Phase 3 结束: 确认高级特性完成，准备进入测试阶段

#### 2. 向后兼容保障

**策略**:
- 保留 `guide-spec` 作为别名（内部调用 arch → plan）
- 实现双向同步层（状态向量 ↔ v1.x 文件）
- v2.x 期间不移除旧接口

**测试**:
- 编写兼容性测试（v1.x 技能在 v2.0 环境下运行）
- 验证同步层正确性（状态向量更新后 v1.x 文件同步）

#### 3. 安全防护

**四重安全机制**:
1. **最大迭代次数**: 默认 100 次（可配置）
2. **最大重试次数**: 默认 3 次（可配置）
3. **状态震荡检测**: 最近 5 次 ≤ 2 种状态 → 报错
4. **超时控制**: 每个 action 最大 30 分钟

**额外防护**:
- 断路器（连续失败 3 次触发）
- 错误预算（失败率 > 10% 时警告）

---

## 📈 成功指标

### 技术指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| **测试覆盖率** | ≥ 80% | pytest --cov |
| **状态向量读写延迟** | < 10ms | 基准测试 |
| **事件流查询延迟** | < 100ms（10,000 条） | 基准测试 |
| **Loop 引擎启动时间** | < 1s | 基准测试 |
| **Detector 总执行时间** | < 500ms | 基准测试 |

### 用户体验指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| **v1.x 迁移成功率** | ≥ 95% | 用户反馈 |
| **首次运行成功率** | ≥ 90% | Beta 测试 |
| **学习成本** | < 30 分钟 | 用户调查 |
| **自动化效率提升** | ≥ 3x | 基准对比（v1.x vs v2.0） |

---

## 🎯 下一步行动

### 立即执行（本周）

1. **审批实施计划**: 审查本文档，确认范围和工作量
2. **创建 OpenSpec change**: `openspec new change v2-architecture-refactor`
3. **设置开发环境**: 安装 Python 3.8+、PyYAML、pytest
4. **创建功能分支**: `git checkout -b feature/v2-implementation`

### Phase 1 启动（下周）

1. **实现 StateVector 类**: 从 P1-T1 开始
2. **编写单元测试**: 测试驱动开发（TDD）
3. **每周进度审查**: 确保按计划推进

---

## 📝 变更日志

| 日期 | 版本 | 变更 | 作者 |
|------|------|------|------|
| 2026-06-24 | 1.0.0-draft | 初始版本，完整实施计划 | sisyphus |

---

## 📚 相关文档

- [v2-architecture-refactor-plan.md](v2-architecture-refactor-plan.md) — 架构重构方案
- [v2-adr-summary.md](v2-adr-summary.md) — ADR 总结报告
- [v2-loop-engine-guide.md](v2-loop-engine-guide.md) — Loop 引擎使用指南
- [v2-developer-guide.md](v2-developer-guide.md) — 开发者指南
- [v2-config-schema.md](v2-config-schema.md) — 配置 Schema 参考
- [ADR-0001 ~ ADR-0010](adr/) — 完整 ADR 文档

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-28  
**下次审查**: 无（v2.0 已完成）  
**审批状态**: ✅ 完成 — v2.0.0-beta 已于 2026-06-26 发布

