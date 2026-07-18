# Design: skills-reorg-phase3-core

## Decision 1: 内核分组依据

选择 `core/` 下放 6 个模块的依据：
- `event_log.py` (9 importers), `event_types.py` (8), `state_vector.py` (7) — 三者互相关联形成运行时内核,必须同行
- `defaults.py` (6), `lock.py` (6), `atomic_write.py` (4) — 零内部依赖,纯 leaf 工具模块

## Decision 2: Loop 引擎分组依据

`loop/` 收集 v2.0 loop 引擎子系统的全部模块。选择依据：这些模块仅在 `loop_engine.py` 的 import 树中被引用，不被任何 skill `SKILL.md` 直接引用。

## Decision 3: gate.py 保留在顶层

`gate.py` 是唯一被 `actions.py` (→ loop/) 和 `detectors.py` (→ loop/) 同时 lazy-import 的模块。放入 `loop/` 可行（import 路径不变），但保留在顶层作为"跨切门控"语义更清晰。

```python
# actions.py (in loop/)
from skills._lib.gate import _read_arch_handoff_paths  # 顶层 gate，不需要改

# gate.py (top-level) imports 6 modules, 5 in core/:
from skills._lib.core.event_log import EventLog
from skills._lib.core.state_vector import StateVector
# etc.
```

## Decision 4: 现有子目录保留

`schedulers/`、`schemas/`、`plugins/` 已有子目录结构，**不移动**。`schedulers/` 中的文件引用 `event_queue`（→ loop/），`os.walk('skills/_lib')` 递归覆盖，会被正确更新。

## Decision 5: `__init__.py` 更新

`skills/_lib/core/__init__.py` 和 `skills/_lib/loop/__init__.py` 保持空（匹配现有 `_lib/__init__.py` 风格）。所有 import 使用绝对路径 `from skills._lib.core.X`。

## Decision 6: import 路径批量替换

使用 Python 脚本批量更新，而非手工 edit。复用 `tools/phase2_path_migrator.py` 的双模式匹配逻辑（`from skills._lib.X import Y` + `from skills._lib import X`），覆盖范围包括 `skills/`、`tests/` 全目录。

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
    r'from skills\._lib\.human_nodes': 'from skills._lib.loop.human_nodes',
    r'from skills\._lib\.interaction_modes': 'from skills._lib.loop.interaction_modes',
    r'from skills\._lib\.memory': 'from skills._lib.loop.memory',
    r'from skills\._lib\.tribunal': 'from skills._lib.loop.tribunal',
    r'from skills\._lib\.sanitizer': 'from skills._lib.loop.sanitizer',
    r'from skills\._lib\.step_pipeline': 'from skills._lib.loop.step_pipeline',
    r'from skills\._lib\.flowchart': 'from skills._lib.loop.flowchart',
    r'from skills\._lib\.flow_customizer': 'from skills._lib.loop.flow_customizer',
    r'from skills\._lib\.design_phase': 'from skills._lib.loop.design_phase',
    r'from skills\._lib\.loop_state': 'from skills._lib.loop.loop_state',
    r'from skills\._lib\.plugin_loader': 'from skills._lib.loop.plugin_loader',
    r'from skills\._lib\.event_queue': 'from skills._lib.loop.event_queue',
}
```

## Decision 7: 顶层保留模块（非 core/loop）

以下 14 个 .py 文件不归入 `core/` 或 `loop/`，保留在 `_lib/` 顶层（`roadmap_sprint.py` 已在 3C 中列为跨切核心模块）：

| 模块 | 类别 | 保留原因 |
|------|------|---------|
| `arch_quality_gate.py` | 门控 | gate.py 交叉引用，多消费者 |
| `change_alignment.py` | 对齐 | 跨切变更对齐逻辑 |
| `config.py` | 配置 | 多子系统配置解析器（loop_engine.py 和 skill 脚本均有引用） |
| `dependency_scheduler.py` | 调度 | 跨子系统调度 |
| `event_context.py` | 上下文 | 多模块事件上下文 |
| `rate_limiter.py` | 工具 | 跨切速率限制 |
| `session.py` | 会话 | 会话管理（多消费者） |
| `session_base.py` | 会话 | 会话基类（被 session.py/session_manager.py 引用） |
| `session_manager.py` | 会话 | 跨子系统会话协调 |
| `trigger_engine.py` | 触发器 | 触发器引擎 |
| `trigger_registry.py` | 触发器 | 触发器注册表 |
| `triggers.py` | 触发器 | 触发器定义 |
| `validate_delta_targets.py` | 验证 | delta 验证工具 |
| `validate_report.py` | 验证 | 跨切验证报告 |

这些模块引用 core/ 候选模块时（如 `config.py` → `defaults`，`session.py` → `event_log`），替换脚本的 `os.walk` 会正向遍历并正确更新它们的 import 路径。

### 替换脚本覆盖范围

替换脚本必须覆盖以下路径，且处理 `.py` **和 `.bats`** 文件：

```
os.walk('skills')      # 覆盖 skills/_lib/ + skills/<skill>/scripts/
os.walk('tests')       # 覆盖 tests/ 下所有 .py 和 .bats 文件
```

这会确保：
1. Phase 2 移出的 per-skill 脚本（`skills/rddf-session/scripts/rddf_session.py`、`skills/deps/scripts/deps_output.py`、`skills/feature/scripts/feature_view.py`）中的 `atomic_write`/`lock` 引用也被正确更新
2. `tests/integration/test_arch_discovery_contract.bats` 中的内联 Python import（`from skills._lib.event_log`、`from skills._lib.actions`）也被正确更新

## 回滚方案

> ⚠️ 注意：`git checkout` 只恢复文件内容，不撤销 `mv` 操作。必须用 `git clean` 删除残留文件。

```bash
# 第一步：恢复 HEAD 版本的所有文件内容
git checkout HEAD -- skills/ tests/

# 第二步：删除 mv 产生的残留目录/文件（core/ 和 loop/ 子目录中不再属于 git 的文件）
git clean -fd skills/_lib/core/ skills/_lib/loop/

# 第三步：验证
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```
