# ADR-0002: 目标驱动接口与交互模式可配置化

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **替代**: ADR-0001 §3 (菜单驱动接口)

## Context

spec-workflow v1.x 采用**菜单驱动**的用户交互模式：用户在每个 phase 面对数字菜单 (1/2/3/i)，通过选择菜单项推进工作流。这种模式在 v1.0-v1.1 的审计中暴露出三类问题：

1. **Human-in-Loop 缺失灵活性**: 菜单是固定的，用户无法跳过不需要的骤或自定义关键决策点
2. **自动化程度低**: 即使用户希望全自动执行（如 CI/CD 场景），仍需手动选择菜单项
3. **AI 助手兼容性差**: AI 编程助手面对 "i. 其他输入" 菜单项时行为未定义（P3-3 已部分修复）

同时，**Loop 驱动范式**（目标声明 → 自动编排 → 执行 → 反馈）在 AI 编程领域已被验证（GitHub Copilot Workspace、Cursor Agent、OpenHands），但完全移除菜单会失去 human-in-loop 的控制权。

**约束**:
- **不能完全移除菜单**: 菜单是 human-in-loop 的核心机制，必须在关键节点保留
- **向后兼容**: 现有 `skill_use("guide-spec")` 和 `skill_use("guide-ship")` 接口必须继续有效
- **可配置**: 用户应能根据场景选择交互模式（全自动 / 半自动 / 纯手动）

**相关方**:
- 开发者：希望快速自动化重复任务
- 架构师：希望在关键决策点（如 ADR 创建、roadmap 定义）保留人工审查
- AI 助手：需要明确的接口规范，而非解析菜单文本

## Decision

我们采用**三层交互模式可配置架构**，用户通过配置文件或环境变量选择交互模式：

```bash
# 配置方式 1: 环境变量
export SPEC_WORKFLOW_INTERACTION_MODE="loop|menu|hybrid"

# 配置方式 2: 项目级配置 (.spec-workflow.json)
{
  "interaction": {
    "mode": "hybrid",
    "loop_config": { ... },
    "menu_config": { ... }
  }
}

# 配置方式 3: 调用时参数
skill_use("loop", {
  "goal": "complete all changes",
  "mode": "hybrid"  # loop | menu | hybrid
})
```

### 三种交互模式定义

| 模式 | 适用场景 | 行为 | Human-in-Loop 节点 |
|------|---------|------|-------------------|
| **loop** (自动编排) | CI/CD、批量处理、明确目标 | 声明目标后自动执行全流，Loop 引擎自动决策 | 仅在错误/冲突时暂停 |
| **menu** (菜单驱动) | 学习阶段、探索性工作、复杂决策 | 保持现有 v1.x 菜单系统，每个 phase 显示选项 | 所有决策点 |
| **hybrid** (混合模式) | 日常开发（推荐） | Loop 引擎自动执行常规步骤，在**关键节点**显示菜单询问用户 | 预定义的关键节点（见下方） |

### Hybrid 模式关键节点定义

在 hybrid 模式下，以下节点**强制 human-in-loop**（显示菜单）：

| 阶段 | 关键节点 | 菜单内容 | 自动跳过条件 |
|------|---------|---------|------------|
| **arch** | ADR 创建确认 | 显示 ADR 草案，确认/编辑/跳过 | 无（必须确认） |
| **arch** | Roadmap 定义 | 显示 roadmap 模板，选择/自定义 | 已有 roadmap.md |
| **plan** | Change 选择 | 显示待处理 changes，选择要处理的 | `auto_select_changes: true` |
| **plan** | Worktree 创建前 | 确认 worktree 配置（分支名、并行数） | `auto_create_worktree: true` |
| **ship** | Archive 前 | 确认 merge + archive 操作 | `auto_archive: true` |
| **ship** | Cleanup 前 | 显示待删除 worktrees/branches，确认 | `auto_cleanup: true` |
| **任意阶段** | 错误/冲突 | 显示错误详情，提供修复建议 | `auto_retry: true` (最多 3 次) |

