# Tasks: skills-reorg-phase3-core

> **前置条件**: `skills-reorg-phase2-single-skill` 完成,`_lib/` 已减至 ~50 文件

## Task 1: 创建子目录

```bash
mkdir -p skills/_lib/core
mkdir -p skills/_lib/loop
touch skills/_lib/core/__init__.py
touch skills/_lib/loop/__init__.py
```

## Task 2: 移动内核模块 → core/

```bash
mv skills/_lib/{event_log,event_types,state_vector,defaults,lock,atomic_write}.py skills/_lib/core/
```

### 2.1: 批量更新 imports（全量扫描 skills/ + tests/）

> ⚠️ 扫描范围必须包含整个 `skills/` 目录（不仅是 `_lib/`），否则 Phase 2 移出的 per-skill 脚本中的 import 会被遗漏。

用 Python 脚本批量替换——同时处理两种 import 模式：
- Pattern 1: `from skills._lib.MODULE import Y` → `from skills._lib.core.MODULE import Y`
- Pattern 2: `from skills._lib import MODULE` — 仅当 MODULE 是 core/ 或 loop/ 候选时替换

```python
import os, re, fileinput

CORE_MODULES = {
    'event_log', 'event_types', 'state_vector', 'defaults', 'lock', 'atomic_write'
}
LOOP_MODULES = {
    'actions', 'detectors', 'agents', 'human_nodes', 'interaction_modes',
    'memory', 'tribunal', 'sanitizer', 'step_pipeline', 'flowchart',
    'flow_customizer', 'design_phase', 'loop_state', 'plugin_loader', 'event_queue'
}

def build_replacement_map():
    """构建所有替换映射"""
    repl = {}
    for m in CORE_MODULES:
        repl[rf'from skills\._lib\.{m}\b'] = f'from skills._lib.core.{m}'
    for m in LOOP_MODULES:
        repl[rf'from skills\._lib\.{m}\b'] = f'from skills._lib.loop.{m}'
    return repl

REPLACEMENTS = build_replacement_map()

def replace_in_file(filepath):
    """替换文件中的 import 路径"""
    changed = False
    with fileinput.FileInput(filepath, inplace=True) as f:
        for line in f:
            new_line = line
            for pattern, replacement in REPLACEMENTS.items():
                new_line = re.sub(pattern, replacement, new_line)
            if new_line != line:
                changed = True
            print(new_line, end='')
    return changed

# 扫描 skills/ 全目录（递归进入 _lib/ 和各 skill 的 scripts/）
changed_files = []
for root, dirs, files in os.walk('skills'):
    # 跳过 __pycache__
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            if replace_in_file(path):
                changed_files.append(path)

# 扫描 tests/ 全目录（含 .py 和 .bats 文件中的内联 Python import）
for root, dirs, files in os.walk('tests'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py') or f.endswith('.bats'):
            path = os.path.join(root, f)
            if replace_in_file(path):
                changed_files.append(path)

print(f"Changed {len(changed_files)} files:")
for cf in sorted(changed_files):
    print(f"  {cf}")
```

**验证**: 
```bash
# 旧路径应全部消失
grep -rn "from skills._lib.event_log\b" skills/ tests/ && echo "FAIL: old paths remain" || echo "PASS"
grep -rn "from skills._lib.actions\b" skills/ tests/ && echo "FAIL: old paths remain" || echo "PASS"
# 新路径应出现
grep -r "from skills._lib.core.event_log" skills/ tests/ | head -3
grep -r "from skills._lib.loop.actions" skills/ tests/ | head -3
```

## Task 3: 移动 Loop 引擎 → loop/

```bash
mv skills/_lib/{actions,detectors,agents,human_nodes,interaction_modes,memory,tribunal,sanitizer,step_pipeline,flowchart,flow_customizer,design_phase,loop_state,plugin_loader,event_queue}.py skills/_lib/loop/
```

### 3.1: 再次运行批量替换脚本

Task 2.1 的脚本已包含 LOOP_MODULES，运行它即可——不需要单独脚本。

### 3.2: 验证 gate.py ↔ actions.py 环不破裂

```bash
# gate.py 在 _lib/ 顶层,被 loop/actions.py 和 loop/detectors.py lazy-import
grep -n "gate" skills/_lib/loop/actions.py skills/_lib/loop/detectors.py
# 预期: from skills._lib.gate import _read_arch_handoff_paths  (gate 保留在顶层,无需改)
```

## Task 4: 更新 tests/conftest.py

更新 conftest.py L3-L7 的 docstring（路径注释过期，提及 `skills._lib.core.xxx` / `skills._lib.loop.xxx`）。

## Task 4.5: 更新 Phase2 回归测试

`tests/integration/test_phase2_python_imports.py` 的 `SHARED_MODULES` 列表锁定 16 个模块在 `skills._lib.X` 路径可导入。Phase 3 移走其中多个后，需更新此测试：

