# Design: fix-scan-state-binding

## 问题分析

### Bug 1: `scan-state.sh` 的 `owner` 变量跨行损坏

`skills/guide/scripts/scan-state.sh` 中 `scan_session_binding()` 的 `owner` 赋值在当前分支里被切坏成三行：

```bash
local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$
# check_stale_workflow_state() is called automatically at the end of scan_state()
}"
```

这会把注释行卷进 shell 字符串，导致 `owner` 变量不是一个单行 session id，而是污染后的多行文本。结果是后续 Python 端 `find_current_binding(owner)` 无法命中当前绑定，session binding 检测静默失效。

**修复**：恢复为单行赋值，并把注释放回独立行：

```bash
# owner = current OpenCode session id, or host+pid fallback.
local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
# check_stale_workflow_state() is called automatically at the end of scan_state()
```

### Bug 2: `check_heartbeat_timeouts()` 需要从绑定扫描流程中独立出来

当前 `scan_session_binding()` 把 heartbeat GC 逻辑和 binding 查询混在同一个 Python heredoc 中，虽然能工作，但职责不清晰，也让后续复用更难。

**修复**：把 heartbeat timeout 清理提取成独立 shell helper `check_heartbeat_timeouts()`，再由 `scan_session_binding()` 调用它。这样：

- `check_heartbeat_timeouts()` 只负责 session GC
- `scan_session_binding()` 先清理超时 session，再做当前绑定和推荐项查询
- 绑定查询逻辑保持只读输出，不修改 `sessions.json`

### Bug 3: dashboard 的 current session 标记仍按“最近 active”判断

`skills/_lib/dashboard/__init__.py::collect()` 当前使用“最近 started 的 active session”作为 `is_current`，这和 `scan_session_binding()` 里的 owner binding 语义不一致。

**修复**：在 `collect()` 中优先用 `OPENCODE_SESSION_ID` 匹配 `owner_opencode_session_id`，将命中的 session 标成 `is_current=True`；如果没有 owner 匹配，再回退到现有的“最近 active”逻辑，保持向后兼容。

## 设计决策

### D1: heartbeat GC 保持在 scan-state 层，避免散落到 dashboard

`check_heartbeat_timeouts()` 属于 workflow state 清理职责，不应进入 dashboard collector。dashboard 只消费已经整理好的 sessions 视图。

### D2: dashboard current 标记采用 owner 优先、active 回退

优先级如下：

1. 若 `OPENCODE_SESSION_ID` 存在，优先匹配 `owner_opencode_session_id == OPENCODE_SESSION_ID`
2. 若没有 owner 匹配，回退到“最近 active session”
3. 若两者都没有，当前 session 不标记

这样能保证和 `scan_session_binding()` 的 binding 语义一致，同时不破坏旧数据。

### D3: 回归测试覆盖两个入口

新增一个 bats 回归文件锁定 `scan_session_binding()` 的 owner 解析与 heartbeat 调用链，再补一个 Python 单元测试覆盖 dashboard collector 的 owner 优先逻辑。

## 影响分析

### 受影响文件

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `skills/guide/scripts/scan-state.sh` | Modify | 修复 `owner` 语法、拆出 `check_heartbeat_timeouts()`、恢复绑定扫描流程 |
| `skills/_lib/dashboard/__init__.py` | Modify | `collect()` 增加 owner-based current 标记与 active 回退 |
| `tests/integration/test_fix_scan_state_binding.bats` | Modify | 回归测试覆盖 syntax fix、heartbeat flow、binding 输出 |
| `tests/unit/test_dashboard_renderer.py` | Modify | 补 owner-based `is_current` 测试 |

### 不受影响

- `skills/rddf-session/scripts/rddf_session.py`：不改业务语义，只调用其现有方法
- `skills/_lib/dashboard/renderer.py`：渲染层继续消费 `is_current`，无需改动
- `tests/conftest.py`：不需要额外桥接

## 验收标准映射

| 验收标准 | 实现方式 |
|---|---|
| rddf dashboard session 区块显示当前 session 绑定而非 "(no active session)" | `collect()` 用 owner 匹配标记 current，renderer 继续渲染 `is_current` |
| scan_session_binding 不因语法错误提前中断 | 修复 `owner` 赋值的跨行损坏 |
| 所有现有测试通过 | bats + pytest 回归覆盖 |

## 测试策略

### bats 回归

新增 `tests/integration/test_fix_scan_state_binding.bats`，覆盖：

1. `scan_session_binding` 在 `OPENCODE_SESSION_ID` 设定时返回 current binding
2. `scan_session_binding` 在 `OPENCODE_SESSION_ID` 缺失时，`owner` 仍保持单行且不会卷入注释
3. `check_heartbeat_timeouts()` 仍在 binding flow 内被调用，绑定输出不为空
4. sessions.json 缺失时，函数静默返回 0

### Python 单元

扩展 `tests/unit/test_dashboard_renderer.py`：

1. `OPENCODE_SESSION_ID` 存在时，owner 匹配的 session 标为 current
2. `OPENCODE_SESSION_ID` 不存在时，回退到最近 active session
