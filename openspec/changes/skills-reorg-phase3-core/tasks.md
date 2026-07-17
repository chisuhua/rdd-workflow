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

### 2.1: 批量更新 imports (~30 文件)

用 Python 脚本批量替换：
```python
import os, re, fileinput

CORE_MAP = {
    'event_log': 'core.event_log',
    'event_types': 'core.event_types',
    'state_vector': 'core.state_vector',
    'defaults': 'core.defaults',
    'lock': 'core.lock',
    'atomic_write': 'core.atomic_write',
}

def replace_in_file(filepath):
    with fileinput.FileInput(filepath, inplace=True) as f:
        for line in f:
            for old, new in CORE_MAP.items():
                line = re.sub(
                    rf'from skills\._lib\.{old}\b',
                    f'from skills._lib.{new}',
                    line
                )
            print(line, end='')

for root, dirs, files in os.walk('skills/_lib'):
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            replace_in_file(os.path.join(root, f))

for root, dirs, files in os.walk('tests'):
    for f in files:
        if f.endswith('.py'):
            replace_in_file(os.path.join(root, f))

# loop_engine.py
replace_in_file('skills/loop_engine.py')
```

**验证**: `grep -r "from skills._lib.event_log\b" skills/ tests/` 应为空（所有旧引用已替换为 `core.event_log`）

## Task 3: 移动 Loop 引擎 → loop/

```bash
mv skills/_lib/{actions,detectors,agents,human_nodes,interaction_modes,memory,tribunal,sanitizer,step_pipeline,flowchart,flow_customizer,design_phase,loop_state,plugin_loader,event_queue}.py skills/_lib/loop/
```

### 3.1: 批量更新 imports (~20 文件)

同 Task 2.1 的脚本，替换目标为 loop 模块。

```python
LOOP_MAP = {
    'actions': 'loop.actions',
    'detectors': 'loop.detectors',
    'agents': 'loop.agents',
    'human_nodes': 'loop.human_nodes',
    'interaction_modes': 'loop.interaction_modes',
    'memory': 'loop.memory',
    'tribunal': 'loop.tribunal',
    'sanitizer': 'loop.sanitizer',
    'step_pipeline': 'loop.step_pipeline',
    'flowchart': 'loop.flowchart',
    'flow_customizer': 'loop.flow_customizer',
    'design_phase': 'loop.design_phase',
    'loop_state': 'loop.loop_state',
    'plugin_loader': 'loop.plugin_loader',
    'event_queue': 'loop.event_queue',
}
```

### 3.2: 验证 gate.py ↔ actions.py 环不破裂

```bash
# gate.py 在 _lib/ 顶层,被 loop/actions.py 和 loop/detectors.py lazy-import
grep -n "gate" skills/_lib/loop/actions.py skills/_lib/loop/detectors.py
```

## Task 4: 更新 tests/conftest.py

更新 conftest.py L3-L7 的 docstring（路径注释过期）。

## Task 5: 全量验证

```bash
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
# 预期: ~143 tests passed (91 unit + ~52 integration)
```

**若失败**: 检查是否有漏掉的 import（`grep "from skills._lib\." skills/_lib/*.py | grep -v "core\|loop\|iteration\|gate\|state\|roadmap\|..."`  找未被替换的残留引用）。

## Task 6: CI 配置更新

```yaml
# .github/workflows/test.yml L52-53
# 旧: python3 skills/_lib/validate_baseline.py
# 新: python3 skills/propose/scripts/validate_baseline.py (Phase 2 已移动)
```

## Task 7: commit

```bash
git add skills/_lib/core/ skills/_lib/loop/ skills/_lib/*.py skills/loop_engine.py tests/
git commit -m "refactor(skills): Phase 3 — reorganize _lib/ into core/ + loop/ subdirectories

- Create _lib/core/: event_log, event_types, state_vector, defaults, lock, atomic_write (runtime kernel, 6 files)
- Create _lib/loop/: actions, detectors, agents, memory, tribunal, etc. (v2.0 loop engine, 15 files)
- Keep cross-cutting modules at _lib/ top-level: gate.py, iteration.py, state.sh, rddf_session_hooks.sh, worktree.sh, archive.sh, discover-arch-artifacts.sh, roadmap_state.py, status_helpers.sh
- Update all Python imports across ~50 files: from skills._lib.X → from skills._lib.core.X or from skills._lib.loop.X
- Update 57 test files with new import paths
- gate.py stays at top-level to avoid breaking actions↔gate↔detectors lazy-import cycle"
```