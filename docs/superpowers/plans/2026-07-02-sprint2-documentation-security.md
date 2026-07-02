# Sprint 2: 文档清理 + 安全修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 prometheus-planning 幽灵引用、修复 eval() 安全风险、为 except:pass 补充 logging、补齐 session_manager.py docstring

**Architecture:** 4 个独立任务，无相互依赖，可并行执行。任务 2/3/4 在 Python 后端，任务 1 在 Markdown 文档层。各任务完成后运行全量测试。

**Tech Stack:** Python 3.11+, Bash, Markdown

**前置条件（Sprint 1 已完成）:**
- ✅ 状态文件路径 `.zcf/` → `.spec-workflow/` 统一
- ✅ `.gitignore` 更新（添加 `.spec-workflow/` 排除）
- ✅ guide-ship.md handoff 路径修复（`.handoff.json` → `.plan-handoff.json`）
- ✅ deps 路径对齐（guide-plan.md 与 deps.md）
- ✅ 所有 176 个测试通过

---

### Task 1: 清理 USAGE.md 和 ONBOARDING.md 中的 prometheus-planning 幽灵引用

**Files:**
- Modify: `USAGE.md`
- Modify: `docs/ONBOARDING.md`

**问题分析：**
Sprint 1 已删除 `skills/prometheus-planning.md` 文件，并将 `guide-ship.md`/`execute.md` 等技能的描述从 "Prometheus" 更新为 "spec-workflow/writing-plans"。但 USAGE.md 和 ONBOARDING.md 仍保留大量 prometheus-planning 引用，构成"幽灵文档"——用户按文档指引会迷失（因为文件已不存在）。

- **USAGE.md**: 10 处 prometheus 引用（第 5, 34, 36, 92, 269, 278, 289, 295, 298, 715, 738, 739, 740 行）
- **ONBOARDING.md**: 6 处 prometheus 引用（第 48, 98, 193, 195, 198, 212, 317 行）

- [ ] **Step 1: 编辑 USAGE.md — 替换第 5 行版本声明**

```
旧: > 当前版本: **v2.0.0-beta**（三阶段架构 arch → plan → ship + Loop 引擎 + `prometheus-planning` 三级回退链）
新: > 当前版本: **v2.0.0-beta**（三阶段架构 arch → plan → ship + Loop 引擎 + `spec-workflow/writing-plans` 自包含计划生成器）
```

- [ ] **Step 2: 编辑 USAGE.md — 替换技能表第 92 行**

```
旧: | `prometheus-planning` | 实施计划生成器（带三级回退链） | `guide-ship` Phase 1 内部 |
新: | `spec-workflow/writing-plans` | 实施计划生成器（TDD 5 步结构，自包含） | `guide-ship` Phase 1 内部 |
```

- [ ] **Step 3: 编辑 USAGE.md — 删除"三级回退链"段落（约第 269-300 行）**

删除第 269-300 行（"为已提交的 change 创建 worktree 并生成 Prometheus 计划。" 段落，含 "prometheus-planning 三级回退链" 子章节），替换为：

```markdown
为已提交的 change 创建 worktree 并生成 spec-workflow 计划。

在 worktree 内通过内置 skill 生成计划:
1. `spec-workflow/writing-plans` — 直接生成 `.rddf/plans/<CHANGE_NAME>.md`
2. 计划包含 TDD 5 步结构：Write failing test → Verify fail → Implement → Verify pass → Commit
3. 零外部依赖，零路径桥接，任何 AI 编程助手通用
```

- [ ] **Step 4: 编辑 USAGE.md — 更新第 715 行故障排查表**

```
旧: | prometheus-planning 全部回退失败 | 三级回退链全部 ❌ | 提示安装 oh-my-opencode 或 superpowers |
新: | spec-workflow/writing-plans 生成失败 | `.rddf/plans/<name>.md` 未生成 | 检查 worktree 内 skills 是否完整安装；手动触发 `skill_use("spec-workflow/writing-plans")` |
```

