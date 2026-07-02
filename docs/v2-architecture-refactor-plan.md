# Spec-Workflow v2.0 架构重构方案

> **版本**: 2.0.0-draft  
> **日期**: 2026-06-22  
> **状态**: ADR 已采纳，**未实施**  
> **决策者**: sisyphus

> ## ⚠️ DRAFT — ADR 已采纳但代码未实施
>
> 本文档汇总的 v2.0 架构（arch → plan → ship 三阶段、Loop 引擎、审判委员会等）的 **ADRs 已被作者采纳为设计决策**，但**实际代码改动尚未开始**。
>
> - 文档中引用的 `skills/guide-arch.md`、`skills/loop-engine.py` 等文件**不存在**
> - 当前 v1.x 代码继续按 ADR-0001 描述的双阶段架构运行
> - 实施进度详见 `docs/v2-implementation-plan.md`

---

## 📋 执行摘要

本文档汇总了 spec-workflow v2.0 的完整架构重构方案，从当前的**状态机驱动**范式升级到 **Loop 驱动 + Human-in-Loop** 的 AI 编程范式。

### 核心变更

| 维度 | v1.x (当前) | v2.0 (目标) |
|------|------------|------------|
| **架构** | 双阶段 (spec/ship) | 三阶段 (arch → plan → ship) |
| **驱动方式** | 菜单驱动 | Loop 驱动 + 可配置交互模式 |
| **交互模式** | 固定菜单 | loop / menu / hybrid (可配置) |
| **状态管理** | 13 个分散文件 | 统一状态向量 + 事件流 |
| **Human-in-Loop** | 所有决策点 | 7 类关键节点 (可配置) |
| **自动化程度** | 手动 | 自动编排 + 错误自愈 |

---

## 🏗️ 架构决策 (ADR)

本次重构定义了 **9 个 ADR**（8 个已采纳 + 1 个 v2.1 候选），形成完整的架构决策链：

### ADR-0002: 目标驱动接口与交互模式配置（修订）

**决策**: 采用三种可配置交互模式 + 设计先行阶段 + 便携规范

| 模式 | 适用场景 | Human-in-Loop |
|------|---------|---------------|
| **loop** | CI/CD、批量处理 | 仅错误时暂停 |
| **menu** | 学习阶段、探索 | 所有决策点 |
| **hybrid** (推荐) | 日常开发 | 7 类关键节点 |

**设计先行阶段**（Loop 启动前）:
1. 目标设计：明确产出物和完成标准
2. 验证设计：确定检查机制
3. 控制设计：设置刹车机制（断路器、最大迭代）

**便携规范**: 支持 `loop.yaml`（人类可读）和 `.spec-workflow.json`（机器可读）

### ADR-0003: 三阶段架构重构

**决策**: 按人工介入程度切分为三阶段

```
arch (高介入)  →  plan (中介入)  →  ship (低介入)
  ↓                ↓                ↓
ADR/Roadmap    Change 生成      执行/归档
架构治理       自动化生成       自动化执行
```

**阶段职责**:
- **arch**: ADR 创建、roadmap 定义、架构差距分析
- **plan**: 扫描 change 候选、生成 artifacts、依赖分析
- **ship**: worktree 创建、Prometheus 计划、执行、归档

### ADR-0004: Loop 引擎核心设计（修订）

**决策**: 采用 5 大构建块 + 多 Agent 协作

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

**技术栈**: Python (核心逻辑) + bash (系统操作)

### ADR-0005: Human-in-Loop 节点定义（修订）

**决策**: 扩展为三种验证模式 + 节点策略

| 验证模式 | 适用场景 | 优点 |
|---------|---------|------|
| **human** | 架构决策、高风险操作 | 最可靠 |
| **multi_model** | 代码质量、合规性 | 自动化 + 高质量 |
| **script** | 格式化、测试验证 | 快速、可重复 |

**节点策略**:
- **fixed**: 固定验证模式（adr_create、execute_error 必须是 human）
- **configurable**: 用户可配置（archive_confirm、change_select 等）

### ADR-0006: 状态向量与事件流设计（修订）

**决策**: 统一状态向量 + JSONL 事件流 + 记忆系统

- **状态向量**: `.rddf/state/state-vector.json` (单一权威来源)
- **事件流**: `.rddf/state/event-log.jsonl` (完整审计追踪)
- **记忆系统**: 执行痕迹、失败学习、配置推荐、中断恢复
- **同步层**: 与 v1.x 状态文件双向兼容

