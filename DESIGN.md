---
name: openspec-workflow-skills
description: "设计 OpenSpec workflow skills，将自定义命令文档转化为可执行 skill，填补现有 OpenSpec 技能链中的执行层空白"
---

# OpenSpec Workflow Skills 设计方案

> 作者: Sisyphus
> 日期: 2026-05-17
> 状态: 草稿

## 1. 背景与动机

### 1.1 现有状态

项目已安装 **OpenSpec CLI** (v1.3.1) 并在 `/workspace/project/CppHDL/` 初始化完毕。当前已有 4 个 OpenSpec 技能：

| Skill | 位置 | 阶段 |
|-------|------|------|
| `openspec-explore` | `.opencode/skills/openspec-explore/` | 探索期 |
| `openspec-propose` | `.opencode/skills/openspec-propose/` | 提案期 |
| `openspec-apply-change` | `.opencode/skills/openspec-apply-change/` | 执行期 |
| `openspec-archive-change` | `.opencode/skills/openspec-archive-change/` | 归档期 |

同时，用户设计了 **6 个自定义命令文档**（位于 `~/.config/opencode/commands/`）：

| 命令文件 | 描述 | 现有 OpenSpec 等价 |
|----------|------|-------------------|
| `opsx-plan` | 基于 change 生成 Prometheus 实施计划 | ❌ 无等价技能 |
| `work-new` | 创建 worktree 隔离环境 | ❌ 无等价技能 |
| `work-start` | 在 worktree/主分支执行 change | ⚠️ `openspec-apply-change`（但无 worktree 和计划流） |
| `work-done` | 完成 change 并归档 | ⚠️ `openspec-archive-change`（但无 merge 和 worktree 清理） |
| `work-list` | 列出 worktrees 和状态 | ❌ 无等价技能 |
| `work-status` | 查看 change 详细状态 | ❌ 无等价技能 |

### 1.2 问题分析

现有技能链存在 **关键断层**：

```
openspec-propose → ❓(opsx-plan) → ❓(work-new) → openspec-apply-change → ❓(work-list/status) → openspec-archive-change
                          ↓                ↓                                    ↓
                      Prometheus       worktree                              worktree merge
                      计划生成           隔离                                    + 清理
```

1. **无规划阶段**: `openspec-propose` 直接到 `openspec-apply-change`，缺少 Prometheus 计划生成、风险评估、任务分解
2. **无工作隔离**: `openspec-apply-change` 在主分支直接执行，无法并行处理多个 change
3. **无状态跟踪**: 缺少查看进度、检测不同步、识别问题的统一入口
4. **不完整的完成流程**: `openspec-archive-change` 仅归档，不处理 git merge、branch 删除、worktree 清理

### 1.3 目标

设计 3 个新技能，填补上述断层：

1. **`openspec-workflow-plan`** — 将 OpenSpec change 转换为 Prometheus 可执行计划（替代 `/opsx-plan`）
2. **`openspec-workflow-execute`** — 带 worktree 隔离的任务执行（整合 `/work-new` + `/work-start`）
3. **`openspec-workflow-status`** — 状态查看与问题检测（整合 `/work-list` + `/work-status`）并增强 `/work-done`

---

## 2. 架构设计

### 2.1 核心约束（方案 A）

```
┌─────────────────────────────────────────────┐
│  git worktree add 只可见已 commit 的文件     │
│                                             │
│  主分支工作目录                                │
│  ├── openspec/changes/<name>/  ← 未跟踪     │
│  │   (仅当 git commit 后，分支才包含这些文件)  │
│  └── ...                                     │
│                                             │
│  .zcf/<name>-wt/ (worktree)                 │
│  └── openspec/changes/<name>/               │
│      ← 只可见目标分支 openspec/<name>         │
│        所指向 commit 中包含的文件              │
└─────────────────────────────────────────────┘

结论：创建 worktree 前，change artifacts 必须已
commit 到 openspec/<name> 分支。
```

