# rdd-workflow v2.0 Loop 引擎使用指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **目标读者**: 所有用户（初学者到高级）

---

## 📋 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [三种交互模式](#三种交互模式)
- [设计先行阶段](#设计先行阶段)
- [5 大构建块](#5-大构建块)
- [多 Agent 协作](#多-agent-协作)
- [门控机制](#门控机制)
- [Human-in-Loop 节点](#human-in-loop-节点)
- [记忆系统](#记忆系统)
- [故障排查](#故障排查)
- [最佳实践](#最佳实践)

---

## 概述

rdd-workflow v2.0 引入了全新的 **Loop 引擎**，从状态机驱动升级到自主运行的 AI 编程范式。

### 核心特性

| 特性 | 说明 | 优势 |
|------|------|------|
| **三种交互模式** | loop / menu / hybrid | 适应不同场景 |
| **设计先行阶段** | 目标/验证/控制设计 | 防止偏离目标 |
| **5 大构建块** | Goal → Plan → Execute → Verify → Adapt | 自主运行 |
| **多 Agent 协作** | Planner → Executor → Verifier | 提高质量 |
| **门控机制** | 阶段切换前检查清单 | 保证质量 |
| **记忆系统** | 中断恢复、配置推荐 | 持续学习 |

---

## 快速开始

### 1. 安装 v2.0

```bash
npm install rdd-workflow@2.0.0
```

### 2. 创建配置文件

```bash
# 最小配置
cat > .rddf.json << 'EOF'
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid"
  }
}
EOF
```

### 3. 运行 Loop

```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "hybrid"
})
```

### 4. 观察执行

```
🚀 Loop 引擎启动

=== Loop 执行流程图 ===

目标: complete all pending changes

┌─────────────────────────────────────────────────────────────┐
│  Arch 阶段 (架构定义)                                        │
│  ├─ ADR 创建 ─────→ [门控: ADR ≥ 1]                         │
│  ├─ Roadmap 定义 ──→ [门控: roadmap.md 存在]                │
│  └─ 架构差距分析 ──→ [门控: pending_gaps == 0]              │
└─────────────────────────────────────────────────────────────┘
    ↓ (门控通过)
┌─────────────────────────────────────────────────────────────┐
│  Plan 阶段 (变更生成)                                        │
│  ├─ 扫描 change 候选 ─→ [门控: changes.count ≥ 1]           │
│  ├─ 生成 artifacts ──→ [门控: .openspec.yaml 存在]          │
│  └─ 依赖分析 ────────→ [门控: deps_analysis 完成]           │
└─────────────────────────────────────────────────────────────┘
    ↓ (门控通过)
┌─────────────────────────────────────────────────────────────┐
│  Ship 阶段 (变更执行)                                        │
│  ├─ 创建 worktree ───→ [门控: worktree 创建成功]            │
│  ├─ 生成 Prometheus ─→ [门控: plan 文件存在]                │
│  ├─ 执行 work units ─→ [门控: 100% 完成]                    │
│  └─ 归档 change ─────→ [门控: archive 成功]                 │
└─────────────────────────────────────────────────────────────┘
    ↓ (门控通过)
✅ 目标达成: complete all pending changes

控制参数:
  - 最大迭代次数: 100
  - 最大重试次数: 3
  - 断路器: 启用

📊 当前状态: 2 active changes, 0 worktrees

Iteration 1: Scanning state...
Iteration 1: Found 2 active changes: add-auth, add-user-profile
Iteration 1: Generating plan...
Iteration 1: Entering arch phase...

[Arch 阶段开始]
✅ Creating ADR for architecture decisions...
✅ Defining roadmap...
✅ Analyzing architecture gaps...

[门控检查: arch_done]
✅ adr_exists: PASS (3 ADRs found)
✅ roadmap_defined: PASS (roadmap.md exists)
✅ gap_analysis_complete: PASS (0 pending gaps)

[Arch 阶段完成 → 切换到 Plan 阶段]
...
```

---

## 三种交互模式

### 模式 1: loop（全自动）

**适用场景**: CI/CD、批量处理、高置信度任务

```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "loop"
})
```

**行为**:
- ✅ 自动执行所有阶段
- ✅ 仅在错误时暂停
- ✅ 适合无人值守运行

**配置**:
```json
{
  "interaction": {
    "mode": "loop"
  },
  "loop": {
    "max_iterations": 50,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "abort"
    }
  }
}
```

---

### 模式 2: menu（全手动）

**适用场景**: 学习阶段、探索性任务、完全控制

```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "menu"
})
```

**行为**:
- ✅ 每个决策点都显示菜单
- ✅ 用户完全控制流程
- ✅ 适合学习和调试

**菜单示例**:
```
📋 请选择下一步操作:

1. 进入 Arch 阶段 (定义架构)
2. 进入 Plan 阶段 (生成变更)
3. 进入 Ship 阶段 (执行变更)
4. 查看当前状态
5. 查看帮助
6. 中止

选择 [1-6]:
```

**配置**:
```json
{
  "interaction": {
    "mode": "menu"
  }
}
```

---

### 模式 3: hybrid（半自动，推荐）

**适用场景**: 日常开发、平衡自动化和控制权

```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "hybrid"
})
```

**行为**:
- ✅ 自动执行常规操作
- ✅ 关键节点显示菜单（Human-in-Loop）
- ✅ 平衡效率和安全性

**关键节点**（可配置）:
- `arch.adr_create`: ADR 创建
- `ship.archive_confirm`: 归档确认
- `ship.execute_error`: 错误处理

**配置**:
```json
{
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      "arch.adr_create",
      "ship.archive_confirm",
      "ship.execute_error"
    ]
  }
}
```

---

## 设计先行阶段

Loop 启动前，先完成三阶段设计：

### 1. 目标设计

明确产出物和完成标准：

```json
{
  "goal_design": {
    "description": "complete all pending changes",
    "success_criteria": [
      "active_changes.count == 0",
      "worktrees.count == 0",
      "roadmap.completion >= 0.8"
    ],
    "deliverables": [
      "archived changes in openspec/changes/archive/",
      "updated roadmap.md with completion status"
    ]
  }
}
```

**示例**:
```
🎯 目标设计

描述: complete all pending changes

完成标准:
  ✅ active_changes.count == 0
  ✅ worktrees.count == 0
  ✅ roadmap.completion >= 0.8

预期产出物:
  📄 archived changes in openspec/changes/archive/
  📄 updated roadmap.md with completion status

是否继续？[y/n]:
```

---

### 2. 验证设计

确定检查机制：

```json
{
  "verification_design": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "review_criteria": [
      "all tests pass",
      "no merge conflicts",
      "ADR compliance check"
    ]
  }
}
```

**验证方法**:
- `human`: 人工审核
- `multi_model`: 多 agent 交叉验证
- `script`: 脚本验证

---

### 3. 控制设计

设置刹车机制：

```json
{
  "control_design": {
    "max_iterations": 100,
    "max_retries": 3,
    "stagnation_threshold": 5,
    "error_budget": 0.1,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "escalate_to_human"
    }
  }
}
```

**控制参数**:
- `max_iterations`: 最大迭代次数
- `max_retries`: 最大重试次数
- `stagnation_threshold`: 无进展阈值
- `error_budget`: 错误预算
- `circuit_breaker`: 断路器

---

## 5 大构建块

Loop 引擎的核心循环：

```python
while not goal_achieved():
    # Block 1: Goal
    1. verify_goal()           # 验证目标是否达成
    
    # Block 2: Plan
    2. scan_state()            # 扫描当前状态
    3. generate_plan()         # 生成执行计划
    
    # Block 3: Execute
    4. check_human_nodes()     # 检查是否需要人工确认
    5. execute_plan()          # 执行计划
    
    # Block 4: Verify（集成门控）
    6. verify_results()        # 验证执行结果
    7. gate_check()            # 门控检查
    
    # Block 5: Adapt
    8. update_state()          # 更新状态向量
    9. adapt()                 # 自适应调整（错误恢复）
```

### 构建块 1: Goal（目标验证）

```
🎯 Goal: 检查目标是否达成

当前状态:
  - active_changes: 0
  - worktrees: 0
  - roadmap.completion: 0.85

✅ 目标达成！
  ✅ active_changes.count == 0
  ✅ worktrees.count == 0
  ✅ roadmap.completion >= 0.8

Loop 完成，总迭代次数: 15
```

---

### 构建块 2: Plan（计划生成）

```
📋 Plan: 扫描状态并生成计划

[扫描状态]
✅ Found 2 active changes: add-auth, add-user-profile
✅ Found 0 worktrees
✅ Roadmap completion: 45%

[生成计划]
Actions:
  1. Enter arch phase (create ADRs, define roadmap)
  2. Enter plan phase (generate artifacts)
  3. Enter ship phase (execute changes)

计划生成完成，执行 Actions...
```

---

### 构建块 3: Execute（执行）

```
⚙️ Execute: 执行计划

[Action 1: Enter arch phase]
✅ Creating ADR-0010: Multi-session management
✅ Updating roadmap.md
✅ Architecture gap analysis complete

[Action 2: Enter plan phase]
✅ Scanning change candidates...
✅ Generating proposal for add-auth...
✅ Generating design for add-auth...
✅ Generating tasks for add-auth...

[Action 3: Enter ship phase]
✅ Creating worktree for add-auth...
✅ Generating Prometheus plan...
✅ Executing work units...
  [████████████████████████████████████████] 100% (15/15)

执行完成！
```

---

### 构建块 4: Verify（验证 + 门控）

```
✅ Verify: 验证结果

[验证执行结果]
✅ ADR created: ADR-0010
✅ Roadmap updated: completion 45% → 60%
✅ Work units completed: 15/15

[门控检查: arch_done]
✅ adr_exists: PASS (4 ADRs found)
✅ roadmap_defined: PASS (roadmap.md exists)
✅ gap_analysis_complete: WARNING (1 pending gap)
  ⚠️ 建议完成架构差距分析

门控通过（1 warning），允许切换阶段
```

---

### 构建块 5: Adapt（自适应）

```
🔄 Adapt: 自适应调整

[更新状态向量]
✅ Updated state-vector.json
✅ Recorded event: phase_transition (arch → plan)

[检查是否需要调整]
ℹ️ No adaptation needed

准备下一次迭代...
```

---

## 多 Agent 协作

在 loop 模式下，可以使用多 Agent 协作：

### 配置

```json
{
  "interaction": {
    "mode": "loop"
  },
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    }
  }
}
```

### 协作流程

```
Planner Agent → Executor Agent → Verifier Agent
     ↓              ↓                ↓
  制定计划      执行任务        验证结果
```

**示例**:

```
🤖 多 Agent 协作开始

[Planner Agent]
📋 Planning: Implement add-auth change
  - Analyze requirements
  - Generate implementation plan
  - Define success criteria

[Executor Agent]
⚙️ Executing: add-auth
  - Create worktree
  - Generate code
  - Run tests
  - Commit changes

[Verifier Agent]
✅ Verifying: add-auth
  - Check tests: PASS (15/15 passed)
  - Check merge conflicts: PASS (none)
  - Check ADR compliance: PASS
  - Code quality score: 0.92

[综合判定]
✅ Executor score: 0.90
✅ Reviewer score: 0.92
✅ Final score: 0.91 (权重: 0.4/0.6)

✅ 验证通过！
```

---

## 门控机制

阶段切换前必须通过检查清单：

### 门控检查项

| 门控 | 检查项 | 严重度 | 说明 |
|------|-------|-------|------|
| **arch_done** | ADR ≥ 1 | error | 必须至少创建 1 个 ADR |
| | roadmap 存在 | error | 必须定义 roadmap |
| | 差距分析完成 | warning | 建议完成 |
| **plan_done** | changes committed | error | 所有 changes 必须提交 |
| | artifacts 完整 | error | .openspec.yaml 必须存在 |
| | 依赖分析完成 | warning | 建议完成 |
| **ship_done** | worktrees 空 | error | 所有 worktrees 必须清理 |
| | archive 空 | error | 所有 changes 必须归档 |
| | 测试通过 | error | 所有测试必须通过 |

### 门控失败处理

```
❌ 门控检查失败: arch_done

失败项:
  ❌ adr_exists: FAIL (0 ADRs found, expected ≥ 1)
  ❌ roadmap_defined: FAIL (roadmap.md not found)

请选择:
  1. 返回 Arch 阶段修复（推荐）
  2. 查看详细信息
  3. 强制切换（不推荐，需确认）
  4. 中止

选择 [1-4]:
```

---

## Human-in-Loop 节点

关键节点需要人工确认：

### 节点列表

| 节点 | 阶段 | 默认验证模式 | 说明 |
|------|------|------------|------|
| `arch.adr_create` | arch | human | ADR 创建必须人工确认 |
| `arch.roadmap_define` | arch | human | Roadmap 定义必须人工确认 |
| `plan.change_select` | plan | script | Change 选择可自动验证 |
| `plan.propose_confirm` | plan | multi_model | Proposal 确认多模型验证 |
| `ship.archive_confirm` | ship | multi_model | 归档前多模型验证 |
| `ship.cleanup_confirm` | ship | script | 清理操作脚本验证 |
| `ship.execute_error` | ship | human | 执行错误必须人工处理 |

### 验证模式

**模式 1: human（人工审核）**

```
📋 Human-in-Loop: arch.adr_create

即将创建 ADR:
  - Title: Multi-session management
  - Status: Proposed
  - Dependencies: ADR-0006

是否继续？[y/n]:
```

**模式 2: multi_model（多模型验证）**

```
🤖 Multi-model verification: ship.archive_confirm

[Executor Agent]
✅ Score: 0.90
✅ Strengths: All tests pass, no merge conflicts
✅ Weaknesses: Minor code style issues

[Reviewer Agent]
✅ Score: 0.92
✅ Unique concerns: Consider adding more comments
✅ Confidence: 0.95

[综合判定]
✅ Final score: 0.91
✅ Recommendation: PASS

归档是否继续？[y/n]:
```

**模式 3: script（脚本验证）**

```
📜 Script verification: plan.change_select

Running: .rdd-workflow/scripts/verification/check_changes.py
✅ Changes format: PASS
✅ Artifacts complete: PASS
✅ Dependencies analyzed: PASS

验证通过，自动继续
```

---

## 记忆系统

Loop 引擎从历史执行中学习：

### 中断恢复

```
🔄 恢复执行: add-auth

📊 历史执行记录:
  - 上次执行: 2026-06-22T10:00:00Z
  - 上次结果: 失败
  - 失败原因: test_failure on unit 12
  - 已迭代: 5 次
  - 已重试: 1 次

💡 建议:
  - Merge 前先运行完整测试套件
  - 建议增加 max_iterations 到 50

📊 基于历史执行，推荐配置:
  - max_iterations: 50
  - max_retries: 3
  - verification_method: multi_model

是否使用推荐配置？[y/n]:
```

---

### 重复失败警告

```
⚠️ 警告: change 'refactor-db' 已失败 3 次

📊 学习到的洞察:
  - 问题: Merge 后测试失败频率高
  - 建议: Merge 前先运行完整测试套件
  - 置信度: 85%
  - 出现次数: 5

请选择:
  1. 继续执行（应用推荐配置）
  2. 查看失败详情
  3. 暂停此 change，先处理其他
  4. 中止

选择 [1-4]:
```

---

### 配置推荐

```
📊 基于历史执行，推荐配置

相似目标的历史执行: 5 次
成功执行: 4 次 (80% 成功率)

推荐配置:
  - max_iterations: 50 (基于平均值 33 * 1.5)
  - max_retries: 3 (基于平均值 1.5 * 2)
  - parallel_limit: 3
  - verification_method: multi_model

是否使用推荐配置？[y/n]:
```

---

## 故障排查

### 问题 1: Loop 不启动

**症状**: `skill_use("loop", ...)` 无响应

**解决**:
```bash
# 1. 检查配置
cat .rddf.json | jq '.'

# 2. 检查状态向量
cat .rddf/state/state-vector.json | jq '.version'  # 应该是 "2.0"

# 3. 查看事件流
tail .rddf/state/event-log.jsonl | jq '.'
```

---

### 问题 2: 门控检查失败

**症状**: 阶段切换时报 "Gate check failed"

**解决**:
```bash
# 1. 查看失败详情
cat .rddf/state/event-log.jsonl | jq 'select(.type == "gate_failed")'

# 2. 检查缺失项
# 例如：arch_done 失败
ls docs/adr/  # 检查 ADR
cat roadmap.md  # 检查 roadmap

# 3. 修复后重试
```

---

### 问题 3: 多模型验证失败

**症状**: "Verification failed, scores diverge"

**解决**:
```bash
# 1. 查看验证结果
cat .rddf/state/event-log.jsonl | jq 'select(.type == "verification_completed")'

# 2. 检查分歧原因
# Executor score: 0.9, Reviewer score: 0.5 → 分歧 0.4

# 3. 选项:
# - 升级到人工审核
# - 调整权重配置
# - 更换 reviewer agent
```

---

### 问题 4: 记忆系统不工作

**症状**: 中断后无法恢复

**解决**:
```bash
# 1. 检查记忆系统是否启用
cat .rddf.json | jq '.memory.enabled'  # 应该是 true

# 2. 检查状态向量中的记忆字段
cat .rddf/state/state-vector.json | jq '.memory'

# 3. 检查执行记录
cat .rddf/state/state-vector.json | jq '.memory.executions'
```

---

## 最佳实践

### 1. 选择合适的交互模式

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 首次使用 | menu | 学习流程 |
| 日常开发 | hybrid | 平衡效率和控制 |
| CI/CD | loop | 全自动 |
| 高风险操作 | hybrid | 关键节点确认 |

---

### 2. 配置门控检查

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "adr_exists",
        "condition": "arch_side.adr.count >= 1",
        "severity": "error"
      }
    ]
  }
}
```

---

### 3. 启用记忆系统

```json
{
  "memory": {
    "enabled": true,
    "auto_suggest_config": true
  }
}
```

---

### 4. 使用便携规范

```yaml
# .rdd-workflow/loops/complete-changes.yaml
version: "2.0"
name: "complete-all-changes"

goal:
  description: "complete all pending changes"
  success_criteria:
    - "active_changes.count == 0"
```

---

### 5. 监控事件流

```bash
# 实时监控
tail -f .rddf/state/event-log.jsonl | jq '.'

# 查询特定事件
cat .rddf/state/event-log.jsonl | jq 'select(.type == "gate_failed")'

# 生成进度报告
rdd-workflow report
```

---

## 下一步

- **查看配置 Schema**: [v2-config-schema.md](v2-config-schema.md)
- **查看迁移指南**: [migration/v1-to-v2.md](migration/v1-to-v2.md)
- **查看 ADR 总结**: [v2-adr-summary.md](v2-adr-summary.md)
- **查看完整 ADR**: `docs/adr/` 目录

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

