# ADR-0012: 流程定制层

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0011 (阶段步骤化模型), ADR-0004 (Loop 引擎), ADR-0005 (Human-in-Loop)

## Context

在 ADR-0011 中，我们将阶段从"黑盒"拆分为步骤序列，为定制能力提供了基础架构。但 ADR-0011 只定义了**默认步骤模板**，尚未解决用户如何**定制这些步骤**的问题。

**用户需求**（来自 v2.0 规划讨论）：
1. 在阶段内部插入自定义步骤（如 plan 阶段插入合规审查）
2. 用自定义技能替代默认技能（如用 custom-planner 替代 prometheus-planning）
3. 在特定条件下触发自定义步骤（如只在安全相关 change 时触发安全审查）
4. 设置步骤失败后的处理策略（如回退到前一步骤、升级到人工）

**设计约束**：
- 必须保持**向后兼容**：不配置定制规则时，行为与当前完全一致
- 必须保持**版本兼容**：spec-workflow 升级时，用户的定制配置不被破坏
- 必须保持**安全性**：条件表达式不能直接 eval，必须有受限的语法
- 必须与 ADR-0005 的 Human-in-Loop **共用验证机制**

## Decision

我们引入 **流程定制层 (Flow Customization Layer)**，允许用户通过配置文件定制步骤模板，采用以下核心设计：

### 设计 1：增量覆盖模式

用户**只声明增量**，不声明完整序列。spec-workflow 升级时，默认步骤的变更会自动合并到用户的配置中。

**用户配置**：
```yaml
# .spec-workflow/flow.yaml
version: "2.0"

customizations:
  plan:
    # 在 generate_proposal 之后插入自定义步骤
    - insert_after: "generate_proposal"
      step:
        id: "compliance_review"
        name: "合规审查"
        type: "custom"
        skill: "compliance-review"
        trigger: "always"
        verification_mode: "human"
    
    # 替代默认技能
    - replace: "generate_proposal"
      overrides:
        skill: "custom-planner"
        params:
          template: "detailed"
    
    # 在 commit_change 之前插入条件触发的步骤
    - insert_before: "commit_change"
      step:
        id: "security_audit"
        name: "安全审计"
        type: "custom"
        skill: "security-review"
        trigger: "changes.any(has_security_impact)"
        on_failure: "back_to:generate_proposal"
        on_failure_max_retries: 3
```

**合并逻辑**：
```
默认模板:    [scan → select → generate_proposal → generate_design → generate_tasks → analyze_deps → commit_change]

用户定制:    insert_after generate_proposal: compliance_review
             replace generate_proposal: skill=custom-planner
             insert_before commit_change: security_audit

合并后:      [scan → select → generate_proposal(custom-planner) → compliance_review → generate_design → generate_tasks → analyze_deps → security_audit → commit_change]
```

**优势**：
- 用户只关心自己定制的部分
- 默认步骤升级时自动生效（如 v2.1 新增 `review_proposal` 步骤，用户配置不受影响）
- 避免配置冗长和重复

### 设计 2：自定义步骤定义

自定义步骤的配置结构：

```yaml
step:
  id: "compliance_review"                    # 唯一标识
  name: "合规审查"                            # 显示名称
  type: "custom"                             # 步骤类型（custom/detector/action）
  skill: "compliance-review"                 # 技能名称或路径
  params:                                    # 传递给技能的参数
    check_list: ["license", "export-control"]
    severity: "high"
  
  # 触发条件（见设计 3）
  trigger: "always"
  
  # 验证模式（复用 ADR-0005）
  verification_mode: "human"                 # human / multi_model / script
  
  # 失败处理（见设计 4）
  on_failure: "back_to:generate_proposal"
  on_failure_max_retries: 3
  
  # 可选：覆盖下一步
  on_success: "generate_design"              # 默认是模板中的下一步
  on_failure: "skip"                         # 失败时跳到下一步（而非 abort）
```

### 设计 3：条件触发引擎

触发条件使用**受限表达式语法**，不支持任意 Python 代码：

```yaml
# 无条件触发
trigger: "always"

# 永不触发（禁用步骤）
trigger: "never"

# 基于 change 属性
trigger: "changes.any(has_security_impact)"
trigger: "changes.any(has_tag('compliance'))"
trigger: "changes.all(is_approved)"

# 基于状态
trigger: "state.arch_side.adr_count >= 1"
trigger: "state.plan_side.active_changes.length > 2"

# 基于前序步骤输出
trigger: "context.scan_candidates.data.has_security_changes == true"

# 逻辑组合
trigger: "changes.any(has_security_impact) and state.arch_side.adr_count >= 1"
trigger: "not changes.all(is_approved)"
```

