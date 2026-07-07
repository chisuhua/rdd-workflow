# spec-workflow v2.0 ADR 总结报告

> **生成日期**: 2026-06-22  
> **决策者**: sisyphus  
> **调研来源**: Looper、Anthropic Agents、Claude Code /loop、OpenHands、SWE-Agent、Requesty  
> **ADR 总数**: 12 个（10 个已采纳 + 1 个 v2.1 候选 + 1 个分阶段实施）

> ## 📊 v2.0 ADR 实施状态（2026-06-28）
>
> | ADR | 实施状态 |
> |-----|---------|
> | ADR-0001 | ✅ 已实施（v1.x） |
> | ADR-0002 ~ ADR-0008 | ✅ 已实施（v2.0.0-beta） |
> | ADR-0009 | ❌ 未实施（v2.1 候选占位） |
> | ADR-0010 | ⚠️ 部分实施（v2.0 轻量级） |
> | ADR-0011 | ❌ 未实施（设计已采纳） |
> | ADR-0012 | ❌ 未实施（设计已采纳） |
>
> **图例**：✅ 已实施 | ⚠️ 部分实施 | ❌ 未实施

---

## 📋 执行摘要

spec-workflow v2.0 完成了从**状态机驱动**到 **Loop 驱动**的架构级重构。通过业界调研，提取了 12 个核心设计模式，形成了完整的 ADR 体系：

- **修订 ADR**: 5 个（ADR-0002、0003、0004、0005、0006）
- **新增 ADR**: 3 个（ADR-0007、0008、0010）
- **v2.1 候选**: 1 个（定时循环，原 ADR-0009）
- **v2.0 待实施**: 2 个（ADR-0011、0012）

**核心升级**:
1. ✅ 三阶段架构（arch → plan → ship）
2. ✅ 三种交互模式（loop / menu / hybrid）
3. ✅ Loop 引擎 5 大构建块（Goal → Plan → Execute → Verify → Adapt）
4. ✅ 门控机制（阶段切换前必须通过检查清单）
5. ✅ 审判委员会（多 agent 交叉验证）
6. ✅ 记忆系统（中断恢复、配置推荐、失败学习）
7. ✅ Human-in-Loop 节点（三种验证模式）
8. ✅ 便携规范（loop.yaml 人类可读配置）

---

## 📚 ADR 完整列表

### v1.x 历史 ADR（1 个）

| ADR | 标题 | 状态 | 日期 | 关键决策 |
|-----|------|------|------|---------|
| [ADR-0001](adr/ADR-0001-propose-plan-execute-state-machine.md) | 双阶段状态机分离 (spec/ship) | 已采纳 | 2026-06-08 | guide 拆分为 guide-spec + guide-ship |

---

### v2.0 修订 ADR（5 个）

| ADR | 标题 | 状态 | 主要修订内容 | 调研来源 |
|-----|------|------|------------|---------|
| [ADR-0002](adr/ADR-0002-goal-driven-interaction-modes.md) | 目标驱动接口与交互模式配置 | 已采纳（修订） | ✅ 增加设计先行阶段（目标/验证/控制）<br>✅ 增加便携规范支持（loop.yaml）<br>✅ 三种交互模式（loop/menu/hybrid） | Looper<br>便携规范 |
| [ADR-0003](adr/ADR-0003-three-phase-architecture.md) | 三阶段架构重构 (arch → plan → ship) | 已采纳（实施） | ✅ 按人工介入程度切分三阶段（arch 高 / plan 中 / ship 低）<br>✅ guide-spec 拆分为 guide-arch + guide-plan<br>✅ 向后兼容（guide-spec 保留为别名，自动调用 arch → plan）<br>✅ 推荐器升级（guide 三阶段扫描） | ADR-0001<br>状态机 |
| [ADR-0004](adr/ADR-0004-loop-engine-core-design.md) | Loop 引擎核心设计 | 已采纳（修订） | ✅ 重构为 5 大构建块（Goal/Plan/Execute/Verify/Adapt）<br>✅ 增加多 Agent 协作（Planner/Executor/Verifier）<br>✅ 增加可视化流程图生成 | Requesty<br>OpenHands |
| [ADR-0005](adr/ADR-0005-human-in-loop-nodes.md) | Human-in-Loop 节点定义 | 已采纳（修订） | ✅ 扩展为三种验证模式（human/multi_model/script）<br>✅ 增加节点策略（fixed/configurable）<br>✅ 集成审判委员会（ADR-0008） | Looper |
| [ADR-0006](adr/ADR-0006-state-vector-event-log.md) | 状态向量与事件流设计 | 已采纳（修订） | ✅ 增加记忆系统字段（executions/insights/configs）<br>✅ 支持中断恢复（显示历史上下文）<br>✅ 支持重复失败警告<br>✅ 支持配置推荐 | OpenHands<br>Anthropic |