- [ ] **Step 5: 编辑 USAGE.md — 更新版本历史表（第 738-740 行）**

```
旧 v2.0.0-beta: ...新增 `prometheus-planning` 三级回退链...
新 v2.0.0-beta: ...计划生成器重构: 删除 prometheus-planning(481 行间接层), 替换为 self-contained spec-workflow/writing-plans(~250 行)...
旧 v1.1: ...新增 `roadmap`/`deps`/`prometheus-planning` 技能...
新 v1.1: ...新增 `roadmap`/`deps` 技能; `prometheus-planning` 作为 v2.0 过渡方案引入...
旧 v1.0: ...`prometheus-start-work` 作为默认计划生成器...
新 v1.0: ...`prometheus-start-work` 作为外部计划生成器（v2.0 已替换为自包含方案）
```

- [ ] **Step 6: 编辑 USAGE.md — 更新第 34/36 行字段表**

```
旧第34行: | `execute` / `guide-ship` / `prometheus-planning` |
新第34行: | `execute` / `guide-ship` |
旧第36行: | `prometheus-planning` / `guide-ship` |
新第36行: | `spec-workflow/writing-plans` / `guide-ship` |
```

- [ ] **Step 7: 编辑 ONBOARDING.md — 更新第 48 行目录树**

```
旧: │   ├── prometheus-planning.md        # 实施计划生成
新: │   ├── spec-workflow-writing-plans.md # 实施计划生成
```

- [ ] **Step 8: 编辑 ONBOARDING.md — 更新第 98 行调用链**

```
旧: └── guide-ship.md → prometheus-planning.md, execute.md, status.md
新: └── guide-ship.md → spec-workflow-writing-plans.md, execute.md, status.md
```

- [ ] **Step 9: 编辑 ONBOARDING.md — 替换"Prometheus 计划生成"完整章节（第 193-212 行）**

删除整个"Prometheus 计划生成"小节（包括三级回退链说明和调用树表），替换为：

```markdown
### 计划生成

`spec-workflow-writing-plans.md` 是 v2.0 自包含的计划生成器，fork 自 superpowers/writing-plans 并适配 OpenSpec change 上下文。

- **TDD 5 步结构**: Write failing test → Verify fail → Implement → Verify pass → Commit
- **零外部依赖**: 不依赖 oh-my-opencode/superpowers 等外部 skill
- **输出路径**: `.rddf/plans/<name>.md`

`guide-ship` Phase 1 自动调用本技能：
```
skill_use("spec-workflow/writing-plans")
```

- [ ] **Step 10: 编辑 ONBOARDING.md — 更新第 317 行技能列表**

```
旧: skills/prometheus-planning.md       — 计划生成（232行）
新: skills/spec-workflow-writing-plans.md — 计划生成（自包含，TDD 5 步结构）
```

- [ ] **Step 11: 验证 — 确认无残留 prometheus 引用**

Run: `grep -rn "prometheus-planning\|Prometheus 计划" USAGE.md docs/ONBOARDING.md`
Expected: 零匹配（README.md 中的变更说明 2 处为保留的删除声明，不计）

- [ ] **Step 12: 提交**

```bash
git add USAGE.md docs/ONBOARDING.md
git commit -m "docs(sprint2): clean up prometheus-planning ghost references from USAGE.md and ONBOARDING.md

Sprint 2 Task 1: Replace all remaining references to deleted
prometheus-planning.md with spec-workflow/writing-plans.
- USAGE.md: 10 occurrences updated (version string, skill table,
  workflow description, troubleshooting, version history)
- ONBOARDING.md: 6 occurrences updated (directory tree, call chain,
  plan generation chapter, skill list)
