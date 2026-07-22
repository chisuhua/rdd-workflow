# ADR-0010: 多会话管理与并行执行

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: ✅ 已采纳 + 已实施（v2.0 轻量 + v2.1 完整 + ADR-0017 rddf-session 用户层）
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0004 (Loop 引擎核心设计), ADR-0006 (状态向量与事件流设计)
> **版本目标**: v2.0（方案 A）+ v2.1（方案 B）

## Context

在 rdd-workflow v2.0 实施过程中，用户提出了**多会话场景**需求：

1. **并行执行多个 changes**: 主会话创建子会话，并行处理不同的 changes
2. **父子会话协作**: 主会话监控进度，子会话执行具体任务
3. **依赖关系协调**: changes 之间有依赖关系时，需要调度器
4. **跨会话记忆共享**: 多个会话共享同一个记忆系统

**当前局限**:
- ADR-0006 的状态向量只支持单会话
- ADR-0004 的 `parallel_limit` 只控制 worktree 数量，不控制会话
- 没有依赖图调度器处理 changes 之间的逻辑依赖
- 多会话并发写入状态向量可能冲突

**约束**:
- **向后兼容**: 单会话模式继续有效
- **性能**: 会话间通信必须轻量
- **一致性**: 状态向量必须保持一致（文件锁）
- **渐进式**: v2.0 轻量实现，v2.1 完整实现

## Decision

我们采用**分阶段实施方案**：

### v2.0: 方案 A（轻量级会话管理）

**核心思想**: 通过状态向量隐式协调，不引入复杂的会话管理系统

#### 1. 状态向量扩展（v2.0）

```json
{
  "version": "2.0",
  "timestamp": "2026-06-22T10:30:00Z",
  
  // ... 现有字段 ...
  
  "session_info": {
    "session_id": "sess_20260622_001",
    "parent_session": null,
    "role": "coordinator",  // coordinator | worker
    "status": "running",
    "assigned_changes": ["add-auth", "add-user-profile"],
    "progress": 0.45,
    "started_at": "2026-06-22T10:00:00Z",
    "last_heartbeat": "2026-06-22T10:30:00Z"
  },
  
  "sub_sessions": [
    {
      "session_id": "sess_20260622_002",
      "parent_session": "sess_20260622_001",
      "role": "worker",
      "status": "running",
      "assigned_changes": ["add-auth"],
      "progress": 0.67,
      "last_heartbeat": "2026-06-22T10:29:00Z"
    }
  ]
}
```

#### 2. 会话角色（v2.0）

```python
# 简化的会话角色
SESSION_ROLES_V20 = {
    "coordinator": {
        "description": "主会话，监控进度",
        "responsibilities": [
            "创建子会话",
            "监控进度（读取状态向量）",
            "处理异常（重试或上报）"
        ]
    },
    "worker": {
        "description": "子会话，执行任务",
        "responsibilities": [
            "执行分配的 changes",
            "更新进度到状态向量",
            "报告状态"
        ]
    }
}
```

#### 3. 协调机制（v2.0）

