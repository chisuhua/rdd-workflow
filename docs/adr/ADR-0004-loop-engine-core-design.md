# ADR-0004: Loop 引擎核心设计

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0002 (目标驱动接口), ADR-0003 (三阶段架构)

## Context

spec-workflow v1.x 采用**显式阶段切换**的菜单驱动模式，用户需要在每个 phase 手动选择菜单项推进工作流。这种模式在以下场景存在局限：

1. **自动化场景缺失**: CI/CD 管道、批量处理、明确目标时，用户希望声明目标后自动执行
2. **AI 助手兼容性**: AI 编程助手需要声明式接口（目标 → 自动编排），而非解析菜单文本
3. **状态检测重复**: `guide.md`、`status.md`、各 phase 入口都重复实现状态扫描逻辑
4. **错误恢复手动**: 当前错误处理依赖用户手动选择修复策略，缺乏自动重试/自愈机制

同时，**Loop 驱动范式**（scan → plan → execute → feedback → adapt）已在 AI 编程领域验证成功，但需要解决以下挑战：

**约束**:
- **不能完全替代菜单**: 必须支持 ADR-0002 定义的三种交互模式 (loop/menu/hybrid)
- **向后兼容**: Loop 引擎必须能调用现有 skill 文件（guide-arch/guide-plan/guide-ship）
- **防死循环**: 必须有最大迭代次数、状态震荡检测、重试限制
- **可观测性**: Loop 执行过程必须有完整日志和事件流

**技术假设**:
- Loop 引擎核心逻辑用 **Python** 实现（状态管理、决策、事件流）
- Action 执行保留 **bash**（git worktree、openspec CLI、系统操作）
- 通过 `subprocess` 调用现有 skill 文件

## Decision

我们实现 **Loop 引擎**作为 spec-workflow v2.x 的核心编排器，采用 **Detector-Action 架构** + **状态向量** + **事件流**：

### 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Loop Engine (Python)                      │
├─────────────────────────────────────────────────────────────┤
│  while not goal_achieved() and iterations < MAX_ITERATIONS: │
│    1. scan_state()        # 运行所有 detectors              │
│    2. generate_plan()     # 匹配 detectors → actions        │
│    3. check_human_nodes() # hybrid 模式：是否需要菜单       │
│    4. execute_plan()      # 执行 actions (bash skills)      │
│    5. verify_results()    # 验证执行结果                    │
│    6. update_state()      # 更新状态向量 + 事件流           │
│    7. adapt()             # 错误恢复/重试决策               │
└─────────────────────────────────────────────────────────────┘
         ↓                      ↓                      ↓
    ┌────────┐            ┌──────────┐          ┌──────────┐
    │Detector│            │  Action  │          │  State   │
    │  Scan  │            │ Executor │          │  Vector  │
    └────────┘            └──────────┘          └──────────┘
```

### Detector-Action 架构

#### Detectors (状态检测器)

每个 detector 是独立的 Python 函数，输出结构化状态：

```python
# skills/_lib/detectors.py

def detect_worktrees(state: StateVector) -> DetectionResult:
    """检测活跃 worktrees"""
    result = subprocess.run(
        ["git", "worktree", "list"],
        capture_output=True, text=True
    )
    worktrees = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("openspec/"):
            worktrees.append({
                "path": parts[0],
                "branch": parts[2],
                "change_name": parts[2].replace("openspec/", "")
            })
    return DetectionResult(
        type="worktrees",
        data={"active": worktrees, "count": len(worktrees)}
    )

def detect_pending_changes(state: StateVector) -> DetectionResult:
    """检测待处理 changes"""
    # 扫描 openspec/changes/*/ 目录（排除 archive/）
    changes = []
    for d in Path(state.project_root / "openspec/changes").iterdir():
        if d.is_dir() and d.name != "archive":
            if not (d / ".openspec.yaml").exists():
                changes.append({"name": d.name, "status": "incomplete"})
            else:
                changes.append({"name": d.name, "status": "committed"})
    return DetectionResult(
        type="pending_changes",
        data={"changes": changes, "count": len(changes)}
    )

def detect_roadmap_state(state: StateVector) -> DetectionResult:
    """检测 roadmap 状态"""
    roadmap_file = state.project_root / "roadmap.md"
    if not roadmap_file.exists():
        return DetectionResult(type="roadmap", data={"exists": False})
    
    # 解析 roadmap.md 当前阶段和完成度
    content = roadmap_file.read_text()
    # ... 解析逻辑 ...
    return DetectionResult(
        type="roadmap",
        data={
            "exists": True,
            "current_phase": "core",
            "completion": 0.45,
            "categories": [...]
        }
    )

