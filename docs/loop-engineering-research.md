# Loop 工程业界调研与 spec-workflow v2.0 借鉴方案

> **调研日期**: 2026-06-22  
> **调研范围**: Looper、Anthropic Agents、Claude Code /loop、OpenHands、SWE-Agent、Requesty  
> **目标**: 提取可借鉴到 spec-workflow v2.0 的设计模式

---

## 📊 调研项目概览

| 项目 | 类型 | 核心理念 | 适用场景 |
|------|------|---------|---------|
| **Looper** | Claude Code Skill | 设计先行 + 审判委员会 | 复杂代码迁移、持续审查 |
| **Anthropic Agents** | 框架指南 | 5 种工作流模式 + 增强模式 | 通用 AI Agent 开发 |
| **Claude Code /loop** | 内置命令 | 定时循环 + Routines | 定时任务、PR 监控 |
| **OpenHands** | 开放平台 | 多 Agent + 沙箱 + 工具链 | 企业级开发任务 |
| **SWE-Agent** | 研究项目 | 简单 Agent + SWE-bench | 自动化修复 GitHub Issues |
| **Requesty** | Loop 工程指南 | 5 大构建块 + 门控机制 | 自主 AI Agent 循环 |

---

## 🎯 核心设计模式提取

### 1️⃣ **设计先行模式** (来自 Looper)

#### 原始设计
Looper 强制用户在执行前完成三阶段设计：
1. **目标设计**: 明确产出物和完成标准
2. **验证设计**: 确定检查机制（脚本/模型/人工）
3. **控制设计**: 设置刹车机制（最大迭代、无进展终止）

#### 可借鉴到 spec-workflow v2.0

```json
// .rddf.json 增强 Schema
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
  },
  "verification_design": {
    "method": "multi_model",  // script | single_model | multi_model | human
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
  },
  "control_design": {
    "max_iterations": 100,
    "max_retries_per_action": 3,
    "stagnation_threshold": 5,  // 连续 5 次无进展 → 终止
    "error_budget": 10,  // 允许 10% 的失败率
    "circuit_breaker": {
      "enabled": true,
      "consecutive_failures": 3,
      "action": "escalate_to_human"
    }
  }
}
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 当前 ADR-0004 的 Loop 引擎只有 `max_iterations` 和 `max_retries`
- 应增加**完整的设计阶段**，让用户在执行前明确目标、验证、控制
- 引入**断路器模式** (circuit breaker)，连续失败时自动升级到人工

---

### 2️⃣ **审判委员会模式** (来自 Looper)

#### 原始设计
- 强制要求执行模型和审核模型不同
- 利用不同模型的"盲区差异"降低错误率
- 跨厂商数据脱敏处理

#### 可借鉴到 spec-workflow v2.0

```python
# skills/_lib/verification.py

class TribunalCommittee:
    """审判委员会：多模型交叉验证"""
    
    def __init__(self, config: VerificationConfig):
        self.execution_model = config.execution_model
        self.review_model = config.review_model
        self.require_different_vendors = config.require_different_vendors
    
    def verify_change(self, change_name: str, artifacts: dict) -> VerificationResult:
        """验证 change 质量"""
        # 1. 执行模型评估
        exec_result = self.call_model(
            model=self.execution_model,
            prompt=f"评估 change '{change_name}' 的实施质量...",
            artifacts=artifacts
        )
        
        # 2. 审核模型评估（必须不同厂商）
        if self.require_different_vendors:
            assert self.get_vendor(self.execution_model) != self.get_vendor(self.review_model)
        
        review_result = self.call_model(
            model=self.review_model,
            prompt=f"审查 change '{change_name}' 的代码质量和架构合规性...",
            artifacts=artifacts,
            # 数据脱敏
            sanitized=True
        )
        
        # 3. 综合判定
        if exec_result.score >= 0.8 and review_result.score >= 0.8:
            return VerificationResult(passed=True, scores={"exec": exec_result.score, "review": review_result.score})
        else:
            return VerificationResult(
                passed=False, 
                scores={"exec": exec_result.score, "review": review_result.score},
                feedback=f"执行模型评分: {exec_result.score}, 审核模型评分: {review_result.score}"
            )
    
    def call_model(self, model: str, prompt: str, **kwargs) -> ModelResult:
        """调用不同厂商模型"""
        vendor = self.get_vendor(model)
        if vendor == "anthropic":
            return self.call_anthropic(model, prompt, **kwargs)
        elif vendor == "openai":
            return self.call_openai(model, prompt, **kwargs)
        elif vendor == "ollama":
            return self.call_ollama(model, prompt, **kwargs)
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 当前 ADR-0005 的 human-in-loop 节点只考虑人工审核
- 应增加**多模型交叉验证**机制，特别适合自动化场景
- 在 hybrid 模式下，关键节点可以选择"人工审核"或"多模型审核"

