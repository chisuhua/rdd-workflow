---
优先级: P3
来源: 2026-09-27 add-skill-layer-resolve-project-root-helper (shipped commit 281423d) 实施审计
  — 该 proposal 修了 Python side skill layer leaky abstraction。但 **bash side 仍有
  ad-hoc project_root detection**:
  - skills/_lib/orchestrator_entry.sh:33 已有 bash helper `_resolve_project_root()` (single source of truth)
  - 2 bash scripts 正确用 helper: select_worktree.sh:16, arch_env_check.sh:21
  - **1 bash script 手动重新实现**:`skills/rdd-arch/scripts/roadmap_incremental_update.sh:25-33`
    显式检查 RDDF_PROJECT_ROOT + git probe fallback,与 bash helper 重复
  - 56 bash scripts 使用 `${VAR:-default}` pattern (但用于其他 env vars,非 project_root)
阶段: v4.1 follow-up
分类: refactor
类型: refactor
主题: 跨项目 CLI 契约一致性
依赖: skills/_lib/orchestrator_entry.sh::_resolve_project_root (bash ref impl, existing),
  add-skill-layer-resolve-project-root-helper (shipped commit 281423d)
---

**优先级**: P3 | **来源**: 2026-09-27 add-skill-layer-resolve-project-root-helper 实施审计
**阶段**: v4.1 follow-up | **分类**: refactor
**类型**: refactor | **主题**: 跨项目 CLI 契约一致性
**依赖**: skills/_lib/orchestrator_entry.sh::_resolve_project_root (bash ref, existing)

> **症状**: Bash skill layer 有 1 个 script (`roadmap_incremental_update.sh`) 手动重新实现 `_resolve_project_root` 的逻辑 (RDDF_PROJECT_ROOT 检查 + git probe fallback),而不调用 `skills/_lib/orchestrator_entry.sh:33` 的现有 bash helper。Python side 刚通过 `add-skill-layer-resolve-project-root-helper` (commit 281423d) 修了 leaky abstraction (5 scripts 改 import 路径),bash side 留下同样的 duplication。
>
> **直接证据** (2026-09-27 grep):
> ```
> $ grep -l "RDDF_PROJECT_ROOT.*=\|git.*rev-parse.*show-toplevel" skills/*/scripts/*.sh
> skills/execute/scripts/select_worktree.sh:16:source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/orchestrator_entry.sh"
> skills/rdd-arch/scripts/arch_env_check.sh:21:source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/orchestrator_entry.sh"
> skills/rdd-arch/scripts/roadmap_incremental_update.sh:25-33:# Manual duplicate of _resolve_project_root
>
> $ grep -rn "_resolve_project_root" skills/_lib/
> skills/_lib/orchestrator_entry.sh:33:  (definition site)
> skills/_lib/orchestrator_entry.sh:48:_proj_root="$(_resolve_project_root)"  (usage site)
> ```
>
> **根因**: `roadmap_incremental_update.sh` 写于 bash helper 之前 (per git blame),author 不知道 helper 存在或不愿意跨 source file。

## 架构依据

### Bash helper vs Python wrapper 对称

| Layer | Helper | Status |
|-------|--------|--------|
| Bash | `skills/_lib/orchestrator_entry.sh::_resolve_project_root` (line 33) | ✅ 已存在, 2/3 scripts 用 |
| Python | `skills/_lib/_python_resolve_project_root.py::resolve_project_root` | ✅ 已存在 (commit 281423d), 5/5 scripts 用 |
| Manual duplicate | `roadmap_incremental_update.sh:25-33` | ❌ 1 script 重实现 |

### Symmetric pattern is the goal

- 2 scripts (`select_worktree.sh`, `arch_env_check.sh`) 用 bash helper ✓
- 1 script (`roadmap_incremental_update.sh`) 手动重新实现 ✗
- 修复目标:让 `roadmap_incremental_update.sh` 也用 helper,消除 bash side 唯一残留的 duplication

### User-mentioned "~8 bash scripts with RDDF_HUB_REPO" — clarification

