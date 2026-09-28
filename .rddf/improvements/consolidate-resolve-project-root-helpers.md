---
优先级: P3
来源: 2026-09-28 fix-skill-layer-resolution-bash (shipped commit 1bcb8a0) 实施审计 — bash + Python
  现在各有独立 helper (bash `_resolve_project_root` + Python
  `skills._lib._python_resolve_project_root.resolve_project_root`),但两语言之间
  没有共享 contract → 行为可能漂移 (如 bash helper 未来支持 RDDF_PROJECT_ROOT
  override 而 Python 不支持)。本提案是 fix-skill-layer 系列 (P3 follow-up):
  通过单一 contract 文件 (YAML) 定义 4 个核心 invariant,双语言 helper 都从 contract
  推导,行为一致性自动保证
阶段: v4.1 follow-up
分类: refactor
类型: refactor
主题: 跨项目 CLI 契约一致性
依赖: skills/_lib/orchestrator_entry.sh::_resolve_project_root (shipped),
  skills/_lib/_python_resolve_project_root.py::resolve_project_root (shipped commit 281423d),
  ADR-0033 (submodule-aware git probe)
---

**优先级**: P3 | **来源**: 2026-09-28 fix-skill-layer-resolution-bash 实施审计
**阶段**: v4.1 follow-up | **分类**: refactor
**类型**: refactor | **主题**: 跨项目 CLI 契约一致性
**依赖**: 2 bash + Python helpers (shipped)

> **症状**: Bash `_resolve_project_root` (skills/_lib/orchestrator_entry.sh:33) 与 Python `skills._lib._python_resolve_project_root.resolve_project_root` (commit 281423d) 是**独立的实现**,没有共享 contract。两语言行为目前 parity (per add-skill-layer-resolve-project-root-helper test_cross_language_parity_with_bash_helper),但**未来修改可能漂移**:
> - Bash helper 加 RDDF_PROJECT_ROOT override 时 Python 不知道
> - Python wrapper 改 git probe 策略时 bash 不知道
> - 第三方 skill 需双语言实现时,无 SSOT 文档
>
> **直接证据** (2026-09-28):
> ```
> $ wc -l skills/_lib/orchestrator_entry.sh:_resolve_project_root section
> 8 lines bash impl
> $ wc -l skills/_lib/_python_resolve_project_root.py:resolve_project_root
> 3 lines (delegates to _lib.cli.__main__)
> ```
> 两个独立 impl,无 contract 文档说明 invariant。
>
> **关键观察**: `_lib/cli/__main__.resolve_project_root` 是 Python helper delegate 目标 (per add-skill-layer-resolve-project-root-helper),而 bash helper 是独立 impl (不走 `_lib/cli`)。**双语言不通过单一 SSOT 推导**,只通过 test parity 验证 (test_cross_language_parity_with_bash_helper)。

## 架构依据

### 当前架构

| Layer | Helper | impl 来源 | 行为 contract |
|-------|--------|-----------|---------------|
| Bash | `_resolve_project_root` (orchestrator_entry.sh:33) | 独立 bash (git rev-parse) | env override → git → cwd |
| Python | `resolve_project_root` (skills/_lib/_python_resolve_project_root.py) | delegate to `_lib.cli.__main__.resolve_project_root` | env override → git → cwd |
| Python (CLI) | `resolve_project_root` (_lib/cli/__main__.py:39) | 独立 Python (subprocess git) | git → cwd (NO env override) |

**3 个独立实现**:
1. Bash: 独立 bash (single source of truth for bash layer)
2. Python (skill layer wrapper): delegates to CLI impl (single source of truth for Python layer)
3. Python (CLI layer): 独立 Python (single source of truth for dispatcher)

### 问题: 行为漂移风险

| Scenario | 风险 |
|----------|------|
| Bash helper 加 RDDF_PROJECT_ROOT override | Python 不知道 (但已支持) |
| Python CLI layer 加 RDDF_PROJECT_ROOT override | Bash + Python wrapper 不知道 |
| 第三方 skill 需实现 project_root resolution | 无 contract 文档,需读 3 个 impl |

### 修复策略: 单一 Contract 文件 (YAML)