### 2.2 完整工作流（Commit Gate 模型）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      OpenSpec Workflow Pipeline                          │
│                                                                           │
│  ┌──────────┐   ┌───────────────────────┐                                │
│  │ openspec │   │ openspec-workflow-    │                                │
│  │ -explore  │→  │ propose (本阶段新增)  │                                │
│  │          │   │ 分析文档/代码差距      │                                │
│  └──────────┘   │ 生成建议 → 用户选择    │                                │
│                 │ 调用 openspec-propose  │                                │
│                 └───────────┬───────────┘                                │
│                             ↓                                            │
│              ╔══════════════════════════╗                                │
│              ║  COMMIT GATE (v2 前置)   ║                                │
│              ║  git add + git commit    ║                                │
│              ║  openspec/changes/<name> ║                                │
│              ╚══════════════════════════╝                                │
│                             ↓                                            │
│  ┌─────────────────────────────────────────────┐                        │
│  │  openspec-workflow-plan                      │                        │
│  │  ├ Phase 0: 发现候选 change（可选模式）      │                        │
│  │  │   扫描所有无 worktree 的 change → 推荐    │                        │
│  │  ├ Phase 1: 用户选择（发现模式时）           │                        │
│  │  ├ Phase 2:                                   │                        │
│  │  │  ├ Step 1: COMMIT GATE + 验证前置条件     │                        │
│  │  │  ├ Step 2: 检查是否已有 worktree          │                        │
│  │  │  ├ Step 3: git branch + git worktree add  │                        │
│  │  │  ├ Step 4: 切换到 worktree 读取 artifacts │                        │
│  │  │  ├ Step 5: Prometheus 生成计划            │                        │
│  │  │  └ Step 6: commit plan 到 worktree 分支    │                        │
│  └─────────────────────┬───────────────────────┘                        │
│                        ↓                                                 │
│  ┌─────────────────────────────────────────────┐                        │
│  │  openspec-workflow-execute                   │                        │
│  │  ├ 在 worktree 内（自动检测分支）            │                        │
│  │  ├ 基于 .sisyphus/plans/ 执行                │                        │
│  │  ├ 每个 Work Unit → awk 更新 tasks.md       │                        │
│  │  └ build 验证（独立 build 目录 + ccache）    │                        │
│  └─────────────────────┬───────────────────────┘                        │
│                        ↓                                                 │
│  ┌─────────────────────────────────────────────┐                        │
│  │  openspec-workflow-status                    │                        │
│  │  ├ Mode A: 全局概览                          │                        │
│  │  ├ Mode B: 检测 + 修复（awk 同步）          │                        │
│  │  └ Mode C: git checkout main → merge → archive → cleanup │          │
│  └─────────────────────────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────────────┘
```

> **v2 变更对照**（与 skyline 图中原始设计的关键区别）：
>
> | 维度 | v1（图中设计） | v2（实现修正） | v3（增强） |
> |------|---------------|---------------|-----------|
> | Plan 位置 | main 分支上生成，进 COMMIT GATE | worktree 内生成，不进 main | — |
> | Worktree 时机 | Plan 之后 | Plan 之前 | — |
> | 执行依据 | `openspec instructions --json` | `.sisyphus/plans/<name>.md` | — |
> | 串行模式 | 无 worktree 直接执行 | 已废弃——所有执行在 worktree 内 | — |
> | Plan 输入 | 必须传 change name | 必须传 change name | **可选**：发现模式自动扫描候选 |

### 2.2 技能矩阵

| # | Skill | 输入 | 输出 | 关键工具调用 |
|---|-------|------|------|-------------|
| 0 | `openspec-workflow-propose` | 无（自动扫描） | `proposal-suggestions.md` + change artifacts | 读取 ADR/架构/TODO，用户交互，openspec CLI |
| 1 | `openspec-workflow-plan` | change name | `.sisyphus/plans/<name>.md` | `openspec instructions`, Prometheus agent |
| 2 | `openspec-workflow-execute` | change name | 任务执行状态 | `git worktree`, `openspec instructions`, build/test |
| 3 | `openspec-workflow-status` | change name (可选) | 状态报告 | `git worktree list`, `openspec status/instr`, `jq` |

### 2.3 与现有技能的关系

```
┌──────────────────────────────────────────┐
│          新技能（此设计方案）              │
│                                          │
│  openspec-workflow-plan                  │
│  openspec-workflow-execute               │
│  openspec-workflow-status                │
└──────────────────────────────────────────┘
            ↕ 协作 ↕
┌──────────────────────────────────────────┐
│        现有 OpenSpec 技能                 │
│                                          │
│  openspec-propose    (create)            │
│  openspec-apply-change (implement)       │
│  openspec-archive-change (archive)       │
│  openspec-explore     (think)            │
└──────────────────────────────────────────┘
            ↕ 依赖 ↕