---

### 3️⃣ **门控机制模式** (来自 Requesty Loop Engineering)

#### 原始设计
Requesty 提出 5 大 Loop 构建块：
1. **Goal**: 明确目标
2. **Plan**: 制定计划
3. **Execute**: 执行动作
4. **Verify**: 验证结果（门控）
5. **Adapt**: 自适应调整

关键：**Verify 阶段是门控**，验证失败则不进入下一阶段

#### 可借鉴到 spec-workflow v2.0

```python
# skills/_lib/gate.py

class GateMechanism:
    """门控机制：验证通过才允许继续"""
    
    def __init__(self, config: GateConfig):
        self.gates = {
            "arch_done": self.arch_gate,
            "plan_done": self.plan_gate,
            "ship_done": self.ship_gate
        }
    
    def arch_gate(self, state: StateVector) -> GateResult:
        """Arch 阶段门控"""
        checks = [
            Check(name="adr_exists", condition=len(state.arch_side.adr.files) >= 1),
            Check(name="roadmap_defined", condition=state.arch_side.roadmap.exists),
            Check(name="gap_analysis_complete", condition=state.arch_side.architecture.pending_gaps == 0)
        ]
        
        passed = all(c.condition for c in checks)
        return GateResult(phase="arch", passed=passed, checks=checks)
    
    def plan_gate(self, state: StateVector) -> GateResult:
        """Plan 阶段门控"""
        checks = [
            Check(name="changes_committed", condition=all(
                c.status == "committed" for c in state.plan_side.active_changes
            )),
            Check(name="artifacts_complete", condition=all(
                c.artifacts.get(".openspec.yaml") for c in state.plan_side.active_changes
            )),
            Check(name="deps_analyzed", condition=all(
                c.deps_analysis for c in state.plan_side.active_changes
            ))
        ]
        
        passed = all(c.condition for c in checks)
        return GateResult(phase="plan", passed=passed, checks=checks)
    
    def ship_gate(self, state: StateVector) -> GateResult:
        """Ship 阶段门控"""
        checks = [
            Check(name="worktrees_empty", condition=len(state.ship_side.worktrees) == 0),
            Check(name="archive_empty", condition=len(state.ship_side.pending_archive) == 0),
            Check(name="tests_pass", condition=self.verify_tests(state))
        ]
        
        passed = all(c.condition for c in checks)
        return GateResult(phase="ship", passed=passed, checks=checks)
    
    def verify_transition(self, from_phase: str, to_phase: str, state: StateVector) -> bool:
        """验证阶段切换是否允许"""
        gate = self.gates.get(f"{from_phase}_done")
        if not gate:
            return True  # 无门控
        
        result = gate(state)
        if not result.passed:
            # 门控失败，记录到事件流
            event_log.record("gate_failed", {
                "from_phase": from_phase,
                "to_phase": to_phase,
                "failed_checks": [c.name for c in result.checks if not c.condition]
            })
            return False
        
        return True
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 当前 ADR-0003 的阶段切换只有简单验证
- 应引入**严格的门控机制**，每个阶段完成必须通过检查清单
- 门控失败时自动记录到事件流，便于调试

---

### 4️⃣ **多 Agent 协作模式** (来自 OpenHands / SWE-Agent)

#### 原始设计
- **OpenHands**: 多 Agent 架构（执行 Agent + 验证 Agent + 规划 Agent）
- **SWE-Agent**: 简单 Agent + 工具链（文件编辑、测试运行、git 操作）
- **共同点**: 分离"执行"和"验证"角色

#### 可借鉴到 spec-workflow v2.0

```python
# skills/_lib/multi_agent.py