```python
# skills/_lib/session_v20.py

class SessionCoordinatorV20:
    """轻量级会话协调器（v2.0）"""
    
    def __init__(self, state_vector: StateVector):
        self.state_vector = state_vector
        self.memory = LoopMemory(state_vector)
    
    def create_worker_session(
        self,
        goal: str,
        assigned_changes: List[str]
    ) -> str:
        """创建子会话"""
        session_id = self.generate_session_id()
        
        # 更新状态向量（带锁）
        with self.state_vector.lock():
            state = self.state_vector.load()
            state["sub_sessions"].append({
                "session_id": session_id,
                "parent_session": state["session_info"]["session_id"],
                "role": "worker",
                "status": "running",
                "assigned_changes": assigned_changes,
                "progress": 0.0,
                "started_at": datetime.utcnow().isoformat() + "Z"
            })
            self.state_vector.save(state)
        
        event_log.record("session_created", {
            "session_id": session_id,
            "role": "worker",
            "assigned_changes": assigned_changes
        })
        
        return session_id
    
    def monitor_sessions(self):
        """监控子会话进度"""
        state = self.state_vector.load()
        
        for session in state["sub_sessions"]:
            # 检查心跳（超过 5 分钟无更新视为异常）
            last_heartbeat = datetime.fromisoformat(session["last_heartbeat"])
            if (datetime.utcnow() - last_heartbeat).seconds > 300:
                event_log.record("session_stalled", {
                    "session_id": session["session_id"],
                    "last_heartbeat": session["last_heartbeat"]
                })
                
                # 标记为异常
                session["status"] = "stalled"
        
        self.state_vector.save(state)
    
    def update_session_progress(self, session_id: str, progress: float):
        """更新子会话进度"""
        with self.state_vector.lock():
            state = self.state_vector.load()
            
            for session in state["sub_sessions"]:
                if session["session_id"] == session_id:
                    session["progress"] = progress
                    session["last_heartbeat"] = datetime.utcnow().isoformat() + "Z"
                    break
            
            # 更新 coordinator 总进度
            state["session_info"]["progress"] = self.calculate_total_progress(state)
            
            self.state_vector.save(state)
    
    def calculate_total_progress(self, state: dict) -> float:
        """计算总进度（加权平均）"""
        if not state["sub_sessions"]:
            return 0.0
        
        total_progress = sum(
            s["progress"] * len(s["assigned_changes"])
            for s in state["sub_sessions"]
        )
        total_changes = sum(len(s["assigned_changes"]) for s in state["sub_sessions"])
        
        return total_progress / total_changes if total_changes > 0 else 0.0
```

#### 4. v2.0 限制

| 特性 | v2.0 支持 | 说明 |
|------|----------|------|
| **会话创建** | ✅ | 通过状态向量隐式创建 |
| **进度监控** | ✅ | 读取状态向量 |
| **状态同步** | ✅ | 文件锁保证一致性 |
| **真正并行** | ❌ | 轮流执行（非多进程） |
| **依赖调度** | ❌ | 手动排序 |
| **会话间通信** | ❌ | 仅通过状态向量 |

---

### v2.1: 方案 B（完整会话管理系统）

**核心思想**: 引入专门的 SessionManager，支持真正的并行和协作

#### 1. 完整状态向量扩展（v2.1）

```json
{
  "session_management": {
    "current_session": { ... },
    "active_sessions": [ ... ],
    "session_statistics": {
      "total_sessions_created": 10,
      "active_sessions": 3,
      "completed_sessions": 6,
      "failed_sessions": 1,
      "avg_session_duration_minutes": 15.5
    }
  },
  
  "dependency_graph": {
    "nodes": [
      {"change": "add-auth", "status": "running", "session": "sess_001"},
      {"change": "add-user-profile", "status": "waiting", "session": "sess_002", "deps": ["add-auth"]}
    ],
    "edges": [
      {"from": "add-auth", "to": "add-user-profile"}
    ],
    "execution_order": ["add-auth", "add-user-profile"]
  }
}
```

#### 2. 会话管理器（v2.1）

