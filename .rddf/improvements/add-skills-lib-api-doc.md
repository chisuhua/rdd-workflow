---
优先级: P2
来源: 2026-09-28 多次 fix-skill-layer 系列实施审计 (fix-33-handlers-project-root-anti-pattern
  commit ab5ded7 + fix-skill-layer-project-root-anti-pattern commit c217cde +
  add-skill-layer-resolve-project-root-helper commit 281423d + fix-skill-layer-resolution-bash
  commit 1bcb8a0) — skill layer 自包含约定修复后,**3 层 helper 架构 (bash + Python
  wrapper + Python CLI) 已有稳定 SSOT 模式**,但 `skills/_lib/` 作为 skill 共享 utilities
  入口未正式文档化。新 skill 作者不知道:
  - skills/_lib/ 有哪些模块可用
  - helper 的 contract 与 ADR 引用
  - 跨层 (bash + Python) 的一致性如何维护
  本提案正式化 skills/_lib 为 skill 共享 utilities 入口,文档化所有 helper + 引导新 skill onboarding
阶段: v4.1 follow-up
分类: documentation
类型: documentation
主题: 跨项目 CLI 契约一致性
依赖: skills/_lib/__init__.py (existing shim layer), fix-skill-layer 系列 4 shipped commits,
  consolidate-resolve-project-root-helpers (proposal)
---

**优先级**: P2 | **来源**: 2026-09-28 fix-skill-layer 系列实施审计
**阶段**: v4.1 follow-up | **分类**: documentation
**类型**: documentation | **主题**: 跨项目 CLI 契约一致性
**依赖**: skills/_lib/ 现有模块 + fix-skill-layer 系列 + consolidate-resolve-project-root-helpers (proposal)

> **症状**: `skills/_lib/` 是 rdd-workflow skill layer 的 **helper 入口**(per fix-skill-layer 系列修复),但**未正式文档化**:
> - 没有 README 列出可用模块 (当前 50+ 模块分散在 skills/_lib/)
> - 没有 helper 入口指引 (新 skill 作者不知道 skills._lib._python_resolve_project_root 存在)
> - 没有跨层一致性指南 (bash `_resolve_project_root` ↔ Python `skills._lib._python_resolve_project_root`)
> - 没有 contract 文件入口(consolidate-resolve-project-root-helpers 提议)
>
> **直接证据** (2026-09-28):
> ```
> $ ls skills/_lib/*.py skills/_lib/*.sh | wc -l
> 50+ modules (cli/, core/, dashboard/, iteration/, loop/, schedulers/, adr_catalog.py, ...)
> ```
> **0 documentation files** in skills/_lib/
> 新 skill 作者需 read source code 反向发现 helper。
>
> **影响**:
> - 新 skill 作者 onboarding 时间长 (需 read 30+ module source)
> - 重复实现: 历史已有 2 次同类技能 (propose_quality_check.py + propose_quality_hook.py)
> - 架构意图散落:per `skills/_lib/iteration/__init__.py:3-10` 注释 "skill layer 自包含",但无 README 说明

## 架构依据

### skills/_lib/ 当前状态 (50+ 模块)

| Category | 模块数 | 例子 |
|----------|--------|------|
| Bash helpers | ~10 | `orchestrator_entry.sh`, `archive.sh`, `discover_ship_changes.sh`, `env_checks.sh` |
| Python core | ~5 | `core/lock.py`, `core/atomic_write.py` |
| Python cross-repo | ~5 | `cross_repo_deps.py`, `cross_repo_state.py`, `gh_hub_client.py` |
| Python CLI dispatcher | ~36 | `_lib/cli/*.py` (rdd-arch, rdd-builder, sync-hub, etc.) |
| Python iteration | ~3 | `iteration/store.py`, `iteration/post_archive.py`, `iteration/render.py` |
| Python wrappers | ~2 | `_python_resolve_project_root.py` (shipped) |

### 缺乏文档化的 3 层 helper (bash + Python)

| Layer | Helper | Status |
|-------|--------|--------|
| Bash | `_resolve_project_root` (orchestrator_entry.sh:33) | shipped |
| Python (skill wrapper) | `skills._lib._python_resolve_project_root.resolve_project_root` | shipped |
| Python (CLI dispatcher) | `_lib.cli.__main__.resolve_project_root` | shipped |