class MultiAgentCoordinator:
    """多 Agent 协调器"""
    
    def __init__(self, config: AgentConfig):
        self.agents = {
            "executor": Agent(role="executor", model=config.executor_model),
            "verifier": Agent(role="verifier", model=config.verifier_model),
            "planner": Agent(role="planner", model=config.planner_model)
        }
    
    def execute_change(self, change_name: str) -> ExecutionResult:
        """多 Agent 协作执行 change"""
        # 1. Planner Agent 制定计划
        plan = self.agents["planner"].plan(
            goal=f"Implement change '{change_name}'",
            context=self.get_change_context(change_name)
        )
        
        # 2. Executor Agent 执行
        exec_result = self.agents["executor"].execute(plan)
        
        # 3. Verifier Agent 验证
        verify_result = self.agents["verifier"].verify(
            change_name=change_name,
            artifacts=exec_result.artifacts,
            criteria=plan.success_criteria
        )
        
        # 4. 综合判定
        if verify_result.passed:
            return ExecutionResult(success=True, agent_scores={
                "planner": plan.quality_score,
                "executor": exec_result.quality_score,
                "verifier": verify_result.score
            })
        else:
            # 验证失败，Planner 重新规划
            revised_plan = self.agents["planner"].revise(plan, verify_result.feedback)
            return self.execute_with_revised_plan(change_name, revised_plan)
```

**借鉴价值**: ⭐⭐⭐⭐
- 当前 ADR-0004 的 Loop 引擎是单 Agent（Loop 引擎本身）
- 应引入**多 Agent 协作**，特别是在 loop 模式下
- Planner → Executor → Verifier 三轮协作，提高质量

---

### 5️⃣ **可视化流程图模式** (来自 Looper)

#### 原始设计
Looper 在执行前生成 ASCII 流程图：
```
目标 -> 计划 -> 门控 -> 交付 -> 门控 -> 最终输出
```

#### 可借鉴到 spec-workflow v2.0

```python
# skills/_lib/visualization.py

def generate_flowchart(goal: str, config: LoopConfig) -> str:
    """生成 ASCII 流程图"""
    flowchart = f"""
=== Loop 执行流程图 ===

目标: {goal}

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
✅ 目标达成: {goal}

控制参数:
  - 最大迭代次数: {config.loop.max_iterations}
  - 最大重试次数: {config.loop.max_retries}
  - 断路器: {config.control.circuit_breaker.enabled}
"""
    return flowchart
```

**借鉴价值**: ⭐⭐⭐⭐
- 在执行前显示流程图，让用户清晰理解整个流程
- 特别适合 hybrid 模式，帮助用户理解哪些节点需要人工确认

---

### 6️⃣ **定时循环模式** (来自 Claude Code /loop + Routines)

#### 原始设计
- Claude Code `/loop` 命令：定时触发循环任务
- Routines：后台持续运行的 Agent，监听 Git 提交、PR 等事件

#### 可借鉴到 spec-workflow v2.0

```json
// .rddf.json 定时任务配置
{
  "scheduled_loops": [
    {
      "name": "daily-code-review",
      "schedule": "0 9 * * *",  // 每天 9:00
      "goal": "review all commits from yesterday",
      "mode": "loop",
      "config": {
        "trigger": "git_commits",
        "time_range": "last_24h",
        "review_model": "gpt-4o",
        "output": ".rddf/state/code-reports/daily-review.md"
      }
    },
    {
      "name": "weekly-arch-audit",
      "schedule": "0 10 * * 1",  // 每周一 10:00
      "goal": "audit ADR compliance and roadmap progress",
      "mode": "hybrid",
      "config": {
        "checks": [
          "adr_compliance",
          "roadmap_progress",
          "stale_worktrees"
        ],
        "escalate_on_failure": true
      }
    }
  ]
}
```

**借鉴价值**: ⭐⭐⭐⭐
- 当前 spec-workflow 只有手动触发
- 应支持**定时循环**，如每日代码审查、每周架构审计
- 可与 GitHub Actions 集成，实现 CI/CD 自动化

---

### 7️⃣ **记忆与上下文模式** (来自 OpenHands / Anthropic Agents)

#### 原始设计
- **OpenHands**: 跨会话记忆（保存执行痕迹、失败原因、修复方案）
- **Anthropic Agents**: 上下文管理（工具使用历史、环境变量、文件状态）

#### 可借鉴到 spec-workflow v2.0

```python
# skills/_lib/memory.py