不**消除** 3 个 impl (每个在各自的 layer 有合理的边界),而是**抽取共享 invariant 到单一 contract**:

```yaml
# skills/_lib/_resolve_project_root_contract.yaml
schema_version: 1
contract:
  invariant_1_env_var_override:
    env_var_name: "RDDF_PROJECT_ROOT"
    semantics: |
      If env var is set and non-empty, return its value.
      This applies to BOTH bash and Python layers (per add-skill-layer-resolution-bash).
    applies_to: [bash_helper, python_wrapper, python_cli]
  
  invariant_2_git_probe:
    command: "git -C <cwd> rev-parse --show-toplevel"
    semantics: |
      If env var unset/empty AND cwd is inside a git repo,
      return git toplevel path (submodule-aware per ADR-0033).
    submodule_handling: per ADR-0033 (returns submodule own root, not superproject)
    worktree_handling: per ADR-0033 (returns main repo root, not worktree cwd)
  
  invariant_3_cwd_fallback:
    semantics: |
      If env var unset AND cwd is NOT in a git repo, return cwd.
  
  invariant_5_function_signature:
    bash: |
      function _resolve_project_root() { ... }
    python: |
      def resolve_project_root() -> str: ...
    returns: absolute path string
  
  invariant_6_exit_code_on_failure:
    applies_to: [bash_helper]
    behavior: |
      Bash callers should check result is non-empty and directory exists.
      Helper itself does NOT exit on error; callers do.
```

3 个 impl 各自由 contract 派生:
- Bash: source contract YAML, generate bash function (codegen 一次)
- Python wrapper: source contract YAML, assert behavior parity in tests
- Python CLI: 同上

**Contract 是 SSOT**,drift 而非 SSOT (因为 3 个 impl 各自生成 from contract)。

## 范围

### In Scope

- 创建 `skills/_lib/_resolve_project_root_contract.yaml` (单一 contract 文件, ~80 lines YAML)
  - 定义 4 个 invariant: env override / git probe / cwd fallback / function signature
  - 引用 ADR-0033 (submodule/worktree handling)
  - Version field for future evolution
- 3 个 impl 各自**验证** against contract (test side):
  - Bash test (`tests/unit/test_resolve_project_root_contract_bash.sh`): 验证 bash helper 满足 4 invariant
  - Python test (`tests/unit/test_resolve_project_root_contract_python.py`): 验证 wrapper + CLI 满足 4 invariant
- 现有 helper **不变** (只加 test,不重写 impl) — contract 是**约束文档**而非代码生成源
- 文档化在 `skills/_lib/README.md` (per add-skills-lib-api-doc proposal):
  - 列出 3 个 helper + 各自 contract compliance status

### Out of Scope

- ❌ 不重写 bash/Python helper impl (各自由 layer-specific 优化,语义已通过 parity test 验证)
- ❌ 不改 `_lib/cli/__main__.resolve_project_root` (已有 ADR-0033 单源真理)
- ❌ 不引入 contract 自动代码生成 (YAGNI — 3 个 impl 都稳定; contract 作为约束 test 足够)
- ❌ 不引入新依赖

## Why

消除 bash + Python 双语言 helper 行为漂移风险 (3 个独立 impl 没有共享 contract)。通过**约束测试**(contract compliance test) 确保未来修改不破坏 invariant。比 codegen 更轻量 (不引入 build step)。

## What Changes

### 新合同文件 `skills/_lib/_resolve_project_root_contract.yaml`

