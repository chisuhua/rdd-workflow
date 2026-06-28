# OpenSpec 工作流技能使用指南

> 基于 `guide` 推荐器（spec-side 调 `guide-spec`，ship-side 调 `guide-ship`），覆盖从提案到归档的完整生命周期。
> 支持多 change 并行执行，可分离到不同终端同时运行。
> 当前版本: **v2.0.0-beta**（三阶段架构 arch → plan → ship + Loop 引擎 + `prometheus-planning` 三级回退链）

---

## 核心概念

### Spec 端 vs Ship 端（v1.1 拆分）

`git commit artifacts` 是 spec → ship 的**唯一切换点**。

| 端 | 职责 | 关键产物 |
|----|------|---------|
| **spec 端** (`guide-spec`) | 环境检查 → 路线图 → 扫描/创建 change → 依赖分析 | `openspec/changes/<name>/{proposal,design,tasks}.md` 已提交 |
| **ship 端** (`guide-ship`) | worktree → Prometheus 计划 → 实施执行 → 归档 → 清理 | worktree 目录、`.sisyphus/plans/<name>.md`、归档记录 |

详细架构决策见 [ADR-0001](./docs/adr/ADR-0001-propose-plan-execute-state-machine.md)。

### 两种执行模式

| 模式 | 说明 | 场景 |
|------|------|------|
| **🔒 阻塞执行** | 在当前 session 执行，等待任务完成 | 小改动、快速验证 |
| **🔓 分离执行** | 在新终端执行，当前 session 立即返回 | 多 change 并行、长任务 |

### 状态文件

| 文件 | 位置 | 用途 | 写入方 |
|------|------|------|--------|
| `proposal-suggestions.md` | 项目根目录 | 扫描出的建议列表，随 git 版本控制 | `propose` / `roadmap` / `status` / `guide-arch` / `guide-plan` |
| `openspec/changes/<name>/tasks.md` | change 目录 | Execute 阶段任务清单（权威进度来源） | `execute` / `guide-ship` / `prometheus-planning` |
| `docs/adr/ADR-*.md` | 项目根目录 | 架构决策记录（propose 扫描 + 引用源） | 用户手工编写（待 propose 扫描拾取） |
| `.sisyphus/plans/<name>.md` | worktree 内 | Prometheus 计划文件（ship 端产物） | `prometheus-planning` / `guide-ship` |
| `.zcf/.handoff.json` | 项目根目录 | spec → ship 软交接状态（spec_complete_at / ship_started_at / current_change） | `guide-plan`（plan-done 写入）/ `guide-ship`（ship-started 读取+更新） |
| `.zcf/.arch-handoff.json` | 项目根目录 | arch → plan 阶段交接状态（arch_complete_at / arch_artifacts） | `guide-arch`（arch-done 写入）/ `guide-plan`（plan-start 读取+更新） |
| `.zcf/.plan-handoff.json` | 项目根目录 | plan → ship 阶段交接状态（plan_complete_at / committed_changes） | `guide-plan`（plan-done 写入）/ `guide-ship`（ship-start 读取） |
| `.zcf/.deps-analysis.json` | 项目根目录 | deps 阶段结构化分析结果（依赖图 + 执行顺序） | `deps` / `guide-plan`（deps 阶段） |
| `.zcf/.deps-candidates.json` | 项目根目录 | deps 阶段候选 change 列表 | `guide-plan`（deps 阶段） |
| `.zcf/.deps-output.md` | 项目根目录 | deps 阶段依赖图 + 推荐执行顺序 | `guide-plan`（deps 阶段） |
| `.zcf/index.md` | 项目根目录 | change 索引（自动维护） | `guide-arch` / `guide-plan` |

> 重要：`.zcf/` 目录已被 `.gitignore` 排除，不进 git 仓库。

### 执行状态