class LoopMemory:
    """Loop 记忆系统"""
    
    def __init__(self, project_root: Path):
        self.memory_file = project_root / ".zcf" / "loop-memory.json"
        self.memories = self.load()
    
    def record_execution(self, change_name: str, result: ExecutionResult):
        """记录执行痕迹"""
        memory = {
            "timestamp": datetime.utcnow().isoformat(),
            "change": change_name,
            "success": result.success,
            "iterations": result.iterations,
            "errors": result.errors,
            "retry_count": result.retry_count,
            "final_score": result.quality_score
        }
        self.memories["executions"].append(memory)
        self.save()
    
    def learn_from_failures(self) -> List[Insight]:
        """从失败中学习"""
        failures = [m for m in self.memories["executions"] if not m["success"]]
        
        insights = []
        # 分析常见失败模式
        error_patterns = self.analyze_error_patterns(failures)
        for pattern in error_patterns:
            insights.append(Insight(
                type="error_pattern",
                description=f"常见失败模式: {pattern.error}",
                suggestion=f"建议: {pattern.suggestion}",
                confidence=pattern.confidence
            ))
        
        return insights
    
    def suggest_loop_config(self, goal: str) -> LoopConfig:
        """基于历史数据推荐配置"""
        similar_executions = self.find_similar_executions(goal)
        
        if similar_executions:
            avg_iterations = np.mean([e["iterations"] for e in similar_executions])
            avg_retries = np.mean([e["retry_count"] for e in similar_executions])
            
            return LoopConfig(
                max_iterations=int(avg_iterations * 1.5),  # 1.5x 安全边际
                max_retries=int(avg_retries * 2),
                parallel_limit=self.recommend_parallel_limit(similar_executions)
            )
        else:
            return LoopConfig.default()
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 当前 ADR-0006 的事件流只记录事件，不记录"学习"
- 应增加**记忆系统**，从历史执行中学习
- 基于历史数据自动推荐 Loop 配置，降低用户使用门槛

---

### 8️⃣ **便携规范模式** (来自 Looper)

#### 原始设计
- `loop.yaml`: 人类可读的循环规范
- `loop.resolved.json`: 机器可解析的完整配置
- `run-loop.py`: 独立的 Python 运行器

#### 可借鉴到 spec-workflow v2.0