3 helper **没有统一文档入口** — 新 skill 作者需 grep 找。

## 范围

### In Scope

- 创建 `skills/_lib/README.md` (skill 共享 utilities 入口):
  - **§1 Overview**: skills/_lib 是什么,per `skills/_lib/iteration/__init__.py:3-10` 注释 (skill layer 自包含)
  - **§2 Module Catalog**: 表格列出 50+ 模块 (按 category: bash helpers / Python core / Python cross-repo / etc),每行 1 行说明
  - **§3 Helper Entry Points**: 3 层 project_root resolution (bash `_resolve_project_root`, Python wrapper, CLI dispatcher) + cross-reference 到 consolidate-resolve-project-root-helpers 提议
  - **§4 ADR References**: ADR-0033 (git probe), ADR-0030 (cross-repo federation), 等
  - **§5 Onboarding Guide**: 新 skill 作者如何添加 helper (per skills/_lib/iteration/__init__.py shim layer pattern)
  - **§6 Cross-Layer Consistency**: bash + Python helper 行为一致性如何维护 (per consolidate-resolve-project-root-helpers contract)
- 创建 `skills/_lib/INDEX.md` (新 skill quick reference):
  - 1-page table: 所有 helper + contract reference
  - 按 use case 分类 (project_root / cross_repo / iteration / etc)

### Out of Scope

- ❌ 不改任何 module 行为 (纯文档化,不改 code)
- ❌ 不引入新依赖 (纯 markdown)
- ❌ 不写每个 module 的详细 API doc (那是 docstring job, 不在本 scope)

## Why

正式化 `skills/_lib/` 为 skill 共享 utilities 入口,文档化 50+ 模块 + 3 层 helper 架构,降低新 skill 作者 onboarding 时间,提供跨层一致性 reference。这是 fix-skill-layer 系列实施后的**架构收尾**(5 commits fix-skill-layer + 1 commit consolidate-resolve-project-root-helpers + 本 docs = skill layer 完整 picture)。

## What Changes

### 新 `skills/_lib/README.md` (~150 lines)

```markdown
# skills/_lib — Skill shared utilities entry point

> Per `skills/_lib/iteration/__init__.py:3-10`: skill layer 自包含
> — skills should only depend on their own `_lib/` or shared `_lib/`,
> NOT on dispatcher internals (`_lib/cli/`).

## §1 Overview

`skills/_lib/` 是 rdd-workflow skill layer 的 helper 入口,提供:

- **Bash helpers** (project_root resolution, FHIR, arch discovery)
- **Python core** (FileLock, atomic_write — low-level utilities)
- **Python cross-repo** (CrossRepoDeps, GhHubClient — federation)
- **Python iteration** (store.py, post_archive.py — change archive)
- **Python wrappers** (skill-layer shim — exposes shared API)

`__init__.py` 配置 __path__ 让 `import skills._lib.X` 同时命中:
- worktree 本地副本 (`skills/_lib/X.py`)
- global install fallback (`~/.agents/skills/_lib/X.py`)

## §2 Module Catalog

| Module | Lang | Category | Purpose | ADR |
|--------|------|----------|---------|-----|
| `orchestrator_entry.sh` | bash | project_root | `_resolve_project_root` helper | ADR-0033 |
| `archive.sh` | bash | archive | Archive orchestration | — |
| `env_checks.sh` | bash | env | Env var validation | — |
| `core/lock.py` | python | core | FileLock (atomic file locking) | — |
| `core/atomic_write.py` | python | core | atomic_write_json | — |
| `cross_repo_deps.py` | python | cross-repo | Cross-repo dependency analysis | ADR-0030 |
| `cross_repo_state.py` | python | cross-repo | .cross-repo-pending.json I/O | ADR-0030 |
| `gh_hub_client.py` | python | cross-repo | GitHub API client | ADR-0030 |
| `_python_resolve_project_root.py` | python | wrapper | Skill-layer project_root wrapper | — |
| ... | ... | ... | ... | ... |

(Full table with 50+ modules)

## §3 Helper Entry Points — project_root resolution

Per fix-skill-layer 系列 + consolidate-resolve-project-root-helpers proposal:

| Layer | Import | Purpose |
|-------|--------|---------|
| Bash | `source .../orchestrator_entry.sh` then `_resolve_project_root` | Bash scripts (3 callers) |
| Python (skill layer) | `from skills._lib._python_resolve_project_root import resolve_project_root` | Skill scripts (5 callers) |
| Python (CLI layer) | `from _lib.cli.__main__ import resolve_project_root` (or via PEP 562 shim) | CLI dispatcher (26 callers) |

Contract: see `_resolve_project_root_contract.yaml` (proposal
consolidate-resolve-project-root-helpers).

## §4 ADR References

- **ADR-0033**: submodule-aware git probe for `resolve_project_root`
- **ADR-0030**: cross-repo federation (CrossRepoDeps, GhHubClient)
- **ADR-0025**: design phase separation (iteration/, render.py)
- **ADR-0050**: rdd-builder auto-pick (skill layer wrappers vs direct API)

## §5 Onboarding Guide — How to add a new helper

1. **Determine layer**: bash, Python core, Python cross-repo, Python wrapper?
2. **Check existing modules** (避免重复): `ls skills/_lib/` + grep imports
3. **Follow layer conventions**:
   - Bash: source `_lib` before use, exit on error
   - Python core: type hints + tests
   - Python wrapper: lazy import + shim pattern (per `_python_resolve_project_root.py`)
4. **Add shim** in `__init__.py` if cross-layer exposed (per `iteration/__init__.py` example)
5. **Add contract test** (per consolidate-resolve-project-root-helpers proposal)
7. **Document** in this README §2

## §6 Cross-Layer Consistency

Bash + Python helpers SHALL maintain behavior parity per consolidate-resolve-project-root-helpers contract. Drift detection:

- `tests/unit/test_resolve_project_root_contract_bash.sh`
- `tests/unit/test_resolve_project_root_contract_python.py`

If a layer needs to deviate from contract, document in CONTRACT with version bump + ADR.

## See Also

- `skills/_lib/INDEX.md` (1-page quick reference)
- `docs/adr/` (architectural decisions)
- `tests/unit/test_*` (compliance tests)
```