| 状态 | 含义 |
|------|------|
| ⏳ 等待执行 | 未开始 |
| 🔒 执行中 | 在此 session 阻塞执行 |
| 🔓 分离执行 | 在新终端执行，不阻塞 |
| ✅ 完成 | 所有任务完成 |

---

## 快速开始

### 启动交互式向导

根据当前需求选择入口：

```
# 推荐器入口（不知道调谁时用）
用户: skill_use("guide")

# Spec 端（创建新 change：setup → roadmap → propose → deps）
用户: skill_use("guide-spec")

# Ship 端（已提交的 change：plan → execute → archive → cleanup）
用户: skill_use("guide-ship")
```

`guide` 推荐器会自动检查状态并给出当前合适的选项菜单；如已明确 spec 侧或 ship 侧，可直接调对应状态机跳过推荐步骤。

### 完整 skill 列表 (v2.0 共 12 个)

| Skill | 用途 | 触发方式 |
|-------|------|---------|
| `INSTALL` | 首次安装（将技能复制到项目的 `.opencode/skills/`） | 用户显式调用 |
| `guide` | 推荐器入口（扫描状态，建议调 guide-arch、guide-plan 或 guide-ship） | `skill_use("guide")` |
| `guide-arch` | **新** 架构定义阶段（5 子阶段：setup → adr-create → architecture → roadmap-define → arch-done） | `skill_use("guide-arch")` |
| `guide-plan` | **新** 变更生成阶段（4 子阶段：scan → propose → deps → plan-done） | `skill_use("guide-plan")` |
| `guide-ship` | Ship 端状态机（5 阶段） | `skill_use("guide-ship")` |
| `guide-spec` | **别名** spec 端状态机（自动调用 guide-arch → guide-plan，v3.0 移除） | `skill_use("guide-spec")` |
| `propose` | 扫描 ADR/代码生成建议列表 | `guide-plan` 内部 / 单独使用 |
| `roadmap` | 路线图管理（phase/category 结构） | `guide-arch` 内部 / 单独使用 |
| `deps` | 依赖分析（含 subagent Step 3） | `guide-plan` 内部 / 单独使用 |
| `execute` | 在 worktree 内执行任务 | `guide-ship` 内部 / worktree 内单独使用 |
| `status` | 状态查看 | `guide-ship` 内部 / 单独使用 |
| `prometheus-planning` | 实施计划生成器（带三级回退链） | `guide-ship` Phase 1 内部 |

### 使用 Loop 引擎（v2.0）

```bash
# Loop 模式 — 自动扫描、执行、验证
skill_use("loop", {
  "goal": "complete all pending changes",
  "mode": "loop"
})
```

### 配置示例（v2.0）

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "human_in_loop_nodes": [
      "arch.adr_create",
      "ship.archive_confirm"
    ]
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3
  }
}
```

---

## 完整流程：Spec 端（5 阶段）

### Phase 1 — Setup（环境检查）

首次启动向导时自动进入。

**检测项**：
- openspec CLI 是否可用（v1.3.1+）
- git 工作区是否干净
- 当前分支
- 已有的 worktree 列表
- 构建目录是否存在
- bats-core 1.10+（如使用测试基础设施）
- 活跃 changes 数量

**菜单示例**：

```
环境检查完成。

  openspec CLI:  ✅ 1.3.1
  git 工作区:    ✅ 干净
  当前分支:      master
  Worktrees:     无
  构建目录:      ✅ 存在
  bats-core:     ✅ 1.13.0
  活跃 changes:  0