User 提出的 "~8 bash scripts 用 RDDF_HUB_REPO 等其他 env var" 描述不准确:
- `RDDF_HUB_REPO`, `RDDF_SYNC_DRY_RUN`, `RDDF_REPORT_GH_REPO`, `RDDF_WATCH_DRY_RUN` 等只在 **Python scripts** (sync_hub, watch_hub, report_issue_rfc) 用
- **0 个 bash scripts** 用这些 env vars
- 这些 Python scripts 也不需要修复 — 它们正确用 `os.environ.get` 读各自专属的 Hub config (不是 project_root)

Bash side 唯一残留 duplication 是 `roadmap_incremental_update.sh:25-33` 手动实现 project_root detection。

## 范围

### In Scope

- 修 `skills/rdd-arch/scripts/roadmap_incremental_update.sh:25-33` 用 bash helper:
  ```bash
  # Before (manual duplicate):
  if [ -z "${RDDF_PROJECT_ROOT:-}" ]; then
    echo "❌ RDDF_PROJECT_ROOT is required but not set" >&2
    exit 1
  fi
  if [ ! -d "$RDDF_PROJECT_ROOT" ]; then
    echo "❌ RDDF_PROJECT_ROOT is not a directory: $RDDF_PROJECT_ROOT" >&2
    exit 1
  fi
  export RDDF_PROJECT_ROOT

  # After (use bash helper):
  source "${_ORCHESTRATOR_DIR:-$(dirname "${BASH_SOURCE[0]}")}/../orchestrator_entry.sh" || {
    echo "❌ Cannot source orchestrator_entry.sh" >&2
    exit 1
  }
  export RDDF_PROJECT_ROOT="$(_resolve_project_root)"
  if [ ! -d "$RDDF_PROJECT_ROOT" ]; then
    echo "❌ Resolved RDDF_PROJECT_ROOT is not a directory: $RDDF_PROJECT_ROOT" >&2
    exit 1
  fi
  ```
- 新单元测试 `tests/unit/test_roadmap_incremental_update.sh` (bash test framework)
  - 验证 `_resolve_project_root` 被调用 (grep test)
  - 验证手动实现已删除 (grep test for absence of `RDDF_PROJECT_ROOT is required`)
  - 验证仍正确 export RDDF_PROJECT_ROOT
- 保留现有 `roadmap_incremental_update.sh` 行为不变 (semantics parity)

### Out of Scope

- ❌ 不改 `skills/_lib/orchestrator_entry.sh::_resolve_project_root` 实现本身 (已正确 per ADR-0033 + bash `--show-toplevel`)
- ❌ 不修 56 个 bash scripts 用 `${VAR:-default}` pattern — 那些用于其他 env vars (不是 project_root),无需修复
- ❌ 不引入新依赖

## Why

让 bash skill layer 与 Python skill layer 对称 (Python 已有 wrapper, bash 应统一用 helper)。消除 bash side 唯一残留的 duplication (`roadmap_incremental_update.sh:25-33`),与 add-skill-layer-resolve-project-root-helper (commit 281423d) 形成完整 picture。

## What Changes

### `roadmap_incremental_update.sh` 改用 bash helper

**Before** (line 25-33):
```bash
if [ -z "${RDDF_PROJECT_ROOT:-}" ]; then
  echo "❌ RDDF_PROJECT_ROOT is required but not set" >&2
  exit 1
fi
if [ ! -d "$RDDF_PROJECT_ROOT" ]; then
  echo "❌ RDDF_PROJECT_ROOT is not a directory: $RDDF_PROJECT_ROOT" >&2
  exit 1
fi
export RDDF_PROJECT_ROOT
```

**After**:
```bash
# Source bash helper for project_root resolution (single source of truth)
source "${BASH_SOURCE[0]%/*}/../_lib/orchestrator_entry.sh" 2>/dev/null || \
  source "/dev/stdin <<'ORCH_EOF'
$(cat skills/_lib/orchestrator_entry.sh)
ORCH_EOF
" 2>/dev/null || {
    echo "❌ Cannot source orchestrator_entry.sh" >&2
    exit 1
  }

# Resolve project_root via bash helper (per fix-skill-layer-resolution-bash)
export RDDF_PROJECT_ROOT="$(_resolve_project_root)"
if [ ! -d "$RDDF_PROJECT_ROOT" ]; then
  echo "❌ Resolved RDDF_PROJECT_ROOT is not a directory: $RDDF_PROJECT_ROOT" >&2
  exit 1
fi
```