### 设计先行阶段 (Design-First Phase)

在 Loop 引擎执行前（首次或目标变更时），引导用户完成三阶段设计：

#### 1. 目标设计 (Goal Design)

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
    ],
    "constraints": {
      "max_parallel_worktrees": 3,
      "require_tests": true
    }
  }
}
```

**关键原则**: 不是"做一个更好的登录页"，而是"转化率提升 20%"

#### 2. 验证设计 (Verification Design)

确定谁来检查结果：

```json
{
  "verification_design": {
    "method": "multi_model",  // human | script | multi_model
    "execution_model": "claude-sonnet-4",
    "review_model": "gpt-4o",
    "review_criteria": [
      "all tests pass",
      "no merge conflicts",
      "ADR compliance check"
    ],
    "data_privacy": {
      "sanitize_before_cross_vendor": true,
      "require_explicit_consent": true
    }
  }
}
```

**验证模式**:
- `human`: 人工审核（适合架构决策）
- `script`: 自动化脚本（适合测试验证）
- `multi_model`: 多模型交叉验证（适合代码质量检查）

#### 3. 控制设计 (Control Design)

设置"刹车"机制：

```json
{
  "control_design": {
    "max_iterations": 100,
    "max_retries_per_action": 3,
    "stagnation_threshold": 5,
    "error_budget": 0.1,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "escalate_to_human"
    },
    "timeout_per_action": 1800
  }
}
```

**控制参数**:
- `max_iterations`: 最大迭代次数
- `max_retries_per_action`: 每个 action 最大重试次数
- `stagnation_threshold`: 连续无进展次数阈值
- `error_budget`: 允许的错误比例
- `circuit_breaker`: 断路器（连续失败时自动升级）

### 便携规范支持 (loop.yaml)

同时支持 JSON 和 YAML 格式。`loop.yaml` 是人类可读的循环规范，可纳入版本控制：

```yaml
# .spec-workflow/loops/complete-all-changes.yaml
version: "2.0"
name: "complete-all-changes"
description: "自动完成所有待处理 changes"

design:
  goal:
    description: "complete all pending changes"
    success_criteria:
      - "active_changes.count == 0"
      - "roadmap.completion >= 0.8"
  
  verification:
    method: "multi_model"
    execution_model: "claude-sonnet-4"
    review_model: "gpt-4o"
  
  control:
    max_iterations: 100
    max_retries: 3
    circuit_breaker:
      enabled: true
      consecutive_failures: 3

interaction:
  mode: "hybrid"
  human_in_loop_nodes:
    - "arch.adr_create"
    - "ship.archive_confirm"
```

**存储位置**: `.spec-workflow/loops/<name>.yaml`
- ✅ 集中管理，支持多个 loop 配置
- ✅ 可纳入版本控制，团队共享最佳实践
- ✅ 提供 AI 辅助生成，降低使用门槛

### 配置文件加载优先级

| 优先级 | 配置来源 | 示例 | 适用场景 |
|--------|---------|------|---------|
| 1 (最高) | 命令行参数 | `skill_use("loop", {goal: "..."})` | 临时覆盖 |
| 2 | loop.yaml | `.spec-workflow/loops/complete-all-changes.yaml` | 项目级便携规范 |
| 3 | .spec-workflow.json | `/path/to/project/.spec-workflow.json` | 项目级配置 |
| 4 | 用户级配置 | `~/.spec-workflow/config.json` | 用户全局默认 |
| 5 (最低) | 内置默认值 | Loop 引擎硬编码 | 无配置时回退 |

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "loop": {
      "max_iterations": 100,
      "max_retries": 3,
      "parallel_limit": 3,
      "auto_select_changes": false,
      "auto_create_worktree": false,
      "auto_archive": false,
      "auto_cleanup": false,
      "auto_retry": true
    },
    "menu": {
      "show_tips": true,
      "confirm_destructive": true,
      "human_in_loop_nodes": [
        "arch.adr_create",
        "arch.roadmap_define",
        "plan.change_select",
        "ship.archive_confirm",
        "ship.cleanup_confirm"
      ]
    }
  },
  "goals": {
    "default": "complete all pending changes",
    "shortcuts": {
      "quick-plan": "create worktrees for all changes and generate plans",
      "quick-execute": "execute all pending worktrees",
      "quick-archive": "archive all completed changes"
    }
  }
}
```