请选择:
1. ✅ 继续 → 进入 Roadmap 阶段
2. 🔄 重新检查
i. 其他操作
```

---

### Phase 2 — Roadmap（路线图管理）

确保 `roadmap.md` 和 `roadmap-meta.yaml` 反映当前 phase/category 划分。

**职责**：
- 维护 `roadmap.md`（顶层 phase 列表）
- 维护 `roadmap-meta.yaml`（phase/category 元数据）
- 验证活跃 phase 与现有 change 一致
- 支持新增 phase（如 multi-phase 项目）

**行为**：
1. 读取 `roadmap.md` + `roadmap-meta.yaml`
2. 比对 `openspec/changes/` 中已存在的 change 与 roadmap phase
3. 标记孤儿 change（roadmap 无对应 phase）
4. 提示创建新 phase（如果当前需求不属于任何现有 phase）

**何时跳过**：单 phase 项目，或新增 change 已明确归属于现有 phase。

---

### Phase 3 — Propose（扫描并创建 Change）

扫描 ADR 和代码 TODO，生成建议列表，用户选择后创建 artifacts。

**行为**：
1. 扫描 `docs/adr/ADR-*.md` — 找到已采纳但未实现的 ADR 项
2. 扫描 `docs/architecture/*-gap-analysis.md` — 找到功能缺口
3. 扫描代码中的 `TODO`/`FIXME` 标记
4. 生成 `proposal-suggestions.md` 建议列表

**菜单示例**：

```
建议列表（来自 ADR 扫描 + 代码 TODO）：

🔴 高优先级
1. fix-ns-pollution  — 修复命名空间污染 (ADR-033, 3 个任务)
2. add-stream-pipes  — 实现 Stream 管道操作符 (ADR-022, 5 个任务)

🟡 中优先级
3. add-cdc-support   — 跨时钟域支持

当前已创建: 无

请选择:
1. 创建 fix-ns-pollution
2. 创建 add-stream-pipes
3. 创建 add-cdc-support
4. ✅ 完成 Propose 阶段 → 进入 Deps 阶段
5. 📋 查看所有已创建的 change 详情
i. 手动输入 change 名称
```

**ADR 引用约定**：
- `proposal.md` 必须用 `ADR-NNN §N.M` 格式引用 ADR 章节
- 详见 [docs/adr/README.md](./docs/adr/README.md#引用格式)
- 模板见 [docs/adr/ADR-0000-template.md](./docs/adr/ADR-0000-template.md)

**创建后重新进入此阶段**——可以连续创建多个 change，然后选选项 4 完成。

---

### Phase 4 — Deps（依赖分析）

对刚创建（或已有）的 change 进行依赖分析：识别阻塞依赖、规划执行顺序。

**职责**：
- 检测 candidate change 之间的代码依赖（`docs/proposal-suggestions-format.md` 规则）
- 运行 `deps` 技能（含 subagent Step 3 语义分析 + fallback）
- 输出 `.zcf/.deps-candidates.json`（机器可读）+ `.zcf/.deps-output.md`（人类可读）
- 标注"可并行"vs"需串行"vs"被阻塞"

**行为**：
1. 扫描 `openspec/changes/*/specs/` 中的依赖声明
2. Step 1: 静态分析（语法级）
3. Step 2: 跨 change 重叠检测
4. Step 3: **subagent 语义分析**（v1.1 新增）——使用 subagent 理解"change A 是否逻辑上依赖 change B"
5. Step 4: 汇总报告 + roadmap phase 整合

**何时跳过**：单 change 项目，或所有 change 明确无依赖。

---

### Phase 5 — Handoff（交接给 Ship 端）

`guide-spec` 的最后阶段：检查所有 `openspec/changes/<name>/{proposal,design,tasks}.md` 是否已 git 提交。

```
✅ Spec 端完成

  3 changes 已提交到 master:
  - add-skill-bats-tests
  - implement-deps-subagent-analysis
  - init-adr-directory