┌──────────────────────────────────────────┐
│       Superpowers 技能                    │
│                                          │
│  brainstorming       (创意)              │
│  writing-plans       (计划编写)           │
│  subagent-driven-dev (并行执行)           │
│  verification-before-completion (验证)    │
│  using-git-worktrees (git worktree)      │
└──────────────────────────────────────────┘
```

---

## 3. 技能设计

### 3.1 Skill: `openspec-workflow-plan`

**目的**: 将 OpenSpec change 的 artifacts（proposal/specs/design/tasks）转化为 Prometheus 可执行的实施计划。

**触发方式**: `skill_use("openspec-workflow-plan")` + 用户提供 change name

**输入**:
- `openspec status --change <name> --json` → schema、progress、state
- `openspec instructions apply --change <name> --json` → contextFiles、tasks
- 对应 contextFiles 路径下的 artifacts

**输出**:
- `.sisyphus/plans/<change-name>.md` — Prometheus 格式的实施计划

**步骤**:

1. **验证 change 状态**
   ```bash
   openspec status --change "<name>" --json
   ```
   - `state: "blocked"` → 提示补全 artifacts，终止
   - `state: "all_done"` → 提示已完成，建议归档
   - `state: "ready"` → 继续

2. **获取上下文**
   ```bash
   APPLY=$(openspec instructions apply --change "<name>" --json)
   contextFiles=$(echo "$APPLY" | jq -r '.contextFiles[]')
   ```
   读取所有 contextFiles：proposal.md、specs/*.md、design.md、tasks.md

3. **生成 Prometheus 计划**
   - 将 artifacts 内容 + AGENTS.md 规范 + tasks 传递给 Prometheus agent
   - Prometheus 生成 `.sisyphus/plans/<name>.md`
   - 格式包含：Scope (IN/OUT)、Dependency Graph、Work Units、QA Scenarios

4. **COMMIT GATE —— 提交 change artifacts + 计划文件（强制）**

    这是创建 worktree 的前提条件。必须将以下文件全部提交到当前分支：

    ```bash
    # [脏检测] 先检查有无未提交修改
    if [ -n "$(git status --porcelain openspec/changes/<name>/)" ]; then
        echo "❌ openspec/changes/<name>/ 有未提交修改，请先 commit"
        exit 1
    fi

    # 确认所有 change artifacts 已存在
    test -f openspec/changes/<name>/proposal.md
    test -f openspec/changes/<name>/tasks.md

    # 提交 change artifacts + 计划文件
    git add openspec/changes/<name>/
    git add .sisyphus/plans/<name>.md
    git commit -m "plan: <name> change artifacts + 实施计划"
    ```

   ⚠️ **为什么必须 commit？**
   `git worktree add` 本质是 checkout 分支的 commit 快照。
   只有已 commit 的文件才会出现在新 worktree 中。
   未跟踪的 `openspec/changes/<name>/` 不会跨 worktree 共享。

   ⚠️ **注意：仅 git add 不够，必须 git commit**。
   `git add` 只是 stage 文件到索引，文件尚未进入分支历史。
   `git show HEAD:openspec/changes/<name>/.openspec.yaml` 在仅 staged 时**也会失败**。
   如果 COMMIT GATE 检测不过，排除方法：
   ```bash
   # 检测是否已 staged（add 了但没 commit）
   if git diff --cached --name-only | grep -q "openspec/changes/<name>"; then
       echo "提示: artifacts 已 staged 但未 commit。运行 git commit 后再试"
   fi
   ```

5. **输出提交结果**
    ```
    ✅ 已提交: <commit-hash>
    Change: <name>
    计划文件: .sisyphus/plans/<name>.md
    Artifacts: openspec/changes/<name>/

    下一步建议:
    - 进入 worktree 后执行: `skill_use("openspec-workflow-execute")`
    - 具体步骤: `cd .zcf/<name>-wt` → `skill_use("openspec-workflow-execute")`
    ```

**界面**: 无显式 CLI 调用，通过 AI agent 的 Prometheus 子代理生成

**Guardrails**:
- ⛔ state=blocked → 不生成计划，提示补全
- ⛔ state=all_done → 不生成计划，提示归档
- ⛔ tasks 为空 → 提示需先完善 tasks.md

**Rollback**:
- **commit 被 git hook 拒绝**（lint/format 检查失败）→ 修复问题后重新 commit，无需额外操作
- **Prometheus 生成计划中途失败** → 工作目录无变化，直接重试即可
- **已 commit 但用户不满意** → `git reset --soft HEAD~1` 撤回 commit，保留文件内容重新修改

### 3.2 Skill: `openspec-workflow-execute`

**目的**: 在 worktree 隔离环境中执行 OpenSpec change 的计划任务。

> ~~串行模式~~ 已废弃。v2 corrigendum 确认所有执行必须通过 worktree 隔离。详见下方串行模式废弃说明。

**触发方式**: `skill_use("openspec-workflow-execute")`

**与 `openspec-apply-change` 的关系**：

`openspec-workflow-execute` 是 `openspec-apply-change` 的**升级替代**。关键区别：

| 对比项 | `openspec-apply-change`（旧） | `openspec-workflow-execute`（新） |
|--------|------------------------------|----------------------------------|
| 计划驱动 | ❌ 直接读 tasks.md | ✅ 依赖 Prometheus 计划文件 |
| worktree 隔离 | ❌ 不支持 | ✅ 并行模式隔离开发 |
| 进度自动 commit | ❌ 不自动 | ✅ 并行模式每步自动 commit |
| 前置 COMMIT GATE | ❌ 无 | ✅ 强制执行 |
| 状态检测 | ❌ 无 | ✅ 内置过期检测 |

> 在 `openspec-workflow-execute` 就绪后，`openspec-apply-change` 应视为 **deprecated**。如果用户仍使用 `openspec-apply-change` 完成任务，再用 `openspec-workflow-status` 检查时可能检测到 tasks.md 与 CLI 进度不同步——此时只需同步 tasks.md 即可。

**两种模式**（串行模式已废弃，保留文档仅用于参考）：

| 模式 | 适用场景 | 工作目录 | 是否需要参数 |
|------|---------|---------|-------------|
| ~~串行 (serial)~~ | ~~已废弃~~ | ~~主分支~~ | ~~—~~ |
| **并行 (parallel)** | 唯一支持模式 —— 多 change 并行开发 | worktree | 从 branch 自动识别 |

> **v2 corrigendum**: 串行模式已从所有技能中移除。所有执行必须通过 worktree 隔离环境。
> 以下串行模式流程保留仅用于历史参考，实际已被移除。

**模式识别**:

```bash
CURRENT=$(git branch --show-current 2>/dev/null || echo "")
if echo "$CURRENT" | grep -q '^openspec/'; then
    CHANGE_NAME=$(echo "$CURRENT" | sed 's/^openspec\///')
