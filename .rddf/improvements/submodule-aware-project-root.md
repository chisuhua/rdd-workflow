# submodule-aware-project-root

**优先级**: P0 | **来源**: 用户实战 2026-08-25 — `rddf dashboard` 在 git submodule 内解析到 superproject 的 `.git/modules/<name>` 路径,显示 `not a rdd-workflow project`,即使 submodule 自身的 `.rddf/state/` 实际存在
**阶段**: v2.2 | **分类**: core-impl
**类型**: fix

> **症状**: 在 submodule 内(例如 `/workspace/project/CppTLM/external/PTX-EMU/`)执行 `rddf dashboard` / `rddf status` / `rddf init` 等任意命令,均输出:
> ```
> ℹ️  not a rdd-workflow project (no /workspace/project/CppTLM/.git/modules/external/.rddf/state)
> ```
> 而 `.rddf/state/` 实际存在于 submodule 自身的根 `/workspace/project/CppTLM/external/PTX-EMU/.rddf/state/`。
>
> **范围定位**: 本提案修复**项目根解析**对 submodule 场景的盲区,不重写现有 worktree 处理逻辑(已有 P0-8 测试锁定 worktree 主 repo 优先),也不修改 `--show-toplevel` 的 ~200 处使用(它们在 submodule 内行为正确)。

## 架构依据

### 1. Bug 实证 (2026-08-25 PTX-EMU 子模块)

在 `/workspace/project/CppTLM/external/PTX-EMU/`(git submodule)内实测 `git rev-parse`:

| Flag | 实测输出 | 期望 | 评估 |
|------|---------|------|------|
| `--show-toplevel` | `/workspace/project/CppTLM/external/PTX-EMU` | 同 | ✅ **submodule OK** |
| `--git-dir` | `/workspace/project/CppTLM/.git/modules/external/PTX-EMU` | submodule 自己的 gitdir | ❌ **指向 superproject** |
| `--git-common-dir` | `/workspace/project/CppTLM/.git/modules/external/PTX-EMU` | 同上 | ❌ **指向 superproject** |
| `--show-superproject-working-tree` | `/workspace/project/CppTLM` | superproject 根 | ✅ **submodule 检测专用** |

`_lib/cli/__main__.py::resolve_project_root()` (line 39-79) 处理逻辑:
```python
if "/.git/worktrees/" in common_dir:    # submodule 不匹配
    return ...
if common_dir.endswith("/.git"):        # submodule 不匹配(结尾是 /PTX-EMU 不是 /.git)
    return ...
# Fallback: dirname(common_dir) → /workspace/project/CppTLM/.git/modules/external
return os.path.dirname(common_dir)     # ← 错误!用户期望 submodule 自身的根
```

然后 `state_dir = project_root + ".rddf/state"` → 拼出错误路径 `…/.git/modules/external/.rddf/state`。

### 2. 受影响范围审计 (已 100% 扫描)

**A. 用 `--git-common-dir` 的位置(全部 BUGGY in submodule)**

| 文件:行 | 函数 / 用途 |
|---------|------------|
| `_lib/worktree.sh:69` | `main_repo_root()` — 所有 worktree 相关代码的根解析 |
| `_lib/cli/__main__.py:55` | `resolve_project_root()` — `rddf` CLI 入口 |
| `_lib/cli/__main__.py:92` | `_is_in_worktree()` — worktree 检测 |
| `skills/execute/scripts/select_worktree.sh:52,54` | `RDDF_EXECUTION_ROOT` containment check |

**B. 用 `--git-dir` 的位置(全部 BUGGY in submodule)**

| 文件:行 | 函数 / 用途 |
|---------|------------|
| `_lib/cli/__main__.py:98` | `_is_in_worktree()` 对比逻辑 |
| `_lib/cli/validate_cmd.py:63` | git repo 检测 |
| `install.sh:349` | target_dir 是否为 git repo |
| `tools/archive_on_main.sh:90` | 是否在 git 内 |
| `skills/roadmap/scripts/roadmap_migrate.sh:176` | 是否在 git 内 |
| `skills/spoke-system-prompt-injection/scripts/deploy.sh:69` | target 是否为 git repo |