请选择:
1. 🚀 进入 Ship 端 (skill_use("guide-ship"))
2. ⏸️ 稍后手动进入
```

---

## 完整流程：Ship 端（5 阶段 + 1 退出）

> 实际内部编号为 1, 1.5, 2, 3, 4, 5（ship-done 是 Phase 5 退出判定）。其中 1.5 是 worktree 验证 + 监控选择的子菜单。

### Phase 1 — Plan（Worktree + 计划生成）

为已提交的 change 创建 worktree 并生成 Prometheus 计划。

**入口条件**：`openspec/changes/<name>/{proposal,design,tasks}.md` 已 git 提交（`git show HEAD:<path>` 验证）。

**行为**：
1. 展示所有活跃 changes 的状态表
2. 用户选择要处理的 change
3. 执行 COMMIT GATE（脏检测 + 已提交验证）
4. 创建 branch + worktree（路径: `.zcf/<name>-wt`）
5. 在 worktree 内生成 Prometheus 计划（**自动通过 `prometheus-planning` 三级回退链**）
6. **立即选择执行模式**（🔒 阻塞 / 🔓 分离）

### Phase 1.5 — Worktree 验证 + 监控选择（子菜单）

`guide-ship.md` 内部的子菜单，提示用户是进入 Execute 监控模式还是返回 Plan 阶段。

**行为**：
- 检测到 worktree 已就绪 → 提示「进入 Execute 监控模式」或「继续返回 Plan 阶段」
- 用户选择后继续

**`prometheus-planning` 三级回退链**（v1.1 新增）：

| 优先级 | 来源 | 备注 |
|---|---|---|
| 1️⃣ (推荐) | `oh-my-opencode` 内置 Prometheus (plan) 子代理 | 零依赖，prompt 透明可审计 |
| 2️⃣ (回退) | `superpowers/writing-plans` 技能 | opencode 内置 superpowers 套件 |
| 3️⃣ (已弃用) | `prometheus-start-work` 外部 GitHub 技能 | 兼容 v1.0 用户 |
| ❌ | 全部不可用 | 报错并提示安装 |

详见 [README.md 三级回退链说明](./README.md#实施计划生成器prometheus-planning-的三级回退链)。

**菜单示例**：

```
Plan 阶段

📋 活跃 Changes:
| 变更 | Artifacts | Worktree | 计划文件 |
|-----|-----------|----------|---------|
| fix-ns-pollution | ✅ | ❌ | ❌ |
| add-stream-pipes | ✅ | ❌ | ❌ |

请选择:
1. 为 fix-ns-pollution 创建 worktree + 生成计划
2. 为 add-stream-pipes 创建 worktree + 生成计划
3. 批量处理：全部为已提交的变化创建 worktree
4. 🔄 切换当前焦点变更
5. ↩️ 返回 Propose 阶段（创建更多 change）
i. 其他输入
```

**Worktree 创建完成 → 立即选择执行模式**：

```
fix-ns-pollution worktree 已就绪，请选择执行方式：

📋 fix-ns-pollution 状态:
  Worktree: .zcf/fix-ns-pollution-wt
  计划文件: .sisyphus/plans/fix-ns-pollution.md ✅
  任务数: 3

请选择执行方式:
1. 🔒 在此 session 执行（阻塞）— 等待任务完成后返回
2. 🔓 分离执行（新终端）— 给出操作指引，立即返回
i. 其他输入
```

**分离执行指引**：

```
🔓 分离执行指引

为 fix-ns-pollution 启动分离执行：

1. 在新终端中执行：
   cd "$PROJECT_ROOT/.zcf/fix-ns-pollution-wt"
   skill_use("execute")

2. execute 结果会自动写入 tasks.md

3. 完成后，在此 session 运行 guide-ship 查看最新进度

当前状态：fix-ns-pollution 🔓 等待分离执行
```

**返回 Plan 前的检查 — 是否进入监控**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 发现 1 个 worktree 已就绪

请选择:
1. ✅ 进入 Execute 阶段（实时监控所有 worktree 进度）
2. 🔄 继续返回 Plan 阶段（创建更多 worktree）
i. 其他输入
```

---

### Phase 2 — Execute（监控与执行）

