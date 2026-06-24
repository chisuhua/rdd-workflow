# ADR-0008: 审判委员会设计 (Tribunal Committee)

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0005 (Human-in-Loop 节点定义)
> **调研来源**: Looper 审判委员会机制

## Context

在 ADR-0005 中，我们定义了三种验证模式（human/multi_model/script），其中 `multi_model` 模式需要多模型交叉验证机制。参考 Looper 项目的审判委员会设计，我们需要实现：

1. **盲区差异利用**: 不同模型家族有不同的强项和弱项，交叉验证可以降低错误率
2. **数据隐私保护**: 跨模型传输数据时需要脱敏
3. **综合判定算法**: 如何综合多个模型的评估结果

**约束**:
- 通过 oh-my-opencode 插件调用 agent，不硬编码厂商和模型
- 所有 spec-workflow 配置在 `.spec-workflow/` 目录下
- 数据隐私由 spec-workflow 自主处理，不依赖外部插件

## Decision

我们实现**基于 oh-my-opencode 的审判委员会**机制：

### 1. Agent 调用

通过 opencode task API 调用 oh-my-opencode 的 agent：

```python
# skills/_lib/tribunal.py

class TribunalCommittee:
    """审判委员会：通过 oh-my-opencode 多 agent 交叉验证"""
    
    def __init__(self, config: TribunalConfig):
        self.config = config
        self.sanitizer = DataSanitizer()
    
    def verify_change(
        self,
        change_name: str,
        artifacts: dict,
        executor_agent: str,  # oh-my-opencode agent 名称
        reviewer_agent: str,  # oh-my-opencode agent 名称
        criteria: List[str]
    ) -> TribunalResult:
        """验证 change 质量"""
        
        # 1. 验证 agent 配置
        if executor_agent == reviewer_agent:
            logger.warning(f"执行和审核使用同一 agent: {executor_agent}")
            event_log.record("same_agent_warning", {
                "agent": executor_agent,
                "context": "tribunal_verification"
            })
        
        # 2. 调用执行 agent
        exec_prompt = self.build_execution_prompt(change_name, artifacts, criteria)
        exec_result = self.call_opencode_agent(
            agent_name=executor_agent,
            prompt=exec_prompt,
            role="executor"
        )
        
        # 3. 调用审核 agent（数据脱敏）
        sanitized_artifacts = self.sanitizer.sanitize_for_agent(
            artifacts,
            reviewer_agent
        )
        review_prompt = self.build_review_prompt(change_name, sanitized_artifacts, criteria)
        review_result = self.call_opencode_agent(
            agent_name=reviewer_agent,
            prompt=review_prompt,
            role="reviewer"
        )
        
        # 4. 综合判定
        return self.adjudicate(exec_result, review_result)
    
    def call_opencode_agent(self, agent_name: str, prompt: str, role: str) -> ModelResult:
        """调用 oh-my-opencode 的 agent"""
        result = task(
            subagent_type=agent_name,
            description=f"{role} role for change verification",
            prompt=prompt
        )
        return self.parse_result(result)
```

### 2. 配置管理

#### spec-workflow 配置

```json
// .spec-workflow/config.json

{
  "version": "2.0",
  "verification": {
    "method": "multi_model",
    "executor_agent": "coder",
    "reviewer_agent": "reviewer",
    "review_criteria": [
      "all tests pass",
      "no merge conflicts",
      "ADR compliance check"
    ],
    "weights": {
      "executor": 0.4,
      "reviewer": 0.6
    },
    "divergence_threshold": 0.4
  }
}
```

#### oh-my-opencode 配置（外部插件）

```json
// .opencode/oh-my-opencode.json (外部插件配置)

{
  "agents": {
    "coder": {
      "model": "anthropic/claude-sonnet-4",
      "description": "代码执行 agent"
    },
    "reviewer": {
      "model": "openai/gpt-4o",
      "description": "代码审查 agent"
    }
  }
}
```

**配置分离原则**:
- `.spec-workflow/config.json`: spec-workflow 配置（使用哪个 agent、验证标准）
- `.opencode/oh-my-opencode.json`: 外部插件配置（agent 对应什么模型）

### 3. 综合判定算法

```python
def adjudicate(self, exec_result: ModelResult, review_result: ModelResult) -> TribunalResult:
    """综合判定"""
    
    # 1. 分数加权（审核模型权重更高）
    final_score = (
        exec_result.score * self.config.weights.executor +
        review_result.score * self.config.weights.reviewer
    )
    
    # 2. 检查分歧
    score_diff = abs(exec_result.score - review_result.score)
    if score_diff > self.config.divergence_threshold:
        event_log.record("model_divergence", {
            "exec_score": exec_result.score,
            "review_score": review_result.score,
            "threshold": self.config.divergence_threshold
        })
    
    # 3. 判定
    passed = (
        final_score >= 0.8 and
        exec_result.passed and
        review_result.passed and
        score_diff < self.config.divergence_threshold
    )
    
    return TribunalResult(
        passed=passed,
        final_score=final_score,
        exec_score=exec_result.score,
        review_score=review_result.score,
        score_divergence=score_diff,
        recommendation="pass" if passed else "review_manually"
    )
```

**判定规则**:

| 条件 | 结果 | 说明 |
|------|------|------|
| final_score ≥ 0.8 AND 双方都通过 AND 分歧 < 阈值 | ✅ 通过 | 高质量，一致认可 |
| final_score ≥ 0.8 BUT 分歧 ≥ 阈值 | ⚠️ 人工审查 | 高质量但有分歧 |
| final_score < 0.8 | ❌ 不通过 | 质量不足 |
| 任一方不通过 | ❌ 不通过 | 有一方反对 |

### 4. 数据隐私保护

```python
# skills/_lib/sanitizer.py

class DataSanitizer:
    """数据脱敏器"""
    
    SENSITIVE_PATTERNS = [
        r'api_key["\s:]+\S+',
        r'password["\s:]+\S+',
        r'token["\s:]+\S+',
        r'secret["\s:]+\S+',
        r'/Users/\w+/',
        r'/home/\w+/',
        r'AWS_SECRET_\w+',
        r'PRIVATE_KEY'
    ]
    
    def sanitize_for_agent(self, data: dict, agent_name: str) -> dict:
        """为 agent 脱敏数据"""
        # 检查是否需要脱敏（跨模型传输）
        if not self.requires_sanitization(agent_name):
            return data
        
        # 执行脱敏
        sanitized = json.dumps(data)
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized)
        
        # 记录脱敏日志
        event_log.record("data_sanitized", {
            "agent": agent_name,
            "patterns_applied": len(self.SENSITIVE_PATTERNS)
        })
        
        return json.loads(sanitized)
    
    def requires_sanitization(self, agent_name: str) -> bool:
        """检查是否需要脱敏"""
        # 如果 executor 和 reviewer 使用不同模型，需要脱敏
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('cross_model', False)
```

### 5. 提示词设计

```python
def build_execution_prompt(self, change_name: str, artifacts: dict, criteria: List[str]) -> str:
    """构建执行 agent 提示词"""
    return f"""
你是代码执行专家。请评估 change '{change_name}' 的实施质量。

## Artifacts
{artifacts}

## 评估标准
{chr(10).join([f'- {c}' for c in criteria])}

## 输出格式
{{
  "score": 0.0-1.0,
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["缺点1", "缺点2"],
  "passed": true/false
}}
"""

def build_review_prompt(self, change_name: str, artifacts: dict, criteria: List[str]) -> str:
    """构建审核 agent 提示词（独立视角）"""
    return f"""
你是独立的代码审查专家。请客观评估 change '{change_name}' 的质量。

注意：你的评估将与其他专家交叉验证，请保持独立判断。

## Artifacts
{artifacts}

## 评估标准
{chr(10).join([f'- {c}' for c in criteria])}

## 输出格式
{{
  "score": 0.0-1.0,
  "unique_concerns": ["你独特的担忧"],
  "passed": true/false,
  "confidence": 0.0-1.0
}}
"""
```

### 6. 推荐配置模板

```yaml
# .spec-workflow/templates/verification-pairs.yaml

template_pairs:
  code_quality:
    executor_agent: "coder"
    reviewer_agent: "reviewer"
    description: "代码质量检查（推荐）"
  
  high_security:
    executor_agent: "reviewer"
    reviewer_agent: "coder"
    description: "高安全性审查（反向 agent）"
  
  single_agent:
    executor_agent: "coder"
    reviewer_agent: "coder"
    description: "单 agent 模式（快速验证）"
    warning: "同一 agent 会降低验证质量"
```

### 影响范围

- **In Scope**:
  - 新增 `skills/_lib/tribunal.py` (审判委员会实现)
  - 新增 `skills/_lib/sanitizer.py` (数据脱敏)
  - 更新 `.spec-workflow/config.json` Schema
  - 添加推荐模板到 `.spec-workflow/templates/`
  
- **Out Scope**:
  - 不修改 oh-my-opencode 插件配置
  - 不改变 agent 对应的模型（由用户配置）

### 备选方案

| 备选 | 理由 |
|------|------|
| **硬编码厂商和模型** | 拒绝：缺乏灵活性，用户无法自定义 |
| **单模型验证** | 拒绝：失去盲区差异优势，错误率高 |
| **基于 oh-my-opencode 的多 agent** | 接受：灵活、可扩展、解耦 |

## Consequences

### 正面

- **质量提升**: 多 agent 交叉验证，降低错误率
- **灵活性**: 用户可自定义 agent 和模型
- **隐私保护**: spec-workflow 自主处理数据脱敏
- **解耦**: 不硬编码厂商和模型，通过 oh-my-opencode 抽象

### 负面 / 风险

- **成本增加**: 每次验证需要调用 2 个 agent
  - **缓解**: 提供 single_agent 模式（快速验证）
- **配置复杂**: 需要配置 oh-my-opencode 和 spec-workflow
  - **缓解**: 提供推荐模板
- **同 agent 风险**: 用户可能配置同一 agent
  - **缓解**: 警告并记录到事件流

### 后续待办

- [ ] 实现 `skills/_lib/tribunal.py`
- [ ] 实现 `skills/_lib/sanitizer.py`
- [ ] 添加审判委员会单元测试
- [ ] 添加集成测试（multi_model 验证场景）
- [ ] 编写审判委员会文档和配置指南
- [ ] 提供推荐模板示例

## References

- ADR-0005 — Human-in-Loop 节点定义（multi_model 验证模式）
- Looper — 审判委员会机制（多模型交叉验证）
- `.spec-workflow/config.json` — spec-workflow 配置
- `.opencode/oh-my-opencode.json` — oh-my-opencode 插件配置（外部）