```python
# skills/_lib/session_manager.py

class SessionManager:
    """完整会话管理器（v2.1）"""
    
    def __init__(self, state_vector: StateVector):
        self.state_vector = state_vector
        self.memory = LoopMemory(state_vector)
        self.dep_scheduler = DependencyScheduler()
        self.process_pool = ProcessPoolExecutor()
    
    def create_session(
        self,
        goal: str,
        mode: str = "loop",
        parent_session: str = None,
        assigned_changes: List[str] = None
    ) -> str:
        """创建新会话（真正的并行）"""
        session_id = self.generate_session_id()
        
        # 启动新进程
        future = self.process_pool.submit(
            self.run_session,
            session_id=session_id,
            goal=goal,
            mode=mode,
            parent_session=parent_session,
            assigned_changes=assigned_changes
        )
        
        # 更新状态向量
        with self.state_vector.lock():
            state = self.state_vector.load()
            state["session_management"]["active_sessions"].append({
                "session_id": session_id,
                "parent_session": parent_session,
                "role": "worker" if parent_session else "coordinator",
                "goal": goal,
                "mode": mode,
                "status": "running",
                "assigned_changes": assigned_changes or [],
                "progress": 0.0,
                "started_at": datetime.utcnow().isoformat() + "Z"
            })
            self.state_vector.save(state)
        
        return session_id
    
    def coordinate_sessions(self):
        """协调多个会话（完整实现）"""
        while not self.all_changes_completed():
            # 1. 构建依赖图
            dep_graph = self.dep_scheduler.build_dependency_graph(
                self.get_active_changes()
            )
            
            # 2. 拓扑排序
            execution_order = self.dep_scheduler.topological_sort(dep_graph)
            
            # 3. 分配 changes 到子会话（考虑依赖）
            for change in execution_order:
                if self.can_assign_to_session(change):
                    self.assign_change_to_session(change)
            
            # 4. 监控进度
            self.monitor_sessions()
            
            # 5. 处理失败
            self.handle_failed_sessions()
            
            # 6. 更新 coordinator 进度
            self.update_coordinator_progress()
            
            wait(60)
    
    def handle_failed_sessions(self):
        """处理失败会话"""
        for session in self.get_failed_sessions():
            # 1. 记录到记忆系统
            self.memory.record_session_failure(session)
            
            # 2. 推荐修复策略
            suggestion = self.memory.suggest_recovery(session)
            
            # 3. 重试或上报
            if session["retry_count"] < 3:
                self.retry_session(session)
            else:
                self.escalate_to_parent(session)
```

#### 3. 依赖图调度器（v2.1）

```python
# skills/_lib/dependency_scheduler.py

class DependencyScheduler:
    """依赖图调度器"""
    
    def build_dependency_graph(self, changes: List[dict]) -> dict:
        """构建依赖图"""
        graph = {
            "nodes": [],
            "edges": []
        }
        
        for change in changes:
            graph["nodes"].append({
                "change": change["name"],
                "status": change["status"],
                "deps": change.get("deps", [])
            })
            
            for dep in change.get("deps", []):
                graph["edges"].append({
                    "from": dep,
                    "to": change["name"]
                })
        
        return graph
    
    def topological_sort(self, graph: dict) -> List[str]:
        """拓扑排序（确定执行顺序）"""
        # 使用 Kahn 算法
        in_degree = {}
        adj = {}
        
        for node in graph["nodes"]:
            in_degree[node["change"]] = len(node["deps"])
            adj[node["change"]] = []
        
        for edge in graph["edges"]:
            adj[edge["from"]].append(edge["to"])
        
        # 找到所有入度为 0 的节点
        queue = [node for node, degree in in_degree.items() if degree == 0]
        execution_order = []
        
        while queue:
            node = queue.pop(0)
            execution_order.append(node)
            
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return execution_order
    
    def can_execute(self, change: str, completed_changes: List[str]) -> bool:
        """检查 change 是否可以执行（依赖已满足）"""
        change_info = self.get_change_info(change)
        return all(dep in completed_changes for dep in change_info.get("deps", []))
```

#### 4. v2.1 特性

| 特性 | v2.1 支持 | 说明 |
|------|----------|------|
| **真正并行** | ✅ | 多进程/多线程 |
| **依赖调度** | ✅ | DAG 拓扑排序 |
| **会话间通信** | ✅ | 进程间消息队列 |
| **动态负载均衡** | ✅ | 自动分配 changes |
| **会话持久化** | ✅ | 崩溃恢复 |
| **跨项目协作** | ✅ | 远程会话支持 |

---

## 实施计划

### v2.0 实施（当前版本）

**工作量**: 2-3 天

| 任务 | 文件 | 说明 |
|------|------|------|
| 扩展状态向量 | `state_vector.py` | 增加 `session_info` 和 `sub_sessions` 字段 |
| 实现轻量级协调器 | `session_v20.py` | 创建、监控、更新进度 |
| 集成到 Loop 引擎 | `loop-engine.py` | 支持会话角色 |
| 添加单元测试 | `test_session_v20.py` | 测试基本功能 |
| 更新文档 | `USAGE.md` | 添加多会话使用说明 |