**支持的内置函数**：

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `changes.any(predicate)` | 谓词 | bool | 任一 change 满足条件 |
| `changes.all(predicate)` | 谓词 | bool | 所有 change 满足条件 |
| `changes.filter(predicate)` | 谓词 | list | 筛选满足条件的 change |
| `has_security_impact` | - | bool | change 是否有安全影响 |
| `has_tag(tag)` | string | bool | change 是否有指定标签 |
| `is_approved` | - | bool | change 是否已审批 |
| `has_compliance_impact` | - | bool | change 是否有合规影响 |

**支持的操作符**：

| 操作符 | 示例 | 说明 |
|--------|------|------|
| `==`, `!=`, `>`, `<`, `>=`, `<=` | `state.arch_side.adr_count >= 1` | 比较 |
| `and`, `or`, `not` | `A and B` | 逻辑组合 |
| `in` | `"security" in change.tags` | 成员检查 |
| `length` | `changes.length > 0` | 长度 |

**表达式解析器**：

```python
# skills/_lib/trigger_engine.py

class TriggerEngine:
    """条件触发引擎"""
    
    def evaluate(self, expression: str, context: EvaluationContext) -> bool:
        """评估触发条件"""
        # 解析表达式（AST）
        ast = self.parse(expression)
        
        # 评估 AST（受限环境）
        return self.eval_ast(ast, context)
    
    def eval_ast(self, ast: ASTNode, context: EvaluationContext) -> bool:
        if ast.type == "function_call":
            return self.eval_function(ast.name, ast.args, context)
        elif ast.type == "comparison":
            left = self.eval_value(ast.left, context)
            right = self.eval_value(ast.right, context)
            return self.compare(left, ast.operator, right)
        elif ast.type == "logical":
            if ast.operator == "and":
                return self.eval_ast(ast.left, context) and self.eval_ast(ast.right, context)
            elif ast.operator == "or":
                return self.eval_ast(ast.left, context) or self.eval_ast(ast.right, context)
            elif ast.operator == "not":
                return not self.eval_ast(ast.operand, context)
        # ... 更多类型
        
    def eval_function(self, name: str, args: List, context: EvaluationContext) -> bool:
        if name == "changes.any":
            predicate = args[0]
            return any(self.eval_predicate(predicate, change) for change in context.changes)
        elif name == "has_security_impact":
            return context.change.has_security_impact
        # ... 更多函数
        
    def eval_value(self, node: ASTNode, context: EvaluationContext) -> Any:
        if node.type == "field_access":
            return self.resolve_field(node.path, context)
        elif node.type == "literal":
            return node.value
        # ... 更多类型
```

**安全保证**：
- 不使用 `eval()` 或 `exec()`
- 只允许预定义的函数和操作符
- 不允许函数定义、变量赋值、导入模块
- 解析失败时返回 false（而非抛出异常）

### 设计 4：失败处理策略

步骤失败后的处理策略：

```yaml
# 回退到指定步骤
on_failure: "back_to:generate_proposal"
on_failure_max_retries: 3      # 最大回退次数（默认 3）

# 跳过此步骤
on_failure: "skip"

# 中止整个流程
on_failure: "abort"

# 升级到人工
on_failure: "escalate_to_human"
```

**回退逻辑**：

```python
def handle_failure(self, step: StepDefinition, result: StepResult) -> StepAction:
    """处理步骤失败"""
    action = step.on_failure or "abort"
    
    if action.startswith("back_to:"):
        target_id = action.split(":")[1]
        retries = self.failure_counts.get(step.id, 0)
        
        if retries >= step.on_failure_max_retries:
            # 超过最大回退次数，升级到人工
            return StepAction(type="escalate_to_human")
        
        self.failure_counts[step.id] = retries + 1
        return StepAction(type="back_to", target=target_id)
    
    elif action == "skip":
        return StepAction(type="skip")
    
    elif action == "abort":
        return StepAction(type="abort", error=result.error)
    
    elif action == "escalate_to_human":
        return StepAction(type="escalate_to_human")
```

**回退限制**：
- 回退只能在**同一个阶段内**，不能跨阶段
- 回退不能形成**无限循环**（通过 `on_failure_max_retries` 限制）
- 回退时记录到**事件流**（便于审计）

### 设计 5：步骤上下文 (StepContext)

步骤间通过 `StepContext` 共享数据：

```python
# skills/_lib/step_context.py

class StepContext:
    """步骤间共享数据的上下文"""
    
    def __init__(self):
        self._data = {}
    
    def set(self, key: str, value: Any):
        self._data[key] = value
    
    def get(self, key: str, default=None) -> Any:
        return self._data.get(key, default)
    
    def update(self, data: dict):
        self._data.update(data)
    
    def has(self, key: str) -> bool:
        return key in self._data
    
    def snapshot(self) -> dict:
        """创建快照（用于序列化到状态向量）"""
        return self._data.copy()
    
    def restore(self, snapshot: dict):
        """从快照恢复（用于中断恢复）"""
        self._data = snapshot.copy()
```

