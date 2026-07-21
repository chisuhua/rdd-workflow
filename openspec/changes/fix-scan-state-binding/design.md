# Design: fix-scan-state-binding

## 问题分析

### Bug 1: scan-state.sh line 231-233 变量展开语法错误

当前代码 (`skills/guide/scripts/scan-state.sh:231-233`):

```bash
local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$
# check_stale_workflow_state() is called automatically at the end of scan_state()
}"
```

**根因**: 双引号字符串跨行,内嵌的 `# check_stale_workflow_state()...` 注释行落在 `${...:-default}` 的 default 子表达式内部,导致:

1. 当 `OPENCODE_SESSION_ID` 已设置 (生产常见路径) -> `${VAR:-default}` 短路返回 VAR 值,bug 不触发 (隐蔽性强)。
2. 当 `OPENCODE_SESSION_ID` 未设置 -> `owner` 被污染为多行字符串:
   ```
   my-host_12345
   # check_stale_workflow_state() is called automatically at the end of scan_state()
   ```
   该字符串随后作为 `$owner` 传入 Python heredoc 的 `sys.argv[2]`,导致 `coord.find_current_binding(owner)` 永远匹配不到任何 session,绑定检测静默失败。

**修复**: 将 `owner` 赋值与注释分离,并补充缺失的闭合 brace:

```bash
# owner = current OpenCode session id (or host+pid fallback when not bound)
local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
# check_stale_workflow_state() is called automatically at the end of scan_state()
```

### Bug 2: Python import 路径缺失 dash-bridge

`scan_session_binding` 的 Python heredoc (line 240):
```python
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
```

`skills/rddf-session/` 目录名含连字符,Python 不能直接 import `skills.rddf_session`。`tests/conftest.py` 通过 dash-bridge 注册 `sys.modules['skills.rddf_session']` 让 pytest 工作,但 standalone Python heredoc 没有此桥接 -> `ModuleNotFoundError` -> `while read` 循环空跑 -> `BINDING_LINES` 永远为空。

**修复**: 在 Python heredoc 头部复制 conftest 的 dash-bridge 模式,或直接用 `importlib` 从 `skills/rddf-session/scripts/rddf_session.py` 加载。选择后者更简洁、更显式,不依赖 sys.modules 副作用。

### Wiring: dashboard renderer session 区块

`skills/_lib/dashboard/__init__.py::collect()` line 296-315 当前用"最近 active 的 session"作为 `is_current`:

```python
active = [s for s in sessions if s.get("state") == "active"]
active.sort(key=lambda s: s.get("started_at") or "", reverse=True)
current_id = active[0].get("session_id") if active else None
```

**问题**: 这不是"当前 session 绑定"--`is_current` 应基于 `owner_opencode_session_id == os.environ["OPENCODE_SESSION_ID"]`,与 `scan_session_binding` 的 `find_current_binding(owner)` 语义一致。否则 dashboard 显示的 "current" 与 guide recommender 推荐的 binding 不一致 (spec 2026-07-14 §3 binding policy)。

**修复**: `collect()` 读取 `OPENCODE_SESSION_ID` 环境变量,优先标记 `owner_opencode_session_id == OPENCODE_SESSION_ID` 的 session 为 `is_current`;回退到"最近 active"逻辑以保持向后兼容 (旧 sessions.json 可能没有 owner 字段)。

## 设计决策

### D1: dash-bridge 实现 - importlib vs sys.modules 注册

**选择**: `importlib.util.spec_from_file_location` 直接从文件路径加载 `rddf_session.py`。

**理由**:
- 不污染 `sys.modules` (standalone Python 进程,无下游消费者)
- 显式表达"从 rddf-session/scripts/ 加载"的意图
- 与 `tests/conftest.py` 的 dash-bridge 互不干扰 (conftest 在 pytest 内,heredoc 在 bash 子进程)
- 已知 `skills/rddf-session/scripts/rddf_session.py` 存在 (`ls` 验证)

### D2: dashboard is_current 策略 - 环境变量优先 + active 回退

**选择**: 三层优先级:

1. `OPENCODE_SESSION_ID` 环境变量存在 -> 找 `owner_opencode_session_id == OPENCODE_SESSION_ID` 且 state != abandoned 的 session 标记为 current
2. 找不到 owner 匹配 -> 回退到"最近 active"逻辑 (现有行为)
3. 都没有 -> 不标记任何 session 为 current (现有行为)

**理由**:
- 向后兼容: 旧 sessions.json 无 owner 字段时仍按 active 排序
- 与 scan_session_binding 语义一致: 都用 owner 字段做绑定匹配
- 环境变量缺失时优雅降级 (CI 环境、非交互式运行)

### D3: scan_session_binding 不解耦 check_heartbeat_timeouts

**proposal 范围**: "将 check_heartbeat_timeouts() 从 scan_session_binding 中解耦提取为独立函数"

**重新评估**: 当前 `check_heartbeat_timeouts()` 已经是 `RddfSessionCoordinator` 的方法 (不在 `scan_session_binding` 中),Python heredoc 只是调用它 (`coord.check_heartbeat_timeouts()`)。proposal 描述的"解耦"实际上已经在 `rddf_session.py` 中完成。本 change 仅需确保该调用在语法 bug 修复后能正常工作。

**决定**: 不重复解耦 (DRY)。本 change 聚焦: (a) 修复语法 bug, (b) 修复 import 路径, (c) dashboard wiring。

## 影响分析

### 受影响文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `skills/guide/scripts/scan-state.sh` | Modify | 修复 line 231-233 语法 + 修复 Python heredoc import 路径 |
| `skills/_lib/dashboard/__init__.py` | Modify | `collect()` 增加 OPENCODE_SESSION_ID-based is_current 标记 |
| `tests/integration/test_fix_scan_state_binding.bats` | Create | 回归测试: syntax fix + import 路径 + binding 输出 |
| `tests/unit/test_dashboard_renderer.py` | Modify | 增加 is_current-by-owner 测试用例 |

### 不受影响

- `skills/rddf-session/scripts/rddf_session.py` - 不修改 (proposal Out Scope)
- `skills/_lib/dashboard/renderer.py` - 不修改 (proposal Out Scope: "不修改 dashboard 渲染逻辑"); 渲染层已正确消费 `is_current` 字段
- `tests/conftest.py` - 不修改 (dash-bridge 已正确)

### 风险

- **R1**: 修改 `collect()` 可能影响现有 dashboard 测试。缓解: 增加 owner-based 测试用例,保留 active-fallback 测试。
- **R2**: importlib 加载方式与 conftest dash-bridge 可能行为不一致。缓解: 两者独立运行在不同进程 (bash heredoc vs pytest),互不干扰。

## 验收标准映射

| Proposal 验收标准 | 实现方式 |
|------------------|---------|
| rddf dashboard session 区块显示当前 session 绑定而非 "(no active session)" | `collect()` 用 OPENCODE_SESSION_ID 标记 is_current; renderer 已渲染 is_current session |
| scan_session_binding 不因语法错误提前中断 | 修复 line 231-233 语法 + 修复 Python import 路径 |
| 所有现有测试通过 | 运行 bats + pytest 验证 |

## 测试策略

### 回归测试 (bats)

新增 `tests/integration/test_fix_scan_state_binding.bats`:

1. **语法修复**: `scan_session_binding` 在 `OPENCODE_SESSION_ID` 未设置时不再污染 owner 变量
2. **import 路径**: `scan_session_binding` 实际产生 `BINDING_LINES` (非空) 当 sessions.json 有匹配绑定
3. **未设置 binding**: `scan_session_binding` 输出 "No current binding" 当 owner 无匹配
4. **dashboard is_current**: `collect()` 标记 owner 匹配的 session 为 current

### 单元测试 (pytest)

扩展 `tests/unit/test_dashboard_renderer.py`:

1. `collect()` with `OPENCODE_SESSION_ID` set -> matching session `is_current=True`
2. `collect()` without `OPENCODE_SESSION_ID` -> fallback to most-recent-active (现有行为)