---

### v2.0 新增 ADR（3 个）

| ADR | 标题 | 状态 | 核心设计 | 调研来源 |
|-----|------|------|---------|---------|
| [ADR-0007](adr/ADR-0007-gate-mechanism.md) | 门控机制设计 | 已采纳 | ✅ error/warning 两级严重度<br>✅ 阶段切换前必须通过检查清单<br>✅ 支持强制切换（需确认并记录）<br>✅ 支持插件扩展 | Requesty<br>5 大构建块 |
| [ADR-0008](adr/ADR-0008-tribunal-committee.md) | 审判委员会设计 | 已采纳 | ✅ 基于 oh-my-opencode 的多 agent 调用<br>✅ 强制不同 agent（警告但允许同 agent）<br>✅ 数据脱敏（跨模型传输）<br>✅ 综合判定算法（权重 0.4/0.6） | Looper<br>审判委员会 |
| [ADR-0010](adr/ADR-0010-multi-session-management.md) | 多会话管理与并行执行 | 已采纳（分阶段） | ✅ v2.0: 轻量级会话管理<br>✅ v2.1: 完整会话管理系统<br>✅ 状态向量扩展（session_info）<br>✅ 基本的父子会话协作 | OpenHands<br>Anthropic |

---

### v2.0 待实施 ADR（2 个）

> 设计已采纳但代码尚未实施。v2.0.0-beta 之后的迭代中实施。

| ADR | 标题 | 状态 | 核心设计 | 调研来源 |
|-----|------|------|---------|---------|
| [ADR-0011](adr/ADR-0011-phase-step-pipeline-model.md) | 阶段步骤化执行模型 | 已采纳（待实施） | ✅ 阶段模板（按 phase 拆解步骤）<br>✅ 触发器条件驱动步骤执行<br>✅ 步骤引擎（执行单元）<br>✅ 中断恢复（步骤级粒度） | 阶段步骤化<br>中断恢复 |
| [ADR-0012](adr/ADR-0012-flow-customization-layer.md) | 流程定制层 | 已采纳（待实施） | ✅ 增量覆盖（基于基础流程的扩展）<br>✅ 条件触发（基于上下文激活）<br>✅ 自定义技能注册<br>✅ 多项目复用 | 流程定制<br>复用机制 |

---

### v2.1 候选 ADR（2 个）

| ADR | 标题 | 状态 | 说明 |
|-----|------|------|------|
| ADR-0009（候选） | 定时循环与事件触发 | 待定 | ⏸️ 留到 v2.1 实施<br>📋 支持 cron 表达式定时触发<br>📋 支持事件触发（Git push、PR 创建）<br>📋 后台 Routines 持续监控 |
| ADR-0010 方案 B | 完整会话管理系统 | 待定 | ⏸️ 留到 v2.1 实施<br>📋 SessionManager（多进程并行）<br>📋 DependencyScheduler（DAG 调度）<br>📋 进程间通信 |

**延迟理由**:
1. **ADR-0009**: v2.0 聚焦核心 Loop 引擎架构，定时循环是增强功能
2. **ADR-0010 方案 B**: v2.0 先实现轻量级方案，v2.1 再引入完整会话管理
3. 避免 v2.0 范围蔓延

---

## 🏗️ 架构演进图

```
v1.0 (2026-06-03)          v1.1 (2026-06-05)          v2.0 (2026-06-22)
─────────────────          ─────────────────          ─────────────────
单文件 guide.md     →      双阶段 spec/ship     →     三阶段 arch/plan/ship
(10 个 phase)              (ADR-0001)                 (ADR-0003)
                                                      +
                                                 Loop 引擎 (ADR-0004)
                                                  5 大构建块
                                                      +
                                            三种交互模式 (ADR-0002)
                                          loop / menu / hybrid
                                                      +
                                         Human-in-Loop 节点 (ADR-0005)
                                      human / multi_model / script
                                                      +
                                           状态向量+事件流 (ADR-0006)
                                           + 记忆系统（中断恢复）
                                                      +
                                              门控机制 (ADR-0007)
                                     error/warning 两级 + 插件扩展
                                                      +
                                          审判委员会 (ADR-0008)
                                    多 agent 交叉验证 + 数据脱敏
                                                      +
                                        多会话管理 (ADR-0010)
                                          v2.0: 轻量级
                                          v2.1: 完整实现
```