```python
# OLD
SHARED_MODULES = [
    "skills._lib.event_log",
    "skills._lib.state_vector",
    "skills._lib.actions",
    ...
]

# NEW
CORE_MODULES = [
    "skills._lib.core.event_log",
    "skills._lib.core.event_types",
    "skills._lib.core.state_vector",
    "skills._lib.core.defaults",
    "skills._lib.core.lock",
    "skills._lib.core.atomic_write",
]
LOOP_MODULES = [
    "skills._lib.loop.actions",
    "skills._lib.loop.detectors",
    "skills._lib.loop.agents",
    "skills._lib.loop.human_nodes",
    "skills._lib.loop.interaction_modes",
    "skills._lib.loop.memory",
    "skills._lib.loop.tribunal",
    "skills._lib.loop.sanitizer",
    "skills._lib.loop.step_pipeline",
    "skills._lib.loop.flowchart",
    "skills._lib.loop.flow_customizer",
    "skills._lib.loop.design_phase",
    "skills._lib.loop.loop_state",
    "skills._lib.loop.plugin_loader",
    "skills._lib.loop.event_queue",
]
TOPLEVEL_MODULES = [
    "skills._lib.gate",
    "skills._lib.iteration",
    "skills._lib.roadmap_state",
    "skills._lib.roadmap_sprint",
    "skills._lib.config",
    ...
]
```

## Task 5: 全量验证

```bash
# 5.1: 核心 import 验证
python3 -c "
from skills._lib.core.event_log import EventLog
from skills._lib.core.state_vector import StateVector
from skills._lib.loop.actions import all_actions
from skills._lib.loop.detectors import all_detectors
from skills._lib.gate import Gate
from skills._lib.iteration import load_iteration
print('ALL IMPORTS OK')
"

# 5.2: per-skill 脚本 import 验证（Phase 2 遗漏修复验证）
python3 -c "
from skills.rddf_session.scripts.rddf_session import *
from skills.deps.scripts.deps_output import *
from skills.feature.scripts.feature_view import *
print('PER-SKILL SCRIPTS OK')
"

# 5.3: Phase 2 回归测试
python3 -m pytest tests/integration/test_phase2_python_imports.py -v

# 5.4: 全量 Python 测试
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
# 预期: all passed, 0 failures

# 5.4b: .bats 文件中的内联 Python import 验证
bats tests/integration/test_arch_discovery_contract.bats
# 预期: all passed（确保 .bats 文件中的 Python import 路径已更新）

# 5.5: 残留旧路径检查
grep -rn "from skills._lib.event_log\b" skills/ tests/ && echo "FAIL" || echo "PASS"
grep -rn "from skills._lib.actions\b" skills/ tests/ && echo "FAIL" || echo "PASS"
grep -rn "from skills._lib.state_vector\b" skills/ tests/ && echo "FAIL" || echo "PASS"
```

**若失败**: 
```bash
# 查找所有未被替换的 skills._lib.X 引用（排除顶层保留模块）
grep -rn "from skills\._lib\." skills/ tests/ | grep -vE "core\.|loop\.|iteration|gate|roadmap_state|roadmap_sprint|arch_quality_gate|change_alignment|config|event_context|session|session_base|session_manager|trigger|validate|rate_limiter|dependency_scheduler"
```

## Task 6: CI 配置更新

```yaml
# .github/workflows/test.yml L52-53
# 旧: python3 skills/_lib/validate_baseline.py
# 新: python3 skills/propose/scripts/validate_baseline.py (Phase 2 已移动)
```

## Task 7: commit

```bash
git add skills/_lib/core/ skills/_lib/loop/ skills/_lib/*.py skills/loop_engine.py skills/*/scripts/*.py tests/
git commit -m "refactor(skills): Phase 3 — reorganize _lib/ into core/ + loop/ subdirectories

- Create _lib/core/: event_log, event_types, state_vector, defaults, lock, atomic_write (runtime kernel, 6 files)
- Create _lib/loop/: actions, detectors, agents, memory, tribunal, etc. (v2.0 loop engine, 15 files)
- Keep cross-cutting at _lib/ top-level:
  Core: gate.py, iteration.py, roadmap_state.py, roadmap_sprint.py
  Shell: state.sh, worktree.sh, archive.sh, discover-arch-artifacts.sh, status_helpers.sh
  Other: arch_quality_gate.py, change_alignment.py, config.py, dependency_scheduler.py,
         event_context.py, rate_limiter.py, session.py, session_base.py, session_manager.py,
         trigger_engine.py, trigger_registry.py, triggers.py, validate_delta_targets.py, validate_report.py
- Update all Python imports across skills/ and tests/: from skills._lib.X → core.X / loop.X
- Update Phase2 regression test SHARED_MODULES → CORE_MODULES + LOOP_MODULES + TOPLEVEL_MODULES
- Per-skill scripts (rddf-session, deps, feature) import paths updated"
```