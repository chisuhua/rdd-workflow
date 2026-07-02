# ADR-0006: 状态向量与事件流设计

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0004 (Loop 引擎核心设计)

## Context

spec-workflow v1.x 使用 **13 个分散的状态文件**（`.rddf/state/` 目录 + git 跟踪文件），存在以下问题：

1. **状态不一致**: 多个文件存储相同信息（如 change 状态在 `proposal-suggestions.md`、`.rddf/state/roadmap-state.json`、`openspec/changes/<name>/.openspec.yaml` 中重复）
2. **死代码风险**: `.rddf/state/phase-gate-report.md` 写但从不读（审计 P3-5）
3. **难以观测**: 没有统一的状态快照，调试时需要手动检查多个文件
4. **缺乏历史**: 状态文件只反映当前状态，无法追溯状态变更历史
5. **Loop 引擎需求**: ADR-0004 的 Loop 引擎需要统一的状态向量作为输入/输出

**约束**:
- **向后兼容**: v1.x 的状态文件在 v2.x 期间继续有效
- **性能**: 状态向量读取/写入必须轻量（Loop 每次迭代都访问）
- **一致性**: 状态向量必须与现有状态文件保持同步
- **可查询**: 支持按时间范围、事件类型查询事件流

## Decision

我们引入 **统一状态向量 (State Vector)** + **事件流 (Event Log)** 作为 v2.x 的核心状态管理机制：

### 状态向量 (State Vector)

#### 文件位置

```
.rddf/state/state-vector.json  (主状态向量)
.rddf/state/state-vector.lock  (并发控制)
```

#### Schema 定义