def detect_health_issues(state: StateVector) -> DetectionResult:
    """检测健康问题和错误"""
    issues = []
    # 检查 openspec CLI 是否可用
    if not shutil.which("openspec"):
        issues.append({"severity": "error", "message": "openspec CLI not found"})
    # 检查 .rddf/state/ 状态文件一致性
    # ... 更多检查 ...
    return DetectionResult(type="health", data={"issues": issues})
```

**内置 Detectors**:
| Detector | 检测内容 | 输出 |
|----------|---------|------|
| `detect_worktrees` | 活跃 worktrees | worktree 列表 + 进度 |
| `detect_pending_changes` | 待处理 changes | changes 列表 + 状态 |
| `detect_archived_changes` | 已归档 changes | archive 统计 |
| `detect_roadmap_state` | roadmap 状态 | 当前阶段 + 完成度 |
| `detect_adr_status` | ADR 文档状态 | ADR 数量 + 最新 |
| `detect_health_issues` | 环境问题 | 错误/警告列表 |
| `detect_test_gaps` | 测试覆盖缺口 | 未测试文件列表 |
| `detect_stale_branches` | 过期分支 | 可删除分支列表 |

#### Actions (执行动作)

每个 action 调用现有 skill 文件或 bash 脚本：

```python
# skills/_lib/actions.py