**C. 用 `--show-toplevel` 的位置 (submodule OK / worktree NOT OK)**

约 200 处,标准化模式 `PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)`。已有 `main_repo_root()` 抽象层,worktree 兼容性问题已收敛到 `_lib/worktree.sh:67` 单点。**这些不需修改**,通过 `main_repo_root()` 间接调用即可。

**D. 用 `--show-superproject-working-tree` 的位置**

0 处 — 项目中**从未使用**此 flag。Submodule 检测通道完全缺失。

### 3. 与已有约定 / ADR 的关系

- **P0-8** (`tests/integration/test_execute_main_root.bats`): 已锁定 `_lib/worktree.sh::main_repo_root()` 在 worktree 内返回主仓库根。本提案**不破坏**该契约 — 仍用 `--git-common-dir` 处理 worktree 路径,只在 submodule 检测命中时**优先**用 `--show-toplevel`。
- **AGENTS.md §关键约定**: "`main_repo_root()` 用 `git rev-parse --git-common-dir` 获取主仓库路径 (worktree 安全)" — 本提案扩展而非颠覆该约定。
- **2026-07-20 add-rddf-cli-v1**: `--git-common-dir` 是 v1 设计选择(worktree 优先)。本提案**补全**其在 submodule 场景的盲区,保持 v1 向后兼容。
- **未来可能新建 ADR-0033 `submodule-aware-project-root-resolution`** 记录此设计选择。

### 4. 用户语义期望

用户在 submodule 内调用 rddf CLI,期望两种行为之一:

| 选项 | 语义 | 适用 |
|------|------|------|
| **A. submodule 当独立项目** ✅ 选 | rddf 在 submodule 根读 `.rddf/state/`,每个 submodule 自管理 | 嵌入式、firmware、外部依赖项目(用户现状 PTX-EMU 属此类) |
| B. 继承 superproject | rddf 把 submodule 当作 superproject 一部分,fallback 到 superproject 的 state | 多 monorepo 工作流 |

本提案选 **A**,理由:
- 用户的 `.rddf/state/` 实际存在于 submodule 根(已实证),用户希望就地使用
- Git submodule 本就是独立 git repo,语义上应是独立项目
- 200+ 处 `--show-toplevel` 已经在 submodule 内返回 submodule 根,本提案与其他代码风格一致
- 不需要为 submodule 引入新概念(`superproject_state_dir` fallback)

## 范围

### In Scope

**A. 核心辅助函数修复 (3 处)**

1. **`_lib/worktree.sh:67` `main_repo_root()`**
   - 入口检测 `--show-superproject-working-tree`
   - 非空 → submodule 模式 → 返回 `git rev-parse --show-toplevel` (submodule 自身根)
   - 空 → 保留现有 `--git-common-dir` worktree 处理逻辑

2. **`_lib/cli/__main__.py:39` `resolve_project_root()`**
   - 同样的 submodule 优先检测逻辑
   - 保留现有 worktree / main repo 分支逻辑

3. **`_lib/cli/__main__.py:82` `_is_in_worktree()`**
   - 在 submodule 内 `--git-common-dir == --git-dir`,会**错误**判定为非 worktree
   - 加 submodule 检测,submodule 内**直接**返回 False

**B. 次要入口 (2 处)**

4. **`_lib/cli/validate_cmd.py:63`** — `--git-dir` → `--show-toplevel` (验证 git repo 时用 toplevel 检测更一致)

5. **`skills/execute/scripts/select_worktree.sh:52,54`** — containment check 在 submodule 场景需用 `--show-toplevel` 对比,而非 `--git-common-dir`

**C. 文档与 ADR**

