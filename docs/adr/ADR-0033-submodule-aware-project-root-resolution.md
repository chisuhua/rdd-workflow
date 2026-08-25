# ADR-0033: Submodule-Aware Project Root Resolution

> **状态**: 待定
> **日期**: 2026-08-25
> **决策者**: rdd-workflow maintainers
> **来源提案**: [.rddf/improvements/submodule-aware-project-root.md](../.rddf/improvements/submodule-aware-project-root.md)

## Context

rdd-workflow 的项目根解析基础设施(`main_repo_root()` in `_lib/worktree.sh`、`resolve_project_root()` in `_lib/cli/__main__.py`)基于 `git rev-parse --git-common-dir` 设计,目标是**worktree-safe**: 在 worktree 内执行时返回主仓库根(而非 worktree 自身根),让 `.rddf/state/` 写入集中到主仓库。

但这一设计在 **git submodule** 场景下失效:

| 用户场景 | `--git-common-dir` 返回 | 期望 | 实际行为 |
|---------|------------------------|------|---------|
| 主 repo | `/super/.git` | `/super` | ✅ 正确 |
| Linked worktree | `/super/.git/worktrees/<name>` | `/super` | ✅ 正确 |
| **Git submodule** | `/super/.git/modules/<name>` | `/super/<name>` (submodule 自身根) | ❌ **错误** |

**2026-08-25 实战案例** (PTX-EMU 子模块):

```
$ cd /workspace/project/CppTLM/external/PTX-EMU
$ git rev-parse --git-common-dir
/workspace/project/CppTLM/.git/modules/external/PTX-EMU

$ git rev-parse --show-toplevel
/workspace/project/CppTLM/external/PTX-EMU  ← 用户期望的"项目根"

$ rddf dashboard
ℹ️  not a rdd-workflow project (no /workspace/project/CppTLM/.git/modules/external/.rddf/state)
                    ↑ 错误的路径                              ↑ 真实 .rddf/state/ 实际存在于此处
```

详细审计清单见源提案 §架构依据 §2(影响 5 处 `--git-common-dir` + 6 处 `--git-dir` 用法)。

### 为什么 `--git-common-dir` 在 submodule 下失效

Git submodule 物理上把 gitdir 存放在 superproject 的 `.git/modules/<name>/`,而不是 submodule 自身的 `.git/`(`.git` 实际是个 `gitdir: ...` 引用文件)。`--git-common-dir` 在 submodule 内**透明地**穿越到 superproject 的 gitdir,丢失了"submodule 是独立 git repo"这一语义。

正确的 submodule 根获取方式是 `git rev-parse --show-toplevel`,它在 submodule 内返回 submodule 自身的工作树根,而**不**穿越到 superproject。

**架构依据**:
- ADR 不存在先例 — `--show-superproject-working-tree` flag 在项目中从未使用
- AGENTS.md §关键约定: "`main_repo_root()` 用 `git rev-parse --git-common-dir` 获取主仓库路径 (worktree 安全)" — 现有约定为 worktree 优化,需扩展
- P0-8 测试 `tests/integration/test_execute_main_root.bats`: 锁定 worktree 主 repo 契约
- 2026-07-20 `add-rddf-cli-v1` 设计选择: v1 CLI 优先 worktree 安全

### 用户语义期望调研

Submodule 用户期望两种行为之一:

| 选项 | 语义 | 用户场景 |
|------|------|---------|
| **A. submodule 当独立项目** ✅ | rddf 在 submodule 根读 `.rddf/state/`,每个 submodule 自管理 | 嵌入式、firmware、外部依赖项目(本案例 PTX-EMU) |
| B. 继承 superproject | fallback 到 superproject 的 `.rddf/state/` | 多 monorepo 工作流 |

本 ADR 选 **A**,理由:
- 用户的 `.rddf/state/` 实际存在于 submodule 根(已实证),用户期望就地使用
- Git submodule 本就是独立 git repo,语义上应是独立项目
- 200+ 处 `--show-toplevel` 已经在 submodule 内返回 submodule 根,与选项 A 一致
- 选项 B 引入新概念(`superproject_state_dir` fallback)增加复杂度

## Decision

**采用选项 A: submodule 当独立项目**。在所有项目根解析入口添加 submodule 检测层,优先级:

```
1. 检测 submodule (git rev-parse --show-superproject-working-tree)
   ├─ 非空 → 返回 git rev-parse --show-toplevel (submodule 自身根)
   └─ 空   → 走原有 worktree 处理逻辑 (main_repo_root / resolve_project_root)
```

### 影响范围

**In Scope**:
- `_lib/worktree.sh:67` `main_repo_root()` — 添加 submodule 检测优先分支
- `_lib/cli/__main__.py:39` `resolve_project_root()` — 添加 submodule 检测优先分支
- `_lib/cli/__main__.py:82` `_is_in_worktree()` — submodule 内直接返回 False(否则会错误判定为非 worktree)
- `_lib/cli/validate_cmd.py:63` — `--git-dir` → `--show-toplevel`
- `skills/execute/scripts/select_worktree.sh:52,54` — containment check 在 submodule 项目下用 `--show-toplevel`
- `install.sh:349` / `tools/archive_on_main.sh:90` / `roadmap_migrate.sh:176` / `deploy.sh:69` — 加注释说明 `--git-dir` 在 submodule 内的行为(语义仍正确)
- 新增 `tests/integration/test_submodule_root_resolution.bats` (≥ 8 case)
- 新增本 ADR-0033 + 更新 AGENTS.md / guide.md / USAGE.md 文档

**Out Scope**:
- ~200 处 `--show-toplevel` 用法(已正确,通过抽象层间接调用)
- 重写 worktree 处理逻辑(P0-8 契约保留)
- `superproject_state_dir` fallback(本决策不采用选项 B)
- 处理 git worktree 嵌套 submodule 场景(罕见,留未来)
- 现有 `--git-dir` 用法的语义修改(仅加注释)

### 备选方案

| 备选 | 理由 | 决策 |
|------|------|------|
| **A. submodule 当独立项目** ✅ | 与 200+ `--show-toplevel` 用法一致;语义最简;submodule 本是独立 git repo | **采纳** |
| B. 继承 superproject (fallback state_dir) | 支持 monorepo 工作流 | 拒绝:增加复杂度,用户期望在 submodule 自管理(已实证) |
| C. 仅文档说明,不改代码 | 0 改动 | 拒绝:用户报 `not a rdd-workflow project` 是真 bug,不是文档缺失 |
| D. 在所有 --git-dir/--git-common-dir 用法改用 --git-dir 的"绝对路径展开"形式 | 试图通过路径操作兼容 submodule | 拒绝:治标不治本;submodule 内 `--git-dir` 仍指 superproject 的 modules 路径 |

### 检测函数标准模式

**Bash** (`_lib/worktree.sh::main_repo_root()` 改造):
```bash
main_repo_root() {
  local superproject
  superproject=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
  if [ -n "$superproject" ]; then
    # Submodule: --show-toplevel returns the submodule's own working tree root
    git rev-parse --show-toplevel 2>/dev/null || pwd
    return
  fi
  # Original worktree / main-repo logic (preserved for P0-8 contract)
  local common_dir
  common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || { pwd; return; }
  case "$common_dir" in
    /*) ;;
    *) common_dir="$(pwd)/$common_dir" ;;
  esac
  case "$common_dir" in
    */.git) dirname "$common_dir" ;;
    */.git/worktrees/*) dirname "$(dirname "$common_dir")" ;;
    *) dirname "$common_dir" ;;
  esac
}
```

**Python** (`_lib/cli/__main__.py::resolve_project_root()` 改造):
```python
def resolve_project_root() -> str:
    # Submodule-aware priority: --show-toplevel wins in submodule
    try:
        r_super = subprocess.run(
            ["git", "rev-parse", "--show-superproject-working-tree"],
            capture_output=True, text=True, timeout=10,
        )
        if r_super.returncode == 0 and r_super.stdout.strip():
            r_toplevel = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if r_toplevel.returncode == 0 and r_toplevel.stdout.strip():
                return os.path.abspath(r_toplevel.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Existing worktree / main-repo logic (preserved)
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return os.getcwd()
    if r.returncode != 0:
        return os.getcwd()
    common_dir = r.stdout.strip()
    if not common_dir:
        return os.getcwd()
    if not os.path.isabs(common_dir):
        common_dir = os.path.abspath(common_dir)
    if "/.git/worktrees/" in common_dir:
        return os.path.abspath(os.path.join(common_dir, "..", "..", ".."))
    if common_dir.endswith("/.git"):
        return os.path.abspath(os.path.join(common_dir, ".."))
    return os.path.dirname(common_dir)
```