---

## 🔗 ADR 依赖关系

```
ADR-0001 (双阶段分离 - v1.1)
    ↓
ADR-0003 (三阶段重构) ──→ ADR-0002 (交互模式 + 设计先行 + 便携规范)
    ↓                        ↓
ADR-0004 (Loop 引擎) ←───────┘
  5 大构建块 + 多 Agent
    ↓
ADR-0005 (Human-in-Loop) ──→ ADR-0008 (审判委员会)
  三种验证模式                    多 agent 交叉验证
    ↓                            ↓
ADR-0006 (状态向量) ←────────────┘
  + 记忆系统
    ↓
ADR-0007 (门控机制)
  error/warning 两级
    ↓
ADR-0010 (多会话管理)
  v2.0: 轻量级
  v2.1: 完整实现

v2.1 候选:
ADR-0010 方案 B ──→ 完整会话管理系统
  - 多进程并行
  - DAG 调度
ADR-0009 ──→ 定时循环 + 事件触发
  - cron 表达式
  - Git 事件
```

---

## 🎯 核心设计模式总结

### 1. 三阶段架构（ADR-0003）

**按人工介入程度切分**:

| 阶段 | 人工介入 | 主要产出 | 典型场景 |
|------|---------|---------|---------|
| **arch** | 高 | ADR、roadmap、架构文档 | 定义架构决策、规划路线图 |
| **plan** | 中 | openspec changes（proposal/design/tasks） | 生成变更提案 |
| **ship** | 低 | 代码实现、测试、归档 | 自动执行变更 |

---

### 2. 三种交互模式（ADR-0002）

| 模式 | 自动化程度 | 适用场景 | 配置 |
|------|-----------|---------|------|
| **loop** | 全自动 | 成熟项目、高置信度任务 | `mode: "loop"` |
| **menu** | 全手动 | 探索性任务、学习阶段 | `mode: "menu"` |
| **hybrid** | 半自动 | 大多数场景（推荐） | `mode: "hybrid"` |

**设计先行阶段**（Loop 启动前）:
1. **目标设计**: 明确产出物和完成标准
2. **验证设计**: 确定检查机制
3. **控制设计**: 设置刹车机制（断路器、最大迭代）

---

### 3. Loop 引擎 5 大构建块（ADR-0004）

```python
while not goal_achieved():
    # Block 1: Goal
    1. verify_goal()
    
    # Block 2: Plan
    2. scan_state()
    3. generate_plan()
    
    # Block 3: Execute
    4. check_human_nodes()
    5. execute_plan()
    
    # Block 4: Verify（集成门控）
    6. verify_results()
    7. gate_check()
    
    # Block 5: Adapt
    8. update_state()
    9. adapt()
```

**多 Agent 协作**（loop 模式）:
```
Planner Agent → Executor Agent → Verifier Agent
     ↓              ↓                ↓
  制定计划      执行任务        验证结果
```

---

### 4. 门控机制（ADR-0007）

**阶段切换前必须通过检查清单**:

| 门控 | 检查项 | 严重度 |
|------|-------|-------|
| **arch_done** | ADR ≥ 1、roadmap 存在、差距分析完成 | error/error/warning |
| **plan_done** | changes committed、artifacts 完整、依赖分析完成 | error/error/warning |
| **ship_done** | worktrees 空、archive 空、测试通过 | error/error/error |

**门控失败处理**:
```
1. 返回上一阶段修复（推荐）
2. 查看详细信息
3. 强制切换（需确认并记录）
4. 中止
```

---

### 5. 审判委员会（ADR-0008）

**多 agent 交叉验证**:

```python
# 配置
executor_agent: "coder"      # oh-my-opencode agent 名称
reviewer_agent: "reviewer"   # 必须不同 agent

# 判定算法
final_score = exec_score * 0.4 + review_score * 0.6
passed = final_score >= 0.8 AND 双方都通过 AND 分歧 < 0.4
```

**数据隐私**:
- 跨模型传输自动脱敏（API Keys、密码、路径）
- 跨 agent 需要用户确认
- 支持本地 agent（数据不出本机）

---

### 6. 记忆系统（ADR-0006）

**执行痕迹记录**:
```json
{
  "change": "add-auth",
  "success": false,
  "iterations": 5,
  "errors": [{"type": "test_failure"}],
  "interrupted_by": "user"
}
```