Execute 阶段是**监控模式**——读取 `tasks.md` 进度、显示所有 worktree 状态、提供执行入口。**不是实际执行者**（实际执行在 worktree 内的 sub-session 中完成）。

**监控模式入口点**（三处均可进入）：

| 入口点 | 触发条件 |
|--------|---------|
| **工作流状态恢复** | 新 session 调用 `guide-ship`，检测到已有 worktree |
| **Plan 返回前** | worktree 创建完成后选择执行模式前 |
| **Execute 菜单** | 任何时候可刷新或返回 Plan |

**前置检测**（每次入口执行）：

```bash
# 读取所有 tasks.md 的实际进度
LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    branch=$(git worktree list | grep "$wt" | awk '{print $3}')
    name=$(echo "$branch" | sed 's|openspec/||')
    tasks_file="$wt/openspec/changes/$name/tasks.md"

    total=$(grep -c "^- \[" "$tasks_file" 2>/dev/null || echo 0)
    done=$(grep -c "^- \[x\]" "$tasks_file" 2>/dev/null || echo 0)
    progress="${done}/${total}"
    echo "  $name → $progress"
done

echo ""
echo "上次检测: $LAST_CHECK"
```

**菜单示例**：

```
Execute 阶段（监控模式）

📋 所有 Worktrees 状态:（实时读取 tasks.md）
| 变更 | Worktree | 进度 | 执行状态 |
|-----|----------|------|---------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | 1/3 | 🔒 执行中 |
| add-stream-pipes | .zcf/add-stream-pipes-wt | 2/5 | 🔓 分离执行 |

上次检测: 2026-05-18 10:35:00

请选择:
1. 🔒 在此 session 执行 fix-ns-pollution（阻塞）
2. 🔓 分离执行 fix-ns-pollution（新终端）
3. 🔒 在此 session 执行 add-stream-pipes（阻塞）
4. 🔓 分离执行 add-stream-pipes（新终端）
5. 📋 查看任务列表（指定变更）
6. 🔧 运行构建验证（指定变更）
7. 🔄 刷新进度（重新读取所有 tasks.md）
8. ↩️ 返回 Plan 阶段（创建更多 worktree）
i. 其他输入
```

**关键特性**：
- 任何时候可以返回 Plan 阶段添加更多 worktree
- 进度来自 `tasks.md` 实际读取，每次入口自动刷新
- 「🔄 刷新进度」可手动重新读取所有 `tasks.md`
- 「上次检测」时间戳让用户知道状态是实时的
- **Execute 主要写 `tasks.md`**：在 roadmap 模式下，额外更新 `.zcf/.deps-analysis.json`（结构化依赖图，详见上方「状态文件」章节）

---

### Phase 3 — Archive（状态检查 + 归档）

检查所有 change 状态，对可归档的 change 执行 `archive_change`。

**职责**：
- 读取每个 worktree 的 `tasks.md` 进度
- 识别 100% 完成的 change（可归档）
- 调用 `archive_change` 合并到 default branch + `openspec archive`
- 检查是否还有未处理 change/worktree

**菜单示例**：

```
Status 阶段

📋 所有 Changes 状态:
| 变更 | Worktree | 任务进度 | 状态 |
|-----|----------|---------|------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | 3/3 ✅ | 可归档 |
| add-stream-pipes | .zcf/add-stream-pipes-wt | 2/5 🔄 | 进行中 |

请选择:
1. 归档 fix-ns-pollution（merge → archive）
2. 查看 add-stream-pipes 进度（继续执行）
3. 📊 全局概览（所有 change + worktree）
4. 🔍 详细检测（同步问题等）
5. ↩️ 返回 Execute 阶段
i. 其他输入
```

**推荐方式**（使用项目自带 helper）：

```bash
# 在项目根目录（master 分支）
source skills/_lib/archive.sh
archive_change "<change-name>"
```