else
    echo "❌ 当前不在 worktree 内（branch: $CURRENT）"
    echo "请在 worktree 内执行: cd .zcf/<name>-wt"
    exit 1
fi
```



> ⚠️ **串行模式已废弃**。以下内容保留仅用于历史参考。
> 实际技能中已完全移除串行模式，所有执行必须在 worktree 内。

#### 串行模式流程（已废弃）

1. **验证前置条件**
   - change 存在（`openspec status --change "<name>" --json`）
   - 计划文件存在：
     ```bash
     test -f .sisyphus/plans/<name>.md || {
       echo "❌ 计划文件不存在: .sisyphus/plans/<name>.md"
       echo "请先执行 openspec-workflow-plan 生成计划"
       exit 1
     }
     ```
   - 验证计划未过期（tasks.md 不比计划文件新）：
     ```bash
     PLAN_MTIME=$(stat -c %Y .sisyphus/plans/<name>.md 2>/dev/null || echo 0)
     TASKS_MTIME=$(stat -c %Y openspec/changes/<name>/tasks.md 2>/dev/null || echo 0)
     if [ "$TASKS_MTIME" -gt "$PLAN_MTIME" ]; then
         echo "⚠️ tasks.md 比计划文件新，计划可能已过期"
         echo "建议重新执行 openspec-workflow-plan 刷新"
         # 不阻塞，仅警告
     fi
     ```

2. **获取任务列表**
   ```bash
   openspec instructions apply --change "<name>" --json
   ```
   - 跳过已完成任务
   - 按计划顺序执行

3. **执行任务循环**
   - 读取任务描述和代码变更要求
   - 实现代码变更（遵循 AGENTS.md 规范）
   - 更新 tasks.md: `- [ ]` → `- [x]`
   - 验证: `lsp_diagnostics` → `cmake --build` → `ctest`

4. **任务完成后**
   - 显示 `COMPLETE/TOTAL` 进度
   - 如全部完成 → 建议执行 `openspec-archive-change` 或 workflow-status

#### 并行模式流程

1. **COMMIT GATE 验证 —— change artifacts 必须已提交**

   ```bash
   # 检查 openspec/changes/<name> 是否存在于目标分支
   git show openspec/<name>:openspec/changes/<name>/.openspec.yaml > /dev/null 2>&1
   if [ $? -ne 0 ]; then
       echo "❌ Change artifacts 未在分支 openspec/<name> 中"
       echo ""
       echo "当前工作目录有以下文件（未提交）："
       ls -la openspec/changes/<name>/ 2>/dev/null || echo "(空)"
       echo ""
       echo "必须先执行 openspec-workflow-plan，确保以下文件已 commit："
       echo "  - openspec/changes/<name>/*"
       echo "  - .sisyphus/plans/<name>.md"
       exit 1
   fi

   # 确认计划文件也存在
   git show openspec/<name>:.sisyphus/plans/<name>.md > /dev/null 2>&1
   if [ $? -ne 0 ]; then
       echo "❌ 计划文件未在分支 openspec/<name> 中"
       echo "请先执行 openspec-workflow-plan"
       exit 1
   fi
   ```

   ⚠️ 这是**核心约束**。`git worktree add` 只 checkout 已 commit 的内容，未提交的 `openspec/changes/<name>/` 在 worktree 中不可见。

2. **创建 worktree**

   ```bash
   # 前置检查：必须在 main 分支执行
   # 从 main 分叉确保 openspec/<name> 不会继承非 main 分支的变更历史
   if [ "$(git branch --show-current)" != "main" ] && [ "$(git branch --show-current)" != "master" ]; then
       echo "❌ 创建 worktree 必须在 main/master 分支执行"
       echo "当前分支: $(git branch --show-current)"
       echo ""
       echo "请先切换到 main: git checkout main"
       echo "（plan 的 commit 可通过 cherry-pick 移植：git cherry-pick <plan-commit-hash>）"
       exit 1
   fi

    # 若 branch 还不存在（首次），从 main 创建
    git show-ref --verify refs/heads/openspec/<name> > /dev/null 2>&1 || \
        git branch openspec/<name> main

    # 检查 worktree 目录冲突
    if [ -d ".zcf/<name>-wt" ]; then
        if git worktree list | grep -q ".zcf/<name>-wt"; then
            echo "⚠️  Worktree 目录已存在且已注册，直接使用"
        else
            echo "❌ 目录 .zcf/<name>-wt 已存在但未注册为 worktree"
            echo "请手动清理：rm -rf .zcf/<name>-wt"
            exit 1
        fi
    else
        # 创建 worktree
        git worktree add .zcf/<name>-wt openspec/<name>
    fi
   cd .zcf/<name>-wt
   ```

   > ⚠️ **关于 plan 阶段不在 main 分支的特殊情况**：
   > 如果 plan 阶段的 commit 发生在非 main 分支（如 `hotfix`），worktree 从 `main` 创建后**不会包含这些 commit**。
   > 处理方式：
   > 1. 切回 plan 所在分支，`git log --oneline` 找到 plan 的 commit-hash
   > 2. 切回 main，`git cherry-pick <plan-commit-hash>` 移植 plan commit
   > 3. 再执行本流程

3. **执行任务循环**（注意构建目录隔离）

   > ⚠️ **worktree 构建目录隔离**：
   > 每个 worktree 必须使用独立的 build 目录，避免多个 worktree 共享同一个 `build/` 导致构建互相覆盖：
   > ```bash
   > # 在 worktree 内首次构建时
   > cmake -B build-<name> -S .
   > cmake --build build-<name> -j$(nproc)
   > 
   > # 构建别名简化
   > alias build-<name>='cmake --build build-<name> -j$(nproc)'
   > ```

4. **提交进度**
   ```bash
   cd .zcf/<name>-wt
   git add -A
   git commit -m "progress: <name> - N/M tasks"
   ```

**Guardrails**:
- ⛔ **COMMIT GATE 强制执行**: worktree 创建前必须验证 `openspec/changes/<name>` 和 `.sisyphus/plans/<name>.md` 已存在于目标分支。验证方式: `git show openspec/<name>:路径 > /dev/null`
- ⛔ 不能在 worktree 内再创建 worktree
- ⛔ 无计划文件 → 提示先执行 `openspec-workflow-plan`
- ⛔ change 不存在 → 提示先创建
- ✅ worktree 模式默认自动 commit 保存进度

**Rollback**:
- **worktree 创建失败**（分支已存在等）→ `git worktree prune` 清理残留锁文件，修复后重试
- **worktree 被意外删除**（`rm -rf .zcf/<name>-wt`）→ git 记录仍保留，`git worktree list` 仍能看到已删除的 worktree。清理方式：`git worktree prune`。worktree 内未提交的更改**永久丢失**
- **任务执行中途中断**（用户取消/网络超时）→ 已完成的 `tasks.md` 更新（`- [ ]` → `- [x]`）保留，下次从断点恢复。`openspec instructions apply` 会自动跳过 `done=true` 的任务
- **worktree 内 commit 被 hook 拒绝** → 在 worktree 内修复后重试 commit，不影响主分支
- **worktree 内用户想放弃** → `git checkout .` 丢弃未提交更改（注意：tasks.md 的 `- [x]` 标记也会丢失，需手动恢复）

### 3.3 Skill: `openspec-workflow-status`

**目的**: 统一视图查看所有 change/worktree 的状态，检测问题并给出建议。整合 work-list + work-status + work-done 检查功能。

**触发方式**: `skill_use("openspec-workflow-status")`

**三种运行模式**:

#### 模式 A: 全局概览（无参数）

```bash
# 列出 worktrees
git worktree list