def action_create_worktree(change_name: str, config: LoopConfig) -> ActionResult:
    """创建 worktree"""
    result = subprocess.run(
        ["bash", "-c", f"""
        source skills/_lib/worktree.sh
        create_worktree "{change_name}"
        """],
        cwd=config.project_root,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return ActionResult(success=True, data={"worktree": change_name})
    else:
        return ActionResult(success=False, error=result.stderr)

def action_generate_plan(change_name: str, config: LoopConfig) -> ActionResult:
    """生成 Prometheus 计划"""
    result = subprocess.run(
        ["bash", "-c", f"""
        skill_use("prometheus-planning", "{change_name}")
        """],
        cwd=config.project_root,
        capture_output=True, text=True
    )
    # ... 验证计划文件生成 ...
    return ActionResult(success=True)

def action_execute_worktree(change_name: str, config: LoopConfig) -> ActionResult:
    """执行 worktree 中的 work units"""
    result = subprocess.run(
        ["bash", "-c", f"""
        skill_use("execute", "{change_name}")
        """],
        cwd=config.project_root,
        capture_output=True, text=True
    )
    # ... 解析执行结果 ...
    return ActionResult(success=True)

def action_archive_change(change_name: str, config: LoopConfig) -> ActionResult:
    """归档 change"""
    result = subprocess.run(
        ["bash", "-c", f"""
        source skills/_lib/archive.sh
        archive_change "{change_name}"
        """],
        cwd=config.project_root,
        capture_output=True, text=True
    )
    return ActionResult(success=True)
```

**内置 Actions**:
| Action | 调用技能 | 描述 |
|--------|---------|------|
| `action_create_worktree` | `_lib/worktree.sh` | 创建 worktree + branch |
| `action_generate_plan` | `prometheus-planning` | 生成 Prometheus 计划 |
| `action_execute_worktree` | `execute` | 执行 work units |
| `action_archive_change` | `_lib/archive.sh` | merge + archive + cleanup |
| `action_cleanup_stale` | bash | 清理过期 worktrees/branches |
| `action_update_roadmap` | `roadmap` | 更新 roadmap 进度 |
| `action_create_adr` | AI 助手 | 创建 ADR 文档 |

### 状态向量设计

```json
// .rddf/state/state-vector.json
{
  "version": "2.0",
  "timestamp": "2026-06-22T10:30:00Z",
  "project_root": "/path/to/project",
  "goal": {
    "description": "complete all pending changes",
    "mode": "hybrid",
    "started_at": "2026-06-22T10:00:00Z"
  },
  "arch_side": {
    "adr_count": 3,
    "roadmap": {
      "exists": true,
      "current_phase": "core",
      "completion": 0.45
    },
    "health": {
      "errors": [],
      "warnings": []
    }
  },
  "plan_side": {
    "active_changes": [
      {"name": "add-auth", "status": "committed"},
      {"name": "refactor-db", "status": "incomplete"}
    ],
    "deps_analysis": {...}
  },
  "ship_side": {
    "worktrees": [
      {
        "name": "add-auth",
        "branch": "openspec/add-auth",
        "progress": 0.7,
        "plan_tasks": 15,
        "completed_tasks": 10
      }
    ],
    "pending_archive": [],
    "last_action": "execute_unit_5"
  },
  "loop_state": {
    "iterations": 5,
    "retries": 0,
    "current_phase": "ship",
    "state_history": ["arch", "plan", "ship", "ship", "ship"]
  }
}
```

### 事件流设计

```jsonl
// .rddf/state/event-log.jsonl (每行一个事件)
{"ts": "2026-06-22T10:00:00Z", "type": "loop_started", "goal": "complete all changes"}
{"ts": "2026-06-22T10:00:01Z", "type": "scan_completed", "detectors": 8, "duration_ms": 150}
{"ts": "2026-06-22T10:00:02Z", "type": "plan_generated", "actions": 3, "mode": "hybrid"}
{"ts": "2026-06-22T10:00:03Z", "type": "human_in_loop", "node": "plan.change_select", "decision": "select_all"}
{"ts": "2026-06-22T10:00:10Z", "type": "worktree_created", "change": "add-auth"}
{"ts": "2026-06-22T10:00:15Z", "type": "plan_generated", "change": "add-auth", "tasks": 15}
{"ts": "2026-06-22T10:30:00Z", "type": "unit_completed", "change": "add-auth", "unit": 5, "total": 15}
{"ts": "2026-06-22T11:00:00Z", "type": "change_archived", "change": "add-auth"}
{"ts": "2026-06-22T11:00:01Z", "type": "loop_iteration", "iteration": 5, "state": "ship"}
```

### Loop 引擎核心循环

```python
# skills/loop-engine.py

class LoopEngine:
    def __init__(self, goal: str, config: LoopConfig):
        self.goal = goal
        self.config = config
        self.state = load_state_vector()
        self.event_log = EventLog()
        self.iterations = 0
        self.state_history = []
    
    def run(self):
        """主循环"""
        while not self.goal_achieved():
            self.iterations += 1
            
            # 安全检查
            if self.iterations > self.config.max_iterations:
                raise LoopError(f"Max iterations ({self.config.max_iterations}) exceeded")
            if self.detect_state_oscillation():
                raise LoopError("State oscillation detected")
            
            # 1. 扫描状态
            detections = self.scan_state()
            self.event_log.record("scan_completed", {"detectors": len(detections)})
            
            # 2. 生成计划
            plan = self.generate_plan(detections)
            self.event_log.record("plan_generated", {"actions": len(plan.actions)})
            
            # 3. Human-in-Loop 检查 (hybrid 模式)
            if self.config.mode == "hybrid":
                plan = self.check_human_nodes(plan)
            
            # 4. 执行计划
            results = self.execute_plan(plan)
            self.event_log.record("plan_executed", {"success": results.success})
            
            # 5. 验证结果
            if not results.success:
                if self.config.auto_retry and results.retries < self.config.max_retries:
                    self.adapt_and_retry(results)
                    continue
                else:
                    raise LoopError(f"Action failed: {results.error}")
            
            # 6. 更新状态
            self.update_state(results)
            self.state_history.append(self.state.loop_state.current_phase)
    
    def goal_achieved(self) -> bool:
        """检查目标是否达成"""
        if "complete all changes" in self.goal:
            return (
                len(self.state.plan_side.active_changes) == 0 and
                len(self.state.ship_side.worktrees) == 0 and
                len(self.state.ship_side.pending_archive) == 0
            )
        elif "create worktrees" in self.goal:
            return all(
                wt.exists for wt in self.state.ship_side.worktrees
            )
        # ... 更多目标类型 ...
        return False
    
    def scan_state(self) -> List[DetectionResult]:
        """运行所有 detectors"""
        detectors = [
            detect_worktrees,
            detect_pending_changes,
            detect_roadmap_state,
            detect_adr_status,
            detect_health_issues,
            # ... 更多 detectors ...
        ]
        return [d(self.state) for d in detectors]
    
    def generate_plan(self, detections: List[DetectionResult]) -> Plan:
        """根据检测结果生成计划"""
        actions = []
        for detection in detections:
            actions.extend(self.match_actions(detection))
        return Plan(actions=actions)
    
    def match_actions(self, detection: DetectionResult) -> List[Action]:
        """匹配 detectors → actions"""
        if detection.type == "pending_changes" and detection.data["count"] > 0:
            return [action_create_worktree(change["name"]) for change in detection.data["changes"]]
        elif detection.type == "worktrees" and detection.data["count"] > 0:
            return [action_execute_worktree(wt["name"]) for wt in detection.data["active"]]
        # ... 更多匹配规则 ...
        return []
    
    def check_human_nodes(self, plan: Plan) -> Plan:
        """Hybrid 模式：检查是否需要 human-in-loop"""
        for action in plan.actions:
            if action.node in self.config.menu.human_in_loop_nodes:
                decision = self.show_menu(action)
                if decision == "skip":
                    plan.actions.remove(action)
                elif decision == "modify":
                    action = self.modify_action(action)
        return plan
    
    def detect_state_oscillation(self) -> bool:
        """检测状态震荡（防止死循环）"""
        if len(self.state_history) < 5:
            return False
        recent = self.state_history[-5:]
        return len(set(recent)) <= 2  # 如果最近 5 次只有 ≤2 种状态，认为震荡
```

### 安全机制

| 机制 | 实现 | 默认值 |
|------|------|-------|
| 最大迭代次数 | `iterations < MAX_ITERATIONS` | 100 |
| 最大重试次数 | `retries < MAX_RETRIES` | 3 |
| 状态震荡检测 | 检查最近 5 次状态历史 | ≤2 种状态 = 震荡 |
| 错误升级 | 重试失败后抛出 `LoopError` | - |
| 超时控制 | 每个 action 最大执行时间 | 30 分钟 |
| 并行限制 | 同时执行的 worktrees 数量 | 3 |

### 影响范围

- **In Scope**:
  - 新增 `skills/loop-engine.py` (Loop 引擎核心)
  - 新增 `skills/_lib/detectors.py` (状态检测器)
  - 新增 `skills/_lib/actions.py` (执行动作)
  - 新增 `.rddf/state/state-vector.json` (状态向量)
  - 新增 `.rddf/state/event-log.jsonl` (事件流)
  
- **Out Scope**:
  - 不改变现有 skill 文件内部逻辑（只通过 subprocess 调用）
  - 不改变 openspec CLI 接口
  - 不改变 `.rddf/state/` 目录结构（只新增文件）

### 备选方案

| 备选 | 理由 |
|------|------|
| **纯 bash 实现** | 拒绝：状态管理、JSON 解析、事件流在 bash 中复杂度高 |
| **完全重写 skill 文件** | 拒绝：迁移成本过高，保留现有 skill 作为 action 调用 |
| **外部依赖 (Celery/Airflow)** | 拒绝：引入过重依赖，spec-workflow 应保持轻量 |
| **Python + bash hybrid** | 接受：Python 处理逻辑，bash 处理系统操作 |

## Consequences

### 正面

- **自动化支持**: 支持 CI/CD 场景，声明目标后自动执行
- **AI 友好**: 声明式接口，AI 助手可直接调用 `skill_use("loop", {goal: ...})`
- **可观测性**: 完整事件流，支持审计、调试、进度报告
- **错误恢复**: 自动重试 + 自适应调整，减少人工干预
- **模块化**: Detector-Action 架构，添加新检测器/动作只需扩展，不需修改核心

### 负面 / 风险

- **学习成本**: 用户需要理解 Loop 引擎配置和工作原理
  - **缓解**: 提供默认配置和教程
- **调试复杂度**: Python + bash 混合，错误追踪需要跨语言
  - **缓解**: 事件流完整记录，提供 `spec-workflow debug` 命令
- **性能开销**: Python 进程启动 + subprocess 调用
  - **缓解**: 缓存状态向量，减少重复扫描

### 后续待办

- [ ] 实现 `skills/loop-engine.py` 核心循环
- [ ] 实现内置 detectors (8 个)
- [ ] 实现内置 actions (7 个)
- [ ] 实现状态向量和事件流
- [ ] 实现安全机制（迭代限制、震荡检测、重试）
- [ ] 添加 Loop 引擎单元测试
- [ ] 添加集成测试（loop 模式 × 三阶段）
- [ ] 编写 Loop 引擎文档和教程

## References

- ADR-0002 — 目标驱动接口与交互模式配置
- ADR-0003 — 三阶段架构 (arch → plan → ship)
- `skills/guide-arch.md` — arch 阶段状态机（Loop 引擎将调用）
- `skills/guide-plan.md` — plan 阶段状态机（Loop 引擎将调用）
- `skills/guide-ship.md` — ship 阶段状态机（Loop 引擎将调用）
- GitHub Copilot Workspace — Loop 驱动自动编排参考
- OpenHands — 事件流和状态管理参考