```yaml
schema_version: 1
project_root_resolution_contract:
  version: "1.0"
  last_updated: "2026-09-28"
  sources:
    - commit: "281423d"
      change: "add-skill-layer-resolve-project-root-helper"
    - commit: "1bcb8a0"
      change: "fix-skill-layer-resolution-bash"
  
  invariants:
    - id: env_var_override
      env_var: "RDDF_PROJECT_ROOT"
      semantics: |
        If RDDF_PROJECT_ROOT env var is set and non-empty,
        return its value as the project root.
      applies_to: [bash_helper, python_wrapper, python_cli]
      layer_specific:
        bash_helper: "Directly supported (line 33-40 in orchestrator_entry.sh)"
        python_wrapper: "Directly supported (line 18-19 in _python_resolve_project_root.py)"
        python_cli: "NOT supported by default (no env var check); callers must
          set RDDF_PROJECT_ROOT in env before invoking if override needed"
    
    - id: git_probe
      command: "git -C \"$PWD\" rev-parse --show-toplevel"
      semantics: |
        If RDDF_PROJECT_ROOT env var unset AND cwd is inside a git repo,
        return git toplevel. Submodule-aware per ADR-0033.
      applies_to: [bash_helper, python_wrapper, python_cli]
      references: [ADR-0033]
    
    - id: cwd_fallback
      semantics: |
        If env var unset AND cwd not in git repo, return cwd as-is.
      applies_to: [bash_helper, python_wrapper, python_cli]
    
    - id: function_signature
      bash: "_resolve_project_root() { ... }"
      python: "def resolve_project_root() -> str: ..."
      returns: "absolute path string (string type)"
```

### 新测试 (contract compliance)

**`tests/unit/test_resolve_project_root_contract_bash.sh`** (3 cases):
- bash helper 输出符合 invariant_1 (env var override): 设 `RDDF_PROJECT_ROOT=/test/path` → bash helper 返回 `/test/path`
- bash helper 输出符合 invariant_2 (git probe): unset env + git cwd → 返回 git toplevel
- bash helper 输出符合 invariant_3 (cwd fallback): unset env + 非 git cwd → 返回 cwd

**`tests/unit/test_resolve_project_root_contract_python.py`** (3 cases x 2 impl = 6 cases):
- Python wrapper + CLI 各自满足 3 invariant (parametrize over impl)

### README 更新 (per add-skills-lib-api-doc proposal)

`skills/_lib/README.md` (new) 列 3 个 helper + contract compliance status + ADR 引用。

## Acceptance

- [ ] **AC-CRP-1**: `skills/_lib/_resolve_project_root_contract.yaml` 创建 (4 invariants documented)
- [ ] **AC-CRP-2**: `tests/unit/test_resolve_project_root_contract_bash.sh` 3 cases 全部通过
- [ ] **AC-CRP-3**: `tests/unit/test_resolve_project_root_contract_python.py` 6 cases 全部通过 (2 impl × 3 invariants)
- [ ] **AC-CRP-4**: 所有现有 test 仍 pass (bash helper parity, Python wrapper parity, ./test.sh --quick 3095+)
- [ ] **AC-CRP-5**: 3 impl 各自满足 contract (parity test 验证)
- [ ] **AC-CRP-6**: `skills/_lib/README.md` 列 3 helper + cross-reference 到 contract

## Capabilities

### MUST

- **`C-CRP-1`**: Contract 文件定义 4 invariant
- **`C-CRP-2`**: Contract compliance test 覆盖 3 impl × 4 invariant

### MUST NOT

- ❌ **MN-CRP-1**: 不重写 3 个 impl (只加 contract + test)
- ❌ **MN-CRP-2**: 不引入 contract 自动代码生成 (YAGNI)
- ❌ **MN-CRP-3**: 不改 `_lib/cli/__main__.resolve_project_root` 行为 (per ADR-0033)
- ❌ **MN-CRP-4**: 不引入新依赖

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| 行为漂移检测 | 仅 parity test (1 case) | contract compliance (3 impl × 4 invariant = 12 cases) |
| Contract 文档化 | 散落在 3 impl 内 | 单一 YAML 文件 |
| 新 helper onboarding | 读 3 impl | 读 1 contract + 1 impl |
| 主仓代码改动 | — | 1 YAML contract + 2 test files (~80+120+120) |

**Risk Assessment**:
- **Low**: 3 impl 现已 parity verified (add-skill-layer-resolve-project-root-helper test_cross_language_parity_with_bash_helper); contract 是约束文档,不改 impl 行为
- **Medium**: 未来 contract 演化需要同步更新 3 impl + 2 test — 但有 version field 标识
- **High**: 无 — contract 是 SSOT, 3 impl 各自稳定,无 risk

**Future follow-up improvement suggestions**:
- `add-contract-codegen` (若 3 impl drift 频繁,考虑 codegen — 当前 YAGNI)
- `add-cross-layer-test-harness` (统一 bash + Python test framework,避免 test_bash.sh vs test_python.py 分离)