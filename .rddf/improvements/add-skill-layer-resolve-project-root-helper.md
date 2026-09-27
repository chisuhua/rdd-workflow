---
优先级: P2
来源: 2026-09-26 fix-skill-layer-project-root-anti-pattern (shipped commit c217cde) 实施审计
  — 该 proposal 修了 5 个 skill scripts 的 anti-pattern,但每个 script 都直接 `from _lib.cli.__main__ import
  resolve_project_root`(绕过了 skills/_lib/),破坏了 skill layer 自包含性约定 (其他 skill 模块如
  `skills/rddf-session/scripts/` 不依赖 `_lib/cli/`,因为 skill layer 应仅依赖自己的 `_lib/` 或
  共享 `_lib/`)。Bash 已有 helper (`skills/_lib/orchestrator_entry.sh:33` `_resolve_project_root`),
  但 Python 端无对应 helper,造成 skill scripts 直接 import dispatcher 内部实现 — leaky abstraction
阶段: v4.1 follow-up
分类: refactor
类型: refactor
主题: 跨项目 CLI 契约一致性
依赖: fix-skill-layer-project-root-anti-pattern (shipped commit c217cde),
  skills/_lib/orchestrator_entry.sh:_resolve_project_root (bash reference impl),
  _lib/cli/__main__.py:resolve_project_root (Python reference impl per ADR-0033)
---

**优先级**: P2 | **来源**: 2026-09-26 fix-skill-layer-project-root-anti-pattern 实施审计
**阶段**: v4.1 follow-up | **分类**: refactor
**类型**: refactor | **主题**: 跨项目 CLI 契约一致性
**依赖**: fix-skill-layer-project-root-anti-pattern (shipped), bash _resolve_project_root (existing)

> **症状**: fix-skill-layer-project-root-anti-pattern 实施后,5 个 skill scripts 都 `from _lib.cli.__main__ import resolve_project_root`。但 `_lib/cli/__main__` 是 CLI dispatcher 的实现细节 — skill layer 不应直接 import dispatcher 内部。skill layer 应仅依赖自己的 `_lib/` (per skill 自包含约定,见 `skills/_lib/iteration/__init__.py:3-10` 注释)。
>
> **直接证据** (2026-09-26 grep):
> ```
> $ grep -rn "from _lib.cli" skills/*/scripts/*.py
> skills/propose/scripts/propose_quality_check.py:31:from _lib.cli.__main__ import resolve_project_root
> skills/propose/scripts/propose_quality_hook.py:21:from _lib.cli.__main__ import resolve_project_root
> skills/report-issue/scripts/report_issue_rfc.py:18:from _lib.cli.__main__ import resolve_project_root
> skills/sync-hub/scripts/sync_hub.py:24:from _lib.cli.__main__ import resolve_project_root
> skills/watch-hub/scripts/watch_hub.py:24:from _lib.cli.__main__ import resolve_project_root
> ```
> 5/5 modified scripts leaky import from dispatcher internals.
>
> **根因**:
> 1. Python 端无 skill-layer-friendly wrapper for project_root resolution
> 2. skill layer 唯一现有的 `_lib/` helper 是 Python-agnostic (shim layer re-exports)
> 3. skill scripts 直接 reach 到 `_lib/cli/__main__.resolve_project_root` 是阻抗不匹配的副产物
>
> **对比 — bash 端已正确** (`skills/_lib/orchestrator_entry.sh:33`):
> ```bash
> _resolve_project_root() {
>     if [ -n "${RDDF_PROJECT_ROOT:-}" ]; then
>         echo "$RDDF_PROJECT_ROOT"
>         return
>     fi
>     local git_root
>     git_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" && {
>         echo "$git_root"
>         return
>     }
>     echo "$PWD"
> }
> ```
> Bash 端已有 `_resolve_project_root` helper,symmetrical 模式:`env var override → git probe → cwd fallback`
> Python 端缺对应 wrapper,导致 5 个 skill scripts 直接 import dispatcher 实现

## 架构依据

### skill layer 边界

Per `skills/_lib/iteration/__init__.py:3-10` (verbatim):
```python
# Backward-compat shim re-exports from _lib.iteration for existing code.
# `from _lib.iteration import X` — without this, bash subprocess invocations
# would not find `skills._lib.iteration.X`.
```

skill layer 自包含约定:
- `skills/_lib/*` 是 skill 的 helper layer (shim + subskill 共享 utilities)
- `_lib/*` 是 dispatcher 的实现 layer (CLI, sync-hub, etc.)
- skill scripts **应**通过 `from _lib.X` import 共享 utilities,**不**直接 import dispatcher internals