# 列出 active changes
openspec list --json

# 获取每个 change 的进度
for change in $(openspec list --json | jq -r '.[]'); do
    openspec instructions apply --change "$change" --json | jq '{name: "$change", progress}'
done
```

输出格式：
```
## OpenSpec 工作台

### Worktrees
┌──────────────┬──────────────────────────────┬───────────────────┬────────┐
│ Change       │ Path                         │ Branch            │ Status │
├──────────────┼──────────────────────────────┼───────────────────┼────────┤
│ add-axi4-dma │ .zcf/add-axi4-dma-wt         │ openspec/add-...  │ 4/7    │
└──────────────┴──────────────────────────────┴───────────────────┴────────┘

### Active Changes
├── add-axi4-dma    (4/7) - 执行中
├── bug-spi-fix     (0/3) - 未开始
└── refactor-core   (✓)   - 已完成，待归档

### 建议
- /work-start add-axi4-dma  → 继续执行
- /work-start bug-spi-fix   → 开始新任务
- /opsx-archive refactor-core → 归档已完成 change
```

#### 模式 B: 单 change 详情（有参数）

1. **获取数据**
   ```bash
   STATUS=$(openspec status --change "<name>" --json)
   APPLY=$(openspec instructions apply --change "<name>" --json)
   ```

2. **检测问题**
   - **状态不同步**: `openspec progress.complete` vs `tasks.md` 实际完成数
   - **未提交更改**: worktree 有 unstaged 文件
   - **计划过期**: tasks.md 比 `.sisyphus/plans/<name>.md` 新

##### 不同步修复指引

检测到不同步时，**不需要重新执行 plan**。`openspec instructions apply` 的 progress 直接来源于 tasks.md 的 `- [x]` 标记计数。修复方法：

```bash
# 1. 确认实际完成的任务
grep "\- \[x\]" openspec/changes/<name>/tasks.md

