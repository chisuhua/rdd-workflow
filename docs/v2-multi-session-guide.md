# spec-workflow v2.0 多会话使用指南

> **版本**: 2.0.0  
> **日期**: 2026-06-22  
> **ADR 参考**: [ADR-0010](../adr/ADR-0010-multi-session-management.md)

---

## 📋 目录

- [概述](#概述)
- [v2.0 轻量级会话管理](#v20-轻量级会话管理)
- [父子会话协作](#父子会话协作)
- [会话状态监控](#会话状态监控)
- [会话故障排查](#会话故障排查)
- [v2.1 完整会话管理预告](#v21-完整会话管理预告)

---

## 概述

### 什么是多会话？

多会话（Multi-Session）允许主会话创建子会话，子会话并行执行 spec-workflow 流程，并与父会话协作。

### 会话角色

| 角色 | 说明 | 职责 |
|------|------|------|
| **coordinator** | 主会话（协调者） | 创建子会话、监控进度、汇总结果 |
| **worker** | 子会话（工作者） | 执行具体任务、报告进度 |

### v2.0 vs v2.1 对比

| 特性 | v2.0（轻量级） | v2.1（完整） |
|------|---------------|-------------|
| **并行执行** | ❌ 轮流执行 | ✅ 真正并行 |
| **依赖调度** | ❌ 不支持 | ✅ DAG 调度器 |
| **进程间通信** | ❌ 状态向量 | ✅ 消息队列 |
| **会话持久化** | ❌ 内存中 | ✅ 数据库 |
| **负载均衡** | ❌ 不支持 | ✅ 动态分配 |
| **适用场景** | 简单任务 | 复杂任务 |

---

## v2.0 轻量级会话管理

### 创建子会话

```bash
# 主会话创建子会话
skill_use("loop", {
  "goal": "complete add-auth change",
  "mode": "hybrid",
  "session": {
    "role": "coordinator",
    "create_workers": true,
    "assigned_changes": ["add-auth"]
  }
})
```

### 会话状态向量

```json
{
  "session_info": {
    "session_id": "sess_20260622_001",
    "parent_session": null,
    "role": "coordinator",
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
      "started_at": "2026-06-22T10:05:00Z",
      "last_heartbeat": "2026-06-22T10:29:00Z"
    },
    {
      "session_id": "sess_20260622_003",
      "parent_session": "sess_20260622_001",
      "role": "worker",
      "status": "running",
      "assigned_changes": ["add-user-profile"],
      "progress": 0.33,
      "started_at": "2026-06-22T10:10:00Z",
      "last_heartbeat": "2026-06-22T10:28:00Z"
    }
  ]
}
```

### 进度计算

v2.0 使用加权平均计算总进度：

```python
def calculate_total_progress(state: dict) -> float:
    """计算总进度（加权平均）"""
    total_progress = sum(
        s["progress"] * len(s["assigned_changes"])
        for s in state["sub_sessions"]
    )
    total_changes = sum(len(s["assigned_changes"]) for s in state["sub_sessions"])
    return total_progress / total_changes if total_changes > 0 else 0.0

# 示例
# sess_20260622_002: progress=0.67, changes=["add-auth"] (1 个)
# sess_20260622_003: progress=0.33, changes=["add-user-profile"] (1 个)
# total_progress = (0.67 * 1 + 0.33 * 1) / (1 + 1) = 0.50
```

### 会话协调器

v2.0 使用轻量级会话协调器：

```python
class SessionCoordinatorV20:
    """轻量级会话协调器（v2.0）"""
    
    def create_worker_session(self, goal: str, assigned_changes: List[str]) -> str:
        """创建子会话"""
        session_id = self.generate_session_id()
        
        with self.state_vector.lock():
            state = self.state_vector.load()
            state["sub_sessions"].append({
                "session_id": session_id,
                "parent_session": state["session_info"]["session_id"],
                "role": "worker",
                "status": "running",
                "assigned_changes": assigned_changes,
                "progress": 0.0
            })
            self.state_vector.save(state)
        
        return session_id
    
    def update_worker_progress(self, session_id: str, progress: float):
        """更新子会话进度"""
        with self.state_vector.lock():
            state = self.state_vector.load()
            for session in state["sub_sessions"]:
                if session["session_id"] == session_id:
                    session["progress"] = progress
                    session["last_heartbeat"] = datetime.utcnow().isoformat()
                    break
            self.state_vector.save(state)
    
    def get_total_progress(self) -> float:
        """获取总进度"""
        state = self.state_vector.load()
        return self.calculate_total_progress(state)
```

---

## 父子会话协作

### 协作流程

```
主会话 (coordinator)
    ↓
1. 扫描 active changes
    ↓
2. 为每个 change 创建子会话 (worker)
    ↓
3. 轮流执行子会话（v2.0 不支持真正并行）
    ↓
4. 监控子会话进度
    ↓
5. 汇总结果，归档 changes
```

### 示例：完成多个 changes

```
🚀 主会话启动

📊 目标: complete all pending changes
📊 发现 2 个 active changes: add-auth, add-user-profile

[创建子会话]
✅ 创建子会话 sess_20260622_002 (worker)
   - 分配: add-auth
   - 状态: running

✅ 创建子会话 sess_20260622_003 (worker)
   - 分配: add-user-profile
   - 状态: running

[执行子会话]
⚙️ 执行 sess_20260622_002 (add-auth)...
   Iteration 1: Entering arch phase...
   Iteration 2: Entering plan phase...
   Iteration 3: Entering ship phase...
   ✅ add-auth completed (progress: 1.0)

⚙️ 执行 sess_20260622_003 (add-user-profile)...
   Iteration 1: Entering arch phase...
   Iteration 2: Entering plan phase...
   Iteration 3: Entering ship phase...
   ✅ add-user-profile completed (progress: 1.0)

[汇总结果]
✅ 所有子会话完成
✅ 总进度: 100%
✅ 归档 changes: add-auth, add-user-profile

🎉 目标达成: complete all pending changes
```

### 会话间通信

v2.0 通过状态向量实现隐式通信：

```python
# 主会话读取子会话状态
state = self.state_vector.load()
for session in state["sub_sessions"]:
    print(f"Session {session['session_id']}: {session['progress']:.0%}")

# 子会话更新进度
self.coordinator.update_worker_progress(
    session_id="sess_20260622_002",
    progress=0.67
)
```

---

## 会话状态监控

### 查看会话状态

```bash
# 查看所有会话
spec-workflow session list

# 输出:
# 会话列表:
#   Session ID                    Role         Status     Progress  Changes
#   sess_20260622_001            coordinator  running    45%       2
#   ├─ sess_20260622_002         worker       running    67%       add-auth
#   └─ sess_20260622_003         worker       running    33%       add-user-profile

# 查看特定会话详情
spec-workflow session show sess_20260622_001

# 输出:
# 会话详情:
#   Session ID: sess_20260622_001
#   角色: coordinator
#   状态: running
#   目标: complete all pending changes
#   进度: 45%
#   子会话: 2
#   分配 changes: add-auth, add-user-profile
#   开始时间: 2026-06-22T10:00:00Z
#   最后心跳: 2026-06-22T10:30:00Z
```

### 实时监控

```bash
# 实时监控股话进度
watch -n 2 'spec-workflow session list'

# 或使用事件流
tail -f .rddf/state/event-log.jsonl | jq 'select(.type == "session_progress")'
```

### 会话报告

```bash
# 生成会话报告
spec-workflow session report

# 输出:
# 会话报告:
#   总会话数: 3
#   运行中: 3
#   已完成: 0
#   失败: 0
#   
#   总进度: 45%
#   预计完成时间: 2026-06-22T11:00:00Z (基于当前速度)
#   
#   子会话详情:
#     1. sess_20260622_002 (add-auth)
#        - 进度: 67%
#        - 状态: running
#        - 阶段: ship
#        - 迭代: 8
#     
#     2. sess_20260622_003 (add-user-profile)
#        - 进度: 33%
#        - 状态: running
#        - 阶段: plan
#        - 迭代: 5
```

---

## 会话故障排查

### 问题 1: 子会话卡住

**症状**: 子会话进度长时间不变

**解决**:
```bash
# 1. 查看子会话心跳
spec-workflow session show sess_20260622_002

# 输出:
# 最后心跳: 2026-06-22T10:15:00Z (15 分钟前)

# 2. 检查是否超时（默认 10 分钟无心跳视为卡住）
# 3. 重启子会话
spec-workflow session restart sess_20260622_002

# 4. 或中止子会话
spec-workflow session abort sess_20260622_002
```

---

### 问题 2: 子会话失败

**症状**: 子会话状态变为 "failed"

**解决**:
```bash
# 1. 查看失败原因
spec-workflow session show sess_20260622_002

# 输出:
# 状态: failed
# 错误: test_failure on unit 12

# 2. 查看事件流
cat .rddf/state/event-log.jsonl | jq 'select(.data.session_id == "sess_20260622_002" and .type == "error")'

# 3. 选项:
# - 修复后重启
# - 标记为失败，继续其他子会话
# - 中止所有子会话

# 4. 重启子会话
spec-workflow session restart sess_20260622_002
```

---

### 问题 3: 进度计算不准确

**症状**: 总进度与预期不符

**解决**:
```bash
# 1. 检查进度计算逻辑
cat .rddf/state/state-vector.json | jq '.sub_sessions[] | {session_id, progress, assigned_changes}'

# 2. 手动计算
# 例如：
# sess_20260622_002: progress=0.67, changes=["add-auth"] (1 个)
# sess_20260622_003: progress=0.33, changes=["add-user-profile"] (1 个)
# total = (0.67*1 + 0.33*1) / (1+1) = 0.50

# 3. 如果计算错误，手动修复
spec-workflow session recalculate-progress
```

---

## rddf-session（用户层抽象，ADR-0017）

rddf-session 是 ADR-0017 引入的**用户视角**会话抽象，叠加在 v2.0 SessionCoordinator 之上。它解决了**跨 OpenCode 会话的 workflow 上下文连续性**问题。

### 与 Session 的区别

| 维度 | SessionCoordinator（v2.0） | rddf-session |
|------|---------------------------|--------------|
| **作用域** | Loop 引擎内部 | 用户 + 跨 OpenCode session |
| **持久化** | 仅内存 | `.rddf/state/sessions.json`（gitignored） |
| **绑定** | 无 | 绑定 OpenCode session ID |
| **粒度** | 父子 sub-sessions | 仅 3 种 kind（stage_arch/plan/ship） |
| **冲突处理** | 无 | 4 选项软提示（放弃/转移/强制/查看） |

### 核心场景

**场景 1：在 OpenCode session A 中执行 `guide-plan` Phase 2 创建 3 个 change 后中断**

**场景 2：在 OpenCode session B 中恢复**

```bash
# 列出所有 sessions（包含 A 创建的）
skill_use("rddf-session", "list")
# Output:
#   session_id       kind         owner                state    last_heartbeat
#   rds_a3f2b1c9d8e7 stage_plan   ses_A_session_id    active   2026-07-09T10:25:00Z

# 查看详情
skill_use("rddf-session", "show", "rds_a3f2b1c9d8e7")

# 恢复（转移所有权给当前 session B）
skill_use("rddf-session", "resume", "rds_a3f2b1c9d8e7")
# → 继续 Phase 2 → Phase 3 → plan-done
```

**场景 3：跨 session 冲突软提示**

当 session B 启动 `skill_use("guide-plan")` 时，发现 A 已创建 active `stage_plan` rddf-session：

```
⚠️ 发现 active stage_plan session: rds_a3f2b1c9d8e7
   原 OpenCode session: ses_A
   当前 OpenCode session: ses_B
   最后心跳: 2026-07-09T10:25:00Z (5 分钟前)

选择:
  1) 放弃原 session — 创建新 rddf-session（丢失上下文）
  2) 转移所有权 — 继续原工作
  3) 强制接管 — 不变更 owner，绕过检测
  4) 仅查看 — 不操作
```

**场景 4：心跳超时与 orphaned 恢复**

30 分钟无心跳 → state 自动从 active → orphaned。下次 `list`/`show`/`resume` 时自动检测并提示用户 resume。

### 子命令参考

| 子命令 | 描述 |
|--------|------|
| `list` | 列出所有 sessions（按 started_at 降序） |
| `show <id>` | 显示单个 session 的完整 JSON |
| `resume <id>` | 转移所有权 + 刷新心跳 + orphaned→active |
| `abandon <id>` | 标记为 abandoned（end_reason=user-abandoned） |
| `archive-history [--keep=N]` | 移动历史 completed/failed/abandoned 到 .archive.json |

### 自动管理

`guide-arch`/`guide-plan`/`guide-ship` 在入口自动创建/查找 rddf-session：
- `guide-arch` 入口 → 创建 `kind=stage_arch`
- `arch-done` 通过 → `stage_arch` → completed
- `guide-plan` 入口 → 创建 `kind=stage_plan`, parent=最新 stage_arch
- `plan-done` 通过 → `stage_plan` → completed
- `guide-ship` 入口 → 创建 `kind=stage_ship`, parent=最新 stage_plan
- 所有 attached_changes archived → `stage_ship` → completed

### 心跳机制

- **写入时机**：每次 `guide-arch`/`guide-plan`/`guide-ship` 阶段内调用时刷新
- **刷新阈值**：5 分钟
- **超时阈值**：30 分钟 → orphaned
- **检测时机**：`list`/`show`/`resume` 调用时惰性检测

### 存储与 Schema

- **文件**：`/workspace/project/spec-workflow/.rddf/state/sessions.json`（gitignored）
- **Schema**：`skills/_lib/schemas/sessions_schema.json` v1
- **并发**：fcntl.flock 保护 + 原子写（write-tmp + rename）

### 与 worktree 完全解耦

rddf-session **不持有** worktree 路径。所有 worktree 由 `git worktree list` 独立管理。换 opencode session 后靠 `git worktree list` 自动发现。

---

## v2.1 完整会话管理预告

### v2.1 新特性

| 特性 | 说明 | 优势 |
|------|------|------|
| **真正并行** | 多进程并行执行 | 速度提升 2-3x |
| **DAG 调度器** | 依赖图拓扑排序 | 自动确定执行顺序 |
| **消息队列** | 进程间通信 | 实时协调 |
| **会话持久化** | 数据库存储 | 崩溃恢复 |
| **负载均衡** | 动态分配任务 | 资源利用率优化 |

### DAG 依赖调度

v2.1 支持 changes 之间的依赖关系：

```yaml
# 依赖图
changes:
  add-auth:
    deps: []
  add-user-profile:
    deps: [add-auth]
  add-dashboard:
    deps: [add-auth, add-user-profile]

# 执行顺序（拓扑排序）
1. add-auth (无依赖)
2. add-user-profile (依赖 add-auth)
3. add-dashboard (依赖 add-auth, add-user-profile)
```

### 并行执行示例（v2.1）

```
🚀 主会话启动 (coordinator)

📊 发现 3 个 active changes:
   - add-auth (无依赖)
   - add-user-profile (依赖: add-auth)
   - add-dashboard (依赖: add-auth, add-user-profile)

[DAG 调度器]
✅ 计算执行顺序:
   1. add-auth
   2. add-user-profile
   3. add-dashboard

✅ 可并行执行: add-auth (阶段 1)

[并行执行]
⚙️ Worker 1: 执行 add-auth...
   ✅ add-auth completed

✅ 依赖满足: add-user-profile 可以开始

⚙️ Worker 1: 执行 add-user-profile...
   ✅ add-user-profile completed

✅ 依赖满足: add-dashboard 可以开始

⚙️ Worker 1: 执行 add-dashboard...
   ✅ add-dashboard completed

🎉 所有 changes 完成！
```

### 消息队列通信（v2.1）

```python
# v2.1 使用消息队列
from message_queue import MessageQueue

mq = MessageQueue()

# 主会话发送任务
mq.send("worker-1", {
    "task": "execute_change",
    "change": "add-auth"
})

# 子会话接收任务
task = mq.receive("worker-1")

# 子会话报告进度
mq.send("coordinator", {
    "session_id": "sess_20260622_002",
    "progress": 0.67,
    "status": "running"
})

# 主会话接收进度
progress = mq.receive("coordinator")
```

### v2.1 发布时间

- **预计时间**: v2.0 发布后 1-2 个月
- **里程碑**:
  - Phase 1: DAG 调度器
  - Phase 2: 消息队列
  - Phase 3: 会话持久化
  - Phase 4: 负载均衡

---

## 最佳实践

### 1. 选择合适的会话模式

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| **单个 change** | 单会话 | 简单直接 |
| **多个无依赖 changes** | v2.0 多会话 | 轮流执行 |
| **多个有依赖 changes** | v2.1 多会话（等待） | DAG 调度 |
| **批量处理** | v2.1 多会话（等待） | 真正并行 |

---

### 2. 监控会话心跳

```json
{
  "session": {
    "heartbeat_interval": 60,
    "timeout_threshold": 600
  }
}
```

---

### 3. 设置合理的子会话数量

```bash
# v2.0 建议: 最多 5 个子会话（轮流执行）
# v2.1 建议: 根据 CPU 核心数（并行执行）

# 检查 CPU 核心数
nproc  # Linux
sysctl -n hw.ncpu  # macOS
```

---

### 4. 记录会话日志

```bash
# 每个会话独立日志
logs/
├── sess_20260622_001.log
├── sess_20260622_002.log
└── sess_20260622_003.log

# 查看日志
tail -f logs/sess_20260622_002.log
```

---

## 下一步

- **查看 ADR-0010**: [ADR-0010-multi-session-management.md](../adr/ADR-0010-multi-session-management.md)
- **查看 Loop 引擎指南**: [v2-loop-engine-guide.md](../v2-loop-engine-guide.md)
- **查看配置 Schema**: [v2-config-schema.md](../v2-config-schema.md)

---

**文档维护者**: sisyphus  
**最后更新**: 2026-06-22  
**下次审查**: v2.0 发布后