6. 新增 **`docs/adr/ADR-0033-submodule-aware-project-root-resolution.md`**
   - 记录 submodule 优先 + worktree 主 repo 保留的双模式设计
   - 引证本次 PTX-EMU 实战和审计清单

7. 更新 **`AGENTS.md`** 关键约定章节,把 submodule 行为纳入 `main_repo_root()` / `resolve_project_root()` 的契约说明

8. **`skills/guide/SKILL.md`** 与 **`USAGE.md`** 添加 1 段说明"在 git submodule 内使用 rddf"

**D. 测试**

9. 新增 **`tests/integration/test_submodule_root_resolution.bats`** (≥ 8 个 case)
   - 在 bats fixture 内创建 git repo + submodule + 各文件
   - 验证 `main_repo_root()` 在 submodule 内返回 submodule 自身根
   - 验证 `resolve_project_root()` 同上
   - 验证 `_is_in_worktree()` 在 submodule 内返回 False
   - 验证在主 repo 内行为不变(worktree 主 repo 优先契约保留)
   - 验证 `validate_cmd.py` 通过 submodule 路径执行成功
   - 验证 `select_worktree.sh` containment check 在 submodule 项目下正确判断

### Out Scope

- **不修改** ~200 处 `--show-toplevel` 用法(已正确,通过抽象层间接调用)
- **不引入** `superproject_state_dir` fallback(用户期望选项 A)
- **不重写** worktree 处理逻辑(保留 P0-8 契约)
- **不修改** `_lib/orchestrator_entry.sh` 等已 ship 的 hook script(它们没 git rev-parse)
- **不修改** `install.sh:349` / `tools/archive_on_main.sh:90` 等"git repo 存在性"检测(虽然用 `--git-dir`,但 submodule 内语义仍正确 — `submodule/.git/modules/<name>` 存在即说明在 git 内)。**仅加注释**说明此行为。
- **不处理** git worktree 嵌套 submodule 场景(罕见,留作未来提案)

## 关键场景

### 场景 1: 主用户场景 — submodule 内 `rddf dashboard` (修复目标)

- **GIVEN** 用户在 `/workspace/project/CppTLM/external/PTX-EMU/`(git submodule)
  + `.rddf/state/` 实际存在于该 submodule 根
- **WHEN** 用户运行 `rddf dashboard`
- **THEN**
  - `resolve_project_root()` 检测 `--show-superproject-working-tree` 非空
  - 返回 `git rev-parse --show-toplevel` = submodule 自身根 `/workspace/project/CppTLM/external/PTX-EMU`
  - `state_dir = <root>/.rddf/state` 存在
  - dashboard 正常渲染,显示当前 changes 状态
  - 不再输出 `not a rdd-workflow project`

### 场景 2: 主 repo / worktree 场景 (回归保护)

- **GIVEN** 用户在主 repo `/workspace/project/rdd-workflow/` 或 worktree `.rddf/wt/<name>/`
- **WHEN** 运行 `rddf dashboard`
- **THEN**
  - `--show-superproject-working-tree` 输出为空(非 submodule)
  - 走现有 `--git-common-dir` 分支
  - worktree 内返回主 repo 根(原 P0-8 契约保留)
  - 主 repo 内返回主 repo 根

### 场景 3: `_is_in_worktree()` 在 submodule 内不误判

- **GIVEN** 用户在 submodule 内
- **WHEN** `_is_in_worktree()` 被调用
- **THEN**
  - 检测 submodule → 直接返回 False
  - **不**走 `--git-common-dir == --git-dir` 对比逻辑(否则会错误判定)
  - 不打印 `running from worktree` 信息行

### 场景 4: `validate` 命令在 submodule 项目根执行

- **GIVEN** 用户在 submodule 根(非 rdd-workflow 项目也无 `.rddf/state`)
- **WHEN** 运行 `rddf validate`
- **THEN**
  - `resolve_project_root()` 修复后正确返回 submodule 根
  - `validate_cmd.py` 的 `git repo` 检查用 `--show-toplevel` → returncode 0 → 通过
  - 不再误判 `✗ git 仓库`

