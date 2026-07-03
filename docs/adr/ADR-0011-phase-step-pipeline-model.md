# ADR-0011: 阶段步骤化执行模型

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0004 (Loop 引擎), ADR-0003 (三阶段架构), ADR-0007 (门控机制)

## Context

在 ADR-0004 中，我们定义了 Loop 引擎的 **Detector-Action 架构**，其中阶段（arch/plan/ship）作为 Loop 引擎的**执行目标**，通过动态匹配 `match_actions()` 决定执行哪些 action。但在 ADR-0004 的设计中：

**每个阶段是一个黑盒**：
```
Loop 引擎
  ├─ 扫描状态 → 检测到需要 plan 阶段
  ├─ 生成计划 → [action_create_worktree, action_generate_plan, ...]
  └─ 执行 → 调用 guide-plan（整个阶段作为一个黑盒）
               └─ 内部子步骤不可见、不可控制
```

**用户需求**：
1. **在阶段内部插入自定义步骤**（如 plan 阶段插入合规审查）
2. **用自定义技能替代默认技能**（如用 custom-planner 替代 prometheus-planning）
3. **在阶段内部设置条件触发**（如只在安全相关 change 时触发安全审查）

**核心冲突**：
- ADR-0004 使用**动态匹配**范式：运行时根据状态决定执行什么
- 定制流程需要**预定义序列**范式：按配置顺序执行步骤

如果不解决这个冲突，任何定制能力都无法在现有 Loop 引擎上安全实现。

## Decision

我们引入 **步骤化执行模型 (Step Pipeline Model)**，将每个阶段从"黑盒"拆分为**可编排的步骤序列**，同时保持与 ADR-0004 的兼容：

### 核心设计：模板 + 触发器模式

```
┌────────────────────────────────────────────────────────────────┐
│                        Loop Engine                              │
│                                                                  │
│  scan_state()                                                    │
│    → 检测到 change 需要 plan 阶段                                │
│    → 触发 plan 阶段模板                                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Phase Template: plan                                    │   │
│  │                                                          │   │
│  │  Step 1: detect_candidates (detector)                   │   │
│  │  Step 2: select_changes (action)                        │   │
│  │  Step 3: generate_proposal (action)                     │   │
│  │  Step 4: generate_design (action)                       │   │
│  │  Step 5: generate_tasks (action)                        │   │
│  │  Step 6: analyze_deps (action)                          │   │
│  │  Step 7: commit_change (action)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  执行后：触发门控检查（ADR-0007）                                │
└────────────────────────────────────────────────────────────────┘
```

**关键设计原则**：

1. **阶段模板是默认步骤序列**：每个阶段有预定义的步骤列表，定义该阶段的"正常流程"
2. **Loop 引擎触发模板**：`match_actions()` 不再直接调用 action，而是触发对应的阶段模板
3. **步骤模板可跳过已完成步骤**：执行前扫描状态，跳过已完成的步骤（支持中断恢复）
4. **门控保持不变**：阶段间门控（ADR-0007）在模板执行完后触发

### 与 ADR-0004 的关系

| 场景 | ADR-0004 原始设计 | ADR-0011 修订后 |
|------|-------------------|----------------|
| **扫描状态** | `detect_pending_changes()` → 检测到 change | 不变 |
| **生成计划** | `match_actions()` → `[action_create_worktree, ...]` | `match_actions()` → `trigger_phase("plan")` |
| **执行** | 直接调用 action（黑盒） | 执行阶段模板的步骤序列 |
| **多个 changes** | 并行匹配多个 action | 为每个 change 启动独立的步骤模板实例 |

**修订内容**：
```python
# ADR-0004 始 match_actions()
def match_actions(self, detection):
    if detection.type == "pending_changes":
        return [action_create_worktree(change["name"]) for change in detection.data["changes"]]

# ADR-0011 修订后
def match_actions(self, detection):
    if detection.type == "pending_changes":
        return [trigger_phase("plan", change["name"]) for change in detection.data["changes"]]
    elif detection.type == "worktrees":
        return [trigger_phase("ship", wt["name"]) for wt in detection.data["active"]]
    elif detection.type == "architecture_needs_update":
        return [trigger_phase("arch")]
```

### 步骤模板定义

每个阶段的模板定义在 `skills/_lib/phase_templates.yaml`：