注: source pattern 跟随 `select_worktree.sh:16` 和 `arch_env_check.sh:21` 的现有 convention。

### 新 bash 测试 `tests/unit/test_roadmap_incremental_update.sh`

```bash
#!/usr/bin/env bats
# Verify roadmap_incremental_update.sh uses _resolve_project_root bash helper
# (per fix-skill-layer-resolution-bash)

@test "uses bash helper for project_root resolution" {
    grep -q "_resolve_project_root" skills/rdd-arch/scripts/roadmap_incremental_update.sh
}

@test "no manual RDDF_PROJECT_ROOT env check" {
    ! grep -q "RDDF_PROJECT_ROOT is required" skills/rdd-arch/scripts/roadmap_incremental_update.sh
}

@test "exports RDDF_PROJECT_ROOT after resolution" {
    grep -q "export RDDF_PROJECT_ROOT" skills/rdd-arch/scripts/roadmap_incremental_update.sh
}
```

## Acceptance

- [ ] **AC-SLB-1**: `roadmap_incremental_update.sh` 调用 `_resolve_project_root` bash helper (grep 验证)
- [ ] **AC-SLB-2**: `roadmap_incremental_update.sh` 不再有手动 RDDF_PROJECT_ROOT env check (grep `RDDF_PROJECT_ROOT is required` 0 hits)
- [ ] **AC-SLB-3**: `roadmap_incremental_update.sh` 仍正确 export RDDF_PROJECT_ROOT (semantics parity)
- [ ] **AC-SLB-4**: 新 bash test `test_roadmap_incremental_update.sh` 3 cases 全部通过
- [ ] **AC-SLB-5**: `./test.sh --quick` 仍 3095+ passed (回归门)
- [ ] **AC-SLB-6**: bash side 与 Python side 对称:2 scripts (Python) + 3 scripts (bash) 都用 wrapper/helper

## Capabilities

### MUST

- **`C-SLB-1`**: `roadmap_incremental_update.sh` 改用 bash helper `_resolve_project_root`
- **`C-SLB-2`**: 新 bash test 覆盖 import + semantics

### MUST NOT

- ❌ **MN-SLB-1**: 不改 bash helper `_resolve_project_root` 实现本身 (已正确 per ADR-0033 + bash `--show-toplevel`)
- ❌ **MN-SLB-2**: 不引入新依赖
- ❌ **MN-SLB-3**: 不改其他 56 bash scripts 的 env var pattern (那些用于其他 env vars,不在本 scope)

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| Bash scripts 手动重实现 project_root detection | 1 (roadmap_incremental_update.sh) | 0 |
| Bash scripts 用 helper | 2 (select_worktree.sh, arch_env_check.sh) | 3 (+ roadmap_incremental_update.sh) |
| Bash/Python 对称性 | 5 Python scripts 用 wrapper, 2 bash scripts 用 helper (asymmetric) | 5 Python + 3 bash (symmetric) |
| 主仓代码改动 | — | 1 bash file (~10 lines) + 1 new bash test (~30 lines) |

**Risk Assessment**:
- **Low**: 单一 file, semantics parity preserved (helper 与 manual logic 行为一致)
- **Medium**: source path 依赖 (path resolution 需正确)— 跟随 select_worktree.sh:16 现有 convention 缓解
- **High**: 无 — 不改公开 API, 不改业务逻辑

**Future follow-up improvement suggestions**:
- `consolidate-resolve-project-root-helpers` (跨语言重构: bash + Python 都通过单一 contract 文件定义)
- `add-skills-lib-api-doc` (正式化 `skills/_lib/` 为 skill 共享 utilities 入口,文档化所有 helper)