```json
{
  "$schema": "https://spec-workflow.dev/schemas/state-vector-v2.json",
  "version": "2.0",
  "timestamp": "2026-06-22T10:30:00Z",
  "project_root": "/absolute/path/to/project",
  
  "goal": {
    "description": "complete all pending changes",
    "mode": "hybrid",
    "started_at": "2026-06-22T10:00:00Z",
    "config_file": ".spec-workflow.json"
  },
  
  "arch_side": {
    "adr": {
      "count": 3,
      "latest": "ADR-0003",
      "files": [
        "docs/adr/ADR-0001-propose-plan-execute-state-machine.md",
        "docs/adr/ADR-0002-goal-driven-interaction-modes.md",
        "docs/adr/ADR-0003-three-phase-architecture.md"
      ],
      "pending_decisions": []
    },
    "roadmap": {
      "exists": true,
      "file": "roadmap.md",
      "current_phase": "core",
      "completion": 0.45,
      "categories": [
        {"name": "基础", "completion": 1.0},
        {"name": "核心", "completion": 0.45},
        {"name": "高级", "completion": 0.0}
      ],
      "last_updated": "2026-06-22T09:00:00Z"
    },
    "architecture": {
      "gap_analysis_files": [
        "docs/architecture/auth-gap-analysis.md"
      ],
      "pending_gaps": 1
    },
    "health": {
      "errors": [],
      "warnings": [
        {"code": "W001", "message": "prometheus CLI not found, using fallback"}
      ],
      "last_check": "2026-06-22T10:29:00Z"
    }
  },
  
  "plan_side": {
    "active_changes": [
      {
        "name": "add-auth",
        "status": "committed",
        "artifacts": {
          "proposal.md": true,
          "design.md": true,
          "tasks.md": true,
          ".openspec.yaml": true
        },
        "roadmap_meta": {
          "phase": "core",
          "category": "auth",
          "priority": "high"
        },
        "deps_analysis": {
          "file_conflicts": 0,
          "adr_refs": ["ADR-0005"],
          "interface_deps": ["auth-module"]
        }
      },
      {
        "name": "refactor-db",
        "status": "incomplete",
        "artifacts": {
          "proposal.md": true,
          "design.md": false,
          "tasks.md": false,
          ".openspec.yaml": false
        }
      }
    ],
    "archived_changes": [
      {"name": "init-project", "archived_at": "2026-06-20T15:00:00Z"}
    ],
    "last_scan": "2026-06-22T10:28:00Z"
  },
  
  "ship_side": {
    "worktrees": [
      {
        "name": "add-auth",
        "path": "/path/to/project/.rddf/state/add-auth-wt",
        "branch": "openspec/add-auth",
        "created_at": "2026-06-22T10:05:00Z",
        "status": "executing",
        "progress": {
          "total_tasks": 15,
          "completed_tasks": 10,
          "failed_tasks": 0,
          "completion": 0.67
        },
        "plan": {
          "file": ".rddf/plans/add-auth.md",
          "generated_at": "2026-06-22T10:06:00Z",
          "source": "oh-my-opencode"
        },
        "last_activity": "2026-06-22T10:25:00Z"
      }
    ],
    "pending_archive": [],
    "completed_changes": [
      {"name": "add-logging", "archived_at": "2026-06-21T18:00:00Z"}
    ],
    "last_action": {
      "type": "execute_unit",
      "change": "add-auth",
      "unit": 10,
      "timestamp": "2026-06-22T10:25:00Z",
      "result": "success"
    }
  },
  
  "loop_state": {
    "engine_version": "2.0",
    "iterations": 5,
    "retries": 0,
    "current_phase": "ship",
    "phase_history": ["arch", "plan", "ship", "ship", "ship"],
    "state_history": [
      {"iteration": 1, "phase": "arch", "timestamp": "2026-06-22T10:00:00Z"},
      {"iteration": 2, "phase": "plan", "timestamp": "2026-06-22T10:01:00Z"},
      {"iteration": 3, "phase": "ship", "timestamp": "2026-06-22T10:05:00Z"},
      {"iteration": 4, "phase": "ship", "timestamp": "2026-06-22T10:15:00Z"},
      {"iteration": 5, "phase": "ship", "timestamp": "2026-06-22T10:25:00Z"}
    ],
    "started_at": "2026-06-22T10:00:00Z",
    "last_iteration": "2026-06-22T10:25:00Z"
  },
  
  "memory": {
    "executions": [
      {
        "change": "add-auth",
        "timestamp": "2026-06-22T10:00:00Z",
        "success": false,
        "iterations": 5,
        "retry_count": 1,
        "final_score": 0.75,
        "errors": [
          {"type": "test_failure", "message": "ctest failed on unit 12"}
        ],
        "verification_method": "multi_model",
        "verification_scores": {
          "executor": 0.8,
          "reviewer": 0.7
        },
        "interrupted_by": "user"
      }
    ],
    
    "learned_insights": [
      {
        "type": "error_pattern",
        "pattern": "test_failure_after_merge",
        "description": "Merge 后测试失败频率高",
        "occurrence_count": 5,
        "suggestion": "Merge 前先运行完整测试套件",
        "confidence": 0.85,
        "learned_at": "2026-06-22T10:30:00Z"
      }
    ],
    
    "recommended_configs": {
      "complete_all_changes": {
        "max_iterations": 50,
        "max_retries": 3,
        "parallel_limit": 3,
        "verification_method": "multi_model",
        "confidence": 0.88
      }
    },
    
    "statistics": {
      "total_executions": 15,
      "success_rate": 0.87,
      "avg_iterations": 5.2,
      "avg_retry_count": 1.3,
      "common_errors": [
        {"error": "test_failure", "count": 5},
        {"error": "merge_conflict", "count": 3}
      ]
    }
  },
  
  "metadata": {
    "spec_workflow_version": "2.0.0",
    "openspec_version": "1.3.1",
    "git_commit": "631f83b",
    "generated_by": "loop-engine",
    "checksum": "sha256:abc123..."
  }
}
```

#### 状态向量操作