`archive_change` 内部执行：
1. **Pre-merge check**：worktree 存在 + 干净 + 在正确分支
2. **Checkout default branch**（动态检测 main/master/develop）+ **fast-forward merge**（如不可 FF，回退到 `--no-ff`）
3. **`openspec archive "<name>" --yes`**：移动 change 到 `openspec/changes/archive/<date>-<name>/`
4. **Worktree remove** + **branch delete**（自动）

**手动方式**（debug/特殊场景）：

```bash
# 1. Merge worktree → default branch
cd "$PROJECT_ROOT"
DEFAULT_BRANCH=$(find_default_branch)  # 来自 skills/_lib/worktree.sh
git checkout "$DEFAULT_BRANCH"
git merge --ff-only "openspec/${CHANGE_NAME}"

# 2. Archive
openspec archive "${CHANGE_NAME}" --yes

# 3. Cleanup
git worktree remove ".zcf/${CHANGE_NAME}-wt"
git branch -d "openspec/${CHANGE_NAME}"
```

### Phase 4 — Cleanup（worktree + branch 清理）

所有 archive 完成后，批量清理剩余的 worktree 和 `openspec/*` branches。

**菜单示例**：

```
清理选项

📋 Worktrees: (列出所有剩余 worktree)
📋 Branches: (列出所有 openspec/* branches)

请选择:
1. 🧹 清理指定 worktree + branch
2. 🗑️ 清理所有 worktree + openspec/* branches
3. 📝 输出测试总结报告（所有 changes 的执行记录）
4. ↩️ 返回上一阶段
i. 其他输入
```

### Phase 5 — Ship-done（退出）

所有 change 已归档且 cleanup 完成后，触发 ship-done 退出判定。

**退出条件**：

```bash
REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l)

if [ "$REMAINING_WT" -eq 0 ] && [ "$REMAINING" -eq 0 ]; then
  echo "🎉 All changes archived — ship-done reached"
fi
```

**Phase 5 菜单**（区分两种语义）：
- **「本次 session 结束」** — 退出 ship-done，下次 session 继续
- **「项目完成」** — 整个项目归档，不再做新 change

```
请选择:
1. 继续处理 (skill_use("guide-ship")) — 还有 worktree 要处理
2. 回到 spec 端 (skill_use("guide-spec")) — 创建更多 changes
3. 本次 session 结束 — 退出 ship-done，稍后继续
4. 项目完成 — 不再做任何 change（此项目归档）
i. 其他输入
```

---

## 并行执行示例

### 场景：同时处理 fix-ns-pollution 和 add-stream-pipes

**Terminal A（主控 session）**：

```
skill_use("guide-ship")
→ Plan 阶段 → 创建 fix-ns-pollution worktree
→ 选择 🔓 分离执行
→ 切换 add-stream-pipes → 创建 worktree
→ 选择 🔓 分离执行
→ 进入 Execute 监控模式

（主控 session 保持可操作，可继续其他操作或等待）
```

**Terminal B（fix-ns-pollution 执行）**：