**交付物**:
- ✅ 状态向量支持会话信息
- ✅ 轻量级会话协调器
- ✅ 基本的父子会话协作
- ❌ 不支持真正并行
- ❌ 不支持依赖调度

---

### v2.1 实施（未来版本）

**工作量**: 5-7 天

| 任务 | 文件 | 说明 |
|------|------|------|
| 实现 SessionManager | `session_manager.py` | 完整会话管理 |
| 实现 DependencyScheduler | `dependency_scheduler.py` | 依赖图调度 |
| 实现进程间通信 | `session_ipc.py` | 消息队列 |
| 集成到 Loop 引擎 | `loop-engine.py` | 支持真正并行 |
| 添加集成测试 | `test_session_manager.py` | 测试并行场景 |
| 更新文档 | `USAGE.md` | 添加高级用法 |

**交付物**:
- ✅ 完整会话管理器
- ✅ 依赖图调度器
- ✅ 真正的并行执行
- ✅ 动态负载均衡
- ✅ 会话持久化

---

## 影响范围

### v2.0 In Scope

- 状态向量增加 `session_info` 和 `sub_sessions` 字段
- 轻量级会话协调器（`session_v20.py`）
- Loop 引擎支持会话角色（coordinator/worker）
- 文件锁保证状态向量一致性

### v2.0 Out Scope

- 真正的并行执行（多进程）
- 依赖图调度器
- 进程间通信
- 动态负载均衡

### v2.1 In Scope

- 完整 SessionManager
- DependencyScheduler
- 进程间通信机制
- 真正并行执行

---

## 备选方案

| 备选 | 理由 |
|------|------|
| **v2.0 直接实施方案 B** | 拒绝：复杂度太高，影响 v2.0 交付 |
| **完全不支持多会话** | 拒绝：用户需求明确 |
| **分阶段实施（A → B）** | 接受：平衡交付速度和功能完整性 |

---

## Consequences

### v2.0 正面

- **基本满足需求**: 支持简单的父子会话协作
- **实现简单**: 不需要新的复杂模块
- **向后兼容**: 单会话模式继续有效
- **状态一致**: 文件锁保证一致性

### v2.0 负面 / 风险

- **无真正并行**: 只是轮流执行，性能提升有限
  - **缓解**: v2.1 引入多进程
- **无依赖调度**: 用户需要手动排序 changes
  - **缓解**: v2.1 引入 DAG 调度器
- **状态向量可能变大**: 多个会话信息
  - **缓解**: 提供会话归档命令

### v2.1 正面

- **真正并行**: 多进程执行，性能大幅提升
- **智能调度**: 自动处理依赖关系
- **动态负载均衡**: 自动分配 changes
- **会话持久化**: 崩溃后可恢复

### v2.1 负面 / 风险

- **复杂度高**: 需要进程间通信、同步机制
  - **缓解**: 充分的测试和文档
- **资源消耗**: 多进程占用更多内存
  - **缓解**: 配置最大进程数限制

---

## 后续待办

### v2.0

- [ ] 扩展状态向量 Schema（增加 `session_info` 和 `sub_sessions`）
- [ ] 实现 `skills/_lib/session_v20.py`
- [ ] 集成到 Loop 引擎（支持会话角色）
- [ ] 添加单元试
- [ ] 更新文档（USAGE.md）

### v2.1

- [ ] 实现 `skills/_lib/session_manager.py`
- [ ] 实现 `skills/_lib/dependency_scheduler.py`
- [ ] 实现进程间通信机制
- [ ] 添加集成测试（并行场景）
- [ ] 更新文档（高级用法）

---

## References

- ADR-0004 — Loop 引擎核心设计
- ADR-0006 — 状态向量与事件流设计
- OpenHands — 多 Agent 并行执行参考
- Anthropic Agents — Orchestrator-Workers 模式