```python
# skills/_lib/state_vector.py

class StateVector:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.file = project_root / ".zcf" / "state-vector.json"
        self.lock_file = project_root / ".zcf" / "state-vector.lock"
    
    def load(self) -> dict:
        """加载状态向量（带锁）"""
        with FileLock(self.lock_file):
            if not self.file.exists():
                return self.create_default()
            return json.loads(self.file.read_text())
    
    def save(self, state: dict):
        """保存状态向量（带锁 + 校验）"""
        with FileLock(self.lock_file):
            self.validate(state)
            state["timestamp"] = datetime.utcnow().isoformat() + "Z"
            state["metadata"]["checksum"] = self.calculate_checksum(state)
            self.file.write_text(json.dumps(state, indent=2))
    
    def update_field(self, field_path: str, value: Any):
        """更新嵌套字段 (e.g., "ship_side.worktrees.0.progress")"""
        state = self.load()
        parts = field_path.split(".")
        obj = state
        for part in parts[:-1]:
            if part.isdigit():
                obj = obj[int(part)]
            else:
                obj = obj[part]
        obj[parts[-1]] = value
        self.save(state)
    
    def validate(self, state: dict):
        """验证状态向量 Schema"""
        # 使用 jsonschema 验证
        validate(instance=state, schema=STATE_VECTOR_SCHEMA)
    
    def create_default(self) -> dict:
        """创建默认状态向量"""
        return {
            "version": "2.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "project_root": str(self.project_root),
            "goal": {"description": "", "mode": "menu"},
            "arch_side": {"adr": {"count": 0}, "roadmap": {"exists": False}},
            "plan_side": {"active_changes": []},
            "ship_side": {"worktrees": [], "pending_archive": []},
            "loop_state": {"iterations": 0, "current_phase": "arch"},
            "metadata": {"spec_workflow_version": "2.0.0"}
        }
```

### 事件流 (Event Log)

#### 文件位置

```
.rddf/state/event-log.jsonl  (事件流，每行一个 JSON 对象)
```

#### 事件 Schema

```json
{
  "event_id": "evt_20260622_103000_001",
  "timestamp": "2026-06-22T10:30:00.123Z",
  "type": "worktree_created",
  "severity": "info",
  "source": "loop-engine",
  "iteration": 3,
  "phase": "ship",
  "data": {
    "change_name": "add-auth",
    "worktree_path": "/path/to/.rddf/state/add-auth-wt",
    "branch": "openspec/add-auth"
  },
  "context": {
    "goal": "complete all pending changes",
    "active_worktrees": 1,
    "active_changes": 2
  }
}
```

#### 事件类型定义

| 事件类型 | 严重度 | 触发时机 | 数据字段 |
|---------|-------|---------|---------|
| `loop_started` | info | Loop 引擎启动 | goal, mode, config |
| `loop_completed` | info | Loop 引擎完成 | iterations, duration, result |
| `loop_error` | error | Loop 引擎错误 | error_type, message, stack |
| `scan_started` | debug | 开始扫描状态 | detectors_count |
| `scan_completed` | info | 扫描完成 | detectors, duration_ms, findings |
| `plan_generated` | info | 生成执行计划 | actions_count, mode |
| `plan_executed` | info | 执行计划 | success, duration_ms |
| `human_in_loop` | info | 显示菜单 | node_id, choice, timeout |
| `worktree_created` | info | 创建 worktree | change_name, path, branch |
| `worktree_removed` | info | 删除 worktree | change_name, reason |
| `plan_generated` | info | 生成 Prometheus 计划 | change_name, tasks_count, source |
| `unit_started` | debug | Work Unit 开始 | change_name, unit_id, total |
| `unit_completed` | info | Work Unit 完成 | change_name, unit_id, result |
| `unit_failed` | error | Work Unit 失败 | change_name, unit_id, error |
| `change_archived` | info | Change 归档 | change_name, merge_result |
| `error_retry` | warn | 错误重试 | error, retry_count, max_retries |
| `state_updated` | debug | 状态向量更新 | fields_updated |
| `phase_transition` | info | 阶段切换 | from_phase, to_phase, reason |
| `goal_achieved` | info | 目标达成 | goal, iterations, duration |