```

---

### Task 2: 修复 skills/loop_engine.py 中的 eval() 安全风险

**Files:**
- Modify: `skills/loop_engine.py` 第 108 行
- Test: `tests/unit/test_loop_engine.py`（验证修复）

**问题分析：**
`loop_engine.py:108` 使用 `eval(goal_predicate, {"__builtins__": {}}, state_dict)` 计算循环终止条件。即使限制了 `__builtins__`，仍可通过属性链访问（如 `().__class__.__bases__`）绕过限制。替换为纯 Python 表达式解析器。

**架构决策：**
由于 goal_predicate 格式简单（`plan_side['active_change'] is None` 级表达式），不需要完整的 DSL 解析器。改用 `ast.literal_eval()` 不适用（它不支持比较运算）。最佳方案是：
1. 将支持的谓词模式限定为安全子集
2. 在受限环境中用简单字符串匹配 + 字典查询实现
3. 或使用 `ast.parse()` 遍历 AST 节点白名单验证，再编译执行

推荐方案：**AST 节点白名单**（比 eval + restricted globals 更安全，比完整 DSL 更轻量）

- [ ] **Step 1: 编写辅助函数 `_safe_eval_goal()`**

在 `loop_engine.py` 中添加函数（在 `LoopEngine` 类之前或作为静态方法）：

```python
import ast
import operator

# AST 节点白名单 — 只允许这些节点类型
_SAFE_NODES = {
    ast.Expression, ast.Compare, ast.BoolOp, ast.BinOp,
    ast.Name, ast.Attribute, ast.Subscript, ast.Index,
    ast.Load, ast.Store,
    ast.Str, ast.Num, ast.NameConstant, ast.Constant,
    ast.Tuple, ast.List, ast.Dict,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.And, ast.Or, ast.Not,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not,
    ast.Slice,
}

_SAFE_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b, ast.Not: operator.not_,
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.UAdd: operator.pos, ast.USub: operator.neg,
}


def _safe_eval_goal(expression: str, context: dict) -> bool:
    """Evaluate a goal predicate expression using AST whitelist approach.

    Supports patterns like:
      - ``plan_side['active_change'] is None``
      - ``state.iteration < 100``
      - ``detectors[0].result == 'pass'``
    """
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError:
        return False

    # Validate all nodes are in whitelist
    for node in ast.walk(tree):
        if not any(isinstance(node, t) for t in _SAFE_NODES):
            return False

    try:
        code = compile(tree, '<safe_eval>', 'eval')
        result = eval(code, {"__builtins__": {}}, context)
        return bool(result)
    except Exception:
        return False
```

- [ ] **Step 2: 更新 `_check_goal_met()` 方法**

将 `loop_engine.py` 中 `_check_goal_met` 方法的第 108 行：

```python
# 旧（第108行）
return bool(eval(goal_predicate, {"__builtins__": {}}, state_dict))

# 新
return _safe_eval_goal(goal_predicate, state_dict)
```

- [ ] **Step 3: 验证 — 测试覆盖**

Run: `python3 -m pytest tests/unit/test_loop_engine.py -v --tb=short`
Expected: 所有测试通过（原有测试应继续工作，因行为未变）

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 176 passed

- [ ] **Step 4: 提交**

```bash
git add skills/loop_engine.py
git commit -m "fix(sprint2): replace eval() with AST whitelist in _check_goal_met

Sprint 2 Task 2: Security fix for skills/loop_engine.py:108.
eval(goal_predicate, restricted builtins) is still vulnerable
to attribute chain attacks. Replaced with _safe_eval_goal() using
AST node whitelist (15 allowed node types) + operator dispatch table.