# 2. 如果某些已完成任务在 tasks.md 中仍是 - [ ]，手动标记
sed -i 's/- \[ \] 实现数据传输/- [x] 实现数据传输/' openspec/changes/<name>/tasks.md

# 3. 重新检测——CLI 进度会自动同步（它直接读 tasks.md）
echo "✅ 同步完成。重新运行 openspec-workflow-status 确认"
```

> ⚠️ **不要重新执行 openspec-workflow-plan 来解决同步问题**。那会通过 Prometheus 重新生成 `.sisyphus/plans/<name>.md`，覆盖原有的任务分解细节、风险标注和 QA 场景。只需同步 tasks.md 即可。

3. **输出报告**
   ```
   ## Change: <name>
   Progress: 4/7 (57%)
   State: ready
   
   ⚠️ 检测到 1 个问题:
   - 状态不同步: CLI 报告 4/7, tasks.md 实际 3/7
   
   ### 已完成
   - [x] 实现 AXI4 Lite 接口
   - [x] 添加 DMA 控制器
   - [x] 实现内存映射
   - [x] 添加中断支持 (已实现但未更新 tasks.md)
   
   ### 剩余
   - [ ] 实现数据传输
   - [ ] 添加错误处理
   - [ ] 编写测试用例
   ```

#### 模式 C: 完成检查 + 归档（/work-done 等价）

以下检测适用于所有 change。如果 worktree 中全部任务已完成，提示用户执行 `openspec-archive-change` 或 `openspec-workflow-status` 模式 C 归档。

在并行模式中，完整流程如下：

```bash
# 1. 检查 worktree 目录是否还存在
if [ ! -d .zcf/<name>-wt ]; then
    echo "⚠️ Worktree 目录已不存在，跳过清理"
    git worktree prune
fi

# 2. 检查 worktree 有未提交更改
cd .zcf/<name>-wt
git status --porcelain
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Worktree 有未提交的更改"
    git status --short
    echo ""
    echo "请先 commit 或 stash："
    echo "  git add -A && git commit -m 'WIP: <name>'"
    echo "  或 git stash"
    exit 1
fi

# 3. 检查 divergent（worktree branch 是否落后 main）
cd .zcf/<name>-wt
git fetch origin main 2>/dev/null || true  # 获取远程 main 最新状态
MERGE_BASE=$(git merge-base openspec/<name> main)
MAIN_TIP=$(git rev-parse main)
if [ "$MERGE_BASE" != "$MAIN_TIP" ]; then
    echo "⚠️ openspec/<name> 落后于 main"
    echo "  创建 worktree 后 main 有新的 commit"
    echo ""
    echo "选项："
    echo "  1. rebase: git rebase main（推荐，线性历史）"
    echo "  2. merge: git merge main（保留分支拓扑）"
    echo "  3. 无视 divergence，直接 merge 到 main"
    echo ""
    # 用户选择后继续。rebase 后重新验证 build 通过
fi

# 4. 切换到 main 并 merge（--no-ff 保留分支历史）
cd /workspace/project/CppHDL   # 回到主仓库
git checkout main
git merge --no-ff openspec/<name> -m "change: <name> 合并到 main"
# --no-ff 强制创建 merge commit，保留 change 分支的历史线索

# 5. 处理 merge 冲突
if [ $? -ne 0 ]; then
    echo "⚠️ 合并冲突，请手动解决"
    echo "  git status          # 查看冲突文件"
    echo "  git add <resolved>  # 标记已解决"
    echo "  git commit          # 完成 merge"
    echo ""
    echo "解决后继续："
    echo "  openspec archive <name>"
    echo "  git branch -d openspec/<name>"
    echo "  git worktree remove .zcf/<name>-wt"
    exit 1
fi

# 6. 归档 change（CLI 自动处理）
# 基础设施/工具链/纯文档变更加 --skip-specs
openspec archive <name>

