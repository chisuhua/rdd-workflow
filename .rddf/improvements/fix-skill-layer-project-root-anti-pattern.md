---
优先级: P2
来源: 2026-09-26 fix-33-handlers-project-root-anti-pattern (shipped commit ab5ded7) 实施审计
  — 该 proposal 修了 26 个 `_lib/cli/*.py` handler,但未触及 `skills/*/scripts/*.py` skill layer。
  精确扫描:5 个 skill scripts 仍用 `os.getcwd()` 作为 project_root fallback:
  - `skills/propose/scripts/propose_quality_check.py` (用 `PROJECT_ROOT` env var)
  - `skills/propose/scripts/propose_quality_hook.py` (用 `PROJECT_ROOT`)
  - `skills/report-issue/scripts/report_issue_rfc.py` (用 `RDDF_PROJECT_ROOT`)
  - `skills/sync-hub/scripts/sync_hub.py` (用 `RDDF_PROJECT_ROOT`)
  - `skills/watch-hub/scripts/watch_hub.py` (用 `RDDF_PROJECT_ROOT`)
  Skill layer 完全不用 `_lib.cli.__main__.resolve_project_root()` (0 hits grep)
阶段: v4.1 follow-up
分类: refactor
类型: refactor
主题: 跨项目 CLI 契约一致性
依赖: fix-33-handlers-project-root-anti-pattern (shipped commit ab5ded7), ADR-0033
  submodule-aware project_root resolution
---

**优先级**: P2 | **来源**: 2026-09-26 fix-33-handlers-project-root-anti-pattern 实施审计
**阶段**: v4.1 follow-up | **分类**: refactor
**类型**: refactor | **主题**: 跨项目 CLI 契约一致性
**依赖**: fix-33-handlers-project-root-anti-pattern (shipped), ADR-0033

> **症状**: `rdd-workflow` skill layer (`skills/*/scripts/*.py`) 有 5 个 script 使用 `os.environ.get("...") or os.getcwd()` anti-pattern 作为 project_root fallback,但 `_lib/cli/__main__.resolve_project_root()` 已实现 (per ADR-0033 submodule-aware git 探测) 且**无 skill 使用**。
>
> **直接证据** (2026-09-26 grep):
> ```
> $ grep -l "os\.getcwd()" skills/*/scripts/*.py
> skills/propose/scripts/propose_quality_check.py
> skills/propose/scripts/propose_quality_hook.py
> skills/report-issue/scripts/report_issue_rfc.py
> skills/sync-hub/scripts/sync_hub.py
> skills/watch-hub/scripts/watch_hub.py
>
> $ grep -rn "resolve_project_root" skills/
> (empty — 0 skills use resolve_project_root)
> ```
>
> **典型反模式**:
> ```python
> # skills/sync-hub/scripts/sync_hub.py:38
> project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
>
> # skills/propose/scripts/propose_quality_check.py:272
> project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
> ```
>
> **根因**: fix-33-handlers-project-root-anti-pattern 的 proposal 显式 scope-out 了 skill layer（"❌ 不改 `skills/*/scripts/*.py` 类似反模式"）。本提案是显式 follow-up。
>
> **影响**:
> - Skill scripts 在 git submodule / worktree 内执行时,cwd 解析错误
> - 直接调 `python3 skills/sync-hub/scripts/sync_hub.py --contract auth.yaml` (不经 `__main__.py` 注入 env var) 时,fallback 到 cwd — 在项目子目录里执行就失败
> - 与 fix-33-handlers 修复后不一致 — handler 层统一了,skill 层仍是 anti-pattern

## 架构依据

### env var 双轨制 (重要发现)

扫描发现 skill layer 用 **两种 env var**:

| Env var | 来源 | 使用场景 |
|---------|------|----------|
| `RDDF_PROJECT_ROOT` | Python `_lib/cli/__main__.py:203` `os.environ.setdefault` | 3 个 scripts: report_issue_rfc / sync_hub / watch_hub |
| `PROJECT_ROOT` (无 `RDDF_` 前缀) | Bash scripts `export PROJECT_ROOT=...` (e.g. `from_issue.sh:76`, `from_roadmap.sh:91`, `execute_step7.sh:22`, `select_worktree.sh:61`) | 2 个 scripts: propose_quality_check / propose_quality_hook |

**这是有意设计的双轨制**:
- Python CLI 调用链: `__main__.py` 注入 `RDDF_PROJECT_ROOT`
- Bash 调用链: shell script `export PROJECT_ROOT=$RDD_WORKFLOW_REPO`

修复策略**保持双轨制**(不重命名 env var),只移除 `os.getcwd()` anti-pattern:
- 5 个 scripts 各加 import `from _lib.cli.__main__ import resolve_project_root`
- 替换 `os.getcwd()` 为 `resolve_project_root()`
- 保留 env var override 行为 (env 优先)

### 与 fix-33-handlers 的关系

`fix-33-handlers-project-root-anti-pattern` (shipped commit `ab5ded7`) 修复了 `_lib/cli/*.py` 32 handler 的反模式(精确 26 file modified),但 proposal 的 Out of Scope 明确写道: "❌ 不改 `skills/*/scripts/*.py` 类似反模式"。本提案是显式 follow-up。

skill layer 数量更小(5 vs 26),scope 更可控,可走 rdd-quick 旁路 (≤ 2 files + ≤ 3 tasks)。但提议保留 rdd-builder P0-P3 流程以保持一致性。

## 范围

### In Scope

- 5 个 skill scripts 把 `os.getcwd()` 改为 `resolve_project_root()`:
  - `skills/propose/scripts/propose_quality_check.py` (env var: `PROJECT_ROOT`)
  - `skills/propose/scripts/propose_quality_hook.py` (env var: `PROJECT_ROOT`)
  - `skills/report-issue/scripts/report_issue_rfc.py` (env var: `RDDF_PROJECT_ROOT`)
  - `skills/sync-hub/scripts/sync_hub.py` (env var: `RDDF_PROJECT_ROOT`)
  - `skills/watch-hub/scripts/watch_hub.py` (env var: `RDDF_PROJECT_ROOT`)
- 每个 script 加 `from _lib.cli.__main__ import resolve_project_root  # noqa: E402`
- 新单元测试 `tests/unit/test_skill_layer_project_root_resolution.py`: 验证 5 个 script 各能自解析 + 保留 env var 双轨制
- 保留 `PROJECT_ROOT` 和 `RDDF_PROJECT_ROOT` 两个 env var 不重命名(双轨制向后兼容)

### Out of Scope

- ❌ 不改 bash scripts (e.g. `skills/add-improve/scripts/from_issue.sh:76` `export PROJECT_ROOT`) — bash 已用 `_resolve_project_root` helper (per `skills/_lib/orchestrator_entry.sh:33`)
- ❌ 不重命名 env var (`PROJECT_ROOT` ↔ `RDDF_PROJECT_ROOT`) — 双轨制有意设计
- ❌ 不改 `_lib/cli/__main__.resolve_project_root()` 实现本身(已正确 per ADR-0033)
- ❌ 不改 4 个已正确用 `from _lib.X` import 的 skill scripts (propose_change / roadmap_incremental_update / write_arch_handoff / append_history) — 它们已经在用 project_root 参数化模式

## Why

统一 skill layer 的 project_root 解析逻辑,消除双轨制下的 anti-pattern,让 skill scripts 在 submodule / worktree / 项目子目录 context 下能正确解析。这是 fix-33-handlers 在 `_lib/cli/*.py` 层修复的 skill-layer 镜像。

## What Changes

### 5 个 skill scripts 替换 anti-pattern

**Before** (示例 `skills/sync-hub/scripts/sync_hub.py:38`):
```python
project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
```

**After**:
```python
from _lib.cli.__main__ import resolve_project_root  # noqa: E402,F401

# ... in main:
project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()
```