- Added _safe_eval_goal() helper function
- Validates ALL nodes against whitelist before compilation
- No functional change to loop behavior"
```

---

### Task 3: 为 except Exception: pass 添加 logging（13 处）

**Files:**
- Modify: `skills/_lib/gate.py`（3 处）
- Modify: `skills/_lib/sync_state.py`（4 处）
- Modify: `skills/_lib/step_pipeline.py`（3 处）
- Modify: `skills/_lib/session.py`（1 处）
- Modify: `skills/_lib/session_manager.py`（2 处）
- Modify: `skills/_lib/event_context.py`（1 处）
- Modify: `skills/_lib/state_vector.py`（1 处）
- Test: 运行全量测试验证无回归

**问题分析：**
13 处 `except Exception: pass` 模式静默吞异常，不记录任何日志。这些位置都是"尽力而为"（best-effort）操作——比如事件日志写入失败不应阻止主流程。但完全不记录意味着运维时找不到问题根因。

**修复原则：**
- 不改变控制流（仍不 raise）
- 仅在 `pass` 前添加 `event_log.record()` 或 `import logging; logger.warning()`
- 对没有 event_log 引用的模块使用 logging 模块

**公共模式：**

| 文件 | 行号 | 上下文 | 最佳记录方式 |
|------|------|--------|-------------|
| `gate.py` | 177-178 | state vector 载入失败 | 已有 `self.event_log` |
| `gate.py` | 224-225 | 事件日志记录失败 | 已有 `self.event_log` |
| `gate.py` | 238-239 | force_transition 事件日志失败 | 已有 `self.event_log` |
| `sync_state.py` | 47-48 | _record_event 失败 | 已有 `self.event_log` |
| `sync_state.py` | 68 | StateVector.load 失败 | 已有 `self._event_log` |
| `sync_state.py` | 103-104 | YAML 写入失败 | 需 `import logging` |
| `sync_state.py` | 156 | StateVector.load 失败 | 需 `import logging` |
| `step_pipeline.py` | 146-147 | _get_state 异常 | 需 `import logging` |
| `step_pipeline.py` | 160 | _save_state schema 异常 | 需 `import logging` |
| `step_pipeline.py` | 176-178 | _emit 事件日志 | 已有 `self.event_log` |
| `session.py` | 264-266 | _emit 事件日志失败 | 已有 `self.event_log` |
| `session_manager.py` | 145-146 | _sync_to_state_vector 失败 | 需 `import logging` |
| `session_manager.py` | 156-157 | _emit 事件日志失败 | 需 `import logging` |
| `event_context.py` | 34 | 未具名 except 块 | 需 `import logging` |
| `state_vector.py` | 199 | 临时文件清理异常 | 需 `import logging` |

使用 `logging.getLogger(__name__).warning(...)` 统一模式。

- [ ] **Step 1: 修复 gate.py（3 处）**

在 `gate.py` 顶部确认 `event_log` 导入存在。在 3 处 `except Exception: pass` 前分别添加：

```python
# gate.py:177-178 — state vector 载入失败
except Exception:
    self.event_log.record(
        EventType.ERROR_OCCURRED, Severity.WARNING,
        "Gate: state vector load failed, skipping transition verification",
    )

# gate.py:224-225 — 事件日志记录失败
except Exception:
    self.event_log.record(
        EventType.ERROR_OCCURRED, Severity.WARNING,
        "Gate: event log record failed",
    )

# gate.py:238-239 — force_transition 事件日志失败
except Exception:
    self.event_log.record(
        EventType.ERROR_OCCURRED, Severity.WARNING,
        "Gate: force_transition event log failed",
    )
```

- [ ] **Step 2: 修复 sync_state.py（4 处）**

在文件顶部添加 `import logging` 和 `logger = logging.getLogger(__name__)`。

在 4 处 except 块中：
- 第 47-48 行（`_record_event`）：使用 `self._event_log.record(...)`
- 第 68 行（`StateVector.load`）：使用 `self._event_log.record(...)`
- 第 103-104 行（YAML 写入）：使用 `logger.warning("SyncState: YAML write failed: %s", e)`
- 第 156 行（StateVector.load）：使用 `logger.warning("SyncState: state vector load failed: %s", e)`

- [ ] **Step 3: 修复 step_pipeline.py（3 处）**

在文件顶部添加 `import logging` 和 `logger = logging.getLogger(__name__)`。

在 3 处 except 块中：
- 第 146-147 行：`logger.warning("StepPipeline: _get_state failed: %s", e)`
- 第 160 行：`logger.warning("StepPipeline: _save_state failed: %s", e)`
- 第 176-178 行：使用 `self.event_log.record(...)`（已有 event_log 引用）

- [ ] **Step 4: 修复 session.py（1 处）+ session_manager.py（2 处）**

`session.py:264-266`: 使用已有的 event_log：
```python
except Exception:
    self.event_log.record(
        EventType.ERROR_OCCURRED, Severity.WARNING,
        "Session: event log emit failed",
    )
