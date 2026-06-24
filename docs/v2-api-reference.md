# spec-workflow v2.0 API 参考文档

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **语言**: Python 3.8+

---

## 📋 目录

- [state_vector.py](#state_vectorpy)
- [event_log.py](#event_logpy)
- [loop_engine.py](#loop_enginepy)
- [session_v20.py](#session_v20py)
- [gate.py](#gatepy)
- [tribunal.py](#tribunalpy)
- [memory.py](#memorypy)

---

## state_vector.py

状态向量模块，管理 spec-workflow 的单一真相源。

### 类: `StateVector`

#### `__init__(path: str = ".zcf/state-vector.json")`

初始化状态向量。

**参数**:
- `path`: 状态向量文件路径

**示例**:
```python
from state_vector import StateVector

sv = StateVector(".zcf/state-vector.json")
```

---

#### `load() -> dict`

加载状态向量。

**返回**:
- `dict`: 状态向量数据

**示例**:
```python
state = sv.load()
print(state["version"])  # "2.0"
```

---

#### `save(state: dict) -> None`

保存状态向量。

**参数**:
- `state`: 状态向量数据

**示例**:
```python
state["arch_side"]["adr"].append({
    "id": "ADR-0010",
    "title": "Multi-session management"
})
sv.save(state)
```

---

#### `lock() -> contextmanager`

获取文件锁（线程安全）。

**返回**:
- `contextmanager`: 锁上下文管理器

**示例**:
```python
with sv.lock():
    state = sv.load()
    state["plan_side"]["active_changes"].append(new_change)
    sv.save(state)
```

---

#### `update_field(field_path: str, value: Any) -> None`

更新指定字段。

**参数**:
- `field_path`: 字段路径（点分隔）
- `value`: 新值

**示例**:
```python
sv.update_field("arch_side.roadmap.completion", 0.60)
sv.update_field("plan_side.active_changes", [])
```

---

#### `get_field(field_path: str, default: Any = None) -> Any`

获取指定字段。

**参数**:
- `field_path`: 字段路径（点分隔）
- `default`: 默认值

**返回**:
- `Any`: 字段值

**示例**:
```python
completion = sv.get_field("arch_side.roadmap.completion", 0.0)
changes = sv.get_field("plan_side.active_changes", [])
```

---

#### `reset() -> None`

重置状态向量到初始状态。

**示例**:
```python
sv.reset()
```

---

### 状态向量 Schema

```json
{
  "version": "2.0",
  "arch_side": {
    "adr": [],
    "roadmap": {
      "exists": false,
      "completion": 0.0,
      "phases": [],
      "changes": []
    },
    "architecture": {
      "current": {},
      "target": {},
      "pending_gaps": 0
    }
  },
  "plan_side": {
    "active_changes": [],
    "deps_analysis": {
      "complete": false,
      "graph": {}
    }
  },
  "ship_side": {
    "worktrees": [],
    "archive": []
  },
  "memory": {
    "enabled": true,
    "executions": [],
    "failure_patterns": [],
    "config_recommendations": {}
  },
  "session_info": {
    "session_id": null,
    "parent_session": null,
    "role": "coordinator",
    "status": "idle",
    "assigned_changes": [],
    "progress": 0.0
  },
  "sub_sessions": []
}
```

---

## event_log.py

事件流模块，记录所有状态变更事件。

### 类: `EventLog`

#### `__init__(path: str = ".zcf/event-log.jsonl")`

初始化事件流。

**参数**:
- `path`: 事件流文件路径

---

#### `append(event_type: str, data: dict, metadata: dict = None) -> None`

追加事件。

**参数**:
- `event_type`: 事件类型
- `data`: 事件数据
- `metadata`: 元数据（可选）

**示例**:
```python
from event_log import EventLog

el = EventLog(".zcf/event-log.jsonl")

el.append("state_updated", {
    "field": "arch_side.adr",
    "old_value": [],
    "new_value": ["ADR-0010"]
})

el.append("phase_transition", {
    "from_phase": "arch",
    "to_phase": "plan",
    "gate_passed": True
})
```

---

#### `query(type: str = None, limit: int = 10, reverse: bool = True) -> list`

查询事件。

**参数**:
- `type`: 事件类型过滤（可选）
- `limit`: 返回数量限制
- `reverse`: 是否倒序

**返回**:
- `list`: 事件列表

**示例**:
```python
# 查询最近 10 个事件
events = el.query(limit=10)

# 查询特定类型事件
phase_events = el.query(type="phase_transition", limit=5)

# 查询所有 gate_failed 事件
failed_gates = el.query(type="gate_failed", limit=None)
```

---

#### `get_events_since(timestamp: str) -> list`

获取指定时间后的事件。

**参数**:
- `timestamp`: ISO 8601 时间戳

**返回**:
- `list`: 事件列表

**示例**:
```python
events = el.get_events_since("2026-06-22T10:00:00Z")
```

---

#### `clear() -> None`

清空事件流。

**示例**:
```python
el.clear()
```

---

### 事件类型

| 事件类型 | 说明 | 数据字段 |
|---------|------|---------|
| `state_updated` | 状态更新 | `field`, `old_value`, `new_value` |
| `phase_transition` | 阶段切换 | `from_phase`, `to_phase`, `gate_passed` |
| `gate_check` | 门控检查 | `gate`, `checks`, `passed` |
| `gate_failed` | 门控失败 | `gate`, `failed_checks`, `reason` |
| `gate_forced` | 强制切换 | `gate`, `failed_checks`, `reason` |
| `adr_created` | ADR 创建 | `adr_id`, `title`, `status` |
| `change_created` | Change 创建 | `change_id`, `title`, `status` |
| `worktree_created` | Worktree 创建 | `worktree_path`, `change`, `branch` |
| `work_unit_completed` | Work Unit 完成 | `worktree`, `unit_id`, `status` |
| `verification_completed` | 验证完成 | `method`, `score`, `passed` |
| `session_started` | 会话开始 | `session_id`, `goal`, `mode` |
| `session_progress` | 会话进度 | `session_id`, `progress`, `phase` |
| `session_completed` | 会话完成 | `session_id`, `status`, `final_score` |
| `error` | 错误 | `session_id`, `error_type`, `message` |

---

## loop_engine.py

Loop 引擎模块，实现 5 大构建块。

### 类: `LoopEngine`

#### `__init__(config: dict)`

初始化 Loop 引擎。

**参数**:
- `config`: 配置字典

**示例**:
```python
from loop_engine import LoopEngine

config = {
    "interaction": {"mode": "hybrid"},
    "loop": {
        "max_iterations": 100,
        "max_retries": 3,
        "parallel_limit": 3
    }
}

engine = LoopEngine(config)
```

---

#### `run(goal: str) -> dict`

运行 Loop。

**参数**:
- `goal`: 目标描述

**返回**:
- `dict`: 执行结果

**示例**:
```python
result = engine.run("complete all pending changes")
print(result["status"])  # "success"
print(result["iterations"])  # 15
```

---

#### `stop() -> None`

停止 Loop。

**示例**:
```python
engine.stop()
```

---

#### `pause() -> None`

暂停 Loop。

**示例**:
```python
engine.pause()
```

---

#### `resume() -> None`

恢复 Loop。

**示例**:
```python
engine.resume()
```

---

#### `get_status() -> dict`

获取 Loop 状态。

**返回**:
- `dict`: 状态信息

**示例**:
```python
status = engine.get_status()
print(status["current_iteration"])
print(status["current_phase"])
print(status["progress"])
```

---

### 5 大构建块

#### Block 1: `verify_goal() -> bool`

验证目标是否达成。

**返回**:
- `bool`: 是否达成

---

#### Block 2: `generate_plan() -> dict`

生成执行计划。

**返回**:
- `dict`: 执行计划

---

#### Block 3: `execute_plan(plan: dict) -> dict`

执行计划。

**参数**:
- `plan`: 执行计划

**返回**:
- `dict`: 执行结果

---

#### Block 4: `verify_results() -> dict`

验证执行结果。

**返回**:
- `dict`: 验证结果

---

#### Block 5: `adapt() -> None`

自适应调整。

---

## session_v20.py

轻量级会话协调器（v2.0）。

### 类: `SessionCoordinatorV20`

#### `__init__(state_vector: StateVector)`

初始化会话协调器。

**参数**:
- `state_vector`: 状态向量实例

---

#### `create_session(goal: str, role: str = "coordinator") -> str`

创建会话。

**参数**:
- `goal`: 目标描述
- `role`: 会话角色（coordinator/worker）

**返回**:
- `str`: 会话 ID

**示例**:
```python
from session_v20 import SessionCoordinatorV20

coordinator = SessionCoordinatorV20(sv)
session_id = coordinator.create_session(
    goal="complete add-auth change",
    role="coordinator"
)
```

---

#### `create_worker_session(goal: str, assigned_changes: List[str]) -> str`

创建子会话。

**参数**:
- `goal`: 目标描述
- `assigned_changes`: 分配的 changes 列表

**返回**:
- `str`: 子会话 ID

---

#### `update_progress(session_id: str, progress: float) -> None`

更新会话进度。

**参数**:
- `session_id`: 会话 ID
- `progress`: 进度（0.0-1.0）

---

#### `get_progress(session_id: str) -> float`

获取会话进度。

**参数**:
- `session_id`: 会话 ID

**返回**:
- `float`: 进度（0.0-1.0）

---

#### `get_total_progress() -> float`

获取总进度（加权平均）。

**返回**:
- `float`: 总进度

---

#### `list_sessions() -> list`

列出所有会话。

**返回**:
- `list`: 会话列表

---

#### `abort_session(session_id: str) -> None`

中止会话。

**参数**:
- `session_id`: 会话 ID

---

## gate.py

门控检查器模块。

### 类: `GateChecker`

#### `__init__(config: dict)`

初始化门控检查器。

**参数**:
- `config`: 门控配置

---

#### `check_gate(gate_name: str, state: dict) -> dict`

执行门控检查。

**参数**:
- `gate_name`: 门控名称
- `state`: 状态向量

**返回**:
- `dict`: 检查结果

**示例**:
```python
from gate_checker import GateChecker

gc = GateChecker(config)

result = gc.check_gate("arch_done", state)
print(result["passed"])  # True/False
print(result["checks"])  # 检查项列表
```

---

#### `register_custom_gate(name: str, script_path: str) -> None`

注册自定义门控。

**参数**:
- `name`: 门控名称
- `script_path`: 脚本路径

---

### 门控检查项

#### `class GateCheck`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 检查项名称 |
| `passed` | bool | 是否通过 |
| `severity` | str | 严重度（error/warning） |
| `message` | str | 消息 |

---

## tribunal.py

审判委员会模块（多 Agent 验证）。

### 类: `TribunalCommittee`

#### `__init__(config: dict)`

初始化审判委员会。

**参数**:
- `config`: 验证配置

---

#### `verify(executor_result: dict) -> dict`

执行多 Agent 验证。

**参数**:
- `executor_result`: 执行结果

**返回**:
- `dict`: 验证结果

**示例**:
```python
from tribunal import TribunalCommittee

tribunal = TribunalCommittee(config)

result = tribunal.verify({
    "change": "add-auth",
    "code_quality": 0.92,
    "tests_passed": 1.0,
    "completion": 0.85
})

print(result["final_score"])  # 0.91
print(result["passed"])  # True
```

---

#### `calculate_divergence(scores: List[float]) -> float`

计算分歧度。

**参数**:
- `scores`: 评分列表

**返回**:
- `float`: 分歧度（0-1）

---

### 验证结果

#### `class VerificationResult`

| 字段 | 类型 | 说明 |
|------|------|------|
| `passed` | bool | 是否通过 |
| `final_score` | float | 最终评分 |
| `divergence` | float | 分歧度 |
| `recommendation` | str | 建议 |
| `escalate_to_human` | bool | 是否升级到人工 |

---

## memory.py

记忆系统模块。

### 类: `MemorySystem`

#### `__init__(state_vector: StateVector, config: dict)`

初始化记忆系统。

**参数**:
- `state_vector`: 状态向量实例
- `config`: 记忆配置

---

#### `record_execution(execution: dict) -> None`

记录执行。

**参数**:
- `execution`: 执行数据

**示例**:
```python
from memory_system import MemorySystem

memory = MemorySystem(sv, config)

memory.record_execution({
    "execution_id": "exec_20260622_001",
    "goal": "complete add-auth",
    "status": "success",
    "iterations": 15,
    "final_score": 0.91
})
```

---

#### `recommend_config(goal: str) -> dict`

推荐配置。

**参数**:
- `goal`: 目标描述

**返回**:
- `dict`: 推荐配置

---

#### `detect_failure_patterns() -> list`

检测失败模式。

**返回**:
- `list`: 失败模式列表

---

#### `archive_executions(retention_days: int = 90) -> int`

归档执行记录。

**参数**:
- `retention_days`: 保留天数

**返回**:
- `int`: 归档数量

---

#### `get_execution_history(limit: int = 10) -> list`

获取执行历史。

**参数**:
- `limit`: 返回数量

**返回**:
- `list`: 执行历史

---

## 下一步

- **查看配置 Schema**: [v2-config-schema.md](v2-config-schema.md)
- **查看开发者指南**: [v2-developer-guide.md](v2-developer-guide.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](v2-loop-engine-guide.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