```
cd "$PROJECT_ROOT/.zcf/fix-ns-pollution-wt"
skill_use("execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

**Terminal C（add-stream-pipes 执行）**：

```
cd "$PROJECT_ROOT/.zcf/add-stream-pipes-wt"
skill_use("execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

**回到 Terminal A**：

```
skill_use("guide-ship")
→ Execute 监控模式检测到 tasks.md 进度已更新
→ 显示最新进度
→ 可选择归档或继续监控
```

---

## 测试基础设施

> 适用于 v1.1+ 项目的 spec-workflow 验证。

### 工具链

| 工具 | 用途 | 版本要求 |
|------|------|---------|
| `bats-core` | bash 自动化测试框架 | 1.10+（推荐 1.13+） |
| `git` | 测试工作树管理 | 2.25+ |
| `openspec` CLI | 验证 change artifacts | 1.3.1+ |

### 目录结构

```
tests/
├── README.md                       # 测试说明
├── test_helper.bash                # setup/teardown + `load_lib` 解析器
├── smoke.bats                      # 7 个基础设施断言
├── _lib/                           # 共享辅助函数 + 单元测试
│   ├── skill.bash                  # skill frontmatter/metadata/commands/section 解析
│   ├── deps-subagent.bash          # deps subagent Step 3 验证
│   ├── test_skill.bats             # skill.bash 单元测试（8 cases）
│   ├── test_state.bats             # skills/_lib/state.sh 单元测试
│   └── test_worktree.bats          # skills/_lib/worktree.sh 单元测试
└── integration/                    # 端到端 / CLI 集成测试
    ├── test_<issue-id>.bats        # P0/P1/P2/P3 fix 的回归锁
    ├── test_*_skill.bats           # 每个 skill 的结构/metadata 覆盖（9 个文件）
    ├── test_*_subagent.bats        # subagent 集成测试
    ├── test_skill_metadata_consistency.bats  # package.json ↔ skills/ ↔ smoke.bats 一致性
    ├── test_adr_directory.bats     # docs/adr/ 完整性（init-adr-directory 验证）
    ├── test_archive_dedup.bats     # 归档去重
    └── ...
```

### 运行测试

```bash
# 全部测试（推荐 CI）
bats tests/

# 仅 smoke（快速验证）
bats tests/_lib/test_skill.bats

# 集成测试
bats tests/integration/

# 全部
npm test   # 等价于 bats tests/
```

### 编写新测试的约定

- **共享辅助函数**放在 `tests/_lib/*.bash`（被 `@load "<filename>"` 引用）
- **单元测试**在 `tests/_lib/test_*.bats`（直接调用 `_lib` 内的 bash 函数）
- **集成测试**在 `tests/integration/test_*.bats`（创建完整 OpenSpec change 进行端到端验证）
- **bats @test 命名**：`"模块: 场景描述"`，如 `@test "skill: metadata has name, version, evolved-from"`

详见 [tests/README.md](./tests/README.md)。

---

## ADR 生命周期

> v1.1+：`init-adr-directory` 已建立 `docs/adr/` 目录，所有架构决策应记录为 ADR。

### 文件结构

```
docs/adr/
├── README.md                                # ADR 索引 + 约定
├── ADR-0000-template.md                     # 模板（保留槽位）
├── ADR-0001-propose-plan-execute-state-machine.md
└── ...                                       # 实际 ADR
```

### 命名约定

| 模式 | 含义 | 是否必须 |
|------|------|---------|
| `ADR-0000-template.md` | 模板（保留槽位，不算实际 ADR） | ✅ |
| `ADR-NNNN-<kebab-case-name>.md` | 实际 ADR，NNNN 从 0001 起 | ✅ |

### 状态字段

| 状态 | 含义 |
|------|------|
| **提议 (Proposed)** | 已记录，等待审查 |
| **已采纳 (Accepted)** | 已实施或即将实施 |
| **已弃用 (Deprecated)** | 已被新 ADR 替代 |
| **已废弃 (Superseded)** | 明确标记不再适用 |

### 何时写 ADR

- ✅ 引入新 phase/category（roadmap 变更）
- ✅ 拆分/合并技能（如 v1.0 → v1.1 的 `guide` 拆分为 `guide-spec` + `guide-ship`）
- ✅ 添加新测试基础设施（如 `init-adr-directory` 的 bats 设计）
- ✅ 修改核心工作流契约（如 phase 边界、git commit 切换点）
- ❌ 单个 bug 修复（用 commits + PR 描述）
- ❌ 内部实现细节（无架构影响）

### 引用格式

- `proposal.md` 引用：`ADR-NNN §N.M`（如 `ADR-0001 §3`）
- Markdown 交叉引用：`[ADR-0001](./docs/adr/ADR-0001-propose-plan-execute-state-machine.md)`

详见 [docs/adr/README.md](./docs/adr/README.md)。

---

## 错误处理

| 错误场景 | 检测方式 | 修复指引 |
|----------|----------|----------|
| 未 commit 就 plan | `git status --porcelain` + `git show HEAD:<path>` 失败 | 提示先 commit artifacts |
| artifacts 有未提交修改 | `git status --porcelain openspec/changes/<name>/` 非空 | 提示先 commit 再 plan |
| worktree 目录冲突 | `-d .zcf/<name>-wt` 但 `git worktree list` 未注册 | 提示 `rm -rf .zcf/<name>-wt` |
| tasks.md 不同步 | tasks.md 进度与 state 不一致 | Guide 入口时自动从 tasks.md 同步 |
| worktree 分支冲突 | `git worktree add` 失败 | 提供 `git worktree list` 查看现有 |
| 未 plan 就 status | `.sisyphus/plans/<name>.md` 不存在 | 提示先执行 plan |
| execute 不在 worktree 内 | `git branch --show-current` 非 `openspec/` | 提示先进入 worktree 或使用分离执行 |
| prometheus-planning 全部回退失败 | 三级回退链全部 ❌ | 提示安装 oh-my-opencode 或 superpowers |
| bats-core 缺失 | `bats --version` 失败 | 提示安装 bats-core 1.10+ |
| ADR 引用格式错误 | `grep -E "ADR-[0-9]+ §[0-9]+" proposal.md` 无匹配 | 提示按 ADR-NNN §N.M 格式补充 |

---

## 关键约束提醒

1. **COMMIT GATE**：worktree 创建前必须 commit，否则 `git worktree add` 看不到 artifacts
2. **Branch 检查**：`git branch --show-current` 必须是 `master` 才能创建 worktree（本项目默认分支）
3. **不同步处理**：用 `awk index()` 直接修改 `tasks.md`，不重新 run plan（会覆盖 `.sisyphus/plans/`）
4. **Execute 只写 `tasks.md`**：不写 state 文件，由 guide 从 `tasks.md` 同步进度
5. **任何时候可返回 Plan**：Execute 菜单有「返回 Plan 阶段」选项，可添加更多 worktree
6. **ADR 是契约**：`docs/adr/ADR-*.md` 一旦 `已采纳 (Accepted)`，必须由 `propose` 阶段的扫描器拾取并转化为 change
7. **Skill metadata 只读**：所有 skill 文件的 `name`/`version`/`compatibility`/`metadata` 前置字段不可修改
8. **execute 阶段不 commit/push**：plan 中明确 `Executor stops after the summary report`，commit 留到 archive 阶段

---

## 版本演进

| 版本 | 关键变更 |
|------|---------|
| **v2.0.0-beta** (current) | 三阶段架构 `arch` → `plan` → `ship`（新增 `guide-arch`/`guide-plan`，`guide-spec` 保留为兼容别名）；Loop 引擎 `loop_engine.py` + `skills/_lib/`；新增 `prometheus-planning` 三级回退链；保留 v1.x 全部分阶段逻辑 |
| v1.1 | 拆分 `guide` 为 `guide-spec` (5 阶段) + `guide-ship` (4 阶段)；新增 `roadmap`/`deps`/`prometheus-planning` 技能；建立 `docs/adr/` 目录（ADR-0001 记录拆分决策）；加入 bats-core 测试基础设施；`prometheus-start-work` 降级为 deprecated |
| v1.0 | 单一 `guide` 技能驱动全流程；`prometheus-start-work` 作为默认计划生成器 |
| 2026-06-04 之前 | 使用 `generatedBy: X.Y` 元数据，已重命名为 `evolved-from` |

详见 [ADR-0001](./docs/adr/ADR-0001-propose-plan-execute-state-machine.md)。
