---
优先级: P2
来源: >-
  2026-09-28 多次 fix-skill-layer 系列实施审计 (fix-33-handlers-project-root-anti-pattern
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
状态: 已实施并验收（2026-11-24 立项 → 归档为 2026-11-24-add-skills-lib-api-doc；8/8 AC pass；README 274 行 / INDEX 83 行，零代码改动）
依赖: >-
  skills/_lib/__init__.py (existing shim layer), fix-skill-layer 系列 4 shipped commits,
  consolidate-resolve-project-root-helpers (proposal)
---

**优先级**: P2 | **来源**: 2026-09-28 fix-skill-layer 系列实施审计
**阶段**: v4.1 follow-up | **分类**: documentation
**类型**: documentation | **主题**: 跨项目 CLI 契约一致性
**依赖**: skills/_lib/ 现有模块 + fix-skill-layer 系列 + consolidate-resolve-project-root-helpers (proposal)

> **症状**: `skills/_lib/` 是 rdd-workflow skill layer 的 **helper 入口**(per fix-skill-layer 系列修复),但**未正式文档化**:
> - 没有 README 列出可用模块
> - 没有 helper 入口指引 (新 skill 作者不知道 skills._lib._python_resolve_project_root 存在)
> - 没有跨层一致性指南 (bash `_resolve_project_root` ↔ Python `skills._lib._python_resolve_project_root`)
> - 没有 contract 文件入口
>
> **直接证据（2026-11-24 重测，原 2026-09-28 数字已过时）**:
> ```
> $ ls skills/_lib/*.sh | wc -l ; ls skills/_lib/*.py | wc -l
> 16 shims / 19 python shims  (+7 子包目录)
> $ find _lib -maxdepth 1 -name '*.py' | wc -l ; find _lib -maxdepth 1 -name '*.sh' | wc -l
> 89 真实现 .py / 20 真实现 .sh  (+10 子包: cli core dashboard iteration loop plugins schedulers schemas templates verifier)
> ```
> `skills/_lib/` 现有**唯一**文档 `AGENT_TOOL_USAGE.md`（22 行）讲的是 *agent 工具调用决策树*，不是模块目录 ⇒
> **模块目录仍是 0 文档**。新 skill 作者需 read source code 反向发现 helper。
>
> **⚠️ 关键前提更正（2026-11-24）**：commit `c3a90fe`（flatten package layout）之后，
> **真实现层在仓库根的 `_lib/`**，`skills/_lib/` 只剩 **shim 层**（bash 转发 + Python identity-merge）。
> 原提案把 `skills/_lib/` 当成「50+ 模块所在地」是**过时认知** —— 照原口径写出的 README 会是一张**错误的层地图**
> （把 shim 当真身、把 89 个真实现模块漏在文档外）。本提案的目录必须**双层分栏**。
>
> **影响**:
> - 新 skill 作者 onboarding 时间长 (需 read 30+ module source)
> - 重复实现: 历史已有 2 次同类技能 (propose_quality_check.py + propose_quality_hook.py)
> - 架构意图散落:per `skills/_lib/iteration/__init__.py:3-10` 注释 "skill layer 自包含",但无 README 说明

## 架构依据

### 两层结构（2026-11-24 实测）

| 层 | 位置 | 规模 | 角色 |
|---|---|---|---|
| **真实现层** | 仓库根 `_lib/` | 89 顶层 `.py` + 20 `.sh` + 10 子包（`cli` ~36 模块 / `core` / `dashboard` / `iteration` / `loop` / `plugins` / `schedulers` / `schemas` / `templates` / `verifier`） | 全部真实逻辑 |
| **shim 层** | `skills/_lib/` | 16 `.sh` 转发 + 19 `.py` identity-merge + 7 子包 `__init__.py` 扩 `__path__` | skill 侧稳定导入面 + 全局安装 fallback |

`skills/_lib/__init__.py` 把 `__path__` 设为 `[skills/_lib, 仓库根 _lib, ~/.agents/skills/_lib]`，让
`import skills._lib.X` 同时命中三处 —— 这是**路径加宽**，不是模块复制。

| 真实现层分组 | 模块数 | 例子 |
|----------|--------|------|
| Python CLI dispatcher | ~36 | `_lib/cli/*.py` |
| Python 顶层模块 | ~50 | `gate.py`, `recommender.py`, `arch_quality_gate.py`, `cross_repo_*.py` |
| Python core | ~3 | `core/lock.py`, `core/atomic_write.py` |
| Python iteration | ~4 | `iteration/store.py`, `iteration/post_archive.py`, `iteration/render.py` |
| Python verifier | — | `verifier/cache.py`, `verifier/audit.py`, `verifier/discovery.py` |
| Bash helpers | 20 | `orchestrator_entry.sh`, `archive.sh`, `state.sh`, `worktree.sh` |

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
  - **§1 Overview**: 两层结构（仓库根 `_lib/` = 真实现；`skills/_lib/` = shim + `__path__` 加宽），per `skills/_lib/__init__.py` 与 `iteration/__init__.py`
  - **§2 Module Catalog**: **双层分栏**表格（真实现层按 category 分组 + shim 层逐条），每行 1 行说明
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

正式化 `skills/_lib/` 为 skill 共享 utilities 入口,文档化**两层结构**（仓库根 `_lib/` 真实现 + `skills/_lib/` shim）与 3 层 helper 架构,降低新 skill 作者 onboarding 时间,提供跨层一致性 reference。这是 fix-skill-layer 系列实施后的**架构收尾**(5 commits fix-skill-layer + 1 commit consolidate-resolve-project-root-helpers + 本 docs = skill layer 完整 picture)。

## What Changes

### 新 `skills/_lib/README.md` (~150 lines)

```markdown
# skills/_lib — Skill shared utilities entry point

> Per `skills/_lib/iteration/__init__.py:3-10`: skill layer 自包含
> — skills should only depend on their own `_lib/` or shared `_lib/`,
> NOT on dispatcher internals (`_lib/cli/`).

## §1 Overview

`skills/_lib/` 是 rdd-workflow skill layer 的**导入面**,背后是两层:

| 层 | 位置 | 内容 |
|---|---|---|
| 真实现层 | 仓库根 `_lib/` | 全部逻辑（89 顶层 .py + 20 .sh + 10 子包） |
| shim 层 | `skills/_lib/` | bash 转发 + Python identity-merge + 子包 `__path__` 加宽 |

`skills/_lib/__init__.py` 把 `__path__` 设为三处，让 `import skills._lib.X` 同时命中:
- `skills/_lib/`（shim，本地）
- 仓库根 `_lib/`（真实现）
- `~/.agents/skills/_lib/`（全局安装 fallback）

## §2 Module Catalog

### 2.1 真实现层（仓库根 `_lib/`）

| Module | Lang | Category | Purpose | ADR |
|--------|------|----------|---------|-----|
| `cli/` | python | dispatcher | `rddf` 子命令实现（~36 个） | — |
| `gate.py` | python | gate | 阶段门判定 | — |
| `recommender.py` | python | guide | 阶段推荐阶梯（ADR-0062） | ADR-0062 |
| `arch_quality_gate.py` | python | arch | ADR 形态校验 | ADR-0060 |
| `verifier/` | python | verifier | verdict cache / audit / discovery | ADR-0034 |
| `core/lock.py` | python | core | FileLock（原子文件锁） | — |
| `core/atomic_write.py` | python | core | atomic_write_json | — |
| `cross_repo_deps.py` | python | cross-repo | 跨仓依赖分析 | ADR-0030 |
| `gh_hub_client.py` | python | cross-repo | GitHub API client | ADR-0030 |
| `iteration/store.py` | python | iteration | iteration 状态读写 | ADR-0025 |
| `orchestrator_entry.sh` | bash | project_root | `_resolve_project_root` | ADR-0033 |
| `archive.sh` | bash | archive | 归档编排 | ADR-0061 |
| `state.sh` | bash | state | 状态读写 helper | — |

（实施时补全 ≥30 条，覆盖全部 10 个子包）

### 2.2 shim 层（`skills/_lib/`）

| Module | 形态 | 说明 |
|--------|------|------|
| `state.sh` / `archive.sh` / … | bash 转发 | 优先仓库根 `_lib/`，回退 `~/.agents/skills/_lib/` |
| `adr_catalog.py` / `cross_repo_*.py` / … | identity-merge | `exec` 真实现源码 ⇒ `is ` 恒等成立 |
| `iteration/` / `core/` / … | `__path__` 加宽 | 让 `from skills._lib.X import Y` 命中真实现 |

（16 `.sh` + 19 `.py` 逐条列全）

## §3 Helper Entry Points — project_root resolution

Per fix-skill-layer 系列 + 契约文件 `_lib/_resolve_project_root_contract.yaml`（`consolidate-resolve-project-root-helpers` 已实施）:

| Layer | Import | Purpose |
|-------|--------|---------|
| Bash | `source .../orchestrator_entry.sh` then `_resolve_project_root` | Bash scripts (3 callers) |
| Python (skill layer) | `from skills._lib._python_resolve_project_root import resolve_project_root` | Skill scripts (5 callers) |
| Python (CLI layer) | `from _lib.cli.__main__ import resolve_project_root` (or via PEP 562 shim) | CLI dispatcher (26 callers) |

Contract: `_lib/_resolve_project_root_contract.yaml`（canonical；`skills/_lib/_resolve_project_root_contract.yaml` 只是兼容指针）。

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
5. **Add contract test** (per `_lib/_resolve_project_root_contract.yaml`)
6. **Document** in this README §2

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

- [x] **AC-API-1**: `skills/_lib/README.md` 创建 (≥ 6 sections, ≥ 150 lines)
- [x] **AC-API-2**: `skills/_lib/INDEX.md` 创建 (1-page quick reference)
- [x] **AC-API-3**: README §2 Module Catalog **双层分栏** —— 真实现层（仓库根 `_lib/`）≥ 30 条且覆盖全部 10 个子包；shim 层（`skills/_lib/`）逐条列全（16 `.sh` + 19 `.py`）。**判据**：`grep -c '^| `' README.md` 的表格行数 ≥ 46，且文中出现 `_lib/` 与 `skills/_lib/` 两层的对照表
- [x] **AC-API-4**: README §3 Helper Entry Points 指向 **契约文件** `_lib/_resolve_project_root_contract.yaml`（`consolidate-resolve-project-root-helpers` 提议**已实施**，不再是"未来提议"）
- [x] **AC-API-5**: README §4 ADR References ≥ 3 ADR 引用，且每个编号在 `docs/adr/` 磁盘上存在（`rddf doctor --category docs-consistency` 会扫）
- [x] **AC-API-6**: README §5 Onboarding Guide ≥ 5 步，且步骤编号连续（原草稿 1-5 后跳到 7，须修正）
- [x] **AC-API-7**: README §6 Cross-Layer Consistency 引用两个既有契约测试：`tests/unit/test_resolve_project_root_contract_bash.sh`、`tests/unit/test_resolve_project_root_contract_python.py`（两者须真实存在，不是臆造文件名）
- [x] **AC-API-8**: 门禁全绿 —— `python3 -m pytest tests/unit/ -q` 与 `python3 -m ruff check .` 通过（**不绑具体用例数**：数字随语料漂移，写死会立刻过时，参考本提案自己的 AC-API-3 与原 3095+ 的前车之鉴）

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
| Helper 可发现性 | grep（`skills/_lib/` 唯一文档 `AGENT_TOOL_USAGE.md` 讲的是 agent 工具决策树，不是模块目录） | README §2 双层目录 + INDEX table |
| 跨层一致性 reference | 散落 5 commits + 一个 YAML 契约文件 | README §6 指向两个契约测试 |
| 主仓代码改动 | — | 2 markdown files (~250 lines) |

**Risk Assessment**:
- **Low**: 纯文档化,不改 code;门禁判据见 AC-API-8（不绑用例数）
- **High**: 无 —— **前提**：按 2026-11-24 的双层结构写；若照原「50+ 模块都在 `skills/_lib/`」的过时口径写，产出的是一张错误的层地图（把 shim 当真身、89 个真实现模块漏记）

**Future follow-up improvement suggestions**:
- `add-helper-api-docstrings` (docstring per module - 与本 proposal 互补)
- `add-skills-lib-changelog` (CHANGELOG.md for skills/_lib/ — 跟踪 helper 演化)
## 实施记录

**2026-11-24 · 立项 → 实现 → 归档（全绿）**

| 项 | 内容 |
|---|---|
| change | `2026-11-24-add-skills-lib-api-doc`（`openspec/changes/archive/`） |
| 产出 | `skills/_lib/README.md`（274 行 / 6 节 / 168 个模块行）+ `skills/_lib/INDEX.md`（83 行速查） |
| 代码改动 | **零**（未改任何 `.sh` / `.py` / `.bats` —— MN-API-1 / MN-API-2） |
| 验收 | 8/8 AC pass（verdict cache 锚点 = 分支 tip `f9870ccb`） |
| 门禁 | 主仓 `./test.sh --full --regression` **ALL PASSED**（bats 新增失败 0 / 未评估 0 / zombie 0；pytest unit 3641 passed 0 failed；integration 192 passed；validate 162 passed 0 failed） |

### 前提更正（立项前）

原提案把 `skills/_lib/` 当成「50+ 模块所在地」。`c3a90fe`（flatten package layout）之后**真实现层在仓库根 `_lib/`**
（89 顶层 `.py` + 20 `.sh` + 10 子包），`skills/_lib/` 只是 shim 层（16 `.sh` 转发 + 19 `.py` identity-merge + 6 子目录 `__path__` 加宽）。
照原口径写出的 README 会是一张**错误的层地图**（把 shim 当真身、89 个真实现模块漏记）⇒ README 改为**双层分栏**。
目录数据**由脚本从磁盘采集**（不手抄），避免文档自己变成新的漂移源。

### ⚠️ 实施期发现的仓库级缺陷（仅记录，不在本 change 修）

**D3 spec-delta 生成器与仓库自己的 spec 形态守卫不兼容。**
归档动作会把 proposal 的 Acceptance 经 `generate_spec_delta()` 落成 `openspec/specs/<change>/spec.md`，
其形态是 `### Requirement: acceptance-N` + `- **WHEN** the change is applied` —— 恰是
`tests/unit/test_spec_requirement_form.py` 明令禁止的**退化 Requirement 形态**（判据①无语义名 / 判据②恒真 WHEN）。

- **首次暴露**：step 2（`fix-agents-md-worktree-commit-flow`）归档后，下一次改动的全量门报 20 处退化形态；
- **第二次确认**：step 4（本 change）归档后，同一守卫再次报 8 处 —— **每一条经 D3 delta 归档的 change 都会撞上**；
- **连带**：每新增一份 spec 都要同步 `tests/unit/test_v4_residue_check.py` 的 R4 文件数常量（该测试 docstring 明写此规矩）。

**本次处置**：两份 spec 都已**重写为合规形态**（语义化 Requirement + 可区分 WHEN + 真 `## Purpose`），并同步了 R4 常量。
**根因未修** —— 真正的修法在 `generate_spec_delta()`（rdd-planner 侧）：让它产出语义化 Requirement 名与可区分 WHEN。
那属于**另一个 change 的范围**（改 rdd-planner 的生成器 + 可能需要一条新 ADR），本 change 不越界动它 —— **另案立项**。

### 另一条流程盲区（仅记录）

仓库规则是「archive **前**跑全量回归门」，但**归档动作本身会生成 tracked 的契约面工件**（`openspec/specs/**`）。
门跑在产物生成**之前** ⇒ 看不见自己刚造的东西 ⇒ step 2 是「归档前门绿、归档后红」。
覆盖它的只有**下一次**改动的前置门。要根治得改 `phase3_archive.sh` 的流程（归档后补一次门），属另案。

