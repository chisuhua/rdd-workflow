# RDDF-0001: 修复 rddf-session 跨运行时导入路径断裂

> **状态**: Proposed
> **日期**: 2026-07-23
> **来源**: PTX-EMU guide-plan → rddf-session hook 失败实战
> **影响范围**: rdd-workflow 所有调用 rddf-session 的消费者

---

## 问题描述

`skills/rddf-session/scripts/rddf_session.py` 在 commit `38cf932` 中被重构为外观模式（facade），使用**相对导入**从 `rddf_session_pkg/` 子模块引用类型。这一重构破坏了所有非 pytest 运行时的导入路径。

### 两条断裂的导入路径

**路径 A: `rddf_session_hooks.sh`（被 guide-plan/arch/ship 调用）**

```python
# rddf_session_hooks.sh 第 59 行
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
```

**失败原因**: `sys.path[0]` 指向项目根目录。Python 在此目录下查找 `skills/rddf_session/`（下划线），但实际目录名为 `skills/rddf-session/`（连字符）。Python 标识符中不允许连字符，导致 `ModuleNotFoundError`。

**路径 B: `scan-state.sh`（被 guide 技能调用）**

```python
# scan-state.sh 第 353-357 行
module_path = os.path.join(sys.argv[2], "skills", "rddf-session", "scripts", "rddf_session.py")
spec = importlib.util.spec_from_file_location("rddf_session", module_path)
rddf_session = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rddf_session
spec.loader.exec_module(rddf_session)
```

**失败原因**: 此路径绕过了模块名解析（直接通过文件路径加载），但 `rddf_session.py` 现在使用**相对导入**（`from .rddf_session_pkg._types import ...`）。`importlib.util.spec_from_file_location` 不会自动设置 `__package__`，因此相对导入失败。

### 波及范围

| 消费者 | 调用方式 | 状态 |
|---------|---------|------|
| `rddf_session_hooks.sh:entry()` | `from skills.rddf_session...import` | ❌ 断裂 |
| `rddf_session_hooks.sh:close()` | `from skills.rddf_session...import` | ❌ 断裂 |
| `scan-state.sh:check_heartbeat_timeouts()` | `importlib.util.spec_from_file_location` | ❌ 断裂 |
| `scan-state.sh:scan_session_binding()` | `importlib.util.spec_from_file_location` | ❌ 断裂 |
| pytest tests (`conftest.py`) | 合成模块别名 | ✅ 通过 |
| `rddf` CLI (`skills._lib.cli`) | 直接导入 | ⚠️ 依赖 Python 路径设置 |

### bats 测试确认

```
$ bats tests/integration/test_rddf_session_hooks_extraction.bats
15 tests, 10 failures    # 所有 10 个运行时测试均因 ModuleNotFoundError 失败
```

---

## 根因分析

### 直接原因: 连字符目录名 + 相对导入 = 双重断裂

```
rdd-workflow/skills/
├── rddf-session/           ← 连字符，Python import 不可见
│   └── scripts/
│       ├── rddf_session.py  ← 使用 from .rddf_session_pkg import ...
│       └── rddf_session_pkg/ ← 子模块包
│           ├── _types.py
│           ├── _store.py
│           ├── _commands.py
│           └── _binding.py
├── guide/                  ← scan-state.sh 在此
└── guide-plan/             ← rddf_session_hooks.sh 被 source 在此
```

### 历史: 重构引入但未更新消费者

| commit | 变更 | 问题 |
|--------|------|------|
| `2789cf0` | 将 rddf_session 从 `_lib/` 移到 `rddf-session/scripts/` | 目录名引入连字符 |
| `38cf932` | 拆分为外观模式 + `rddf_session_pkg/`，使用相对导入 | 相对导入要求 `__package__` |

`conftest.py` 中的 dash-bridge（`skills.rddf_session → skills/rddf-session/` 合成模块别名）**仅在 pytest 下工作**，不会影响 bash heredoc 或 CLI Python 进程。

---

## 修复方案

### 方案 A（推荐）: `rddf_session.py` 使用 importlib 自加载子模块

将 `rddf_session.py` 开头的相对导入替换为基于 `importlib.util.spec_from_file_location` 的自加载模式：

```python
"""RddfSessionCoordinator — facade over internal modules.

This file is now the public API surface. All implementation lives in
rddf_session_pkg/ submodules (types, store, commands, binding).

Submodule loading: uses importlib.util.spec_from_file_location instead of
relative imports (from .rddf_session_pkg import ...). This ensures the
module works correctly when loaded via:
  - from skills.rddf_session.scripts.rddf_session import ...  (hooks.sh)
  - importlib.util.spec_from_file_location(...)               (scan-state.sh)
  - pytest (conftest.py dash-bridge)
"""

import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional

# ── Self-load submodules via file path (bypass relative import requirement) ──
_PKG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rddf_session_pkg')
for _sub_name, _sub_file in [
    ('_types', '_types.py'),
    ('_store', '_store.py'),
    ('_commands', '_commands.py'),
    ('_binding', '_binding.py'),
]:
    _mod_path = os.path.join(_PKG_DIR, _sub_file)
    _spec = importlib.util.spec_from_file_location(
        f'rddf_session_pkg.{_sub_name}', _mod_path
    )
    _mod = importlib.util.module_from_spec(_spec)
    _mod.__package__ = 'rddf_session_pkg'
    sys.modules[f'rddf_session_pkg.{_sub_name}'] = _mod
    _spec.loader.exec_module(_mod)

from rddf_session_pkg._types import (  # noqa: F401
    HeartbeatConfig,
    RddfSession,
    RddfSessionError,
    SchemaValidationError,
    ConflictError,
    ...
)
from rddf_session_pkg._store import RddfSessionStore  # noqa: F401
from rddf_session_pkg._commands import RddfSessionCommands  # noqa: F401
from rddf_session_pkg._binding import RddfSessionBinding  # noqa: F401
```