**记忆系统核心能力**:
1. 中断恢复：显示历史上下文 + 推荐配置
2. 重复失败警告：失败 ≥ 3 次时警告
3. 配置推荐：基于历史成功执行推荐参数
4. 失败学习：自动分析错误模式

### ADR-0007: 门控机制设计（新增）

**决策**: 阶段切换前必须通过检查清单

| 门控 | 检查项 | 严重度 |
|------|-------|-------|
| **arch_done** | ADR ≥ 1、roadmap 存在、差距分析完成 | error/error/warning |
| **plan_done** | changes committed、artifacts 完整、依赖分析完成 | error/error/warning |
| **ship_done** | worktrees 空、archive 空、测试通过 | error/error/error |

**门控失败处理**:
1. 返回上一阶段修复（推荐）
2. 查看详细信息
3. 强制切换（需确认并记录）
4. 中止

### ADR-0008: 审判委员会设计（新增）

**决策**: 基于 oh-my-opencode 的多 agent 交叉验证

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

### ADR-0010: 多会话管理与并行执行（新增，分阶段实施）

**决策**: v2.0 轻量级会话管理 + v2.1 完整会话管理系统

**v2.0（方案 A - 轻量级）**:
- 状态向量增加 `session_info` 和 `sub_sessions` 字段
- 轻量级会话协调器（通过状态向量隐式协调）
- 支持基本的父子会话协作
- ❌ 不支持真正并行（轮流执行）
- ❌ 不支持依赖调度

**v2.1（方案 B - 完整实现）**:
- 完整 SessionManager（多进程并行）
- DependencyScheduler（DAG 拓扑排序）
- 进程间通信机制
- 动态负载均衡
- 会话持久化

---

## 📐 新架构全景

### 用户视角

```bash
# 方式 1: 声明目标 (Loop 模式)
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "hybrid"
})

# 方式 2: 传统菜单 (向后兼容)
skill_use("guide-arch")   # 架构定义
skill_use("guide-plan")   # 变更生成
skill_use("guide-ship")   # 变更执行

# 方式 3: 配置文件
# .spec-workflow.json
{
  "interaction": {
    "mode": "hybrid",
    "loop": { "max_iterations": 100 },
    "menu": { "human_in_loop_nodes": [...] }
  }
}
```

### 系统架构

```
┌────────────────────────────────────────────────────────────┐
│                    用户接口层                                │
│  skill_use("loop")  |  skill_use("guide-*")  |  配置文件    │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                    Loop 引擎层                               │
│  scan → plan → execute → verify → adapt                    │
│  (Python: loop-engine.py)                                  │
└────────────────────────────────────────────────────────────┘
            ↓                        ↓                        ↓
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│  Detector 层  │          │  Action 层    │          │  状态管理层  │
│  (8 detectors)│         │  (7 actions)  │          │  (向量+事件) │
└──────────────┘          └──────────────┘          └──────────────┘
            ↓                        ↓                        ↓
┌────────────────────────────────────────────────────────────┐
│                    技能文件层                                │
│  guide-arch.md  |  guide-plan.md  |  guide-ship.md          │
│  propose.md     |  execute.md     |  status.md              │
└────────────────────────────────────────────────────────────┘
            ↓
┌────────────────────────────────────────────────────────────┐
│                    系统工具层                                │
│  git worktree  |  openspec CLI  |  Prometheus  |  cmake    │
└────────────────────────────────────────────────────────────┘
```

---

## 🗺️ 实施路线图

### Phase 1: 核心基础（2-3 周）

**目标**: 实现核心基础设施，向后兼容

- [ ] 实现 `skills/_lib/state_vector.py` (状态向量 + 记忆系统) — ADR-0006
- [ ] 实现 `skills/_lib/event_log.py` (事件流) — ADR-0006
- [ ] 实现 `skills/_lib/gate.py` (门控机制) — ADR-0007
- [ ] 实现 `.spec-workflow.json` 配置解析器 — ADR-0002
- [ ] 实现与 v1.x 状态文件的同步层 — ADR-0006

**交付物**:
- ✅ 状态向量、事件流、记忆系统可运行
- ✅ 门控机制可运行
- ✅ 配置文件支持（JSON + YAML）

### Phase 2: Loop 引擎核心（3 周）

**目标**: 实现 Loop 引擎 5 大构建块