```yaml
# skills/_lib/phase_templates.yaml
version: "2.0"

templates:
  arch:
    description: "架构定义阶段"
    steps:
      - id: "scan_architecture"
        type: "detector"
        module: "detectors"
        function: "detect_architecture"
        
      - id: "identify_gaps"
        type: "detector"
        module: "detectors"
        function: "detect_gaps"
        
      - id: "create_adr"
        type: "action"
        module: "actions"
        function: "action_create_adr"
        
      - id: "define_roadmap"
        type: "action"
        module: "actions"
        function: "action_define_roadmap"
        
      - id: "output_docs"
        type: "action"
        module: "actions"
        function: "action_output_arch_docs"

  plan:
    description: "变更生成阶段"
    steps:
      - id: "scan_candidates"
        type: "detector"
        module: "detectors"
        function: "detect_candidates"
        
      - id: "select_changes"
        type: "action"
        module: "actions"
        function: "action_select_changes"
        
      - id: "generate_proposal"
        type: "action"
        module: "actions"
        function: "action_generate_proposal"
        
      - id: "generate_design"
        type: "action"
        module: "actions"
        function: "action_generate_design"
        
      - id: "generate_tasks"
        type: "action"
        module: "actions"
        function: "action_generate_tasks"
        
      - id: "analyze_deps"
        type: "action"
        module: "actions"
        function: "action_analyze_deps"
        
      - id: "commit_change"
        type: "action"
        module: "actions"
        function: "action_commit_change"

  ship:
    description: "变更执行阶段"
    steps:
      - id: "select_change"
        type: "action"
        module: "actions"
        function: "action_select_change_for_ship"
        
      - id: "create_worktree"
        type: "action"
        module: "actions"
        function: "action_create_worktree"
        
      - id: "generate_plan"
        type: "action"
        module: "actions"
        function: "action_generate_plan"
        
      - id: "execute_units"
        type: "action"
        module: "actions"
        function: "action_execute_worktree"
        
      - id: "run_tests"
        type: "action"
        module: "actions"
        function: "action_run_tests"
        
      - id: "merge_to_main"
        type: "action"
        module: "actions"
        function: "action_merge_to_main"
        
      - id: "archive_change"
        type: "action"
        module: "actions"
        function: "action_archive_change"
        
      - id: "cleanup_worktree"
        type: "action"
        module: "actions"
        function: "action_cleanup_worktree"
```

### 步骤类型

| 类型 | 说明 | 输入 | 输出 |
|------|------|------|------|
| `detector` | 状态检测，不改变状态 | 无 | `DetectionResult` |
| `action` | 执行操作，改变状态 | 上下文数据 | `ActionResult` |
| `custom` | 自定义步骤（ADR-0012 定义） | 上下文数据 | `StepResult` |

### 步骤执行引擎

```python
# skills/_lib/step_pipeline.py

class StepPipeline:
    """阶段步骤执行引擎"""
    
    def __init__(self, template: PhaseTemplate, state: StateVector, change_name: str = None):
        self.template = template
        self.state = state
        self.change_name = change_name
        self.context = StepContext()  # 步骤间共享数据
        self.event_log = EventLog()
    
    def execute(self) -> PipelineResult:
        """执行步骤序列"""
        # 1. 跳过已完成步骤（支持中断恢复）
        steps_to_run = self.skip_completed(self.template.steps)
        
        # 2. 顺序执行
        for step in steps_to_run:
            self.event_log.record("step_started", {
                "phase": self.template.name,
                "step": step.id,
                "change": self.change_name
            })
            
            # 执行步骤
            result = self.execute_step(step)
            
            # 记录事件
            self.event_log.record("step_completed", {
                "phase": self.template.name,
                "step": step.id,
                "success": result.success
            })
            
            # 处理失败
            if not result.success:
                return PipelineResult(
                    success=False,
                    failed_step=step.id,
                    error=result.error
                )
            
            # 更新上下文
            if result.data:
                self.context.update(result.data)
        
        return PipelineResult(success=True)
    
    def skip_completed(self, steps: List[StepDefinition]) -> List[StepDefinition]:
        """跳过已完成步骤（基于状态向量）"""
        remaining = []
        for step in steps:
            if self.is_step_completed(step):
                self.event_log.record("step_skipped", {
                    "step": step.id,
                    "reason": "already_completed"
                })
                continue
            remaining.append(step)
        return remaining
    
    def is_step_completed(self, step: StepDefinition) -> bool:
        """判断步骤是否已完成"""
        if step.type == "detector":
            return False  # detector 总是执行
        
        # 基于状态判断 action 是否已完成
        if step.id == "create_worktree":
            return self.change_name in [wt.name for wt in self.state.ship_side.worktrees]
        elif step.id == "generate_proposal":
            change = self.get_change(self.change_name)
            return change and change.artifacts.get("proposal")
        elif step.id == "execute_units":
            change = self.get_change(self.change_name)
            return change and change.progress == 1.0
        # ... 更多判断规则
        
        return False
    
    def execute_step(self, step: StepDefinition) -> StepResult:
        """执行单个步骤"""
        if step.type == "detector":
            return self.execute_detector(step)
        elif step.type == "action":
            return self.execute_action(step)
        elif step.type == "custom":
            return self.execute_custom(step)
        else:
            raise ValueError(f"Unknown step type: {step.type}")
    
    def execute_detector(self, step: StepDefinition) -> StepResult:
        """执行 detector 步骤"""
        func = self.load_function(step.module, step.function)
        result = func(self.state, self.change_name)
        self.context.set(step.id, result)
        return StepResult(success=True, data={step.id: result})
    
    def execute_action(self, step: StepDefinition) -> StepResult:
        """执行 action 步骤"""
        func = self.load_function(step.module, step.function)
        result = func(self.state, self.context, self.change_name)
        
        if result.success:
            self.context.set(step.id, result.data)
            return StepResult(success=True, data={step.id: result.data})
        else:
            return StepResult(success=False, error=result.error)
    
    def execute_custom(self, step: StepDefinition) -> StepResult:
        """执行自定义步骤（ADR-0012 定义）"""
        # 在 ADR-0012 中实现
        pass
```