**优点**:
- 一处修改，所有消费者自动修复
- 保留外观模式 + 子模块化结构
- 兼容所有三种导入路径（hooks.sh、scan-state.sh、pytest）
- 无目录改名风险

**缺点**:
- `rddf_session.py` 中增加 ~15 行加载逻辑
- 加载顺序依赖（子模块必须先于外观导入）通过 for 循环保证

### 方案 B: 修复所有消费者

分别修改 `rddf_session_hooks.sh` 和 `scan-state.sh` 中的 Python 片段：

**`rddf_session_hooks.sh`** → 改用 `importlib.util.spec_from_file_location`：
```python
import importlib.util, os, sys
project_root = os.environ["PROJECT_ROOT"]
module_path = os.path.join(project_root, "skills", "rddf-session", "scripts", "rddf_session.py")
spec = importlib.util.spec_from_file_location("rddf_session", module_path)
rddf_session_mod = importlib.util.module_from_spec(spec)
rddf_session_mod.__package__ = "rddf_session.scripts"
sys.modules["rddf_session"] = rddf_session_mod
spec.loader.exec_module(rddf_session_mod)
RddfSessionCoordinator = rddf_session_mod.RddfSessionCoordinator
```

**`scan-state.sh`** → 增加 `__package__` 设置：
```python
# 在 exec_module 前添加:
rddf_session.__package__ = "rddf_session.scripts"
```

**优点**: 不修改 `rddf_session.py`
**缺点**: 两处修改，遗漏任一消费者则仍断裂

### 方案 C: 目录改名

将 `skills/rddf-session/` 改为 `skills/rddf_session/`。

**优点**: 彻底解决模块名问题
**缺点**: 
- 目录改名影响 git 历史追踪
- 需更新所有 `SKILL.md` 中引用该目录的路径
- 需更新 `conftest.py` 中的 dash-bridge 映射
- 影响所有 `.opencode/skills/` 安装脚本中该目录的引用

---

## 验证方法

### 修复后验证清单

```bash
# 1. Python 导入测试（模拟 hooks.sh 调用方式）
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$PWD python3 -c '
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
print(f"✅ hooks.sh path OK: {RddfSessionCoordinator}")
'

# 2. Python 导入测试（模拟 scan-state.sh 调用方式）
cd /workspace/project/rdd-workflow
python3 -c '
import importlib.util, os, sys
module_path = os.path.join(os.getcwd(), "skills", "rddf-session", "scripts", "rddf_session.py")
spec = importlib.util.spec_from_file_location("rddf_session", module_path)
mod = importlib.util.module_from_spec(spec)
mod.__package__ = "rddf_session.scripts"
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
print(f"✅ scan-state.sh path OK: {mod.RddfSessionCoordinator}")
'

# 3. bats 测试
bats tests/integration/test_rddf_session_hooks_extraction.bats

# 4. 现有 pytest 无回归
cd tests && python3 -m pytest integration/test_phase2_python_imports.py -v 2>&1 | tail -5
```

### 回归风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| 子模块加载顺序错误 | 低 | for 循环按依赖顺序加载（_types → _store → _commands → _binding） |
| pytest dash-bridge 与新加载方式冲突 | 低 | conftest.py 的模块别名可能被覆盖；用 `if mod_name not in sys.modules` 保护 |
| 已有 `rddf` CLI 命令受影响 | 低 | CLI 使用 `python3 -m skills._lib.cli` 独立加载路径，不受影响 |

---

## 决策

**推荐方案 A**: 修改 `rddf_session.py` 使用 importlib 自加载子模块。

理由:
1. **一处修改，全局修复** — 无需追踪所有消费者
2. **保持所有现有导入路径兼容** — hooks.sh (str→import)、scan-state.sh (importlib)、pytest (dash-bridge)
3. **最小化变更范围** — 仅修改 `rddf_session.py` 一个文件
4. **不破坏现有测试** — pytest dash-bridge 无冲突

### 2026-07-28 审计发现: 部分修复状态

**hooks.sh 路径**: 已通过 `skills/rddf_session.py` proxy 文件（`__path__` 桥接）在 2026-07-23 修复。该文件将 Python 的 `skills.rddf_session` 模块名映射到文件系统目录 `skills/rddf-session/`。导入路径 (`from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator`) 正常运行。

**scan-state.sh 路径**: 仍断裂。`importlib.util.spec_from_file_location` 直接加载带连字符路径的文件时，相对导入 `from .rddf_session_pkg import ...` 因缺失 `__package__` 设置而失败。

**bats 测试 (15/15)**: 全部通过，但覆盖范围仅限于 hooks 功能，未测试 scan-state.sh 的运行时导入路径。

**修正建议**: 原方案 A（importlib 自加载）仍为推荐修复方案。hooks.sh 的临时 proxy 修复可保留作为后备，但 scan-state.sh 路径需要主动修复。|