### 行为矩阵 (决策后契约)

| CWD 上下文 | `--show-superproject-working-tree` | 走哪分支 | 返回 |
|-----------|-----------------------------------|---------|------|
| 主 repo | 空 | worktree 分支 (`--git-common-dir`) | 主 repo 根 |
| Linked worktree | 空 | worktree 分支 (`--git-common-dir`) | 主 repo 根 |
| Git submodule | 非空 (superproject 根) | submodule 分支 (`--show-toplevel`) | submodule 自身根 |
| Nested submodule | 非空 (直接 superproject 根) | submodule 分支 (`--show-toplevel`) | submodule 自身根 |
| 非 git 目录 | (命令失败) | fallback | `pwd` |

## Consequences

### 正面

- **修复真实用户 bug**: PTX-EMU 用户在 submodule 内可用 rddf CLI
- **不影响 worktree 契约**: P0-8 测试继续全绿
- **不影响 superproject 工作流**: 检测到非 submodule,走原逻辑,行为零变化
- **正确处理 nested submodule**: `--show-superproject-working-tree` 返回直接 superproject,`--show-toplevel` 返回自身,自然递归
- **代码风格统一**: 与 ~200 处 `--show-toplevel` 用法一致(都返回自身工作树根)
- **新测试覆盖**: `tests/integration/test_submodule_root_resolution.bats` 锁定 submodule 行为
- **文档清晰**: AGENTS.md / guide.md / USAGE.md 明确说明 submodule 行为

### 负面 / 风险

- **引入新 flag**: `--show-superproject-working-tree` 在项目中首次使用;git 2.25+ 已支持(2019 年 release,远低于项目要求的 git 2.25+ baseline)
- **5 处 `--git-dir` 用法语义微妙**: 加注释说明,但不改逻辑(`submodule/.git/modules/<name>` 存在即 git repo 存在,语义仍正确)
- **`select_worktree.sh` containment check 行为变化**: submodule 项目下 RDDF_EXECUTION_ROOT 不再通过主 repo containment check(预期行为,但需明确错误提示)
- **下游脚本如果新增 `--git-common-dir` 而忘加 submodule 检测**: 需要在 `_lib/worktree.sh` docstring 警告;由 code review / new tests 兜底

### 兼容性

| 上下文 | 旧行为 | 新行为 | 兼容性 |
|--------|--------|--------|--------|
| 主 repo | 主 repo 根 | 主 repo 根 | ✅ 不变 |
| Worktree | 主 repo 根 | 主 repo 根 | ✅ 不变 |
| Submodule | ❌ superproject 的 `.git/modules/` 父目录 | ✅ submodule 自身根 | ✅ **修复** |
| 非 git 目录 | `pwd` | `pwd` | ✅ 不变 |

### 替代方案评估

- **选项 B (fallback superproject state)**: 引入新概念和 fallback 链路;用户期望已在 submodule 自管理;复杂度增加。**拒绝**。
- **选项 C (仅文档)**: 实际 bug 不修复,用户报告失败。**拒绝**。
- **方案 D (路径操作兼容)**: 治标不治本;`--git-dir` 仍指向 superproject。**拒绝**。

## 参考

- 源提案: [.rddf/improvements/submodule-aware-project-root.md](../.rddf/improvements/submodule-aware-project-root.md)
- Git 文档: [`git rev-parse --show-superproject-working-tree`](https://git-scm.com/docs/git-rev-parse#Documentation/git-rev-parse.txt---show-superproject-working-tree)
- 相关 ADR:
  - 暂无 — 本 ADR 是首个 submodule 主题决策
- 相关测试: `tests/integration/test_execute_main_root.bats`(P0-8 现有契约),新建 `tests/integration/test_submodule_root_resolution.bats`
- 实战证据: PTX-EMU `/workspace/project/CppTLM/external/PTX-EMU/` 2026-08-25