### 新 `skills/_lib/INDEX.md` (~60 lines)

1-page table — 所有 helper + import path + 用途。

## Acceptance

- [ ] **AC-API-1**: `skills/_lib/README.md` 创建 (≥ 6 sections, ≥ 150 lines)
- [ ] **AC-API-2**: `skills/_lib/INDEX.md` 创建 (1-page quick reference)
- [ ] **AC-API-3**: README §2 Module Catalog 列出 ≥ 30 模块 (per current `ls skills/_lib/`)
- [ ] **AC-API-4**: README §3 Helper Entry Points 引用 consolidate-resolve-project-root-helpers 提议
- [ ] **AC-API-5**: README §4 ADR References ≥ 3 ADR 引用
- [ ] **AC-API-6**: README §5 Onboarding Guide ≥ 5 步
- [ ] **AC-API-7**: README §6 Cross-Layer Consistency 引用 contract compliance test
- [ ] **AC-API-8**: 所有现有 test 仍 pass (./test.sh --quick 3095+)

## Capabilities

### MUST

- **`C-API-1`**: README + INDEX 创建,文档化 50+ 模块 + 3 层 helper
- **`C-API-2`**: 6 sections 完整 (Overview, Catalog, Helper Entry Points, ADR, Onboarding, Cross-Layer)

### MUST NOT

- ❌ **MN-API-1**: 不改任何 module 行为 (纯文档化)
- ❌ **MN-API-2**: 不引入新依赖 (纯 markdown)
- ❌ **MN-API-3**: 不写每个 module 的详细 API doc (那是 docstring job)

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| Onboarding 时间 (新 skill 作者) | ~2h (read 30+ module source) | ~15min (read README + INDEX) |
| Helper 可发现性 | grep (0 docs) | README §2 + INDEX table |
| 跨层一致性 reference | 散落 5 commits | README §6 + INDEX |
| 主仓代码改动 | — | 2 markdown files (~210 lines) |

**Risk Assessment**:
- **Low**: 纯文档化,不改 code;现有 test 仍 3095+ pass
- **High**: 无

**Future follow-up improvement suggestions**:
- `add-helper-api-docstrings` (docstring per module - 与本 proposal 互补)
- `add-skills-lib-changelog` (CHANGELOG.md for skills/_lib/ — 跟踪 helper 演化)