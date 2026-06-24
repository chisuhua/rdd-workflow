# spec-workflow v2.0 配置 Schema 参考

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **配置文件**: `.spec-workflow.json` + `loop.yaml`

---

## 📋 目录

- [概述](#概述)
- [配置优先级](#配置优先级)
- [.spec-workflow.json Schema](#spec-workflowjson-schema)
- [loop.yaml Schema](#loopyaml-schema)
- [配置示例库](#配置示例库)
- [验证工具](#验证工具)

---

## 概述

spec-workflow v2.0 支持两种配置格式：

| 格式 | 文件 | 用途 | 人类可读 | 版本控制 |
|------|------|------|---------|---------|
| **JSON** | `.spec-workflow.json` | 机器配置，完整 Schema | ❌ 部分 | ✅ 是 |
| **YAML** | `loop.yaml` | 便携规范，人类可读 | ✅ 是 | ✅ 是 |

---

## 配置优先级

配置加载优先级（从高到低）：

```
1. skill_use() 参数（运行时覆盖）
    ↓
2. loop.yaml（便携规范）
    ↓
3. .spec-workflow.json（项目配置）
    ↓
4. 环境变量（全局配置）
    ↓
5. 默认值（内置）
```

### 示例

```bash
# 1. 默认值
skill_use("loop", {goal: "complete changes"})
# 使用 .spec-workflow.json 或默认值

# 2. 指定 loop.yaml
skill_use("loop", {
  goal: "complete changes",
  config_file: ".spec-workflow/loops/quick.yaml"
})

# 3. 运行时覆盖
skill_use("loop", {
  goal: "complete changes",
  mode: "loop",  # 覆盖配置文件中的 mode
  max_iterations: 50  # 覆盖配置文件中的 max_iterations
})
```

---

## .spec-workflow.json Schema

### 完整 Schema

```json
{
  "$schema": "https://spec-workflow.dev/schemas/config-v2.json",
  "version": "2.0",
  
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [...]
  },
  
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "parallel_limit": 3,
    "circuit_breaker": {...}
  },
  
  "verification": {
    "method": "human",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "weights": {...},
    "divergence_threshold": 0.4
  },
  
  "memory": {
    "enabled": true,
    "retention_days": 90,
    "auto_suggest_config": true
  },
  
  "gates": {
    "arch_done": [...],
    "plan_done": [...],
    "ship_done": [...]
  }
}
```

### 字段详解

#### `version` (必需)

- **类型**: `string`
- **枚举**: `"2.0"`
- **说明**: 配置文件版本

```json
{
  "version": "2.0"
}
```

---

#### `interaction` (必需)

- **类型**: `object`
- **说明**: 交互模式配置

**字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `mode` | `string` | ✅ | `"hybrid"` | 交互模式（loop/menu/hybrid） |
| `human_in_loop_nodes` | `array` | ❌ | `[]` | Human-in-Loop 节点列表 |

**mode 枚举值**:

| 值 | 说明 | 适用场景 |
|---|------|---------|
| `"loop"` | 全自动 | CI/CD、批量处理 |
| `"menu"` | 全手动 | 学习阶段、探索 |
| `"hybrid"` | 半自动（推荐） | 日常开发 |

**human_in_loop_nodes 格式**:

```json
{
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      // 简单格式（字符串）
      "arch.adr_create",
      "ship.archive_confirm",
      
      // 完整格式（对象）
      {
        "node": "plan.change_select",
        "verification_mode": "script",
        "skip_if": "auto_select_changes",
        "script": ".spec-workflow/scripts/verification/check_changes.py"
      },
      {
        "node": "ship.archive_confirm",
        "verification_mode": "multi_model",
        "skip_if": "auto_archive",
        "executor_agent": "coder",
        "reviewer_agent": "reviewer",
        "review_criteria": [
          "all tests pass",
          "no merge conflicts"
        ]
      }
    ]
  }
}
```

**human_in_loop_nodes 字段**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `node` | `string` | ✅ | 节点 ID |
| `verification_mode` | `string` | ✅ | 验证模式（human/multi_model/script） |
| `skip_if` | `string` | ❌ | 跳过条件 |
| `script` | `string` | ❌ | 验证脚本路径（script 模式） |
| `executor_agent` | `string` | ❌ | 执行 agent（multi_model 模式） |
| `reviewer_agent` | `string` | ❌ | 审核 agent（multi_model 模式） |
| `review_criteria` | `array` | ❌ | 审核标准（multi_model 模式） |

---

#### `loop` (必需)

- **类型**: `object`
- **说明**: Loop 引擎配置

**字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `max_iterations` | `integer` | ❌ | `100` | 最大迭代次数 |
| `max_retries` | `integer` | ❌ | `3` | 最大重试次数 |
| `parallel_limit` | `integer` | ❌ | `3` | 最大并行 worktrees 数量 |
| `circuit_breaker` | `object` | ❌ | - | 断路器配置 |

**circuit_breaker 字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | `boolean` | ❌ | `true` | 是否启用断路器 |
| `consecutive_failures` | `integer` | ❌ | `3` | 连续失败次数阈值 |
| `action` | `string` | ❌ | `"escalate_to_human"` | 触发后的动作 |

**action 枚举值**:

| 值 | 说明 |
|---|------|
| `"escalate_to_human"` | 升级到人工 |
| `"abort"` | 中止 Loop |
| `"retry"` | 重试 |

**示例**:

```json
{
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "parallel_limit": 3,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "escalate_to_human"
    }
  }
}
```

---

#### `verification` (可选)

- **类型**: `object`
- **说明**: 验证配置（审判委员会）

**字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `method` | `string` | ❌ | `"human"` | 验证方法 |
| `executor_agent` | `string` | ❌ | `"coder"` | 执行 agent |
| `reviewer_agent` | `string` | ❌ | `"reviewer"` | 审核 agent |
| `weights` | `object` | ❌ | - | 权重配置 |
| `divergence_threshold` | `number` | ❌ | `0.4` | 分歧阈值 |

**method 枚举值**:

| 值 | 说明 |
|---|------|
| `"human"` | 人工审核 |
| `"multi_model"` | 多 agent 交叉验证 |
| `"script"` | 脚本验证 |

**weights 字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `executor` | `number` | ❌ | `0.4` | 执行 agent 权重 |
| `reviewer` | `number` | ❌ | `0.6` | 审核 agent 权重 |

**示例**:

```json
{
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    },
    "divergence_threshold": 0.4
  }
}
```

---

#### `memory` (可选)

- **类型**: `object`
- **说明**: 记忆系统配置

**字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | `boolean` | ❌ | `true` | 是否启用记忆系统 |
| `retention_days` | `integer` | ❌ | `90` | 记忆保留天数 |
| `auto_suggest_config` | `boolean` | ❌ | `true` | 自动推荐配置 |

**示例**:

```json
{
  "memory": {
    "enabled": true,
    "retention_days": 90,
    "auto_suggest_config": true
  }
}
```

---

#### `gates` (可选)

- **类型**: `object`
- **说明**: 门控配置（自定义检查清单）

**字段**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `arch_done` | `array` | ❌ | Arch 阶段门控检查项 |
| `plan_done` | `array` | ❌ | Plan 阶段门控检查项 |
| `ship_done` | `array` | ❌ | Ship 阶段门控检查项 |

**检查项格式**:

```json
{
  "name": "adr_exists",
  "condition": "arch_side.adr.count >= 1",
  "severity": "error",
  "message": "必须至少创建 1 个 ADR"
}
```

**severity 枚举值**:

| 值 | 说明 |
|---|------|
| `"error"` | 必须通过，否则无法切换阶段 |
| `"warning"` | 建议通过，但可以强制切换 |

**示例**:

```json
{
  "gates": {
    "arch_done": [
      {
        "name": "adr_exists",
        "condition": "arch_side.adr.count >= 1",
        "severity": "error",
        "message": "必须至少创建 1 个 ADR"
      },
      {
        "name": "roadmap_defined",
        "condition": "arch_side.roadmap.exists == true",
        "severity": "error",
        "message": "必须定义 roadmap"
      },
      {
        "name": "gap_analysis_complete",
        "condition": "arch_side.architecture.pending_gaps == 0",
        "severity": "warning",
        "message": "建议完成架构差距分析"
      }
    ]
  }
}
```

---

## loop.yaml Schema

### 完整 Schema

```yaml
version: "2.0"
name: "complete-all-changes"
description: "自动完成所有待处理 changes"

goal:
  description: "complete all pending changes"
  success_criteria:
    - "active_changes.count == 0"
    - "worktrees.count == 0"
    - "roadmap.completion >= 0.8"

interaction:
  mode: "hybrid"
  human_in_loop_nodes:
    - "arch.adr_create"
    - "ship.archive_confirm"

loop:
  max_iterations: 100
  max_retries: 3
  parallel_limit: 3
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
    action: "escalate_to_human"

verification:
  method: "multi_model"
  executor_agent: "coder"
  reviewer_agent: "reviewer"
  weights:
    executor: 0.4
    reviewer: 0.6
  divergence_threshold: 0.4

control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
  
  stagnation_threshold: 5
  error_budget: 0.1

phases:
  arch:
    enabled: true
    gates:
      - "adr_exists"
      - "roadmap_defined"
  
  plan:
    enabled: true
    gates:
      - "changes_committed"
      - "artifacts_complete"
  
  ship:
    enabled: true
    gates:
      - "worktrees_empty"
      - "archive_empty"
```

### 字段详解

#### `version` (必需)

- **类型**: `string`
- **枚举**: `"2.0"`

```yaml
version: "2.0"
```

---

#### `name` (必需)

- **类型**: `string`
- **说明**: Loop 名称（用于标识和日志）

```yaml
name: "complete-all-changes"
```

---

#### `description` (可选)

- **类型**: `string`
- **说明**: Loop 描述

```yaml
description: "自动完成所有待处理 changes"
```

---

#### `goal` (必需)

- **类型**: `object`
- **说明**: 目标定义（设计先行阶段）

**字段**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `description` | `string` | ✅ | 目标描述 |
| `success_criteria` | `array` | ✅ | 完成标准列表 |
| `deliverables` | `array` | ❌ | 预期产出物 |

**示例**:

```yaml
goal:
  description: "complete all pending changes"
  success_criteria:
    - "active_changes.count == 0"
    - "worktrees.count == 0"
    - "roadmap.completion >= 0.8"
  deliverables:
    - "archived changes in openspec/changes/archive/"
    - "updated roadmap.md with completion status"
```

---

#### `interaction` (必需)

同 `.spec-workflow.json` 的 `interaction` 字段。

---

#### `loop` (必需)

同 `.spec-workflow.json` 的 `loop` 字段。

---

#### `verification` (可选)

同 `.spec-workflow.json` 的 `verification` 字段。

---

#### `control` (可选)

- **类型**: `object`
- **说明**: 控制设计（设计先行阶段）

**字段**:

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `circuit_breaker` | `object` | ❌ | - | 断路器配置 |
| `stagnation_threshold` | `integer` | ❌ | `5` | 无进展阈值（连续 N 次无变化） |
| `error_budget` | `number` | ❌ | `0.1` | 错误预算（允许的失败率） |

**示例**:

```yaml
control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
  
  stagnation_threshold: 5
  error_budget: 0.1
```

---

#### `phases` (可选)

- **类型**: `object`
- **说明**: 阶段配置

**字段**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `arch` | `object` | ❌ | Arch 阶段配置 |
| `plan` | `object` | ❌ | Plan 阶段配置 |
| `ship` | `object` | ❌ | Ship 阶段配置 |

**阶段字段**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `enabled` | `boolean` | ❌ | 是否启用此阶段 |
| `gates` | `array` | ❌ | 门控检查项列表 |

**示例**:

```yaml
phases:
  arch:
    enabled: true
    gates:
      - "adr_exists"
      - "roadmap_defined"
  
  plan:
    enabled: true
    gates:
      - "changes_committed"
      - "artifacts_complete"
  
  ship:
    enabled: true
    gates:
      - "worktrees_empty"
      - "archive_empty"
```

---

## 配置示例库

### 示例 1: 最小配置（快速开始）

**文件**: `.spec-workflow.json`

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid"
  }
}
```

**适用场景**: 简单项目，使用默认值

---

### 示例 2: 推荐配置（大多数项目）

**文件**: `.spec-workflow.json`

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      "arch.adr_create",
      "ship.archive_confirm",
      "ship.execute_error"
    ]
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "parallel_limit": 3
  },
  "verification": {
    "method": "human"
  },
  "memory": {
    "enabled": true,
    "auto_suggest_config": true
  }
}
```

**适用场景**: 大多数项目，平衡自动化和控制权

---

### 示例 3: 全自动配置（CI/CD）

**文件**: `.spec-workflow.json`

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "loop"
  },
  "loop": {
    "max_iterations": 50,
    "max_retries": 2,
    "parallel_limit": 5,
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "abort"
    }
  },
  "verification": {
    "method": "script",
    "script": ".spec-workflow/scripts/verification/ci-check.py"
  }
}
```

**适用场景**: CI/CD 流水线，全自动执行

---

### 示例 4: 多模型验证（高质量要求）

**文件**: `.spec-workflow.json`

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      {
        "node": "ship.archive_confirm",
        "verification_mode": "multi_model",
        "executor_agent": "coder",
        "reviewer_agent": "reviewer",
        "review_criteria": [
          "all tests pass",
          "no merge conflicts",
          "ADR compliance check",
          "code quality score >= 0.8"
        ]
      }
    ]
  },
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    },
    "divergence_threshold": 0.4
  }
}
```

**适用场景**: 高质量要求项目，多 agent 交叉验证

---

### 示例 5: 便携规范（团队协作）

**文件**: `.spec-workflow/loops/complete-changes.yaml`

```yaml
version: "2.0"
name: "complete-all-changes"
description: "自动完成所有待处理 changes"

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
  parallel_limit: 3

verification:
  method: "multi_model"
  executor_agent: "coder"
  reviewer_agent: "reviewer"

control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
```

**使用**:

```bash
skill_use("loop", {
  "goal": "complete all pending changes",
  "config_file": ".spec-workflow/loops/complete-changes.yaml"
})
```

**适用场景**: 团队协作，配置需要版本控制

---

## 验证工具

### 验证 .spec-workflow.json

```bash
# 1. 使用 jq 验证 JSON 格式
cat .spec-workflow.json | jq '.'

# 2. 使用 spec-workflow CLI 验证
spec-workflow config validate

# 3. 查看配置解析结果
spec-workflow config show
```

### 验证 loop.yaml

```bash
# 1. 使用 yq 验证 YAML 格式
yq eval '.' .spec-workflow/loops/complete-changes.yaml

# 2. 使用 spec-workflow CLI 验证
spec-workflow config validate --file .spec-workflow/loops/complete-changes.yaml
```

### 常见验证错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `Invalid JSON` | JSON 格式错误 | 使用 `jq` 检查 |
| `Unknown field: xxx` | 字段名错误 | 检查 Schema |
| `Invalid enum value: xxx` | 枚举值错误 | 检查允许的枚举值 |
| `Missing required field: xxx` | 缺少必需字段 | 添加缺失字段 |
| `Type mismatch: expected string, got number` | 类型错误 | 修改字段类型 |

---

## 环境变量

可以通过环境变量覆盖配置：

| 环境变量 | 对应配置字段 | 示例 |
|---------|------------|------|
| `SPEC_WORKFLOW_MODE` | `interaction.mode` | `export SPEC_WORKFLOW_MODE=loop` |
| `SPEC_WORKFLOW_MAX_ITERATIONS` | `loop.max_iterations` | `export SPEC_WORKFLOW_MAX_ITERATIONS=50` |
| `SPEC_WORKFLOW_MAX_RETRIES` | `loop.max_retries` | `export SPEC_WORKFLOW_MAX_RETRIES=2` |
| `SPEC_WORKFLOW_VERIFICATION_METHOD` | `verification.method` | `export SPEC_WORKFLOW_VERIFICATION_METHOD=human` |

---

## 下一步

- **查看迁移指南**: [migration/v1-to-v2.md](migration/v1-to-v2.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](v2-loop-engine-guide.md)
- **查看 ADR 总结**: [v2-adr-summary.md](v2-adr-summary.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