#### 事件流操作

```python
# skills/_lib/event_log.py

class EventLog:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.file = project_root / ".zcf" / "event-log.jsonl"
    
    def record(self, event_type: str, data: dict, severity: str = "info"):
        """记录事件"""
        event = {
            "event_id": self.generate_id(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "severity": severity,
            "source": "loop-engine",
            "iteration": self.get_current_iteration(),
            "phase": self.get_current_phase(),
            "data": data,
            "context": self.get_context()
        }
        with open(self.file, "a") as f:
            f.write(json.dumps(event) + "\n")
    
    def query(self, 
              event_types: List[str] = None,
              severity: str = None,
              time_range: Tuple[str, str] = None,
              limit: int = 100) -> List[dict]:
        """查询事件"""
        events = []
        with open(self.file, "r") as f:
            for line in f:
                event = json.loads(line)
                
                # 过滤条件
                if event_types and event["type"] not in event_types:
                    continue
                if severity and event["severity"] != severity:
                    continue
                if time_range:
                    start, end = time_range
                    if not (start <= event["timestamp"] <= end):
                        continue
                
                events.append(event)
                if len(events) >= limit:
                    break
        
        return events
    
    def get_progress_report(self) -> dict:
        """生成进度报告"""
        events = self.query(limit=10000)
        
        return {
            "total_events": len(events),
            "loop_iterations": len([e for e in events if e["type"] == "loop_iteration"]),
            "worktrees_created": len([e for e in events if e["type"] == "worktree_created"]),
            "worktrees_removed": len([e for e in events if e["type"] == "worktree_removed"]),
            "units_completed": len([e for e in events if e["type"] == "unit_completed"]),
            "units_failed": len([e for e in events if e["type"] == "unit_failed"]),
            "changes_archived": len([e for e in events if e["type"] == "change_archived"]),
            "errors": len([e for e in events if e["severity"] == "error"]),
            "duration": self.calculate_duration(events)
        }
    
    def generate_id(self) -> str:
        """生成事件 ID"""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        seq = self.get_sequence_number(ts)
        return f"evt_{ts}_{seq:03d}"
```

### 记忆系统 (Memory System)

#### 执行痕迹记录

记忆系统保存每次 Loop 执行的详细数据，支持**中断恢复**、**重复失败警告**和**跨 session 学习**：

```python
# skills/_lib/memory.py

class LoopMemory:
    """Loop 记忆系统"""
    
    def __init__(self, state_vector: StateVector):
        self.state_vector = state_vector
        self.memory = state_vector.data.get("memory", {
            "executions": [],
            "learned_insights": [],
            "recommended_configs": {},
            "statistics": {}
        })
    
    def record_execution(self, change_name: str, result: ExecutionResult):
        """记录执行痕迹"""
        execution = {
            "change": change_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "success": result.success,
            "iterations": result.iterations,
            "retry_count": result.retry_count,
            "final_score": result.quality_score,
            "errors": result.errors,
            "verification_method": result.verification_method,
            "verification_scores": result.verification_scores,
            "interrupted_by": result.interrupted_by  # "user" / "error" / "timeout"
        }
        self.memory["executions"].append(execution)
        
        # 更新统计
        self.update_statistics()
        
        # 学习新洞察
        self.learn_from_execution(execution)
        
        # 保存
        self.state_vector.save()
```

#### 中断恢复场景

**v1.x（当前）**: 只能恢复 worktree 进度，无法恢复历史上下文

**v2.0（增加记忆）**: 恢复执行时显示完整上下文