### 场景 5: `select_worktree.sh` containment check 在 submodule 项目下

- **GIVEN** RDDF_EXECUTION_ROOT = submodule 根, _expected_main = 主 repo 根
- **WHEN** `select_worktree.sh` containment check 运行
- **THEN**
  - submodule 的 `--show-toplevel` = RDDF_EXECUTION_ROOT ✓
  - 主 repo 的 `--show-toplevel` = _expected_main ✓
  - containment 判定: **RDDF_EXECUTION_ROOT 不在主 repo 内**(正确!submodule 是独立 repo)
  - 返回清晰的错误提示 "submodule 项目不通过主 repo containment 检查,请用 module 自身根作为 RDDF_EXECUTION_ROOT"

### 场景 6: install.sh 在 submodule 项目根执行 `bash install.sh`

- **GIVEN** install.sh 在 submodule 内被调用,`--git-dir` 返回 superproject 的 `.git/modules/<name>`
- **WHEN** install.sh 检查 `target_dir` 是否为 git repo
- **THEN**
  - `--git-dir` 返回值仍指向**已存在的目录**(superproject 的 modules)
  - `test -d "$target_dir/.git"` 也成立(因为 git 在 submodule 创建 `.git` 文件指向 modules)
  - 检测通过 → install 继续(行为合理)
  - **额外**: 加注释说明 submodule 内此检测实际验证 superproject repo 存在性

### 场景 7: superproject 工作流不破

- **GIVEN** 用户在主 repo(无 submodule 上下文)运行 rddf
- **WHEN** 任意
- **THEN**
  - `--show-superproject-working-tree` 返回空 → 不触发新分支
  - 走原 `--git-common-dir` 逻辑,行为**零变化**
  - 所有现有 P0 测试(test_execute_main_root / test_worktree_commits / test_archive_helper 等)继续通过

### 场景 8: nested submodule (submodule 内还有 submodule) — 明确边界

- **GIVEN** 用户在 nested submodule `/super/sub1/sub2/`
- **WHEN** `rddf dashboard`
- **THEN**
  - `--show-superproject-working-tree` 返回**最近一级** superproject(`/super/sub1`)
  - 当前函数检测到 non-empty → 走 submodule 分支
  - 返回 `--show-toplevel` = `/super/sub1/sub2`(**自身**根) ✅
  - **不**误用 superproject 的 superproject(`/super`)
  - 行为正确(nested case 由递归的 `--show-superproject-working-tree` 自然处理)

## 技术约束

### MUST

- 必须保留 `main_repo_root()` 在 worktree 内返回主 repo 根的 P0-8 契约(`test_execute_main_root.bats` 必须全绿)
- 必须保留 `resolve_project_root()` 在主 repo / worktree 内的现有行为
- submodule 检测必须用 `git rev-parse --show-superproject-working-tree`(标准 flag,跨 git 2.25+ / submodule-aware 系统一致)
- 所有改动必须有对应新增或已有的 bats + Python 测试覆盖
- Python 改动必须保留 type annotations,不能引入 `as any` 等绕过
- Bash 改动必须符合 POSIX sh(同 `_lib/worktree.sh` 现有风格),不引入 bashisms
- 新增 ADR-0033 必须引用本审计清单和 PTX-EMU 实战证据

### MUST NOT

- 不修改 `--show-toplevel` 已 ship 的 200+ 处用法
- 不重写 `main_repo_root()` 现有 worktree 处理分支(保留向后兼容)
- 不引入新的 Python 依赖
- 不引入 `superproject_state_dir` fallback(本提案采用选项 A)
- 不修改 iteration.json / .rddf/state/ schema
- 不在 fix 路径上引入 bash `$VAR` 字符串插值(Oracle C1 安全约束)

### SHOULD