# 7. 清理
git branch -d openspec/<name>
git worktree remove .zcf/<name>-wt
```

> ⚠️ **注意**：整个流程可行的前提是 **COMMIT GATE** 已在 plan 阶段正确执行——即 `openspec/changes/<name>/` 和 `.sisyphus/plans/<name>.md` 已在 `openspec/<name>` 分支中。如果 plan 阶段未 commit 就直接创建了 worktree，worktree 中将缺少这些文件，merge 到 main 时也会丢失。

##### 部分完成处理

如果 `openspec status --json` 显示 `progress.complete < progress.total`，用户有三个选择：

| 选项 | 操作 | 后果 |
|------|------|------|
| **继续执行** | 不执行任何 cleanup，保留 worktree | 用 `/work-start` 继续 |
| **强行归档** | `openspec archive <name>` + 删除 branch + 清理 worktree | 未完成任务丢失，不可恢复 |
| **仅清理 worktree** | 只执行 `git worktree remove`，保留 branch 和 commit | 可重新创建 worktree 继续 |

必须让用户明确选择，默认选项为"继续执行"。

**Guardrails**:
- ⛔ 未提交更改时不执行 merge（要求先 commit/stash）
- ⛔ 合并冲突时终止，提示手动解决后重试
- ⛔ 部分完成时不能用 `/work-done` 全流程（需用户确认是否强力归档）

**Rollback**:
- **merge 冲突** → `git merge --abort` 恢复到 merge 前状态，worktree 和 branch 不变
- **archive 失败**（CLI 报错）→ 不执行 branch 删除和 worktree 清理，重试 archive 或手动处理
- **merge 后发现错误** → `git revert MERGE_HEAD` 在主分支上撤销合并（archive 不可逆，但 git revert 可安全撤销代码变更）
- **用户取消归档** → 不执行任何 cleanup 操作，worktree 和 branch 保持不变，可继续用 `/work-start` 执行

---

## 4. 文件结构

```
/workspace/project/CppHDL/.opencode/skills/
├── openspec-explore/            ← 已存在
│   └── SKILL.md
├── openspec-propose/           ← 已存在
│   └── SKILL.md
├── openspec-apply-change/      ← 已存在
│   └── SKILL.md
├── openspec-archive-change/    ← 已存在
│   └── SKILL.md
├── openspec-workflow-plan/     ← 新建
│   ├── SKILL.md
│   └── scripts/                ← 辅助脚本（可选）
│       └── parse-tasks.sh
├── openspec-workflow-execute/  ← 新建
│   ├── SKILL.md
│   └── scripts/
│       ├── create-worktree.sh
│       └── check-prerequisites.sh
└── openspec-workflow-status/   ← 新建
    ├── SKILL.md
    └── scripts/
        ├── list-all.sh
        └── check-sync.sh