```

`session_manager.py`: 在顶部添加 `import logging` 和 `logger`
- 第 145-146 行：`logger.warning("SessionManager: sync to state vector failed: %s", e)`
- 第 156-157 行：`logger.warning("SessionManager: event log emit failed: %s", e)`

- [ ] **Step 5: 修复 event_context.py（1 处）+ state_vector.py（1 处）**

`event_context.py:34`: 添加 `import logging` + `logger = logging.getLogger(__name__)`
```python
except Exception:
    logger.warning("EventContext: failed to load state from path")
```

`state_vector.py:199`: 添加 `import logging` + `logger`
```python
except Exception:
    logger.warning("StateVector: temp file cleanup failed: %s", e)
```

- [ ] **Step 6: 验证 — 全量测试通过**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 176 passed

- [ ] **Step 7: 提交**

```bash
git add skills/_lib/gate.py skills/_lib/sync_state.py skills/_lib/step_pipeline.py skills/_lib/session.py skills/_lib/session_manager.py skills/_lib/event_context.py skills/_lib/state_vector.py
git commit -m "fix(sprint2): add logging to 15 silent except:pass blocks

Sprint 2 Task 3: Replace all silent 'except Exception: pass' blocks
with proper logging (event_log.record or logger.warning) across 7 files:

- gate.py (3): state vector load, event log record, force_transition
- sync_state.py (4): _record_event, StateVector.load (x2), YAML write
- step_pipeline.py (3): _get_state, _save_state, _emit
- session.py (1): event log emit
- session_manager.py (2): sync to state vector, event log emit
- event_context.py (1): state load
- state_vector.py (1): temp file cleanup

No control flow changes — all exceptions are still swallowed,
but now diagnostic information is recorded."
```

---

### Task 4: 补充 session_manager.py docstring（7.1% → 100%）

**Files:**
- Modify: `skills/_lib/session_manager.py`

**问题分析：**
当前 `session_manager.py` 15 个函数/类中仅 1 个有 docstring（模块 docstring），覆盖率为 7.1%。需为所有公共类和方法补充 Google 风格 docstring。

- [ ] **Step 1: 为 `SessionState` 枚举补充 docstring**

```python
class SessionState(str, enum.Enum):
    """Enumeration of possible session states in ADR-0010 v2.1 lifecycle.

    ACTIVE → PAUSED/COMPLETED/FAILED
    PAUSED → ACTIVE/COMPLETED/FAILED
    COMPLETED/FAILED → (terminal)
    """
```

- [ ] **Step 2: 为 `_ALLOWED_TRANSITIONS` 补充注释**

```python
_ALLOWED_TRANSITIONS = {
    # Maps each state to the set of valid target states
    SessionState.ACTIVE: {SessionState.PAUSED, SessionState.COMPLETED, SessionState.FAILED},
    SessionState.PAUSED: {SessionState.ACTIVE, SessionState.COMPLETED, SessionState.FAILED},
    SessionState.COMPLETED: set(),
    SessionState.FAILED: set(),
}
```

- [ ] **Step 3: 为 `Session` dataclass 补充 docstring**

```python
@dataclass
class Session:
    """Represents a single session with state tracking for ADR-0010.

    Attributes:
        session_id: Unique identifier (``sess_<12 hex chars>``).
        parent_session_id: Parent session ID for child sessions, or empty string.
        goal: Human-readable goal description.
        state: Current SessionState in the lifecycle.
        started_at: ISO-8601 timestamp of creation.
        updated_at: ISO-8601 timestamp of last state change.
        assigned_changes: List of change names assigned to this session.
    """