注: 保留 `or` 而非 `,` (与 fix-33-handlers 一致 — 避免 truthy 检查误捕),保留 env var 优先 fallback 到 git 探测。

### 新单元测试 `tests/unit/test_skill_layer_project_root_resolution.py`

覆盖:
- `[ ] AC-SL-1`: 5 个 script 各能在 `RDDF_PROJECT_ROOT`/`PROJECT_ROOT` 未设时自解析到 git toplevel (subprocess test)
- `[ ] AC-SL-2`: `RDDF_PROJECT_ROOT` env override 优先
- `[ ] AC-SL-3`: `PROJECT_ROOT` env override 优先 (for propose scripts)
- `[ ] AC-SL-4`: 双轨制不互相破坏 (`RDDF_PROJECT_ROOT` 不应被 `PROJECT_ROOT` 拦截)
- `[ ] AC-SL-5`: 0 anti-pattern occurrences 剩余 (grep 验证)
- `[ ] AC-SL-6`: 主仓 `./test.sh --quick` 仍 3068+ passed (回归门)

## Acceptance

- [ ] **AC-SL-1**: 5 个 skill scripts 全部改用 `resolve_project_root()` (grep 验证 0 个 `or os.getcwd()` occurrences 剩余)
- [ ] **AC-SL-2**: 新单元测试 `test_skill_layer_project_root_resolution.py` 覆盖 6+ cases 全部通过
- [ ] **AC-SL-3**: 主仓 `./test.sh --quick` 仍 3068+ passed (回归门)
- [ ] **AC-SL-4**: 5 个 skill scripts 在非 git dir fallback `os.getcwd()` (经 `resolve_project_root()` 已实现)
- [ ] **AC-SL-5**: `RDDF_PROJECT_ROOT` env override 行为保留 (向后兼容)
- [ ] **AC-SL-6**: `PROJECT_ROOT` env override 行为保留 (向后兼容, propose scripts 双轨制)
- [ ] **AC-SL-7**: 双轨制不互相破坏 (env var 各自优先级保留)

## Capabilities

### MUST

- **`C-SL-1`**: 5 个 skill scripts 把 `os.environ.get(...) or os.getcwd()` 改为 `os.environ.get(...) or resolve_project_root()`
- **`C-SL-2`**: 新单元测试覆盖正常 + edge case

### MUST NOT

- ❌ **MN-SL-1**: 不改 env var 名 (`PROJECT_ROOT` ↔ `RDDF_PROJECT_ROOT`) (双轨制向后兼容)
- ❌ **MN-SL-2**: 不改 bash scripts `export PROJECT_ROOT=...` (已正确使用 `_resolve_project_root` helper)
- ❌ **MN-SL-3**: 不改 `_lib/cli/__main__.resolve_project_root()` 实现本身
- ❌ **MN-SL-4**: 不引入新依赖

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| `skills/*/scripts/*.py` 重复实现 | 5 files × 1 处 = 5 occurrences | 0 occurrences |
| Skill scripts 在 submodule 行为 | 错误 (cwd ≠ submodule root) | 正确 (per ADR-0033) |
| Skill scripts 在 worktree 行为 | 错误 (cwd ≠ main repo root) | 正确 |
| 双轨制向后兼容 | ✓ | ✓ (env var 名不变) |
| 主仓代码改动 | — | 5 files 各 ~1 行 + 新 test file (~80 lines) |
| 测试覆盖 | 0 skill layer project_root 测试 | +6 test cases |
| Bash scripts | 0 改动 | 0 改动 (已正确) |

**Risk Assessment**:
- **Low**: 机械化 sed 替换,行为等价 (env override 保留 + bash 双轨制不变)
- **High**: 无 — 不改公开 API, 不改业务逻辑, 不改 bash scripts

**Future follow-up improvement suggestions**:
- `add-skill-layer-resolve-project-root-helper` (在 `skills/_lib/` 下放 Python wrapper `_resolve_project_root_python()`,与 bash `_resolve_project_root()` 对齐)