但当前 5 个 skill scripts 都直接 import `_lib.cli.__main__` — leaky abstraction.本提案修复这个 layering violation.

### 双层 helper 设计

| Layer | Helper | Status |
|-------|--------|--------|
| Bash | `skills/_lib/orchestrator_entry.sh::_resolve_project_root` | ✅ 已存在 (200efdd 前的 wave) |
| Python skill layer | `skills/_lib/_python_resolve_project_root` | ❌ 缺失 — 本提案补 |
| Python CLI layer | `_lib/cli/__main__.py::resolve_project_root` (per ADR-0033) | ✅ 已存在,definer of behavior |
| Python shim | `skills/_lib/cli/__init__.py::__getattr__` (per fix-33-handlers PEP 562) | ✅ 已存在,re-exports |

**修复策略**: 在 `skills/_lib/` 加 Python wrapper `skills/_lib/_python_resolve_project_root.py`,封装行为,skill scripts 通过 `from skills._lib._python_resolve_project_root import resolve_project_root` 引用。这保持:
- `skills/_lib/` 的自包含性 (skill-only utilities 在 skill layer)
- `_lib/cli/__main__.resolve_project_root` 作为 single source of truth (no logic duplication)
- 未来 skill scripts 引用项目根有 clean import path (不穿透到 dispatcher)

## 范围

### In Scope

- 创建 `skills/_lib/_python_resolve_project_root.py` wrapper module:
  - 函数 `resolve_project_root() -> str` (单一公开函数)
  - 实现:1) `os.environ.get("RDDF_PROJECT_ROOT") or`, 2) `_lib.cli.__main__.resolve_project_root()`, 3) `os.getcwd()`
  - **import time safety**: wrapper module import 不触发 `_lib.cli.__main__` 加载循环
  - docstring 引用 ADR-0033 + bash `_resolve_project_root` 对齐
- 5 个 skill scripts 改 import:
  ```python
  # Before:
  from _lib.cli.__main__ import resolve_project_root  # noqa: E402,F401  (per fix-skill-layer)
  # After:
  from skills._lib._python_resolve_project_root import resolve_project_root  # noqa: E402,F401  (per add-skill-layer-resolve-project-root-helper)
  ```
- 新单元测试 `tests/unit/test_skills_lib_python_resolve_project_root.py`:
  - wrapper module importable + callable
  - env var override 行为 (RDDF_PROJECT_ROOT)
  - git probe 行为 (in repo → returns git toplevel)
  - cwd fallback (非 git dir → returns cwd)
  - 与 `_lib.cli.__main__.resolve_project_root()` 行为一致 (parity test)
  - **不**触发 `_lib.cli.__main__` 加载循环 (import test)
- 更新 `skills/_lib/` 添加 docstring/README 说明此 wrapper 的 purpose

### Out of Scope

- ❌ 不改 `_lib/cli/__main__.resolve_project_root()` 实现本身 (per ADR-0033 已正确, single source of truth)
- ❌ 不改 bash `_resolve_project_root` (per `skills/_lib/orchestrator_entry.sh:33`)
- ❌ 不引入新依赖
- ❌ 不重命名函数 (与 bash 对齐用 `resolve_project_root`)
- ❌ 不把 `_lib/cli/__init__.py` 的 PEP 562 `__getattr__` 移到 skill layer (那是 dispatcher concern)

## Why

让 skill layer 有自己的 Python `resolve_project_root` wrapper,与 bash `_resolve_project_root` 对齐。这消除 skill scripts 直接 import `_lib.cli.__main__` 的 leaky abstraction,恢复 skill layer 自包含约定。

## What Changes

### 新模块 `skills/_lib/_python_resolve_project_root.py`

```python
"""Skill-layer Python wrapper for project_root resolution.

Mirrors bash helper at skills/_lib/orchestrator_entry.sh:_resolve_project_root
(per add-skill-layer-resolve-project-root-helper). Delegates to the
canonical implementation at _lib.cli.__main__.resolve_project_root
(per ADR-0033, submodule-aware git probe) — no logic duplication.

Resolution order:
  1. RDDF_PROJECT_ROOT env var (override for tests + caller injection)
  2. _lib.cli.__main__.resolve_project_root() (submodule-aware git probe)
  3. os.getcwd() (fallback when not in git repo)
"""
from __future__ import annotations

import os


def resolve_project_root() -> str:
    """Return the project root for skill scripts.

    See module docstring for resolution order. Symmetric with bash
    `_resolve_project_root` (skills/_lib/orchestrator_entry.sh:33).
    """
    return (
        os.environ.get("RDDF_PROJECT_ROOT")
        or _delegate_to_cli_main_resolver()
        or os.getcwd()
    )


def _delegate_to_cli_main_resolver() -> str:
    """Lazy-import the dispatcher resolver to avoid import-time cycles.

    Importing _lib.cli.__main__ at module load would trigger __main__'s
    own `from skills._lib.cli import list_commands, route` (per
    fix-33-handlers PEP 562 __getattr__); deferring to call-time avoids
    any circular risk.
    """
    from _lib.cli.__main__ import resolve_project_root as _impl
    return _impl()
```