### 影响范围

- **In Scope**: 
  - 新增 `skills/loop-engine.md` (Loop 引擎)
  - 新增 `.spec-workflow.json` 配置文件支持
  - 修改 `skills/guide-spec.md`、`skills/guide-ship.md` 支持三种模式
  - 新增 `skills/_lib/interaction.sh` (交互模式管理)
  
- **Out Scope**:
  - 不改变现有 phase 逻辑（setup/propose/deps/plan/execute/archive）
  - 不改变状态文件格式（`.zcf/` 目录结构保持）
  - 不改变子技能接口（propose/execute/status 保持独立）

### 备选方案

| 备选 | 理由 |
|------|------|
| **完全替换为 Loop** | 拒绝：失去 human-in-loop 控制权，违反用户明确需求 |
| **保留纯菜单** | 拒绝：无支持自动化场景，AI 助手兼容性差 |
| **环境变量切换** | 接受：作为配置方式之一，与 JSON 配置并存 |
| **hybrid 模式** | 接受：平衡自动化与控制权，作为推荐默认模式 |

## Consequences

### 正面

- **灵活性**: 用户根据场景选择交互模式（CI/CD 用 loop，日常用 hybrid，学习用 menu）
- **向后兼容**: 现有菜单接口完全保留，`skill_use("guide-spec")` 行为不变
- **AI 友好**: Loop 模式提供声明式接口，AI 助手可直接调用
- **Human-in-Loop 保障**: hybrid 模式在关键节点强制人工确认，避免自动化风险
- **可观测性**: 配置文件明确记录交互偏好，便于团队共享

### 负面 / 风险

- **配置复杂度**: 新增配置文件，用户需要学习 `.spec-workflow.json` 格式
  - **缓解**: 提供 `spec-workflow init` 命令生成默认配置
- **模式切换成本**: 在不同模式间切换可能需要重新理解工作流
  - **缓解**: 提供 `spec-workflow status` 显示当前模式和可用操作
- **测试矩阵扩大**: 需要测试 3 种模式 × N 个 phase 的组合
  - **缓解**: 优先测试 hybrid 模式（推荐默认），其他模式用集成测试覆盖

### 后续待办

- [ ] 实现 `.spec-workflow.json` 配置解析器 (`skills/_lib/config.sh`)
- [ ] 实现 `skills/loop-engine.md` (Loop 引擎核心)
- [ ] 实现 `skills/_lib/interaction.sh` (交互模式管理)
- [ ] 更新 `guide-spec.md` 和 `guide-ship.md` 支持三种模式
- [ ] 添加配置验证 (JSON Schema)
- [ ] 添加配置示例到 `examples/` 目录
- [ ] 更新 README.md 和 USAGE.md 文档

## References

- ADR-0001 — spec 端/ship 端状态机分离（原始菜单驱动架构）
- `docs/audit/2026-06-05-workflow-audit.md` §15.3 — "i. 其他输入" 无 case 处理
- `skills/guide-spec.md` — 现有 spec 端菜单系统
- `skills/guide-ship.md` — 现有 ship 端菜单系统
- `skills/_lib/worktree.sh` — 可复用的 worktree 操作（Loop 引擎将调用）
- GitHub Copilot Workspace — 目标驱动自动编排参考
- Cursor Agent — human-in-loop 节点设计参考