```yaml
# loop.yaml 示例
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
  
verification:
  method: "multi_model"
  execution_model: "claude-sonnet-4"
  review_model: "gpt-4o"

control:
  circuit_breaker:
    enabled: true
    consecutive_failures: 3
    action: "escalate_to_human"
  
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

**借鉴价值**: ⭐⭐⭐⭐
- 当前 ADR-0002 的配置文件是 `.rddf.json`
- 应同时支持 `loop.yaml`（人类可读）和 JSON（机器可读）
- `loop.yaml` 可纳入版本控制，团队共享最佳实践

---

## 📈 综合借鉴方案

### 优先级排序

| 借鉴项 | 优先级 | 实施难度 | 价值 | 预计工作量 |
|--------|--------|---------|------|-----------|
| **门控机制** | P0 | 低 | ⭐⭐⭐⭐⭐ | 2-3 天 |
| **设计先行** | P0 | 中 | ⭐⭐⭐⭐⭐ | 3-4 天 |
| **记忆系统** | P1 | 中 | ⭐⭐⭐⭐⭐ | 4-5 天 |
| **审判委员会** | P1 | 高 | ⭐⭐⭐⭐⭐ | 5-7 天 |
| **多 Agent 协作** | P1 | 高 | ⭐⭐⭐⭐ | 5-7 天 |
| **可视化流程图** | P2 | 低 | ⭐⭐⭐⭐ | 2-3 天 |
| **便携规范 (YAML)** | P2 | 低 | ⭐⭐⭐⭐ | 2-3 天 |
| **定时循环** | P2 | 中 | ⭐⭐⭐ | 3-4 天 |

### 增强后的 ADR 更新建议

#### ADR-0004 增强 (Loop 引擎)

增加以下组件：
1. **GateMechanism**: 门控机制（P0）
2. **DesignPhase**: 设计先行阶段（P0）
3. **LoopMemory**: 记忆系统（P1）
4. **TribunalCommittee**: 审判委员会（P1）
5. **MultiAgentCoordinator**: 多 Agent 协调（P1）
6. **FlowchartGenerator**: 可视化流程图（P2）

#### ADR-0005 增强 (Human-in-Loop)

增加验证模式选项：
```
human_in_loop_nodes:
  - node: "ship.archive_confirm"
    verification_mode: "human | multi_model | script"
    review_model: "gpt-4o"  # multi_model 模式
    review_criteria: [...]
```

#### ADR-0006 增强 (状态向量)

增加记忆字段：
```json
{
  "memory": {
    "executions": [
      {"change": "add-auth", "success": true, "iterations": 5, "score": 0.9}
    ],
    "learned_insights": [
      {"type": "error_pattern", "description": "...", "suggestion": "..."}
    ],
    "recommended_configs": {
      "complete_all_changes": {"max_iterations": 50, "max_retries": 3}
    }
  }
}
```

---

## 🎓 业界最佳实践总结

### Anthropic 5 种工作流模式

1. **Prompt Chaining**: 顺序执行多个 prompt
2. **Routing**: 根据输入选择不同路径
3. **Parallelization**: 并行执行多个任务
4. **Orchestrator-Workers**: 主 Agent 协调子 Agent
5. **Evaluator-Optimizer**: 评估器 + 优化器循环

**借鉴**: spec-workflow v2.0 的 Loop 引擎应支持这 5 种模式的组合

### Requesty 5 大构建块

1. **Goal**: 明确目标
2. **Plan**: 制定计划
3. **Execute**: 执行动作
4. **Verify**: 验证结果（门控）
5. **Adapt**: 自适应调整

**借鉴**: 这与我们 ADR-0004 的 Loop 引擎设计完全一致，验证了方向正确

### Looper 核心创新

1. **设计先行**: 执行前强制设计目标/验证/控制
2. **审判委员会**: 多模型交叉验证
3. **便携规范**: `loop.yaml` 可版本控制

**借鉴**: 这三点是 Looper 最独特的贡献，应优先借鉴

---

## 🚀 下一步行动

1. **更新 ADR-0004**: 增加门控机制、设计先行、记忆系统
2. **更新 ADR-0005**: 增加多模型验证模式
3. **更新 ADR-0006**: 增加记忆字段
4. **创建 `loop.yaml` Schema**: 定义便携规范格式
5. **实现 GateMechanism**: 作为 Phase 1 的优先任务
6. **实现 DesignPhase**: 作为 Loop 引擎的前置阶段

---

**调研结论**: spec-workflow v2.0 的 Loop 引擎设计方向与业界最佳实践高度一致（Requesty 5 大构建块、Anthropic 工作流模式）。应重点借鉴 Looper 的"设计先行"、"审判委员会"和"便携规范"三大创新，进一步提升架构的严谨性和用户体验。