**核心能力**:
1. **中断恢复**: 显示历史上下文 + 推荐配置
2. **重复失败警告**: 失败 ≥ 3 次时警告 + 分析失败模式
3. **配置推荐**: 基于历史成功执行推荐参数
4. **失败学习**: 自动分析错误模式，生成优化建议

**数据保留**: 永久保留（项目级隔离，提供归档命令）

---

### 7. Human-in-Loop 节点（ADR-0005）

**三种验证模式**:

| 模式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **human** | 架构决策、高风险操作 | 最可靠 | 需要人工 |
| **multi_model** | 代码质量、合规性 | 自动化 + 高质量 | 成本高 |
| **script** | 格式化、测试验证 | 快速、可重复 | 只能检查可自动化项 |

**节点策略**:
- **fixed**: 固定验证模式（adr_create、execute_error 必须是 human）
- **configurable**: 用户可配置（archive_confirm、change_select 等）

---

### 8. 便携规范（ADR-0002）

**loop.yaml 人类可读配置**:
```yaml
version: "2.0"
name: "complete-all-changes"

goal:
  description: "complete all pending changes"
  success_criteria:
    - "active_changes.count == 0"
    - "worktrees.count == 0"

interaction:
  mode: "hybrid"

loop:
  max_iterations: 100
  max_retries: 3

verification:
  method: "multi_model"
  executor_agent: "coder"
  reviewer_agent: "reviewer"

control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
```

**配置优先级**: `loop.yaml` > `.rddf.json` > 环境变量 > 默认值

---

## 📊 对比：v1.x vs v2.0

| 特性 | v1.x | v2.0 | 提升 |
|------|------|------|------|
| **架构** | 双阶段（spec/ship） | 三阶段（arch/plan/ship） | ⭐⭐⭐⭐⭐ |
| **交互** | 菜单驱动 | 三种模式（loop/menu/hybrid） | ⭐⭐⭐⭐⭐ |
| **引擎** | 状态机 | Loop 引擎（5 大构建块） | ⭐⭐⭐⭐⭐ |
| **质量保障** | 无 | 门控机制 + 审判委员会 | ⭐⭐⭐⭐⭐ |
| **状态管理** | 13 个分散文件 | 统一状态向量 + 事件流 | ⭐⭐⭐⭐⭐ |
| **记忆** | 无（每次失忆） | 记忆系统（中断恢复、配置推荐） | ⭐⭐⭐⭐⭐ |
| **验证** | 人工审核 | 三种验证模式（human/multi_model/script） | ⭐⭐⭐⭐⭐ |
| **可观测性** | 低 | 完整事件流 + 进度报告 | ⭐⭐⭐⭐⭐ |
| **配置** | JSON 固定格式 | 便携规范（loop.yaml） | ⭐⭐⭐⭐ |

---

## 🚀 实施路线图

### Phase 1: 核心基础（2-3 周）

| 任务 | 对应 ADR | 优先级 | 工作量 |
|------|---------|--------|--------|
| 实现状态向量 + 事件流 | ADR-0006 | P0 | 3 天 |
| 实现门控机制 | ADR-0007 | P0 | 2-3 天 |
| 实现 Loop 引擎 5 大构建块 | ADR-0004 | P0 | 5 天 |
| 实现三种交互模式 | ADR-0002 | P0 | 3 天 |

### Phase 2: 质量保障（2-3 周）

| 任务 | 对应 ADR | 优先级 | 工作量 |
|------|---------|--------|--------|
| 实现记忆系统 | ADR-0006 | P1 | 4-5 天 |
| 实现 Human-in-Loop 节点 | ADR-0005 | P1 | 3 天 |
| 实现审判委员会 | ADR-0008 | P1 | 5-7 天 |
| 实现可视化流程图 | ADR-0004 | P2 | 2-3 天 |

### Phase 3: 增强功能（1-2 周）

| 任务 | 对应 ADR | 优先级 | 工作量 |
|------|---------|--------|--------|
| 实现便携规范（loop.yaml） | ADR-0002 | P2 | 2-3 天 |
| 实现多 Agent 协作 | ADR-0004 | P1 | 5-7 天 |
| 编写完整测试 | 全部 | P0 | 5 天 |
| 编写文档 | 全部 | P1 | 3 天 |

### v2.1 候选

