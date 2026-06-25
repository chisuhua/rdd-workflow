# Loop Engine 用户指南

> **版本**: 2.0.0
> **日期**: 2026-06-25
> **对应代码**: `skills/loop-engine.py` + `skills/_lib/{detectors,actions,interaction_modes,human_nodes,design_phase,flowchart}.py`

---

## 概述

v2.0 Loop Engine 是 spec-workflow 的 AI-native 执行引擎，替代 v1.x 的静态状态机。它通过一个 5+1 块循环自动驱动工作流前进，并在关键决策点暂停人类输入。

```
verify_goal → scan_state → generate_plan → execute_plan → verify_results → adapt
                       ↑                                          │
                       └──────────────────────────────────────────┘
```

---

## 快速开始

```python
from skills.loop_engine import LoopEngine
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog

# 加载状态向量与事件日志
engine = LoopEngine(
    state=StateVector.load(".spec-workflow/state-vector.json"),
    event_log=EventLog(".spec-workflow/event-log.jsonl"),
)

# 运行循环，直到目标达成或安全机制触发
# 目标谓词使用点路径表达式，对 state.to_dict() 求值
status = engine.run(goal_predicate="plan_side['active_change'] is None")
```

---

## 5+1 构件循环

| 构件 | 职责 | 关键方法 |
|---|---|---|
| `verify_goal` | 评估目标谓词 | `engine.verify_goal(predicate) -> bool` |
| `scan_state` | 运行所有 detector 收集当前状态 | `all_detectors() → [Detector]` |
| `generate_plan` | 将 detector 结果映射到 action | `1:1 mapping by type` |
| `execute_plan` | 按重试策略执行 action | `action.execute(params, event_log)` |
| `verify_results` | 检查所有 action 是否成功 | 返回 bool |
| `adapt` | 更新 phase 标记 | 设置 `loop_state.current_phase` |

---

## 交互模式

3 种模式通过 `loop.yaml` 或运行时参数选择：

| 模式 | 行为 | 适用场景 |
|---|---|---|
| `loop` | 完全自主；除错误外不暂停 | CI/CD、批处理 |
| `menu` | 每个决策点都暂停 | 学习、调试 |
| `hybrid` (默认) | 例行操作自动；配置的人机节点暂停 | 通用 |

### 通过 `loop.yaml` 配置

```yaml
interaction:
  mode: hybrid
  human_nodes:
    - arch.adr_create
    - ship.archive_confirm
```

### 运行时覆盖

```python
from skills._lib.interaction_modes import LoopMode
from skills._lib.human_nodes import HumanNodeRegistry

engine = LoopEngine(
    state=sv, event_log=el,
    mode=LoopMode(HumanNodeRegistry()),  # 强制 loop 模式
)
```

或环境变量：`SPEC_WORKFLOW_MODE=loop`

---

## 7 个人机节点

| 节点 | 默认验证模式 | 触发时机 |
|---|---|---|
| `arch.adr_create` | human | 创建新 ADR 前 |
| `arch.roadmap_define` | human | 修改 roadmap 前 |
| `plan.change_select` | human | 选择活跃 change 前 |
| `plan.propose_confirm` | human | 确认 proposal 前 |
| `ship.archive_confirm` | human | 归档前 |
| `ship.cleanup_confirm` | script | 清理陈旧分支前 |
| `ship.execute_error` | human | 执行错误时 |

**3 种验证模式**:
- `human`: 暂停等待用户输入（调用方处理 UI）
- `multi_model`: 调用 Tribunal（待 v2-advanced-features，暂抛 `NotImplementedError`）
- `script`: 执行配置的 Python 命令，退出码判定

---

## 4 重安全机制

| 机制 | 默认 | 触发 | 退出状态 |
|---|---|---|---|
| 最大迭代 | 100 | iteration ≥ max | `MAX_ITERATIONS_EXCEEDED` |
| 最大重试 | 3 | 同 action 重试 3 次 | `MAX_RETRIES_EXCEEDED` |
| 振荡检测 | 5 iter / ≤2 distinct | 窗口匹配 | `OSCILLATION_DETECTED` |
| 断路器 | 3 连续失败 | 计数 ≥ 3 | `CIRCUIT_BROKEN` |
| 动作超时 | 30 分钟 | 实际超时 | `ActionResult(success=False, error="timeout")` |

