# spec-workflow v2.0 审判委员会指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **ADR 参考**: [ADR-0008](../adr/ADR-0008-tribunal-committee.md)

---

## 📋 目录

- [概述](#概述)
- [多 Agent 验证配置](#多-agent-验证配置)
- [oh-my-opencode Agent 配置](#oh-my-opencode-agent-配置)
- [数据脱敏说明](#数据脱敏说明)
- [判定算法详解](#判定算法详解)
- [验证模式](#验证模式)
- [最佳实践](#最佳实践)

---

## 概述

### 什么是审判委员会？

审判委员会（Tribunal Committee）是 spec-workflow v2.0 的**多 Agent 交叉验证机制**，通过多个 AI 模型独立评估执行结果，提高决策质量。

```
Executor Agent ──→ 评分: 0.90
                     ↓
                  综合判定 ──→ 最终决策
                     ↑
Reviewer Agent ──→ 评分: 0.92
```

### 为什么需要多 Agent 验证？

| 问题 | 单一模型 | 多模型 |
|------|---------|--------|
| **偏差** | 容易受单一模型偏好影响 | 多模型平衡，减少偏差 |
| **盲点** | 可能忽略某些问题 | 不同模型互补 |
| **置信度** | 难以评估 | 通过分歧度评估 |
| **质量** | 取决于单一模型质量 | 加权平均，更稳定 |

---

## 多 Agent 验证配置

### 基础配置

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

### 完整配置

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
    "divergence_threshold": 0.4,
    "review_criteria": [
      "all tests pass",
      "no merge conflicts",
      "ADR compliance check",
      "code quality score >= 0.8"
    ],
    "max_review_rounds": 3,
    "consensus_required": false,
    "escalation_threshold": 0.3
  }
}
```

### 字段详解

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `method` | string | ✅ | - | 验证方法（multi_model/human/script） |
| `executor_agent` | string | ✅ | - | 执行 Agent 名称 |
| `reviewer_agent` | string | ✅ | - | 审核 Agent 名称 |
| `weights` | object | ❌ | - | 权重配置 |
| `weights.executor` | number | ❌ | 0.4 | 执行 Agent 权重 |
| `weights.reviewer` | number | ❌ | 0.6 | 审核 Agent 权重 |
| `divergence_threshold` | number | ❌ | 0.4 | 分歧阈值（0-1） |
| `review_criteria` | array | ❌ | [] | 审核标准列表 |
| `max_review_rounds` | integer | ❌ | 3 | 最大审核轮次 |
| `consensus_required` | boolean | ❌ | false | 是否要求一致同意 |
| `escalation_threshold` | number | ❌ | 0.3 | 升级到人工的分歧阈值 |

---

## oh-my-opencode Agent 配置

### Agent 定义

在 `.opencode/skills/` 目录中定义 Agent：

```
.opencode/
└── skills/
    ├── coder.yaml
    ├── reviewer.yaml
    └── architect.yaml
```

### Coder Agent 配置

```yaml
# .opencode/skills/coder.yaml
name: "coder"
description: "代码执行 Agent"
model: "gpt-4"
temperature: 0.2
max_tokens: 4000
system_prompt: |
  你是一个专业的代码执行 Agent。
  你的职责是：
  1. 根据计划执行代码修改
  2. 运行测试验证
  3. 提交更改
  4. 提供执行报告

  评估标准：
  - 代码质量（0-1）
  - 测试通过率（0-1）
  - 完成度（0-1）
```

### Reviewer Agent 配置

```yaml
# .opencode/skills/reviewer.yaml
name: "reviewer"
description: "代码审核 Agent"
model: "claude-3-opus"
temperature: 0.1
max_tokens: 4000
system_prompt: |
  你是一个严格的代码审核 Agent。
  你的职责是：
  1. 独立评估执行结果
  2. 检查代码质量
  3. 识别潜在问题
  4. 提供改进建议

  评估标准：
  - 代码质量（0-1）
  - 安全性（0-1）
  - 可维护性（0-1）
  - ADR 合规性（0-1）

  注意：
  - 你必须独立评估，不要参考 Executor 的评分
  - 重点关注边缘情况和潜在风险
```

### Architect Agent 配置（可选）

```yaml
# .opencode/skills/architect.yaml
name: "architect"
description: "架构审核 Agent"
model: "claude-3-opus"
temperature: 0.1
max_tokens: 4000
system_prompt: |
  你是一个架构审核 Agent。
  你的职责是：
  1. 评估架构合规性
  2. 检查 ADR 遵守情况
  3. 识别架构风险
  4. 提供架构改进建议
```

### Agent 选择策略

| 场景 | 推荐 Agent 组合 | 原因 |
|------|---------------|------|
| **常规开发** | coder (GPT-4) + reviewer (Claude 3) | 平衡质量和速度 |
| **高质量要求** | coder (Claude 3) + reviewer (GPT-4) + architect (Claude 3) | 三重验证 |
| **快速迭代** | coder (GPT-3.5) + reviewer (GPT-4) | 快速执行，严格审核 |
| **安全关键** | coder (Claude 3) + reviewer (Claude 3) | 最高质量 |

---

## 数据脱敏说明

### 为什么需要脱敏？

多 Agent 验证可能涉及敏感信息：
- 🔒 API 密钥
- 🔒 数据库密码
- 🔒 内部业务逻辑
- 🔒 用户数据

### 脱敏策略

```json
{
  "verification": {
    "data_masking": {
      "enabled": true,
      "rules": [
        {
          "name": "api_keys",
          "pattern": "sk-[a-zA-Z0-9]{32,}",
          "replacement": "[API_KEY_REDACTED]"
        },
        {
          "name": "passwords",
          "pattern": "password:\\s*['\"][^'\"]+['\"]",
          "replacement": "password: [REDACTED]"
        },
        {
          "name": "email_addresses",
          "pattern": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
          "replacement": "[EMAIL_REDACTED]"
        }
      ]
    }
  }
}
```

### 脱敏流程

```
原始代码 ──→ 脱敏处理 ──→ Agent 评估 ──→ 结果返回
```

**示例**:

```python
# 原始代码
api_key = "sk-abc123def456ghi789jkl012mno345pqr"
db_password = "super_secret_password_123"
user_email = "user@example.com"

# 脱敏后（发送给 Agent）
api_key = "[API_KEY_REDACTED]"
db_password = "[REDACTED]"
user_email = "[EMAIL_REDACTED]"
```

### 脱敏规则配置

| 规则 | 模式 | 替换 | 说明 |
|------|------|------|------|
| **API 密钥** | `sk-[a-zA-Z0-9]{32,}` | `[API_KEY_REDACTED]` | OpenAI 风格密钥 |
| **密码** | `password:\s*['"][^'\"]+['\"]` | `password: [REDACTED]` | 密码字段 |
| **邮箱** | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `[EMAIL_REDACTED]` | 邮箱地址 |
| **电话号码** | `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b` | `[PHONE_REDACTED]` | 电话号码 |
| **IP 地址** | `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b` | `[IP_REDACTED]` | IP 地址 |

---

## 判定算法详解

### 加权评分算法

```python
def calculate_final_score(executor_score: float, reviewer_score: float, 
                         weights: dict) -> float:
    """
    计算加权最终评分
    
    Args:
        executor_score: Executor Agent 评分 (0-1)
        reviewer_score: Reviewer Agent 评分 (0-1)
        weights: 权重配置 {"executor": 0.4, "reviewer": 0.6}
    
    Returns:
        final_score: 最终评分 (0-1)
    """
    final_score = (
        executor_score * weights["executor"] +
        reviewer_score * weights["reviewer"]
    )
    return final_score

# 示例
executor_score = 0.90
reviewer_score = 0.92
weights = {"executor": 0.4, "reviewer": 0.6}

final_score = 0.90 * 0.4 + 0.92 * 0.6 = 0.912
```

### 分歧度计算

```python
def calculate_divergence(executor_score: float, reviewer_score: float) -> float:
    """
    计算分歧度
    
    Args:
        executor_score: Executor Agent 评分 (0-1)
        reviewer_score: Reviewer Agent 评分 (0-1)
    
    Returns:
        divergence: 分歧度 (0-1)
    """
    return abs(executor_score - reviewer_score)

# 示例
divergence = abs(0.90 - 0.92) = 0.02  # 低分歧，一致
divergence = abs(0.90 - 0.50) = 0.40  # 高分歧，需人工审核
```

### 判定逻辑

```python
def make_decision(executor_score: float, reviewer_score: float,
                 weights: dict, divergence_threshold: float) -> dict:
    """
    做出验证判定
    
    Returns:
        {
            "passed": bool,
            "final_score": float,
            "divergence": float,
            "recommendation": str,
            "escalate_to_human": bool
        }
    """
    final_score = calculate_final_score(executor_score, reviewer_score, weights)
    divergence = calculate_divergence(executor_score, reviewer_score)
    
    # 判定逻辑
    if divergence > divergence_threshold:
        # 分歧过大，升级到人工
        return {
            "passed": False,
            "final_score": final_score,
            "divergence": divergence,
            "recommendation": "DIVERGENCE_TOO_HIGH",
            "escalate_to_human": True
        }
    elif final_score >= 0.8:
        # 高分通过
        return {
            "passed": True,
            "final_score": final_score,
            "divergence": divergence,
            "recommendation": "PASS",
            "escalate_to_human": False
        }
    elif final_score >= 0.6:
        # 低分通过，建议改进
        return {
            "passed": True,
            "final_score": final_score,
            "divergence": divergence,
            "recommendation": "PASS_WITH_SUGGESTIONS",
            "escalate_to_human": False
        }
    else:
        # 不通过
        return {
            "passed": False,
            "final_score": final_score,
            "divergence": divergence,
            "recommendation": "FAIL",
            "escalate_to_human": False
        }
```

---

## 验证模式

### 模式 1: 基础验证（2 Agents）

```
Executor Agent ──→ 评分: 0.90
                     ↓
                  综合判定
                     ↑
Reviewer Agent ──→ 评分: 0.92
```

**配置**:
```json
{
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer"
  }
}
```

**适用场景**: 常规开发

---

### 模式 2: 三重验证（3 Agents）

```
Executor Agent ──→ 评分: 0.90
                     ↓
Reviewer Agent   ──→ 评分: 0.92  ──→ 综合判定
                     ↑
Architect Agent  ──→ 评分: 0.88
```

**配置**:
```json
{
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "architect_agent": "architect",
    "weights": {
      "executor": 0.3,
      "reviewer": 0.4,
      "architect": 0.3
    }
  }
}
```

**适用场景**: 高质量要求项目

---

### 模式 3: 多轮审核

```
第 1 轮:
  Executor: 0.70
  Reviewer: 0.75
  → 低分通过，建议改进

第 2 轮（改进后）:
  Executor: 0.85
  Reviewer: 0.88
  → 高分通过
```

**配置**:
```json
{
  "verification": {
    "method": "multi_model",
    "max_review_rounds": 3,
    "improvement_threshold": 0.1
  }
}
```

**适用场景**: 需要持续改进的场景

---

### 模式 4: 一致同意（Consensus）

```
Executor: 0.90
Reviewer: 0.92
Architect: 0.88

所有评分 ≥ 0.8 → 一致同意通过
```

**配置**:
```json
{
  "verification": {
    "method": "multi_model",
    "consensus_required": true,
    "consensus_threshold": 0.8
  }
}
```

**适用场景**: 安全关键系统

---

## 验证流程示例

### 完整验证流程

```
🤖 多 Agent 验证开始

[准备阶段]
✅ 加载验证配置
✅ 初始化 Agents: coder, reviewer
✅ 加载审核标准:
  - all tests pass
  - no merge conflicts
  - ADR compliance check
  - code quality score >= 0.8

[Executor Agent 评估]
⚙️ Executor (coder) 开始评估...
  - 代码质量: 0.92
  - 测试通过率: 1.00 (15/15)
  - 完成度: 0.85
  - 综合评分: 0.90
  - 优势: All tests pass, no merge conflicts
  - 劣势: Minor code style issues

[Reviewer Agent 评估]
🔍 Reviewer (reviewer) 开始评估...
  - 代码质量: 0.94
  - 安全性: 0.95
  - 可维护性: 0.90
  - ADR 合规性: 0.88
  - 综合评分: 0.92
  - 独特关注点: Consider adding more comments
  - 置信度: 0.95

[综合判定]
📊 计算最终评分...
  - Executor score: 0.90 (权重: 0.4)
  - Reviewer score: 0.92 (权重: 0.6)
  - 最终评分: 0.912
  - 分歧度: 0.02 (阈值: 0.4)

✅ 验证通过！
  - 最终评分: 0.91
  - 分歧度: 0.02 (低分歧)
  - 建议: PASS

继续执行下一阶段？[y/n]:
```

---

### 分歧过大场景

```
🤖 多 Agent 验证开始

[Executor Agent 评估]
⚙️ Executor (coder) 开始评估...
  - 综合评分: 0.90

[Reviewer Agent 评估]
🔍 Reviewer (reviewer) 开始评估...
  - 综合评分: 0.50
  - 独特关注点: 
    ❌ Security vulnerability in auth module
    ❌ Missing error handling
    ❌ Potential race condition

[综合判定]
📊 计算最终评分...
  - Executor score: 0.90 (权重: 0.4)
  - Reviewer score: 0.50 (权重: 0.6)
  - 最终评分: 0.66
  - 分歧度: 0.40 (阈值: 0.4)

⚠️ 分歧过大！
  - 分歧度: 0.40 (阈值: 0.4)
  - Executor 评分: 0.90
  - Reviewer 评分: 0.50
  - 差异原因: Reviewer 发现安全漏洞

请选择:
  1. 升级到人工审核（推荐）
  2. 查看 Reviewer 详细报告
  3. 重新评估（更换 reviewer agent）
  4. 强制通过（不推荐）

选择 [1-4]:
```

---

## 最佳实践

### 1. 选择合适的 Agent 组合

| 项目类型 | Executor | Reviewer | 原因 |
|---------|----------|----------|------|
| **快速原型** | GPT-3.5 | GPT-4 | 快速执行，严格审核 |
| **生产代码** | GPT-4 | Claude 3 | 高质量 |
| **安全关键** | Claude 3 | Claude 3 + GPT-4 | 最高质量 |
| **实验功能** | GPT-4 | GPT-4 | 平衡 |

---

### 2. 设置合理的权重

```json
{
  "verification": {
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    }
  }
}
```

**原则**:
- ✅ Reviewer 权重 ≥ Executor 权重（审核更重要）
- ✅ 权重总和 = 1.0
- ✅ 根据项目调整

---

### 3. 定义清晰的审核标准

```json
{
  "verification": {
    "review_criteria": [
      "all tests pass",
      "no merge conflicts",
      "ADR compliance check",
      "code quality score >= 0.8",
      "no security vulnerabilities",
      "error handling complete"
    ]
  }
}
```

---

### 4. 启用数据脱敏

```json
{
  "verification": {
    "data_masking": {
      "enabled": true,
      "rules": [
        {
          "name": "api_keys",
          "pattern": "sk-[a-zA-Z0-9]{32,}",
          "replacement": "[API_KEY_REDACTED]"
        }
      ]
    }
  }
}
```

---

### 5. 监控验证质量

```bash
# 查看验证统计
spec-workflow verification stats

# 输出:
# 总验证次数: 100
# 通过次数: 85 (85%)
# 失败次数: 10 (10%)
# 升级到人工: 5 (5%)
#
# 平均分歧度: 0.12
# 平均最终评分: 0.88
#
# Executor 平均评分: 0.90
# Reviewer 平均评分: 0.89
```

---

## 故障排查

### 问题 1: Agent 调用失败

**症状**: "Agent 'reviewer' not found"

**解决**:
```bash
# 1. 检查 Agent 定义
ls .opencode/skills/

# 2. 检查 Agent 配置
cat .opencode/skills/reviewer.yaml

# 3. 验证 oh-my-opencode 安装
oh-my-opencode list

# 4. 测试 Agent
oh-my-opencode test reviewer
```

---

### 问题 2: 分歧度过高

**症状**: "Divergence threshold exceeded"

**解决**:
```bash
# 1. 查看详细报告
cat .rddf/state/event-log.jsonl | jq 'select(.type == "verification_completed")'

# 2. 分析分歧原因
# Executor: 0.90, Reviewer: 0.50 → 分歧 0.40

# 3. 选项:
# - 升级到人工审核
# - 更换 reviewer agent
# - 调整权重
# - 调整分歧阈值
```

---

### 问题 3: 脱敏失败

**症状**: 敏感信息泄露给 Agent

**解决**:
```bash
# 1. 检查脱敏规则
cat .rddf.json | jq '.verification.data_masking'

# 2. 测试脱敏规则
python3 -c "
import re
pattern = r'sk-[a-zA-Z0-9]{32,}'
text = 'api_key = \"sk-abc123def456ghi789jkl012mno345pqr\"'
result = re.sub(pattern, '[API_KEY_REDACTED]', text)
print(result)
"

# 3. 添加缺失的规则
```

---

## 下一步

- **查看 ADR-0008**: [ADR-0008-tribunal-committee.md](../adr/ADR-0008-tribunal-committee.md)
- **查看配置 Schema**: [v2-config-schema.md](../v2-config-schema.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](../v2-loop-engine-guide.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

