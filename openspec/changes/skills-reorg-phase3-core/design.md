# Design: skills-reorg-phase3-core

## Decision 1: 内核分组依据

选择 `core/` 下放 6 个模块的依据：
- `event_log.py` (9 importers), `event_types.py` (8), `state_vector.py` (7) — 三者互相关联形成运行时内核,必须同行
- `defaults.py` (6), `lock.py` (6), `atomic_write.py` (4) — 零内部依赖,纯 leaf 工具模块

## Decision 2: Loop 引擎分组依据

`loop/` 收集 v2.0 loop 引擎子系统的全部模块。选择依据：这些模块仅在 `loop_engine.py` 的 import 树中被引用，不被任何 skill `SKILL.md` 直接引用。

## Decision 3: gate.py 保留在顶层

`gate.py` 是唯一被 `actions.py` (loop/) 和 `detectors.py` (loop/) 同时 lazy-import 的模块。放入 `loop/` 可行（import 路径不变），但保留在顶层作为"跨切门控"语义更清晰。

```python
# actions.py (in loop/)
from skills._lib.gate import _read_arch_handoff_paths  # 顶层 gate

# gate.py (top-level) imports 6 modules, 5 in core/:
from skills._lib.core.event_log import EventLog
from skills._lib.core.state_vector import StateVector
# etc.
```

## Decision 4: 现有子目录保留

`schedulers/`、`schemas/`、`plugins/` 已有子目录结构，**不移动**。

## Decision 5: `__init__.py` 更新

`skills/_lib/core/__init__.py` 和 `skills/_lib/loop/__init__.py` 保持空（匹配现有 `_lib/__init__.py` 风格）。所有 import 使用绝对路径 `from skills._lib.core.X`。

## Decision 6: import 路径批量替换

使用 Python 脚本批量更新，而非手工 edit：

```python
import re, os, fileinput

REPLACEMENTS = {
    r'from skills\._lib\.event_log': 'from skills._lib.core.event_log',
    r'from skills\._lib\.event_types': 'from skills._lib.core.event_types',
    r'from skills\._lib\.state_vector': 'from skills._lib.core.state_vector',
    r'from skills\._lib\.defaults': 'from skills._lib.core.defaults',
    r'from skills\._lib\.lock': 'from skills._lib.core.lock',
    r'from skills\._lib\.atomic_write': 'from skills._lib.core.atomic_write',
    r'from skills\._lib\.actions': 'from skills._lib.loop.actions',
    r'from skills\._lib\.detectors': 'from skills._lib.loop.detectors',
    r'from skills\._lib\.agents': 'from skills._lib.loop.agents',
    # ... 全 16 个 loop 模块
}
```

## 回滚方案

```bash
mv skills/_lib/core/*.py skills/_lib/
mv skills/_lib/loop/*.py skills/_lib/
rmdir skills/_lib/core skills/_lib/loop
git checkout -- skills/ tests/  # 还原所有 import 路径
```