**步骤配置中引用上下文**：

```yaml
steps:
  - id: "scan_candidates"
    type: "detector"
    output: "candidates"    # 输出到 context.candidates
    
  - id: "compliance_review"
    type: "custom"
    input: "candidates"     # 从 context.candidates 读取
    skill: "compliance-review"
```

### 设计 6：自定义技能接口

自定义技能必须实现以下接口：

```python
# skills/_lib/skill_interface.py

from abc import ABC, abstractmethod

class StepResult:
    """步骤执行结果"""
    
    def __init__(self, success: bool, data: dict = None, error: str = None, next_step: str = None):
        self.success = success
        self.data = data or {}
        self.error = error
        self.next_step = next_step  # 可选，覆盖默认的下一步

class CustomSkillInterface(ABC):
    """自定义技能接口规范"""
    
    @abstractmethod
    def execute(self, context: StepContext, params: dict) -> StepResult:
        """
        执行技能
        
        Args:
            context: 步骤上下文（包含前序步骤的输出）
            params: 技能参数（从配置文件中读取）
        
        Returns:
            StepResult:
                - success: bool（是否成功）
                - data: dict（输出到上下文，供后续步骤使用）
                - error: str（失败原因，当 success=False 时）
                - next_step: str（可选，覆盖默认的下一步）
        """
        pass
```

**示例：自定义合规审查技能**：

```python
# skills/custom/compliance-review.py

class ComplianceReview(CustomSkillInterface):
    def execute(self, context: StepContext, params: dict) -> StepResult:
        candidates = context.get("candidates")
        check_list = params.get("check_list", [])
        severity = params.get("severity", "medium")
        
        # 执行合规检查
        violations = []
        for candidate in candidates:
            for check in check_list:
                result = self.run_check(candidate, check)
                if not result.passed:
                    violations.append(result)
        
        if violations:
            return StepResult(
                success=False,
                error=f"Found {len(violations)} compliance violations",
                data={"violations": violations}
            )
        else:
            return StepResult(
                success=True,
                data={"checked": len(candidates), "violations": 0}
            )
    
    def run_check(self, candidate, check: str) -> CheckResult:
        # 实现具体检查逻辑
        pass
```

### 设计 7：与 Human-in-Loop 的关系（ADR-0005）

自定义步骤复用 ADR-0005 的验证机制：

```yaml
step:
  id: "compliance_review"
  verification_mode: "human"     # 复用 ADR-0005
```

| 验证模式 | 说明 | 行为 |
|---------|------|------|
| `human` | 人工验证 | 显示菜单，等待用户确认 |
| `multi_model` | 多模型交叉验证 | 调用多个 LLM 模型验证结果（ADR-0006） |
| `script` | 脚本验证 | 运行验证脚本 |
| `auto` | 自动验证 | 不验证，直接继续 |

**验证逻辑**（复用 ADR-0005）：

```python
def verify_step_result(self, step: StepDefinition, result: StepResult) -> bool:
    """验证步骤结果"""
    mode = step.verification_mode or "auto"
    
    if mode == "human":
        return self.show_verification_menu(step, result)
    elif mode == "multi_model":
        return self.multi_model_verify(step, result)
    elif mode == "script":
        return self.run_verification_script(step, result)
    elif mode == "auto":
        return result.success
```

### 完整配置示例

```yaml
# .spec-workflow/flow.yaml
version: "2.0"

description: "包含安全审查和合规检查的开发流程"

customizations:
  arch:
    # 在 ADR 创建后插入架构审查
    - insert_after: "create_adr"
      step:
        id: "architecture_review"
        name: "架构审查"
        type: "custom"
        skill: "architecture-review"
        trigger: "state.arch_side.adr_count >= 1"
        verification_mode: "human"
        on_failure: "back_to:create_adr"
        on_failure_max_retries: 2

  plan:
    # 用自定义技能生成 proposal
    - replace: "generate_proposal"
      overrides:
        skill: "custom-planner"
        params:
          template: "detailed"
    
    # 在 proposal 后插入合规审查
    - insert_after: "generate_proposal"
      step:
        id: "compliance_review"
        name: "合规审查"
        type: "custom"
        skill: "compliance-review"
        params:
          check_list: ["license", "export-control"]
          severity: "high"
        trigger: "changes.any(has_compliance_impact)"
        verification_mode: "human"
        on_failure: "back_to:generate_proposal"
        on_failure_max_retries: 3
    
    # 在提交前插入安全审计
    - insert_before: "commit_change"
      step:
        id: "security_audit"
        name: "安全审计"
        type: "custom"
        skill: "security-review"
        trigger: "changes.any(has_security_impact)"
        verification_mode: "multi_model"
        on_failure: "abort"

  ship:
    # 在执行前插入执行前审查
    - insert_before: "execute_units"
      step:
        id: "pre_execution_review"
        name: "执行前审查"
        type: "custom"
        skill: "execution-review"
        trigger: "always"
        verification_mode: "human"
    
    # 用自定义技能执行
    - replace: "execute_units"
      overrides:
        skill: "custom-executor"
        params:
          parallel: false
    
    # 在执行后插入审计
    - insert_after: "execute_units"
      step:
        id: "post_execution_audit"
        name: "执行后审计"
        type: "custom"
        skill: "execution-audit"
        trigger: "changes.any(has_security_impact)"
        verification_mode: "auto"
```