- `main_repo_root()` 和 `resolve_project_root()` 的 submodule 检测逻辑**一致**(同样检测方法、同样的优先级)
- 在 `_lib/worktree.sh::main_repo_root()` 函数顶部新增注释,解释 submodule vs worktree 行为矩阵
- `tests/integration/test_submodule_root_resolution.bats` 复用现有 bats fixture 模式(`tests/_lib/test_helper.bash` + tmp git repo)
- 在 `--git-dir` 用法(`install.sh:349` 等 5 处)顶部加注释 `git rev-parse --git-dir; in submodule, returns superproject's .git/modules/<name>; existence check is still semantically correct`

## 验收标准

### 功能验收

- **AC-1**: 在 PTX-EMU submodule 内(`/workspace/project/CppTLM/external/PTX-EMU/`)运行 `rddf dashboard`,不再输出 `not a rdd-workflow project`,而是正常渲染 dashboard 或当前 changes(场景 1)
- **AC-2**: 在主 repo `/workspace/project/rdd-workflow/` 运行 `rddf dashboard`,行为不变(场景 2)
- **AC-3**: 在 worktree `.rddf/wt/<name>/` 运行 `rddf dashboard`,返回主 repo state,P0-8 测试全绿(场景 2)
- **AC-4**: `_is_in_worktree()` 在 submodule 内返回 False,不打印 "running from worktree" 信息行(场景 3)
- **AC-5**: `rddf validate` 在 submodule 项目根能正常执行,git repo 检测通过(场景 4)
- **AC-6**: `select_worktree.sh` containment check 在 submodule 项目下输出清晰错误(场景 5)
- **AC-7**: install.sh 在 submodule 内执行不崩,git repo 检测通过(场景 6)

### 测试覆盖

- **AC-8**: `tests/integration/test_submodule_root_resolution.bats` 至少 8 个 case,覆盖 7 个场景 + nested submodule
- **AC-9**: `tests/integration/test_execute_main_root.bats` 全绿(worktree 契约不破)
- **AC-10**: `tests/unit/test_cli_routing.py` 全绿(已有 `--git-common-dir` 单元测试)
- **AC-11**: `./test.sh --quick` 全绿(bats smoke + pytest unit)
- **AC-12**: `./test.sh --full --regression` 无新增失败(基线已知失败可放行)

### 文档 / 治理

- **AC-13**: 新增 `docs/adr/ADR-0033-submodule-aware-project-root-resolution.md`,格式符合 `ADR-0000-template.md`
- **AC-14**: `AGENTS.md` "关键约定" 章节新增 submodule 子条目,说明 `main_repo_root()` / `resolve_project_root()` 在 submodule 内的新行为
- **AC-15**: `skills/guide/SKILL.md` 或 `USAGE.md` 添加 1 段 submodule 使用说明
- **AC-16**: `_lib/worktree.sh::main_repo_root()` 顶部 docstring 更新,submodule vs worktree vs main repo 行为矩阵
- **AC-17**: 5 处 `--git-dir` 用法顶部加注释说明 submodule 行为

### 依赖 / 兼容性

- **AC-18**: 不引入新 Python / bash 依赖,git 2.25+ 已支持 `--show-superproject-working-tree`(git 2.25+ 自 2019 年 release,实际门槛远低于 rdd-workflow 已要求的 2.25+)
- **AC-19**: Python 3.11+ / bash 4.0+ 兼容(同项目 baseline)

### 实施路径

- **AC-20**: 实施分 3 个 commit,顺序:
  1. `fix(cli): submodule-aware resolve_project_root` (核心函数 + 测试)
  2. `fix(worktree): submodule-aware main_repo_root` (辅助函数 + 测试)
  3. `docs(adr): add ADR-0033 submodule-aware-project-root-resolution` (ADR + AGENTS.md + guide.md 更新)
- **AC-21**: PR 标题: `fix(submodule): resolve project root correctly inside git submodule (P0)`