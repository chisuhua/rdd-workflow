---
SCOPE: shared
STATUS: PROPOSED
---

## Why

Phase 2 移走了 45 个单 skill helper，`_lib/` 剩余 ~50 个文件。但这些文件内部有复杂的依赖图：
- **内核模块**: `event_log.py`（被 9 个文件引用）、`event_types.py`（8 个）、`state_vector.py`（7 个）、`defaults.py`（6 个）、`lock.py`（6 个）、`atomic_write.py`（4 个）— 形成运行时内核
- **Loop 引擎**: `actions.py`, `detectors.py`, `agents.py`, `memory.py` 等 ~20 个文件组成 v2.0 loop 引擎子系统,内部有 lazy-import 循环依赖
- **跨切共享**: `gate.py`, `iteration.py`, `state.sh` 等被多个消费者引用

本 change 将剩余 `_lib/` 文件重组为三个清晰区域：`core/`（内核）、`loop/`（引擎）、和顶层的跨切文件。

## What Changes

### 3A: 内核 → `_lib/core/`

```bash
mkdir -p skills/_lib/core
mv skills/_lib/{event_log,event_types,state_vector,defaults,lock,atomic_write}.py skills/_lib/core/
```

### 3B: Loop 引擎 → `_lib/loop/`

```bash
mkdir -p skills/_lib/loop
mv skills/_lib/{actions,detectors,agents,human_nodes,interaction_modes,memory,tribunal,sanitizer,step_pipeline,flowchart,flow_customizer,design_phase,loop_state,plugin_loader,event_queue}.py skills/_lib/loop/
```

### 3C: 保留在 `_lib/` 顶层

`gate.py`, `iteration.py`, `state.sh`, `rddf_session_hooks.sh`, `worktree.sh`, `archive.sh`, `discover-arch-artifacts.sh`, `roadmap_state.py`, `status_helpers.sh` — 被跨 skill 多消费者引用,不能下沉到子目录。

### 路径更新

- ~30 个 Python 文件：`from skills._lib.event_log` → `from skills._lib.core.event_log`
- ~20 个 Python 文件：`from skills._lib.actions` → `from skills._lib.loop.actions`
- 57 个 Python 测试文件同步更新 import 路径
- `skills/loop_engine.py` 的 imports 更新
- `tests/conftest.py` 文档字符串更新

### 环依赖处理

`gate.py` ↔ `actions.py` ↔ `detectors.py` 的 lazy-import 环需要保留 `gate.py` 在 `_lib/` 顶层（因为 `actions.py` 和 `detectors.py` 都在 `loop/` 下,两者都 lazy-import `gate._read_arch_handoff_paths`,把 `gate.py` 下沉到 `loop/` 可消除路径差异但环仍然存在,放顶层更安全）。

## Impact

- 所有 Python `from skills._lib.X import Y` 需要更新为 `from skills._lib.core.X` 或 `from skills._lib.loop.X`
- 57 个测试文件需批量 import 路径更新
- **这是四个 Phase 中风险最高的** — 一旦出错,Python 测试会大面积失败

## Dependencies

- **前置 change**: `skills-reorg-phase2-single-skill`（`_lib/` 必须先减小到 ~50 个文件）
- **后续 change**: `skills-reorg-phase4-thin`（瘦身 SKILL.md）