- [ ] 实现 `skills/loop-engine.py` (主循环 - 5 大构建块) — ADR-0004
- [ ] 实现三种交互模式（loop/menu/hybrid） — ADR-0002
- [ ] 实现可视化流程图生成 — ADR-0004
- [ ] 实现设计先行阶段（目标/验证/控制） — ADR-0002
- [ ] 实现安全机制（迭代限制、断路器、震荡检测） — ADR-0004

**交付物**:
- ✅ Loop 引擎可运行
- ✅ 三种交互模式支持
- ✅ 安全机制验证通过

### Phase 3: 质量保障（2-3 周）

**目标**: 实现 Human-in-Loop 节点和审判委员会

- [ ] 实现 Human-in-Loop 节点管理（三种验证模式） — ADR-0005
- [ ] 实现 `skills/_lib/tribunal.py` (审判委员会) — ADR-0008
- [ ] 实现 `skills/_lib/sanitizer.py` (数据脱敏) — ADR-0008
- [ ] 实现多 Agent 协作（Planner/Executor/Verifier） — ADR-0004
- [ ] 添加关键节点菜单系统 — ADR-0005

**交付物**:
- ✅ Human-in-Loop 节点可运行
- ✅ 审判委员会可运行
- ✅ 多 Agent 协作支持

### Phase 4: 三阶段拆分（2 周）

**目标**: 将 guide-spec 拆分为 guide-arch + guide-plan

- [ ] 创建 `skills/guide-arch.md` (架构定义阶段) — ADR-0003
- [ ] 重命名 `skills/guide-spec.md` → `skills/guide-plan.md` — ADR-0003
- [ ] 更新 `skills/guide.md` 推荐器支持三阶段 — ADR-0003
- [ ] 实现阶段间交接文件 (`.arch-handoff.json`, `.plan-handoff.json`) — ADR-0003
- [ ] 集成门控机制到阶段切换 — ADR-0007

**交付物**:
- ✅ 三阶段状态机可运行
- ✅ 阶段间切换验证通过（门控）
- ✅ 向后兼容 (guide-spec 别名)

### Phase 5: 集成与测试（2 周）

**目标**: 完整集成测试，文档更新

- [ ] 添加 Loop 引擎单元测试
- [ ] 添加门控机制测试
- [ ] 添加审判委员会测试（多 agent 验证场景）
- [ ] 添加记忆系统测试（中断恢复、配置推荐）
- [ ] 更新 README.md 和 USAGE.md
- [ ] 编写迁移指南 (`docs/migration/v1-to-v2.md`)
- [ ] 编写 Loop 引擎教程

**交付物**:
- ✅ 测试覆盖率 ≥ 80%
- ✅ 文档完整
- ✅ 迁移工具可用

### Phase 6: Beta 发布（1 周）

**目标**: Beta 发布，收集反馈

- [ ] 发布 v2.0.0-beta
- [ ] 收集用户反馈
- [ ] 修复关键问题
- [ ] 性能优化

**交付物**:
- ✅ v2.0.0-beta 发布
- ✅ 用户反馈报告

### v2.1 候选

- [ ] 完整会话管理系统（ADR-0010 方案 B）
  - SessionManager（多进程并行）
  - DependencyScheduler（DAG 调度）
  - 进程间通信
- [ ] 定时循环（cron 表达式） — ADR-0009（候选）
- [ ] 事件触发（Git push、PR 创建） — ADR-0009（候选）
- [ ] 后台 Routines（持续监控） — ADR-0009（候选）

---

## 📊 迁移策略

### 向后兼容承诺

| v1.x 接口 | v2.x 行为 | 弃用时间 |
|-----------|----------|---------|
| `skill_use("guide-spec")` | 内部调用 `guide-arch` → `guide-plan` | v3.0 移除 |
| `skill_use("guide-ship")` | 保持不变 | 长期支持 |
| `skill_use("propose")` | 保持不变 | 长期支持 |
| `skill_use("execute")` | 保持不变 | 长期支持 |
| `.rddf/state/roadmap-state.json` | 通过同步层更新 | v3.0 移除 |

### 迁移路径

```
v1.x 用户
    ↓
安装 v2.0 (向后兼容)
    ↓
使用 guide-spec (自动路由到 arch + plan)
    ↓
尝试 skill_use("loop", {...})
    ↓
配置 .spec-workflow.json
    ↓
完全切换到 Loop 模式 (可选)
```

---

## 🎯 关键设计决策

### Q1: 为什么不完全移除菜单？