所有安全机制均在引擎层强制，无 action 可绕过。

---

## 设计优先阶段（Design-First Phase）

循环启动前可选运行 `DesignPhase`，让用户确认/修改三个设计维度：

```python
from skills._lib.design_phase import DesignPhase, DesignResult

dp = DesignPhase(state=sv, event_log=el)
# 默认维度：goal / verification / control
result = DesignResult(
    goal={"deliverables": ["impl X"], "completion_criteria": "X tests pass"},
    verification={"executor": "deep", "reviewer": "oracle"},
    control={"max_iterations": 50, "max_retries": 2, "oscillation_threshold": 3},
)
dp.apply(result)  # 持久化到 state.loop_state.design
```

---

## 实时流程图

```python
from skills._lib.flowchart import FlowchartGenerator

fc = FlowchartGenerator(state=sv, event_log=el)
print(fc.render())  # < 100ms
```

输出示例：

```
┌─ Loop Engine Progress ─────────────────────────┐
│ Iteration: 7                                   │
│ Gate:      ok                                  │
│ Phase:     [4] Execute Plan                    │
│                                                │
│ Flow:                                          │
│   verify_goal → scan_state → generate_plan     │
│        ↓                                       │
│   execute_plan → verify_results → adapt       │
│        ↓                                       │
│   (loop or exit)                               │
│                                                │
│ Recent errors (1):                             │
│   ! action_create_worktree failed              │
└────────────────────────────────────────────────┘
```

---

## 插件扩展

### 自定义 Detector

在 `.spec-workflow/detectors/` 目录下放一个 Python 文件：

```python
# .spec-workflow/detectors/my_detector.py
from skills._lib.detectors import Detector, DetectionResult

class MyCustomDetector(Detector):
    name = "my_custom"

    def detect(self, state: dict) -> DetectionResult:
        return DetectionResult(
            type="my_custom",
            data={"key": "value"},
            message="my custom check passed",
            severity="info",
        )
```

下次循环启动时自动注册，与内建 detector 一起运行。

### 自定义 Action

在 `.spec-workflow/actions/` 目录下放一个 Python 文件：

```python
# .spec-workflow/actions/my_action.py
from skills._lib.actions import Action, ActionResult

class MyCustomAction(Action):
    name = "action_my_custom"

    def execute(self, params: dict, event_log) -> ActionResult:
        # ... 你的逻辑 ...
        return ActionResult(success=True, data={"result": "ok"})
```

---

## 目标谓词语法

`engine.verify_goal(predicate)` 使用受限的 `eval()` 对 `state.to_dict()` 求值。表达式必须使用点路径访问嵌套字段。

**有效示例**:
- `"plan_side['active_change'] is None"` — 检查无活跃 change
- `"len(ship_side['progress']['completed']) == 5"` — 检查完成数
- `"arch_side['phase'] == 'done' and loop_state['mode'] != 'idle'"` — 复合条件

**安全说明**: `__builtins__` 已禁用，仅可访问 `state.to_dict()` 的字段。

---

## 故障排查

| 现象 | 可能原因 | 解决方案 |
|---|---|---|
| `OSCILLATION_DETECTED` 立即触发 | 最近 5 iter 状态相同 | 检查 plan 生成是否真的产生新 action |
| `MAX_ITERATIONS_EXCEEDED` 很快退出 | `max_iterations` 配置过小 | 在 loop.yaml 中调大 |
| `MultiModelUnavailableError` | 用了 `multi_model` 验证 | 切换到 `human` 或 `script`；等待 v2-advanced-features |
| `ActionResult(success=False, error="timeout")` | action 超过 30 分钟 | 拆分 action 或调大 `action_timeout_seconds` |

---

## 下一步

- **v2-advanced-features**: Tribunal (multi-model verification), Memory, Session agents
- **v2-migration-and-tests**: v1.x → v2.x 迁移指南 + 测试套件
- **v2-beta-release**: 正式版发布管理

详细 API 参考见 `docs/v2-api-reference.md`。