```

同时，现有的命令文档从：
```
/home/ubuntu/.config/opencode/commands/
├── opsx-plan         → 替换为 skill openspec-workflow-plan
├── work-new          → 合并到 skill openspec-workflow-execute
├── work-start        → 合并到 skill openspec-workflow-execute
├── work-done         → 合并到 skill openspec-workflow-status（模式 C）
├── work-list         → 合并到 skill openspec-workflow-status（模式 A）
└── work-status       → 合并到 skill openspec-workflow-status（模式 B）
```

---

## 5. 依赖分析

| 依赖 | 必需程度 | 说明 |
|------|---------|------|
| `openspec` CLI v1.3.1+ | 必需 | 所有操作的基础 |
| `git` (worktree 支持) | 必需 | worktree 隔离模式 |
| `jq` | **必需** | JSON 解析。如不可用，用 Python fallback: `python3 -c "import json,sys; d=json.load(sys.stdin); ..."` |
| `cmake` / `ctest` | 项目相关 | CppHDL 构建验证 |
| Prometheus agent | 必需（opsx-plan） | 生成实施计划 |
| superpowers/writing-plans | 参考 | 计划编写模式 |
| superpowers/using-git-worktrees | 参考 | worktree 最佳实践 |

> **jq fallback 示例**:
> ```bash
> # jq 版本
> openspec instructions apply --change "<name>" --json | jq -r '.state'
>
> # 等价的 Python fallback（无 jq 时使用）
> openspec instructions apply --change "<name>" --json | python3 -c "
> import json,sys
> d = json.load(sys.stdin)
> print(d.get('state', 'unknown'))
> "
> ```

---

## 6. 实现计划

### Phase 1: 创建 Skill 骨架（3 个 SKILL.md）
| 任务 | 文件 | 估算工时 |
|------|------|---------|
| 编写 `openspec-workflow-plan` SKILL.md | `.opencode/skills/openspec-workflow-plan/SKILL.md` | 2-3 小时 |
| 编写 `openspec-workflow-execute` SKILL.md | `.opencode/skills/openspec-workflow-execute/SKILL.md` | 4-6 小时 |
| 编写 `openspec-workflow-status` SKILL.md | `.opencode/skills/openspec-workflow-status/SKILL.md` | 3-4 小时 |

### Phase 2: 辅助脚本（可选）
| 任务 | 说明 |
|------|------|
| `create-worktree.sh` | 封装 git worktree 创建逻辑 |
| `check-sync.sh` | 检测 tasks.md 与 CLI 的不同步 |
| `list-all.sh` | 格式化输出所有 worktree + change 状态 |

### Phase 3: 集成测试
| 任务 | 说明 |
|------|------|
| 创建测试 change | 用 `openspec new change test-workflow` |
| 验证完整链路 | propose → plan → execute → status → archive |
| 验证异常路径 | blocked state、冲突、不同步 |

### Phase 4: 文档
| 任务 | 说明 |
|------|------|
| 更新 AGENTS.md | 记录新技能和命令映射 |
| 更新 docs/superpowers/usage-guide.md | 使用教程 |
| 归档旧 commands/ 文档 | 标记为已迁移 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **COMMIT GATE 被跳过**：用户未 commit 就创建 worktree | **高** | **极高** | worktree 模式入口处强制检测 `git show openspec/<name>:openspec/changes/<name>/.openspec.yaml` |
| `openspec instructions` JSON 格式变化 | 中 | 高 | 技能中尽量用 jq 兼容性查询，定期验证 |
| worktree 冲突（分支已存在） | 低 | 中 | skill 中检测并优雅处理 |
| 用户期望 slash command 而非 skill_use | 中 | 低 | 在 AGENTS.md 或 README 中说明映射关系 |
| Prometheus 计划生成质量不稳定 | 中 | 中 | skill 中加入检查点，用户审核后再执行 |
| 多个技能间状态耦合 | 低 | 高 | 每种技能独立检测状态，不依赖前置技能的执行结果 |

---

## 8. 验收标准

- [ ] `openspec-workflow-plan` 能从 OpenSpec change 生成 `.sisyphus/plans/<name>.md`
- [ ] `openspec-workflow-plan` 提交 change artifacts + 计划文件到当前分支（COMMIT GATE）
- [ ] `openspec-workflow-execute` 并行模式入口强制验证 COMMIT GATE（`git show` 检测）
- [ ] 绕过 COMMIT GATE 时（artifacts 未提交）→ 明确报错并提示先执行 `openspec-workflow-plan`
- [ ] `openspec-workflow-execute` 能创建 worktree 并执行任务
- [ ] 验证 `openspec-workflow-execute` 能否正确识别当前 worktree
- [ ] `openspec-workflow-status` 能列出所有 worktree + change 状态
- [ ] `openspec-workflow-status` 能检测 tasks.md 与 CLI 的不同步
- [ ] `openspec-workflow-status` 模式 C 能执行 merge + archive + cleanup
- [ ] 所有 3 个技能可通过 `skill_use("openspec-workflow-*")` 加载
- [ ] 所有 3 个技能在 CppHDL 项目上通过端到端验证

---

## 9. 附录

### 9.1 旧命令 → 新技能映射表

| 旧命令 | 新技能 | 映射方式 |
|--------|--------|---------|
| `/opsx-plan <name>` | `openspec-workflow-plan` | `skill_use("openspec-workflow-plan")` + AI 读取 change name |
| `/work-new <name>` + `/work-start` | `openspec-workflow-execute` | `skill_use("openspec-workflow-execute")` |
| `/work-done <name>` | `openspec-workflow-status`（模式 C） | `skill_use("openspec-workflow-status")` + AI 判断执行模式 |
| `/work-list` | `openspec-workflow-status`（模式 A） | `skill_use("openspec-workflow-status")` + 无参数 |
| `/work-status <name>` | `openspec-workflow-status`（模式 B） | `skill_use("openspec-workflow-status")` + AI 读取 change name |

### 9.2 COMMIT GATE 数据流参考

```
                          主分支工作目录                  openspec/<name> 分支
                          ──────────────                  ──────────────────
openspec new change       openspec/changes/<name>/        ❌ 不存在（未跟踪）
                          （仅在工作目录中）

openspec-workflow-plan    openspec/changes/<name>/        ❌ 不存在（未跟踪）
（生成计划前）              .sisyphus/plans/<name>.md
                          （仅在工作目录中）

↓ git add + git commit ↓  ↓──────────────────────────→   ✅ openspec/changes/<name>/
                                                          ✅ .sisyphus/plans/<name>.md

git branch openspec/<name>                                ✅ 同 main（包含 change + plan）
git worktree add .zcf/..                                  ✅ 新 worktree 可见所有文件
```

### 9.3 相关文件索引

| 文件 | 说明 |
|------|------|
| `/workspace/project/CppHDL/.opencode/skills/openspec-workflow-plan/SKILL.md` | 计划技能 |
| `/workspace/project/CppHDL/.opencode/skills/openspec-workflow-execute/SKILL.md` | 执行技能 |
| `/workspace/project/CppHDL/.opencode/skills/openspec-workflow-status/SKILL.md` | 状态技能 |
| `/home/ubuntu/.config/opencode/commands/opsx-plan` | 旧命令文档（待归档） |
| `/home/ubuntu/.config/opencode/commands/work-new` | 旧命令文档（待归档） |
| `/home/ubuntu/.config/opencode/commands/work-start` | 旧命令文档（待归档） |
| `/home/ubuntu/.config/opencode/commands/work-done` | 旧命令文档（待归档） |
| `/home/ubuntu/.config/opencode/commands/work-list` | 旧命令文档（待归档） |
| `/home/ubuntu/.config/opencode/commands/work-status` | 旧命令文档（待归档） |
| `/workspace/project/CppHDL/docs/superpowers/specs/2026-05-17-openspec-workflow-skills-design.md` | 本文档 |