**A**: 菜单是 **human-in-loop 的核心机制**。架构决策（ADR 创建）、高风险操作（archive、cleanup）必须保留人工确认。完全自动化会导致：
- 架构治理缺失（跳过 ADR）
- 破坏性操作无确认（误删 worktree）
- 用户失去控制权

### Q2: 为什么用 Python 而不是纯 bash？

**A**: Loop 引擎需要：
- 复杂的状态管理（嵌套 JSON）
- 事件流处理（JSONL 解析）
- 安全机制（震荡检测、重试逻辑）
- 并发控制（文件锁）

这些在 bash 中实现复杂度高、易出错。Python 提供更丰富的标准库和更好的可维护性。

### Q3: 如何防止 Loop 死循环？

**A**: 四重安全机制：
1. **最大迭代次数**: 默认 100 次
2. **最大重试次数**: 默认 3 次
3. **状态震荡检测**: 最近 5 次状态 ≤ 2 种 → 报错
4. **超时控制**: 每个 action 最大 30 分钟

### Q4: 如何保证状态向量与现有文件一致？

**A**: 双向同步层：
```
状态向量 (主) ←→ 同步脚本 ←→ 现有状态文件 (兼容)
```
- 状态向量更新时，自动同步到 `.rddf/state/roadmap-state.json` 等
- 现有文件变更时，自动更新状态向量
- v3.x 移除现有文件，只保留状态向量

---

## 📈 预期收益

### 开发效率

| 场景 | v1.x 耗时 | v2.0 耗时 | 提升 |
|------|----------|----------|------|
| 创建 3 个 changes + worktrees | 15 分钟 | 2 分钟 | **7.5x** |
| 执行 10 个 work units | 30 分钟 | 10 分钟 | **3x** |
| 归档 5 个 changes | 20 分钟 | 5 分钟 | **4x** |

### 代码质量

- **自动化测试**: Loop 引擎自动验证每个 work unit
- **错误恢复**: 自动重试 + 自适应调整
- **架构治理**: ADR 强制确认，避免"跳过架构直接编码"

### 用户体验

- **灵活性**: 三种交互模式适应不同场景
- **可控性**: 关键节点 human-in-loop
- **可观测性**: 完整事件流，进度实时可见

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 概率 | 缓解策略 |
|------|------|------|---------|
| **学习成本高** | 中 | 高 | 提供教程、默认配置、迁移指南 |
| **向后兼容破坏** | 高 | 低 | 同步层、alias、v2.x 期间不移除旧接口 |
| **Loop 死循环** | 高 | 低 | 四重安全机制 |
| **状态不一致** | 中 | 中 | 同步层、校验、文件锁 |
| **性能下降** | 低 | 低 | 缓存、批量写入、异步事件流 |

---

## 📚 相关文档

- [ADR-0002](adr/ADR-0002-goal-driven-interaction-modes.md) — 目标驱动接口与交互模式配置（修订）
- [ADR-0003](adr/ADR-0003-three-phase-architecture.md) — 三阶段架构重构
- [ADR-0004](adr/ADR-0004-loop-engine-core-design.md) — Loop 引擎核心设计（修订）
- [ADR-0005](adr/ADR-0005-human-in-loop-nodes.md) — Human-in-Loop 节点定义（修订）
- [ADR-0006](adr/ADR-0006-state-vector-event-log.md) — 状态向量与事件流设计（修订）
- [ADR-0007](adr/ADR-0007-gate-mechanism.md) — 门控机制设计（新增）
- [ADR-0008](adr/ADR-0008-tribunal-committee.md) — 审判委员会设计（新增）
- [ADR-0010](adr/ADR-0010-multi-session-management.md) — 多会话管理与并行执行（新增，分阶段）
- [v2-adr-summary.md](v2-adr-summary.md) — ADR 完整总结报告
- [docs/audit/2026-06-05-workflow-audit.md](audit/2026-06-05-workflow-audit.md) — v1.1 审计报告

---

## 🚀 下一步行动

1. **确认 ADR 定稿**: 所有 9 个 ADR 已完成讨论和修订 ✅
2. **查看 ADR 总结报告**: [v2-adr-summary.md](v2-adr-summary.md) ✅
3. **创建 OpenSpec change**: `openspec new change v2-architecture-refactor`
4. **开始 Phase 1 实施**: 实现状态向量、事件流、门控机制
5. **每周进度审查**: 确保按计划推进

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: Phase 1 完成后