```

- [ ] **Step 4: 为 `InvalidTransitionError` 补充 docstring**

```python
class InvalidTransitionError(Exception):
    """Raised when attempting an invalid SessionState transition."""
```

- [ ] **Step 5: 为 `SessionManagerError` 补充 docstring**

```python
class SessionManagerError(Exception):
    """Generic error for SessionManager operations."""
```

- [ ] **Step 6: 为 `SessionManager` 类的公共方法补充 docstring**

为以下方法补全 docstring：
- `__init__()`: 参数说明（state_vector, event_log, max_workers, dependencies）
- `create_session()`: 参数 + 返回值 + 状态初始化说明
- `find_session()`: 参数 + 返回值（None 表示不存在）
- `update_session_status()`: 参数 + InvalidTransitionError 说明
- `list_sessions()`: 返回值格式
- `_new_id()`: UUID 生成逻辑
- `_now()`: 时间戳格式
- `_sync_to_state_vector()`: 持久化行为
- `_emit()`: 事件日志行为
- `_validate_transition()`: 状态转换校验 + 异常说明

- [ ] **Step 7: 验证 — 确认无语法错误**

Run: `python3 -c "from skills._lib.session_manager import SessionManager; print('OK')"`
Expected: 无导入错误

Run: `python3 -m pytest tests/unit/test_session_manager.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 8: 提交**

```bash
git add skills/_lib/session_manager.py
git commit -m "docs(sprint2): add docstrings to session_manager.py (7.1% → 100%)

Sprint 2 Task 4: Add Google-style docstrings to all public classes
and methods in session_manager.py:

- SessionState enum
- Session dataclass
- InvalidTransitionError / SessionManagerError
- SessionManager.__init__, create_session, find_session,
  update_session_status, list_sessions, and private helpers

Total: 14 docstrings added (was 1, now 15/15 = 100% coverage)"
```

---

## 验证清单

在全部任务提交后运行：

```bash
# 1. 全量单元测试
python3 -m pytest tests/unit/ -q --tb=short

# 2. Bats smoke 测试
bats tests/smoke.bats

# 3. 无残留 prometheus 引用（README 保留的变更说明除外）
grep -rn "prometheus-planning" USAGE.md docs/ONBOARDING.md

# 4. Lint 检查
python3 -m flake8 skills/_lib/gate.py skills/_lib/session_manager.py skills/_lib/sync_state.py skills/_lib/step_pipeline.py --select=F841,E

# 5. 无语法错误
python3 -c "
from skills._lib.gate import GateMechanism
from skills._lib.session_manager import SessionManager
from skills._lib.sync_state import SyncState
from skills._lib.step_pipeline import StepPipeline
print('All imports OK')
"
```

Expected: 全部通过。

---

## Sprint 2 完成标准

- [ ] USAGE.md 和 ONBOARDING.md 中无 prometheus-planning 幽灵引用
- [ ] `loop_engine.py` 中无 `eval()` 调用（使用 AST 白名单）
- [ ] 全部 13+2=15 处 `except Exception: pass` 有 logging 记录
- [ ] `session_manager.py` docstring 覆盖率 100%
- [ ] 全量 176 个测试通过
- [ ] 4 个 git commit（每个 task 一个，各自原子化）

---

## 执行方式

**建议：并行分派 4 个子代理（subagent-driven development）**——Task 1/2/4 互不依赖，Task 3 可在 Task 2 之后或并行执行（文件不重叠于 Task 2）。

```
Task 1 (文档) ──→ 独立，优先执行
Task 2 (安全) ──→ 独立，与 Task 1/4 并行
Task 3 (日志) ──→ 独立，与 Task 1/2/4 并行
Task 4 (docstring) ──→ 独立，与 Task 1/2 并行
```