| 任务 | 说明 | 对应 ADR | 工作量 |
|------|------|---------|--------|
| 完整会话管理系统 | SessionManager + DependencyScheduler | ADR-0010 方案 B | 5-7 天 |
| 定时循环 | cron 表达式定时触发 | ADR-0009 | 3-4 天 |
| 事件触发 | Git push、PR 创建等 | ADR-0009 | 3-4 天 |
| 后台 Routines | 持续监控 | ADR-0009 | 4-5 天 |

---

## 📁 ADR 文档结构

```
docs/
├── adr/
│   ├── ADR-0000-template.md              (模板)
│   ├── ADR-0001-propose-plan-execute-state-machine.md  (v1.1)
│   ├── ADR-0002-goal-driven-interaction-modes.md       (v2.0 修订)
│   ├── ADR-0003-three-phase-architecture.md            (v2.0)
│   ├── ADR-0004-loop-engine-core-design.md             (v2.0 修订)
│   ├── ADR-0005-human-in-loop-nodes.md                 (v2.0 修订)
│   ├── ADR-0006-state-vector-event-log.md              (v2.0 修订)
│   ├── ADR-0007-gate-mechanism.md                      (v2.0 新增)
│   ├── ADR-0008-tribunal-committee.md                  (v2.0 新增)
│   └── README.md                         (索引 - 已更新)
└── v2-adr-summary.md                   (本文件 - ADR 总结报告)
```

---

## 🎓 业界最佳实践映射

| 调研项目 | 设计模式 | 映射到 ADR | 借鉴价值 |
|---------|---------|-----------|---------|
| **Looper** | 设计先行模式 | ADR-0002 | ⭐⭐⭐⭐⭐ |
| **Looper** | 审判委员会 | ADR-0008 | ⭐⭐⭐⭐⭐ |
| **Looper** | 便携规范 | ADR-0002 | ⭐⭐⭐⭐ |
| **Requesty** | 5 大构建块 | ADR-0004 | ⭐⭐⭐⭐⭐ |
| **Requesty** | 门控机制 | ADR-0007 | ⭐⭐⭐⭐⭐ |
| **OpenHands** | 多 Agent 协作 | ADR-0004 | ⭐⭐⭐⭐ |
| **OpenHands** | 记忆系统 | ADR-0006 | ⭐⭐⭐⭐⭐ |
| **Anthropic** | 上下文管理 | ADR-0006 | ⭐⭐⭐⭐ |
| **Claude Code** | 定时循环 | ADR-0009（候选） | ⭐⭐⭐⭐ |

---

## ⚠️ 风险与缓解策略

| 风险 | 影响 | 缓解策略 |
|------|------|---------|
| **范围蔓延** | v2.0 包含过多功能，延期交付 | ✅ 严格限制核心功能，v2.1 再添加增强功能 |
| **向后兼容** | v1.x 用户迁移困难 | ✅ 保留同步层，v2.x 期间兼容现有状态文件 |
| **复杂度增加** | 用户学习成本高 | ✅ 提供便携规范模板、默认配置、文档 |
| **性能下降** | 状态向量读写频繁 | ✅ 内存缓存、批量写入、文件锁 |
| **存储增长** | 事件流和记忆文件变大 | ✅ 提供归档命令、定期清理 |

---

## ✅ 关键决策总结

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **交互模式** | 三种模式（loop/menu/hybrid） | 平衡自动化和控制权 |
| **验证模式** | human/multi_model/script | 灵活适配不同场景 |
| **门控策略** | error/warning 两级 | 平衡严格性和灵活性 |
| **模型调用** | 基于 oh-my-opencode agent | 解耦，不硬编码厂商和模型 |
| **记忆保留** | 永久保留（项目级） | 长期学习，隐私保护 |
| **配置格式** | JSON + YAML 双支持 | 人类可读 + 机器可读 |
| **定时循环** | 延迟到 v2.1 | 避免 v2.0 范围蔓延 |

---

## 📞 维护信息

- **主要决策者**: sisyphus
- **审计日期**: 2026-06-22
- **下次审查**: v2.0 发布前
- **ADR 维护**: 新增/修订需更新 `docs/adr/README.md` 索引

---

## 🚀 下一步行动

1. **确认 ADR 定稿**: 所有 ADR 已完成讨论和修订 ✅
2. **创建实施计划**: 基于 ADR 创建详细实施路线图
3. **开始编码**: 按 Phase 1 → Phase 2 → Phase 3 顺序实施
4. **编写测试**: 每个 ADR 对应单元测试 + 集成测试
5. **更新文档**: 用户指南、迁移指南、API 文档

---

**报告生成完成！** 🎉

所有 ADR 已定稿，架构决策清晰，可以进入实施阶段。