```python
def resume_execution(self, change_name: str):
    """恢复执行（增强版）"""
    
    # 1. 恢复 worktree 状态（同 v1.x）
    worktree = self.find_worktree(change_name)
    tasks_progress = self.read_tasks_progress(worktree)
    
    # 2. 🆕 恢复记忆上下文
    memory = self.state_vector.memory
    history = memory.get_execution_history(change_name)
    
    if history:
        last_exec = history[-1]
        
        # 显示恢复上下文
        print(f"📊 恢复执行: {change_name}")
        print(f"  - 进度: {tasks_progress.completed}/{tasks_progress.total}")
        print(f"  - 上次执行: {last_exec.timestamp}")
        print(f"  - 上次结果: {'成功' if last_exec.success else '失败'}")
        
        if not last_exec.success:
            print(f"  - 失败原因: {last_exec.errors}")
            
            # 推荐修复策略
            insights = memory.get_insights_for_change(change_name)
            if insights:
                print(f"\n💡 建议:")
                for insight in insights:
                    print(f"  - {insight.suggestion}")
        
        # 推荐配置
        recommended = memory.suggest_config(f"resume {change_name}")
        if self.confirm_config(recommended):
            self.config = recommended
    
    # 3. 从断点继续执行
    self.execute_from_checkpoint(change_name, tasks_progress)
```

#### 重复失败警告

```python
def check_failure_pattern(self, change_name: str):
    """检查重复失败模式"""
    history = self.memory.get_execution_history(change_name)
    failed_count = sum(1 for e in history if not e.success)
    
    if failed_count >= 3:
        print(f"⚠️  警告: change '{change_name}' 已失败 {failed_count} 次")
        
        # 分析失败模式
        insights = self.memory.get_insights(filter_type="error_pattern")
        for insight in insights:
            if change_name in insight.related_changes:
                print(f"\n📊 学习到的洞察:")
                print(f"  - 问题: {insight.description}")
                print(f"  - 建议: {insight.suggestion}")
                print(f"  - 置信度: {insight.confidence:.0%}")
        
        # 提供选项
        choice = show_menu([
            "1. 继续执行（应用推荐配置）",
            "2. 查看失败详情",
            "3. 暂停此 change，先处理其他",
            "4. 中止"
        ])
```

#### 配置推荐

```python
def suggest_config(self, goal: str) -> LoopConfig:
    """基于历史数据推荐配置"""
    # 查找相似目标的历史执行
    similar_executions = self.find_similar_executions(goal)
    
    if not similar_executions:
        return LoopConfig.default()
    
    # 分析成功执行的配置
    successful = [e for e in similar_executions if e["success"]]
    if not successful:
        return LoopConfig.default()
    
    # 推荐配置
    avg_iterations = np.mean([e["iterations"] for e in successful])
    avg_retries = np.mean([e["retry_count"] for e in successful])
    
    return LoopConfig(
        max_iterations=int(avg_iterations * 1.5),  # 1.5x 安全边际
        max_retries=int(avg_retries * 2),
        parallel_limit=self.recommend_parallel_limit(successful),
        verification_method=self.recommend_verification_method(successful)
    )
```

**数据保留策略**:
- 永久保留（提供归档命令）
- 项目级隔离（不跨项目共享）
- 归档命令: `spec-workflow archive-memory --before 2026-01-01`

### 与现有状态文件的同步

#### 同步策略

```
状态向量 (主) ←→ 现有状态文件 (兼容层)

.rddf/state/state-vector.json  (v2.x 主状态)
    ↓ 同步写入
.rddf/state/roadmap-state.json  (v1.x 兼容)
proposal-suggestions.md  (v1.x 兼容)
openspec/changes/<name>/.openspec.yaml  (v1.x 兼容)
```

#### 同步实现