## Consequences

### 正面影响

1. **完全可定制的流程**：用户可以插入自定义步骤、指定技能、设置条件触发
2. **向后兼容**：不配置时行为与当前完全一致
3. **版本兼容**：增量覆盖模式确保升级时配置不被破坏
4. **安全**：条件表达式使用受限语法，不能执行任意代码
5. **可观测**：每个自定义步骤的执行状态记录到事件流

### 负面影响

1. **学习成本**：用户需要学习配置语法
2. **调试难度**：自定义步骤失败时需要跟踪条件表达式和上下文
3. **配置错误风险**：错误的插入点或触发条件可能导致流程异常

### 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| 配置语法错误 | 提供 `flow validate` 命令验证配置 |
| 条件表达式错误 | 解析失败时返回 false（而非崩溃） |
| 无限回退循环 | 限制 `on_failure_max_retries`（默认 3） |
| 自定义技能不兼容 | 定义严格的 CustomSkillInterface |
| 版本不兼容 | 配置文件带版本号，提供迁移工具 |

## Artifacts

| 文件 | 描述 | 行数估算 |
|------|------|---------|
| `skills/_lib/flow_customizer.py` | 流程定制合并引擎 | ~250 |
| `skills/_lib/trigger_engine.py` | 条件触发引擎 | ~200 |
| `skills/_lib/step_context.py` | 步骤上下文 | ~80（ADR-0011 已定义） |
| `skills/_lib/skill_interface.py` | 自定义技能接口 | ~60 |
| 单元测试 | 定制合并、触发引擎、技能接口 | ~400 |
| 集成测试 | 自定义步骤执行、回退逻辑 | ~200 |

## 评估标准

1. **向后兼容**：无 `.spec-workflow/flow.yaml` 时，行为与当前完全一致
2. **增量覆盖**：默认步骤升级时，用户定制配置不被破坏
3. **条件表达式安全**：解析器不执行任意代码，只支持预定义函数
4. **回退限制**：`on_failure_max_retries` 有效防止无限循环
5. **自定义技能兼容**：实现 CustomSkillInterface 的技能可以正确执行

## 输出格式

**定制合并后的步骤序列**（示例）：
```yaml
phase: plan
steps:
  - id: "scan_candidates"
    type: "detector"
    source: "default"
  
  - id: "select_changes"
    type: "action"
    source: "default"
  
  - id: "generate_proposal"
    type: "custom"              # 被替换为自定义技能
    source: "user"
    skill: "custom-planner"
    params:
      template: "detailed"
  
  - id: "compliance_review"     # 用户插入的步骤
    type: "custom"
    source: "user"
    skill: "compliance-review"
    trigger: "changes.any(has_compliance_impact)"
  
  - id: "generate_design"
    type: "action"
    source: "default"
  
  - id: "generate_tasks"
    type: "action"
    source: "default"
  
  - id: "analyze_deps"
    type: "action"
    source: "default"
  
  - id: "security_audit"        # 用户插入的步骤
    type: "custom"
    source: "user"
    skill: "security-review"
    trigger: "changes.any(has_security_impact)"
  
  - id: "commit_change"
    type: "action"
    source: "default"
```

## 备选方案

### 方案 A: 完全声明式流程 DSL

- **优点**: 完全灵活
- **缺点**: 学习成本高，版本兼容困难
- **决策**: 推迟到 v2.1（如果用户需求足够强烈）

### 方案 B: 仅支持阶段间 Hook

- **优点**: 实现简单
- **缺点**: 无法满足阶段内部定制需求
- **决策**: 拒绝（已选择方案 C）

### 方案 C: 阶段内步骤定制（当前选择）

- **优点**: 平衡灵活性和复杂度
- **缺点**: 实现复杂度中等
- **决策**: 采纳

