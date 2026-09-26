---
优先级: P2
来源: 2026-09-25 fix-cmd-help-handling 实施时识别 — 32 个 `_lib/cli/*.py` handler 文件
  重复使用 `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` 反模式 (共 ~36 处),而
  `_lib/cli/__main__.py::resolve_project_root()` 已存在 (ADR-0033 submodule-aware git 探测)
  但**无 handler 使用**。架构层重复实现 → 测试脆弱性 + cross-context bug 风险
阶段: v4.1 follow-up
分类: refactor
类型: refactor
主题: 跨项目 CLI 契约一致性
依赖: fix-cmd-help-handling (已 ship 2026-09-25, commit 200efdd), `rddf-workflow-e2e` test
  rddf_cli_all_subcommands.bats setup() cd to RDD_WORKFLOW_REPO (已 ship PR #1 commit efe89dd)
---

**优先级**: P2 | **来源**: 2026-09-25 fix-cmd-help-handling 实施审计
**阶段**: v4.1 follow-up | **分类**: refactor
**类型**: refactor | **主题**: 跨项目 CLI 契约一致性
**依赖**: fix-cmd-help-handling (shipped), rdd-workflow-e2e PR #1 (shipped)
**主题**: 跨项目 CLI 契约一致性

> **症状**: 32 个 `_lib/cli/*.py` handler 文件重复使用 `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` 反模式（~36 处 occurrences）。但 `_lib/cli/__main__.py::resolve_project_root()` 已实现 submodule-aware git 探测（per ADR-0033），**没有任何 handler 使用它**。
>
> **直接证据** (2026-09-25 rdd-workflow-e2e PR #1 audit):
> ```
> $ grep -l "RDDF_PROJECT_ROOT.*or.*os.getcwd" _lib/cli/*.py | wc -l
> 32
>
> $ grep -rn "from.*resolve_project_root\|import resolve_project_root" _lib/cli/*.py
> (empty — 0 handlers import it)
>
> $ wc -l <(grep "RDDF_PROJECT_ROOT.*or.*os.getcwd\|os.getcwd.*RDDF_PROJECT_ROOT" _lib/cli/*.py)
> 36 (approximate occurrences)
> ```
>
> **根因**:
> 1. **`__main__.py` 在 line 203 已 `os.environ.setdefault("RDDF_PROJECT_ROOT", resolve_project_root())`**,所以 `__main__.py` 调用链下的 handlers 实际**能**通过 `os.environ.get("RDDF_PROJECT_ROOT")` 拿到正确值
> 2. 但**直接调 `python3 -m _lib.cli <sub>` 或第三方脚本不经 `__main__.py`** 时,handler 看到 `RDDF_PROJECT_ROOT` 未设 → fallback `os.getcwd()` → 失败
> 3. `__main__.resolve_project_root()` 是正确实现但**无人使用**——dead code 状态
>
> **典型反模式示例**:
> ```python
> # _lib/cli/version_cmd.py:30
> project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
>
> # _lib/cli/contract_check_cmd.py:45
> os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
>
> # _lib/cli/sync_hub_cmd.py:30
> os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
>
> # _lib/cli/sessions_cmd.py:106, 255  (multi-occurrence)
> project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
> ```

## 架构依据

### 为什么是 architectural smell（不是 cosmetic）

1. **重复逻辑**: 同一逻辑 (`get project root from env or cwd`) 在 32 个文件复制 36 次。任何修改需要 32 文件协同
2. **不一致实现**: 33 个 handler 各自读 env,无人用 `__main__.resolve_project_root()` (submodule-aware git 探测)。这意味着:
   - handler 在 git submodule 内执行时,cwd 解析错误（submodule 内 cwd ≠ superproject root）
   - handler 在 worktree 内执行时,cwd 解析错误（worktree 的 cwd 不等于主 repo root）
3. **e2e test 已暴露**: rdd-workflow-e2e PR #1 (commit `efe89dd`) 加 `setup() cd "$RDD_WORKFLOW_REPO"` 修复 test 6 cwd bug——本质是用 e2e test 的 setup 替 handler 修项目根路径,**而非**让 handler 自己正确解析
4. **Bypass logic**: `__main__.py` 已在 line 203 设了 `RDDF_PROJECT_ROOT`,这暗示**设计者意图 handler 信任 env var**——但实际 handler 不应该依赖 caller 设 env,应自解析
5. **已 ship 的 fix-cmd-help-handling 是 symptom fix**,**根因未消除**: 修 dispatcher 层 `--help` 解决了 e2e test 6 失败,但 handler 业务逻辑仍用 anti-pattern

### 当前项目生态

| 项目 | 用 `resolve_project_root()`? | 备注 |
|------|----------------------------|------|
| `_lib/cli/__main__.py` | ✅ 是 (定义者) | submodule-aware git 探测 |
| 33 `_lib/cli/*.py` handlers | ❌ 否 (32 用 anti-pattern) | 重复实现 |
| `_lib/cli/__init__.py` (route) | n/a | 不解析 project_root |
| `rdd-workflow-e2e/tests/` | 通过 setup() cd | workaround,不修 handler |

## 范围

### In Scope

- `_lib/cli/__init__.py` 加 `from .__main__ import resolve_project_root` 并 re-export (`__all__` 中添加)
- 32 个 `_lib/cli/*.py` handler 把 `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` 改为 `resolve_project_root()`
- 保留 `RDDF_PROJECT_ROOT` env var 作为**override**（向后兼容 — `__main__.py` 注入的 setdefault 不变）:
  ```python
  # 新统一 pattern:
  project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()
  ```
- 加单元测试 `tests/unit/test_cli_project_root_resolution.py`: 验证
  - `RDDF_PROJECT_ROOT` 未设时 → 用 git 探测
  - `RDDF_PROJECT_ROOT` 已设时 → override
  - 在 git submodule 内 → 解析 submodule own root (per ADR-0033)
  - 在非 git dir → fallback `os.getcwd()`
- 更新 `_lib/cli/__main__.py:203` `setdefault` → 保留 (因为这是测试友好的 env-injection)
- 更新 rdd-workflow-e2e `tests/integration/test_rddf_cli_all_subcommands.bats` 移除 `setup() cd "$RDD_WORKFLOW_REPO"` workaround (commit `efe89dd`),因为 handler 现在自解析

### Out of Scope

- ❌ 不改 `resolve_project_root()` 实现本身（已正确，per ADR-0033）
- ❌ 不改 `_lib/cli/__main__.py:203` 的 `os.environ.setdefault("RDDF_PROJECT_ROOT", project_root)` 行为（保留向后兼容）
- ❌ 不改 skill 层 (`skills/`) 的 rddf_session.py 类似反模式（那是另一个 scope,建议作为 follow-up `fix-skill-layer-project-root-anti-pattern`）
- ❌ 不改 `_lib/cli/__init__.py::route()` 入口（已在 fix-cmd-help-handling 修了 help short-circuit）
- ❌ 不引入新依赖

## Why

统一 32 个 handler 的 project_root 解析逻辑，消除重复实现，让 handler 在 submodule / worktree / 非 git dir 等所有 context 下都能正确解析 project_root。这是 fix-cmd-help-handling 的根因层修复（不只是 symptom fix），同时为未来 handler 引入单一事实源（避免继续累积重复）。

## What Changes

### `_lib/cli/__init__.py` 加 re-export

```python
# 新增（顶部 imports 区）
from .__main__ import resolve_project_root  # noqa: F401  (re-exported in __all__)

# 修改 __all__
__all__ = ["route", "list_commands", "_SUBCOMMAND_DESCRIPTION", "resolve_project_root"]
```

### 32 个 handler 替换 anti-pattern（机械化 sed-like 编辑）

**Before** (示例 `_lib/cli/version_cmd.py:30`):
```python
project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
```

**After**:
```python
from skills._lib.cli import resolve_project_root  # noqa: E402  (放在 imports 区块)
# ...
project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()
```

注：保留 env var override 是**有意**的（向后兼容 `__main__.py` setdefault + 测试 env-injection）。仅在 `RDDF_PROJECT_ROOT` 未设时 fallback 到 git 探测。

### 新单元测试 `tests/unit/test_cli_project_root_resolution.py`

覆盖:
- `[ ] AC-PR-1`: `RDDF_PROJECT_ROOT` 未设 + git repo cwd → `resolve_project_root()` 返回 git toplevel
- `[ ] AC-PR-2`: `RDDF_PROJECT_ROOT="<path>"` → override 生效, 返回 `<path>`
- `[ ] AC-PR-3`: 非 git dir → fallback `os.getcwd()`
- `[ ] AC-PR-4`: git submodule 内 → 返回 submodule own root（per ADR-0033）
- `[ ] AC-PR-5`: 33 个 handler 中每个调 `cmd_xxx([])` 不抛异常 + 能找到 `.rddf/state/`（sanity）
- `[ ] AC-PR-6`: 主仓 `./test.sh --quick` 全绿（回归门）

## Acceptance

- [ ] **AC-PR-1**: 32 个 handler 文件全部改用 `resolve_project_root()`（grep 验证 0 个 `RDDF_PROJECT_ROOT or os.getcwd()` occurrences 剩余）
- [ ] **AC-PR-2**: `_lib/cli/__init__.py` re-export `resolve_project_root`（`from skills._lib.cli import resolve_project_root` 不抛 `ImportError`）
- [ ] **AC-PR-3**: 主仓 `./test.sh --quick` 仍 3058+ passed（回归门）
- [ ] **AC-PR-4**: rdd-workflow-e2e test 6 在**移除 `setup() cd`** 后仍 PASS（验证 handler 自解析正确）
- [ ] **AC-PR-5**: 新测试 `test_cli_project_root_resolution.py` 覆盖 AC-PR-1..6 全部通过
- [ ] **AC-PR-6**: handler 在 submodule / worktree / 非 git dir 下能正确解析（per ADR-0033）
- [ ] **AC-PR-7**: `RDDF_PROJECT_ROOT` env var override 行为保留（向后兼容）
- [ ] **AC-PR-8**: 0 new fail in rdd-workflow-e2e CI (after e2e repo re-syncs to this fix)

## Capabilities

### MUST

- **`C-PR-1`**: `_lib/cli/__init__.py` re-export `resolve_project_root` 供 handlers 单点引用
- **`C-PR-2`**: 32 个 handler 把 project_root 解析逻辑改为 `os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()`
- **`C-PR-3`**: 新单元测试覆盖正常 + edge case (submodule / worktree / 非 git)

### MUST NOT

- ❌ **MN-PR-1**: 不修改 `resolve_project_root()` 实现（已正确，per ADR-0033）
- ❌ **MN-PR-2**: 不改 `_lib/cli/__main__.py:203` 的 `os.environ.setdefault("RDDF_PROJECT_ROOT", ...)` (向后兼容)
- ❌ **MN-PR-3**: 不引入新依赖
- ❌ **MN-PR-4**: 不破坏 `RDDF_PROJECT_ROOT` env var override 行为

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| `_lib/cli/*.py` 重复实现 | 32 文件 × ~1.13 处 = 36 occurrences | 0 occurrences (统一 1 处 `resolve_project_root()`) |
| handler 在 submodule 行为 | 错误 (cwd ≠ submodule root) | 正确 (per ADR-0033) |
| handler 在 worktree 行为 | 错误 (cwd ≠ main repo root) | 正确 |
| e2e test 6 workaround | `setup() cd "$RDD_WORKFLOW_REPO"` (commit `efe89dd`) | 可移除 (handler 自解析) |
| 测试友好性 | 需要 env var injection | 既支持 env var injection,也支持 git 探测 |
| 主仓代码改动 | — | 32 文件各 ~1 行 (sed-like) + 1 文件 re-export + 1 新 test file |
| 测试覆盖 | 0 专门的 project_root 解析测试 | +6 test cases (AC-PR-1..6) |

**Risk Assessment**:
- **Low**: 机械化 sed 替换,行为等价 (env override 保留)
- **Medium**: 移除非 git dir fallback — 但 `resolve_project_root()` 已有 fallback (`os.getcwd()` at line 88-94 in `__main__.py`)
- **High**: 无 — 不改公开 API, 不改业务逻辑

**Future follow-up improvement suggestions**:
- `fix-skill-layer-project-root-anti-pattern` (apply same refactor to `skills/*/scripts/*.py` that use `os.getcwd()` for project root — out of scope here)
- `add-resolve-project-root-cli-flag` (allow `--project-root=<path>` CLI flag as 3rd override)