```bash
# skills/_lib/sync_state.sh

sync_state_vector_to_legacy() {
    local state_vector=".rddf/state/state-vector.json"
    
    # 同步 roadmap 状态
    jq -r '.arch_side.roadmap' "$state_vector" | \
        python3 -c "
import json, sys
roadmap = json.load(sys.stdin)
with open('.rddf/state/roadmap-state.json', 'w') as f:
    json.dump({
        'current_phase': roadmap['current_phase'],
        'completion': roadmap['completion']
    }, f)
"
    
    # 同步 proposal suggestions
    jq -r '.plan_side.active_changes' "$state_vector" | \
        python3 -c "
import json, sys
changes = json.load(sys.stdin)
with open('proposal-suggestions.md', 'w') as f:
    f.write('# Proposal Suggestions\n\n')
    for change in changes:
        f.write(f\"- name: {change['name']}\n\")
        f.write(f\"  status: {'已完成' if change['status'] == 'committed' else '待处理'}\n\")
"
}

sync_legacy_to_state_vector() {
    # 从现有文件读取，更新状态向量
    python3 skills/_lib/sync_legacy.py
}
```

### 并发控制

#### 文件锁机制

```python
# skills/_lib/lock.py

import fcntl

class FileLock:
    def __init__(self, lock_file: Path, timeout: int = 10):
        self.lock_file = lock_file
        self.timeout = timeout
        self.fd = None
    
    def __enter__(self):
        self.fd = open(self.lock_file, 'w')
        start_time = time.time()
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError("Failed to acquire lock")
                time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
```

### 影响范围

- **In Scope**:
  - 新增 `.rddf/state/state-vector.json` (状态向量)
  - 新增 `.rddf/state/event-log.jsonl` (事件流)
  - 新增 `skills/_lib/state_vector.py` (状态向量操作)
  - 新增 `skills/_lib/event_log.py` (事件流操作)
  - 新增 `skills/_lib/sync_state.sh` (与现有文件同步)
  
- **Out Scope**:
  - 不删除现有状态文件（v2.x 期间保持兼容）
  - 不改变 openspec CLI 状态管理

### 备选方案

| 备选 | 理由 |
|------|------|
| **完全替换现有状态文件** | 拒绝：迁移成本过高，向后兼容要求 |
| **数据库 (SQLite)** | 拒绝：引入过重依赖，spec-workflow 应保持轻量 |
| **JSON + JSONL** | 接受：轻量、可读、易调试、工具链成熟 |
| **无事件流** | 拒绝：Loop 引擎需要完整审计追踪 |

## Consequences

### 正面

- **统一状态**: 单一状态向量作为权威来源，避免不一致
- **完整历史**: 事件流记录所有状态变更，支持审计和调试
- **可观测性**: 进度报告、错误追踪、性能分析
- **向后兼容**: 与现有状态文件同步，v1.x 工具继续有效
- **并发安全**: 文件锁机制防止竞态条件

### 负面 / 风险

- **存储开销**: 事件流可能增长较快（每次迭代多个事件）
  - **缓解**: 提供事件归档命令 (`spec-workflow archive-events`)
- **同步复杂度**: 状态向量与现有文件双向同步
  - **缓解**: 自动化同步脚本，v3.x 移除现有文件
- **性能**: 每次迭代读写 JSON 文件
  - **缓解**: 内存缓存，批量写入

### 后续待办

- [ ] 实现 `skills/_lib/state_vector.py`
- [ ] 实现 `skills/_lib/event_log.py`
- [ ] 实现 `skills/_lib/sync_state.sh`
- [ ] 添加 JSON Schema 验证
- [ ] 添加并发控制单元测试
- [ ] 添加事件流查询工具
- [ ] 实现进度报告生成 (`spec-workflow report`)
- [ ] 编写状态向量文档

## References

- ADR-0004 — Loop 引擎核心设计
- `docs/audit/2026-06-05-workflow-audit.md` §15.4 — 状态文件分散问题
- `.rddf/state/roadmap-state.json` — 现有 roadmap 状态文件
- `proposal-suggestions.md` — 现有 proposal 状态文件
- OpenHands — 事件流设计参考
- Cursor Agent — 状态管理参考