### 与门控机制的关系（ADR-0007）

门控检查在**阶段模板执行完后**触发，不受步骤化影响：

```
arch 模板执行完毕
  ├─ 步骤 1-5 全部成功
  └─ 触发 arch_done 门控（ADR-0007）
      ├─ 检查清单：ADR 已保存、Roadmap 已更新、...
      └─ 门控通过 → 进入 plan 阶段
```

门控检查**不关心**步骤内部是如何执行的，只关心阶段输出是否符合要求。

### 事件流扩展

步骤化执行增加了细粒度的事件记录：

```jsonl
{"ts": "2026-06-22T10:00:00Z", "type": "phase_started", "phase": "plan", "change": "add-auth"}
{"ts": "2026-06-22T10:00:01Z", "type": "step_started", "phase": "plan", "step": "scan_candidates", "change": "add-auth"}
{"ts": "2026-06-22T10:00:02Z", "type": "step_completed", "phase": "plan", "step": "scan_candidates", "success": true}
{"ts": "2026-06-22T10:00:03Z", "type": "step_started", "phase": "plan", "step": "select_changes", "change": "add-auth"}
{"ts": "2026-06-22T10:00:04Z", "type": "step_completed", "phase": "plan", "step": "select_changes", "success": true}
{"ts": "2026-06-22T10:00:05Z", "type": "step_started", "phase": "plan", "step": "generate_proposal", "change": "add-auth"}
{"ts": "2026-06-22T10:00:10Z", "type": "step_completed", "phase": "plan", "step": "generate_proposal", "success": true}
...
{"ts": "2026-06-22T10:01:00Z", "type": "phase_completed", "phase": "plan", "change": "add-auth"}
```

### 中断恢复

步骤化模型天然支持中断恢复：

```
场景：执行 plan 阶段时中断（generate_design 步骤）
  → 状态向量记录：phase = "plan", last_step = "generate_proposal"

恢复执行：
  → 加载 plan 模板
  → 跳过已完成步骤（scan_candidates, select_changes, generate_proposal）
  → 从 generate_design 继续执行
```

## Consequences

### 正面影响

1. **阶段内部可观测**：每个步骤的执行状态、结果都记录到事件流
2. **支持中断恢复**：可跳过已完成步骤，从断点继续
3. **为定制能力提供基础**：ADR-0012 可在步骤模板中插入自定义步骤
4. **向后兼容**：不配置定制规则时，行为与当前完全一致
5. **与 ADR-0004 兼容**：保留了动态匹配的触发机制，只是执行层改为步骤化

### 负面影响

1. **执行复杂度增加**：步骤引擎增加了 ~500 行代码
2. **配置复杂度增加**：需要维护 phase_templates.yaml
3. **调试难度增加**：步骤间状态传递需要跟踪 StepContext

### 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| 步骤执行性能下降 | 步骤间无额外开销（直接调用函数） |
| 模板维护成本 | 模板版本化，升级时提供迁移工具 |
| 状态判断不准确 | 完善的单元测试覆盖 is_step_completed() 逻辑 |

## Artifacts

| 文件 | 描述 | 行数估算 |
|------|------|---------|
| `skills/_lib/phase_templates.yaml` | 阶段步骤模板定义 | ~120 |
| `skills/_lib/step_pipeline.py` | 步骤执行引擎 | ~350 |
| `skills/_lib/step_context.py` | 步骤间共享数据 | ~80 |
| `skills/loop-engine.py` | 修订 match_actions() | ~20（修订） |
| 单元测试 | 步骤执行、跳过、恢复 | ~400 |

## 评估标准

1. **向后兼容**：不配置定制规则时，`loop-engine` 的行为与当前完全一致
2. **中断恢复**：中断后恢复执行，能正确跳过已完成步骤
3. **事件记录**：每个步骤的开始/完成/跳过都记录到事件流
4. **性能无下降**：步骤化执行的总时间与当前黑盒执行时间相当

## 输出格式

**修订后的状态向量**：
```json
{
  "loop_state": {
    "current_phase": "plan",
    "current_change": "add-auth",
    "current_step": "generate_design",
    "step_history": [
      {"phase": "plan", "step": "scan_candidates", "status": "completed"},
      {"phase": "plan", "step": "select_changes", "status": "completed"},
      {"phase": "plan", "step": "generate_proposal", "status": "completed"}
    ]
  }
}
```

## 备选方案

### 方案 A: 保持阶段黑盒，仅支持阶段间 Hook

- **优点**: 实现简单
- **缺点**: 无法满足阶段内部定制需求
- **决策**: 拒绝

### 方案 B: 完全重写 Loop 引为声明式流程

- **优点**: 完全灵活
- **缺点**: 与 ADR-0004 冲突，需要废弃现有架构
- **决策**: 拒绝