### 5 个 skill scripts 改 import

`grep -l "from _lib.cli.__main__ import resolve_project_root" skills/*/scripts/*.py` 命中 5 个文件,各改 1 行。

### 新单元测试 `tests/unit/test_skills_lib_python_resolve_project_root.py`

覆盖:
- `[ ] AC-SLP-1`: wrapper module importable
- `[ ] AC-SLP-2`: `resolve_project_root()` 返回非空字符串
- `[ ] AC-SLP-3`: `RDDF_PROJECT_ROOT` env var 优先
- `[ ] AC-SLP-4`: 与 `_lib.cli.__main__.resolve_project_root()` 行为一致 (parity)
- `[ ] AC-SLP-5`: import 时不触发 `_lib.cli.__main__` 加载 (subprocess test)
- `[ ] AC-SLP-6`: 5 个 skill scripts 改用新 wrapper 后仍 PASS 现有 `test_skill_layer_project_root_resolution.py`

## Acceptance

- [ ] **AC-SLP-1**: `skills/_lib/_python_resolve_project_root.py` 创建 + 含 `resolve_project_root()` 函数
- [ ] **AC-SLP-2**: 5 个 skill scripts 改 import 路径(从 `_lib.cli.__main__` 到 `skills._lib._python_resolve_project_root`)
- [ ] **AC-SLP-3**: 0 skill scripts 直接 import `_lib.cli.__main__` (grep 验证)
- [ ] **AC-SLP-4**: 新测试 `test_skills_lib_python_resolve_project_root.py` 覆盖 6+ cases 全部通过
- [ ] **AC-SLP-5**: `./test.sh --quick` 仍 3081+ passed (回归门)
- [ ] **AC-SLP-6**: 现有 `test_skill_layer_project_root_resolution.py` 13/13 仍 PASS (行为 parity)
- [ ] **AC-SLP-7**: bash `_resolve_project_root` 与 Python `resolve_project_root` 行为对齐 (cross-language parity)

## Capabilities

### MUST

- **`C-SLP-1`**: `skills/_lib/_python_resolve_project_root.py::resolve_project_root()` 函数存在并 callable
- **`C-SLP-2`**: 5 个 skill scripts 改 import 路径
- **`C-SLP-3`**: 行为与 `_lib.cli.__main__.resolve_project_root()` 一致 (parity)

### MUST NOT

- ❌ **MN-SLP-1**: 不重命名函数 (与 bash `_resolve_project_root` 对齐, Python 简化为 `resolve_project_root`)
- ❌ **MN-SLP-2**: 不引入新依赖
- ❌ **MN-SLP-3**: 不修改 `_lib/cli/__main__.resolve_project_root()` 行为
- ❌ **MN-SLP-4**: 不修改 bash `_resolve_project_root` (`skills/_lib/orchestrator_entry.sh:33`)
- ❌ **MN-SLP-5**: 不引入新的 skill-to-_lib leakage (新 wrapper 仅在 `skills/_lib/` 内)

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| Skill scripts 直接 import `_lib.cli.__main__` | 5 files | 0 files |
| Skill layer 自包含性 | 违反 (skill → dispatcher internals) | 恢复 (skill → skills/_lib/) |
| 双语言 helper 对称 | Bash ✓, Python ❌ | Bash ✓, Python ✓ |
| 测试覆盖 | 13 (test_skill_layer_project_root_resolution) | +6 (test_skills_lib_python_resolve_project_root) |
| 主仓代码改动 | — | 1 新 module (~30 lines) + 5 import 路径改 + 1 新 test file |
| 测试覆盖 (回归门) | 3081 passed | ≥ 3081 passed |

**Risk Assessment**:
- **Low**: 行为 parity 与现有实现一致 (env → git → cwd),只改 import path
- **Medium**: 循环 import 风险 (已有 PEP 562 precedent in fix-33-handlers; 提案用 lazy import 函数规避)
- **High**: 无 — 不改公开 API, 不改业务逻辑

**Future follow-up improvement suggestions**:
- `consolidate-resolve-project-root-helpers` (跨语言重构: bash + Python 都通过单一 contract 文件定义)
- `add-skills-lib-api-doc` (正式化 `skills/_lib/` 为 skill 共享 utilities 入口)