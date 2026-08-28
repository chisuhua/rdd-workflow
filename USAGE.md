# OpenSpec 工作流技能使用指南

> 基于 `guide` 推荐器（arch-side 调 `guide-arch`，plan-side 调 `guide-plan`，ship-side 调 `guide-ship`），覆盖从提案到归档的完整生命周期。
> 支持多 change 并行执行，可分离到不同终端同时运行。
<!-- VERSION_BANNER_START -->
> 当前版本: **v3.0+ (2026-08-26)**（五阶段架构 arch → design → plan → ship → verify + Loop 引擎 + `rdd-workflow-writing-plans` 自包含计划生成器 + `iteration.json` sprint 视图 + 结构化 deps 输出 + `rddf-session` 跨 OpenCode session 恢复 + `rdd-verifier` 阶段验证 + Hub-Spoke 联邦）。`package.json` 标 `3.0.0`，文档与状态契约以 v3.0 为准。
<!-- VERSION_BANNER_END -->

> 📋 **v2.0.2 changelog（sync-workflow-contracts 已落地，2026-07-13）**：
> - 13 个 Markdown skill 全部发布到 `package.json::skills[]`（含 `feature` + `rddf-session`），无 src-only 例外
> - 状态文件表已对齐生产路径：`.rddf/state/.arch-handoff.json` / `.rddf/state/.plan-handoff.json` / `.rddf/state/deps-analysis.json` / `.rddf/state/iteration.json` / `.rddf/state/sessions.json` 全部为点号前缀、gitignored
> - ADR-0013 文件重复已在 `docs/adr/README.md` 顶部 ⚠️ flag 标注（重编号留待后续 `init-deep` 决策 / `fix-adr-index-and-numbering` change）
> - 新增 3 个 anti-drift contract test（`tests/integration/test_doc_contracts.bats` + `tests/integration/test_adr_index.bats` + `tests/unit/test_doc_contracts.py`），任何后续漂移立刻 CI FAIL

---

## 核心概念

### Arch / Plan / Ship 三阶段

`git commit artifacts` 是 plan → ship 的**工作产物切换点**；形式化的交接由 `.rddf/state/.arch-handoff.json` / `.rddf/state/.plan-handoff.json` 分布在 arch→plan、plan→ship 边界（两个文件都以 `.` 前缀，被 `.gitignore` 排除）。

| 端 | 职责 | 关键产物 |
|----|------|---------|
| **arch 端** (`guide-arch`) | `setup → adr-create → architecture → roadmap-define → arch-done`（5 子阶段） | `roadmap.md`（默认，可由 ADR-0016 discovery 重新发现）、`docs/adr/ADR-*.md`、`docs/architecture/*-gap-analysis.md`（可选）、`.rddf/state/.arch-handoff.json` |
| **plan 端** (`guide-plan`) | `scan → propose → deps → plan-done`（4 子阶段） | `openspec/changes/<name>/{proposal,design,tasks}.md` 已提交、`.rddf/state/.plan-handoff.json`、`.rddf/state/.deps-analysis.json` |
| **ship 端** (`guide-ship`) | `plan → verification → execute → review → archive → cleanup → ship-done`（7 子阶段，编号 1, 1.5, 2, 2.5, 3, 4, 5） | worktree 目录或当前分支（轻量模式）、`.rddf/plans/<name>.md`、归档记录、`.rddf/state/iteration.json` |

详细架构决策见 [ADR-0003](./docs/adr/ADR-0003-three-phase-architecture.md)。

### Ship 端两种执行模式（worktree 选择）

`guide-ship` 在 Phase 1 自动检测并行冲突，决定工作区策略：

| 模式 | 触发条件 | 机制 |
|------|---------|------|
| **⚡ 轻量模式 (lightweight)** | 无其他 worktree **且** 仅此一个 change | 直接在主仓库创建 `openspec/<name>` 分支并 `git checkout`，跳过 worktree 创建 |
| **🔀 worktree 模式** | 有活跃 worktree **或** 多个 change | 创建隔离 worktree `.rddf/wt/<name>`，互不干扰 |

轻量模式下所有 worktree/branch 路径退化为 `$PROJECT_ROOT`；归档时直接 merge branch 而非 `archive_change`。模式选择是**工作区隔离策略**，与下面「🔒 阻塞执行 / 🔓 分离执行」是不同维度——后者是单 session 内的**运行时执行模式**（同一 worktree / 轻量分支上如何跑 `execute`），由用户在 worktree 就绪后另行选择。

### 在 git submodule 内使用（v2.2+）

rddf-workflow 从 v2.2 起**submodule-aware**（ADR-0033）。在 git submodule 目录内运行 `rddf dashboard` / `status` / `init` / `validate` 等命令时，`main_repo_root()` 和 `resolve_project_root()` 会优先返回 **submodule 自身的根**（通过 `git rev-parse --show-superproject-working-tree` 检测 + `--show-toplevel`），而**不是**错误地解析到 superproject 的 `.git/modules/<name>`。每个 submodule 独立管理自己的 `.rddf/state/`，符合"每个 submodule 是独立 git repo"的语义。

**注意**：
- nested submodule 自然处理（`--show-superproject-working-tree` 返回最近一级 superproject，`--show-toplevel` 仍返回自身根）
- `--git-dir` 在 submodule 内返回 superproject 的 gitdir，**仅用于存在性检查**时语义仍正确；用于路径解析必须改用 `--show-toplevel` 或 `--git-common-dir`（项目内已统一迁移）
- 详见 `.rddf/improvements/submodule-aware-project-root.md` 和 `docs/adr/ADR-0033-submodule-aware-project-root-resolution.md`

### 运行时执行模式（同 session 内）

| 模式 | 说明 | 场景 |
|------|------|------|
| **🔒 阻塞执行** | 在当前 session 执行，等待任务完成 | 小改动、快速验证 |
| **🔓 分离执行** | 在新终端执行，当前 session 立即返回 | 多 change 并行、长任务 |

### 状态文件

| 文件 | 位置 | 用途 | 写入方 |
|------|------|------|--------|
| `proposal-suggestions.md` | 项目根目录 | 扫描出的建议列表（JSON 数组格式），随 git 版本控制 | `propose` / `roadmap` / `status` / `guide-arch` / `guide-plan` |
| `openspec/changes/<name>/tasks.md` | change 目录 | Execute 阶段任务清单（权威进度来源） | `execute` / `guide-ship` |
| `docs/adr/ADR-*.md` | ADR 目录 | 架构决策记录（propose 扫描 + 引用源） | 用户手工编写（待 propose 扫描拾取） |
| `.rddf/plans/<name>.md` | worktree 内或主仓库（轻量模式） | Prometheus 计划文件（ship 端产物，git tracked） | `rdd-workflow-writing-plans` / `guide-ship` |
| `.rddf/state/.arch-handoff.json` | `.rddf/state/`（gitignored） | arch → plan 阶段交接状态（arch_complete_at / arch_artifacts / adr_dir / roadmap_path / discovered）+ ADR-0016 发现契约 v1 | `guide-arch`（arch-done 写入）/ `guide-plan`（Phase 0 读取+fallback defaults） |
| `.rddf/state/.plan-handoff.json` | `.rddf/state/`（gitignored） | plan → ship 阶段交接状态（plan_complete_at / committed_changes / ship_started_at） | `guide-plan`（plan-done 写入）/ `guide-ship`（ship-start 读取） |
| `.rddf/state/sessions.json` | `.rddf/state/`（gitignored） | **rddf-session 生命周期**（ADR-0017）— 跨 OpenCode session 工作流恢复（stage_arch / stage_plan / stage_ship + heartbeat + 4 选项冲突处理） | `guide-arch` / `guide-plan` / `guide-ship` 入口 + `rddf-session` 技能 5 子命令 |
| `.rddf/state/iteration.json` | `.rddf/state/`（gitignored） | **当前 sprint 视图**（v2.0.1）— change 状态机：proposed → planned → in_worktree → completed → archived；multi-hook 写入 | `propose` / `guide-ship` / `execute` / `deps` / `archive` hooks（集中由 `skills/_lib/iteration.py` 管理） |
| `.rddf/state/deps-analysis.json` | `.rddf/state/`（gitignored） | **结构化** deps 输出（v2.0.1）— 依赖图 + 执行顺序 JSON（schema 见 `skills/_lib/schemas/deps_analysis_schema.json`） | `deps` Step 5b 优先写；Step 6 markdown-fallback 时也写 |
| `.rddf/state/.deps-candidates.json` | `.rddf/state/`（gitignored） | deps 阶段候选 change 列表（机器可读） | `guide-plan`（deps 阶段）/ `review-phase` 自动增量 |
| `.rddf/state/.deps-output.md` | `.rddf/state/`（gitignored） | deps 阶段依赖图 + 推荐执行顺序（人类可读报告；旧 `.rddf/state/deps-output.md` 仅作兼容引用） | `deps` Step 5 / `guide-plan`（deps 阶段） |
| `.rddf/state/index.md` | `.rddf/state/`（gitignored） | change 索引（自动维护） | `guide-arch` / `guide-plan` |

> 重要：`.rddf/state/`、`.rddf/wt/`、`.rddf/detectors/`、`.rddf/actions/` 全部 gitignored；只有 `.rddf/plans/` **随 git 版本控制**（执行契约路径）。

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

# Arch 端（创建新 change：setup → adr-create → architecture → roadmap-define → arch-done）
用户: skill_use("guide-arch")

# Plan 端（已有架构：scan → propose → deps → plan-done）
用户: skill_use("guide-plan")

# Ship 端（已提交的 change：plan → verification → execute → review → archive → cleanup → ship-done，含轻量/worktree 自动检测）
用户: skill_use("guide-ship")
```

`guide` 推荐器会自动检查状态并给出当前合适的选项菜单；如已明确 arch/plan/ship 侧，可直接调对应状态机跳过推荐步骤。

### 完整 skill 列表

`skills/` 目录当前包含 **13 个 Markdown skill 文件**（`INSTALL` + `guide` + `guide-arch` + `guide-plan` + `guide-ship` + `feature` + `propose` + `roadmap` + `deps` + `execute` + `status` + `rddf-session` + `rdd-workflow-writing-plans`）外加 `loop_engine.py`。**v2.0.2 起** `package.json::skills[]` 已**完整发布全部 13 个**（含 `feature` + `rddf-session`），与磁盘无差异。

| Skill | 用途 | 触发方式 |
|-------|------|---------|
| `INSTALL` | 首次安装（将技能复制到项目的 `.opencode/skills/`） | 用户显式调用 |
| `guide` | 推荐器入口（扫描状态，建议调 guide-arch、guide-plan 或 guide-ship） | `skill_use("guide")` |
| `guide-arch` | **新** 架构定义阶段（5 子阶段：`setup → adr-create → architecture → roadmap-define → arch-done`） | `skill_use("guide-arch")` |
| `guide-plan` | **新** 变更生成阶段（4 子阶段：`scan → propose → deps → plan-done`） | `skill_use("guide-plan")` |
| `guide-ship` | **Ship 端状态机（Phase 1, 1.5, 2, 2.5, 3, 4, 5）**：`plan → verification → execute → review → archive → cleanup → ship-done`，含轻量/worktree 自动检测 | `skill_use("guide-ship")` |
| `feature` | feature 管理（summary / dependency graph / per-feature status / execution order；feature- 前缀 change 完整性提示） | `skill_use("feature")` |
| `propose` | 扫描 ADR/代码生成建议列表（`proposal-suggestions.md`，JSON 数组格式） | `guide-plan` 内部 / 单独使用 |
| `roadmap` | 路线图管理（phase/category 结构 + AUTO-SPRINT sentinel，v2.0.1） | `guide-arch` 内部 / 单独使用 |
| `deps` | 依赖分析（含 subagent Step 3，结构化输出 `deps-analysis.json`，v2.0.1） | `guide-plan` 内部 / 单独使用 |
| `execute` | 在 worktree（或轻量模式当前分支）内执行任务，写 `tasks.md` 进度 | `guide-ship` 内部 / worktree 内单独使用 |
| `status` | 状态查看（tasks.md 进度 + iteration.json） | `guide-ship` 内部 / 单独使用 |
| `rddf-session` | **跨 OpenCode session 恢复**（ADR-0017）— 5 子命令：list / resume / abandon / heartbeat / status | `skill_use("rddf-session", "<sub>")` |
| `rdd-workflow-writing-plans` | 实施计划生成器（TDD 5 步结构，自包含，零外部依赖） | `guide-ship` Phase 1 内部 |

### Loop 引擎（v2.0）

Loop 引擎是 `skills/loop_engine.py` 入口的 Python 模块，不是 `skill_use()` 技能。它串联 8 内置检测器 + 7 内置动作 + 插件机制，支持插件化扩展。

**入口方式**：

```bash
# CLI 方式
python3 skills/loop_engine.py --config loop.yaml

# 编程方式（从其他 Python 模块导入）
from skills import loop_engine
```

**配置示例**（v2.0）：

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

## 完整流程：Arch + Plan 端

Arch 端 5 子阶段（`guide-arch`）+ Plan 端 4 子阶段（`guide-plan`），跨阶段通过 `.rddf/state/.arch-handoff.json` 软交接。**下面 5 个 `### Phase X` 小节是一个精简的用户视角 5 段流程**（Setup → Roadmap-define → Propose → Deps → Handoff），合并呈现 Arch Phase 1、Arch Phase 4、Plan Phase 2、Plan Phase 3、Plan Phase 4 这五个**最常用户操作**的节点；**完整的 9 阶段子模型**参考下方的存档列表（含 Arch Phase 2 ADR Create、Arch Phase 3 Architecture、Plan Phase 1 Scan）。

**精简 5 段用户视角（下面 5 个 `### Phase X` 小节逐一展开）：**

- Phase 1 — Setup（环境检查 + ADR-0016 工件发现，对应 Arch Phase 1）
- Phase 2 — Roadmap-define（`roadmap.md` + 可选 `roadmap-meta.yaml`，对应 Arch Phase 4）
- Phase 3 — Propose（扫描 + 创建 change，对应 Plan Phase 2）
- Phase 4 — Deps（依赖分析，对应 Plan Phase 3）
- Phase 5 — Handoff（交接给 Ship 端，对应 Plan Phase 4）

**完整 Arch 5 + Plan 4 子阶段存档列表（仅作引用，不在下面逐节展开）：**

- Arch Phase 1 — Setup（环境检查 + ADR-0016 工件发现）
- Arch Phase 2 — ADR Create（ADR-0016 → `docs/adr/` 默认 discovery）
- Arch Phase 3 — Architecture（ADR-0016 → `docs/architecture/` 可选/可重定位）
- Arch Phase 4 — Roadmap-define（`roadmap.md` + 可选 `roadmap-meta.yaml`）
- Arch Phase 5 — Arch-done（写 `.rddf/state/.arch-handoff.json` + rddf-session 完成）
- Plan Phase 1 — Scan
- Plan Phase 2 — Propose
- Plan Phase 3 — Deps
- Plan Phase 4 — Plan-done（写 `.rddf/state/.plan-handoff.json`）

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
  ADR 目录:      docs/adr
  Roadmap:       roadmap.md

请选择:
1. ✅ 继续 → 进入 adr-create 阶段
2. 🔄 重新检查
i. 其他操作
```

---

### Phase 2 — Roadmap-define（路线图管理）

确保路线图文件反映当前 phase/category 划分。文件路径由 ADR-0016 自动发现，**默认**是 `roadmap.md`（项目根目录），**可选**附带 `roadmap-meta.yaml`（phase/category 元数据）——后者不是必备文件，部分项目可能省略。

**职责**：
- 维护 `roadmap.md`（默认顶层 phase 列表；路径可由 SPEC_WORKFLOW_ROADMAP_PATH 环境变量覆盖）
- 维护 `roadmap-meta.yaml`（**可选** phase/category 元数据；arch 阶段用 `roadmap` 技能管理）
- 验证活跃 phase 与现有 change 一致
- 支持新增 phase（如 multi-phase 项目）

**行为**：
1. 读取 `roadmap.md`（+ `roadmap-meta.yaml`，如存在）
2. 比对 `openspec/changes/` 中已存在的 change 与 roadmap phase
3. 标记孤儿 change（roadmap 无对应 phase）
4. 提示创建新 phase（如果当前需求不属于任何现有 phase）

**何时跳过**：单 phase 项目，或新增 change 已明确归属于现有 phase。

---

### Phase 3 — Propose（扫描并创建 Change）

扫描 ADR 和代码 TODO，生成建议列表，用户选择后创建 artifacts。

**行为**：
1. 扫描 `docs/adr/ADR-*.md`（路径可由 ADR-0016 discovery 或 `SPEC_WORKFLOW_ADR_DIR` 覆盖）—— 找到已采纳但未实现的 ADR 项
2. 扫描 `docs/architecture/*-gap-analysis.md`（**默认 discovery 路径**，如不存在则跳过）—— 找到功能缺口
3. 扫描代码中的 `TODO`/`FIXME` 标记
4. 生成 `proposal-suggestions.md` 建议列表（**JSON 数组格式**，由 `json.load()` 解析，非 grep）

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
- 输出 `.rddf/state/.deps-candidates.json`（机器可读）+ `.rddf/state/.deps-output.md`（人类可读）
- 标注"可并行"vs"需串行"vs"被阻塞"

**行为**：
1. 扫描 `openspec/changes/*/specs/` 中的依赖声明
2. Step 1: 静态分析（语法级）
3. Step 2: 跨 change 重叠检测
4. Step 3: **subagent 语义分析**——使用 subagent 理解"change A 是否逻辑上依赖 change B"
5. Step 4: 汇总报告 + roadmap phase 整合

**何时跳过**：单 change 项目，或所有 change 明确无依赖。

---

### Phase 5 — Handoff（交接给 Ship 端）

`guide-plan` 的最后阶段：检查所有 `openspec/changes/<name>/{proposal,design,tasks}.md` 是否已 git 提交。

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

## 完整流程：Ship 端（Phase 1, 1.5, 2, 2.5, 3, 4, 5）

> Ship 端实际内部编号为 **1, 1.5, 2, 2.5, 3, 4, 5**（ship-done 是 Phase 5 退出判定）。
> - Phase 1 — Plan（commit + 模式检测 + 计划生成）
> - Phase 1.5 — Verification（worktree 验证 + 监控选择子菜单）
> - Phase 2 — Execute（监控 + 阻塞/分离执行）
> - Phase 2.5 — Review（execute 后债务扫描，可跳过）
> - Phase 3 — Archive（状态检查 + 归档 + post-archive fill hook）
> - Phase 4 — Cleanup（worktree + branch 清理）
> - Phase 5 — Ship-done（退出 + rddf-session 关闭）
>
> Phase 1 自动检测并行冲突：无其他 worktree 且仅此一个 change → ⚡ 轻量模式（直接在主仓库创建 branch + 跳过 worktree）；否则 → 🔀 worktree 模式。

### Phase 1 — Plan（Commit + 模式检测 + 计划生成）

为已提交的 change 创建工作区（worktree 或轻量分支）并生成 rdd-workflow 计划。

**入口条件**：`openspec/changes/<name>/{proposal,design,tasks}.md` 已 git 提交（`git show HEAD:<path>` 验证）。

**行为**：
1. **rddf-session 入口 hook（ADR-0017）**：创建或查找当前 opencode session 的 `stage_ship` rddf-session
2. 展示所有活跃 changes 的状态表
3. 用户选择要处理的 change
4. 执行 COMMIT GATE（脏检测 + 已提交验证）
5. **自动检测并行冲突 → 选择模式**：
   - 无其他 worktree **且** 仅此一个 change → ⚡ 轻量模式（创建 `openspec/<name>` branch + `git checkout`，**跳过** worktree 创建；后续归档走轻量归档路径）
   - 有活跃 worktree **或** 多个 change → 🔀 worktree 模式（创建 `.rddf/wt/<name>` 隔离 worktree；归档走 `archive_change`）
6. 在选定工作区通过内置 skill 生成计划：
   - `rdd-workflow-writing-plans` — 直接生成 `.rddf/plans/<CHANGE_NAME>.md`
   - 计划包含 TDD 5 步结构：Write failing test → Verify fail → Implement → Verify pass → **Summary / ready-for-archive**
   - **注意**：TDD 5 步中的「Commit」一词在 plan 词汇里指**「总结报告 + 标记该 Task 可进入 archive」的 archive 交接标记**，**不是** execute 阶段的 `git commit`；execute 阶段本身**不**做 `git commit` / `git push`，所有 git commit 动作留到 archive 阶段
   - 零外部依赖，零路径桥接，任何 AI 编程助手通用
7. **v2.0.1 iteration hook**：计划生成成功后，把 `iteration.json` 中该 change 的 `status` 从 `proposed` 切到 `in_worktree`，写入 `worktree_path` + `plan_path` + `tasks_total`
8. **立即选择运行时执行模式**（🔒 阻塞 / 🔓 分离，见上方「运行时执行模式」表）

**菜单示例**：

```
Plan 阶段

📋 活跃 Changes:
| 变更 | Artifacts | Worktree | 计划文件 |
|-----|-----------|----------|---------|
| fix-ns-pollution | ✅ | ❌ | ❌ |
| add-stream-pipes | ✅ | ❌ | ❌ |

请选择:
1. 为 fix-ns-pollution 创建工作区（轻量分支或 worktree）+ 生成计划
2. 为 add-stream-pipes 创建工作区（轻量分支或 worktree）+ 生成计划
3. 批量处理：为全部已提交的变化创建工作区
4. 🔄 切换当前焦点变更
5. ↩️ 返回 Propose 阶段（创建更多 change）
i. 其他输入
```

**工作区就绪 → 立即选择运行时执行模式**（⚡ 轻量模式 / 🔀 worktree 模式 由 Phase 1 自动检测，下方菜单按检测到的模式呈现对应状态行）：

```
fix-ns-pollution 工作区已就绪（🔀 worktree 模式），请选择执行方式：

📋 fix-ns-pollution 状态:
  执行模式: 🔀 worktree 模式（隔离 worktree）
  Worktree: .rddf/wt/fix-ns-pollution
  计划文件: .rddf/plans/fix-ns-pollution.md ✅
  任务数: 3

请选择执行方式:
1. 🔒 在此 session 执行（阻塞）— 等待任务完成后返回
2. 🔓 分离执行（新终端）— 给出操作指引，立即返回
i. 其他输入
```

> 轻量模式下菜单结构一致，仅「执行模式」与目录项替换为：
> ```
> fix-ns-pollution 工作区已就绪（⚡ 轻量模式），请选择执行方式：
>
> 📋 fix-ns-pollution 状态:
>   执行模式: ⚡ 轻量模式（主仓库分支，无 worktree 隔离）
>   分支: openspec/fix-ns-pollution
>   计划文件: .rddf/plans/fix-ns-pollution.md ✅
>   任务数: 3
> ```

**分离执行指引**（按 Phase 1 检测出的模式分别给出）：

```
🔓 分离执行指引（🔀 worktree 模式）

为 fix-ns-pollution 启动分离执行：

1. 在新终端中执行：
   cd "$PROJECT_ROOT/.rddf/wt/fix-ns-pollution"
   skill_use("execute")

2. execute 结果会自动写入 tasks.md

3. 完成后，在此 session 运行 guide-ship 查看最新进度

当前状态：fix-ns-pollution 🔓 等待分离执行（worktree）
```

```
🔓 分离执行指引（⚡ 轻量模式）

为 fix-ns-pollution 启动分离执行：

1. 在新终端中执行：
   cd "$PROJECT_ROOT"
   git checkout openspec/fix-ns-pollution
   skill_use("execute")

2. execute 结果会自动写入 tasks.md

3. 完成后，在此 session 运行 guide-ship 查看最新进度

当前状态：fix-ns-pollution 🔓 等待分离执行（轻量分支）
```

**返回 Plan 前的检查 — 是否进入监控**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 发现 1 个工作区已就绪（🔀 worktree 模式）

请选择:
1. ✅ 进入 Execute 阶段（实时监控所有 worktree + 轻量分支进度）
2. 🔄 继续返回 Plan 阶段（创建更多工作区）
i. 其他输入
```

> 轻量模式下提示信息替换为「📋 发现 1 个轻量分支已就绪（⚡ 轻量模式）」；多 change 混合时显示「📋 发现 N 个工作区已就绪（M 个 worktree + N-M 个轻量分支）」。

---

### Phase 2 — Execute（监控与执行）

Execute 阶段是**监控模式**——读取 `tasks.md` 进度、显示所有 worktree **和** 轻量分支状态、提供执行入口。**不是实际执行者**（实际执行在 worktree 内或轻量分支当前目录的 sub-session 中完成）。

**监控模式入口点**（三处均可进入）：

| 入口点 | 触发条件 |
|--------|---------|
| **工作流状态恢复** | 新 session 调用 `guide-ship`，检测到已有 worktree 或轻量分支 |
| **Plan 返回前** | 工作区（轻量分支或 worktree）就绪后选择执行模式前（Phase 1.5） |
| **Execute 菜单** | 任何时候可刷新或返回 Plan |

**前置检测**（每次入口执行，覆盖 worktree + 轻量两种模式）：

```bash
# 读取所有 tasks.md 的实际进度
LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

# Worktree 模式
for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    branch=$(git worktree list | grep "$wt" | awk '{print $3}')
    name=$(echo "$branch" | sed 's|openspec/||')
    tasks_file="$wt/openspec/changes/$name/tasks.md"
    total=$(grep -c "^- \[" "$tasks_file" 2>/dev/null || echo 0)
    done=$(grep -c "^- \[x\]" "$tasks_file" 2>/dev/null || echo 0)
    echo "  $name → ${done}/${total} [worktree]"
done

# 轻量模式补充：有 openspec/ 分支但不在 worktree 列表
for branch in $(git branch | grep "openspec/" | sed 's/.*openspec\///'); do
    # ... 跳过已计入 worktree 的分支 ...
    tasks_file="$PROJECT_ROOT/openspec/changes/$branch/tasks.md"
    # ...
    echo "  $branch → ${done}/${total} [轻量]"
done

echo "上次检测: $LAST_CHECK"
```

**菜单示例**：

```
Execute 阶段（监控模式）

📋 所有 Changes 状态:（实时读取 tasks.md，覆盖 worktree + 轻量）
| 变更 | 模式 | 进度 | 执行状态 |
|-----|------|------|---------|
| fix-ns-pollution | worktree | 1/3 | 🔒 执行中 |
| add-stream-pipes | 轻量 | 2/5 | 🔓 分离执行 |

上次检测: 2026-05-18 10:35:00

请选择:
1. 🔒 在此 session 执行 fix-ns-pollution（阻塞）
2. 🔓 分离执行 fix-ns-pollution（新终端）
3. 🔒 在此 session 执行 add-stream-pipes（阻塞）
4. 🔓 分离执行 add-stream-pipes（新终端）
5. 📋 查看任务列表（指定变更）
6. 🔧 运行构建验证（指定变更）
7. 🔄 刷新进度（重新读取所有 tasks.md）
8. ↩️ 返回 Plan 阶段（创建更多工作区）
i. 其他输入
```

**关键特性**：
- 任何时候可以返回 Plan 阶段添加更多 worktree/轻量分支
- 进度来自 `tasks.md` 实际读取，每次入口自动刷新
- 「🔄 刷新进度」可手动重新读取所有 `tasks.md`
- 「上次检测」时间戳让用户知道状态是实时的
- **Execute 主要写 `tasks.md`** + 触发 v2.0.1 `iteration.json` 状态更新（不是 `.rddf/state/deps-analysis.json`——后者只在 `guide-plan` deps 阶段 / Review 自动增量时写入）

---

### Phase 2.5 — Review（执行后审查）

**入口条件**：execute 已完成（`tasks.md` 中所有 `[ ]` 已变 `[x]`），或用户主动选择审查。

**定位**：execute 在 worktree（或轻量分支）中执行 change 后，可能产生三类新债务：
- **范围内债务**：当前 change scope 内不完整（测试覆盖不全、遗漏边角情况）
- **旁效应债务**：独立的代码遗留问题（修 A 文件时发现 B 文件有遗留 TODO）
- **架构漂移**：执行结果偏离 ADR 定义的目标架构

本阶段自动扫描这些债务，分类，并提供回流机制。**默认可跳过（选项 4），不影响 archive**。

**1. 采集债务**：

- 扫描 execute 后新增的 `TODO`/`FIXME`/`HACK`/`WORKAROUND` 标记（git diff HEAD）
- 检测测试回归（`ctest --test-dir build` 等）
- 写入 `/tmp/review_new_todos.txt` + `/tmp/review_test_failures.txt`

**2. 分类展示（用户交互）**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 执行后审查 (Review Phase)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 ${CHANGE_NAME} (${done}/${total} tasks ✅)

🔍 债务扫描结果:
  新增 TODO/FIXME: [N] 条
  测试失败: [N] 个

请选择:
1. 🏠 范围内债务 → 追加到当前 change tasks.md（返回 execute）
2. 🔖 创建新 debt change → 加入 proposal-suggestions.md (type=debt)
3. 📐 架构漂移 → 回注 guide-arch (生成差距分析)
4. ⏭️  跳过 → 直接进入 archive（默认）
5. 📋 查看详细债务内容
i. 手动输入新 change 名称
```

**关键约束**：
- 旁效应债务的 deps 重新分析由**文件冲突**驱动（ADR-0014 决策 3），不按 change type 判断：新 debt change 与活跃 change 共享关键词 → 自动增量 deps（写 `.rddf/state/.deps-candidates.json` + 触发 `deps`）；否则可安全 deferred
- 门控实现：`skills/_lib/gate.py` 的 `review_debt_recorded`（warning 级，不阻断 archive）

---

### Phase 3 — Archive（状态检查 + 归档）

检查所有 change 状态，对可归档的 change 执行 `archive_change`（worktree 模式）或轻量归档路径。

**职责**：
- 读取每个 worktree / 轻量分支的 `tasks.md` 进度
- 识别 100% 完成的 change（可归档）
- 模式检测：有 worktree → `archive_change`；无 worktree → 轻量归档（直接 merge branch + 删除分支 + `openspec archive`）
- 调用 `archive_change` 合并到 default branch + `openspec archive`
- 检查是否还有未处理 change/worktree
- **rddf-session 关闭 hook（ADR-0017）**：archive 成功后刷新对应 `stage_ship` rddf-session 心跳
- **post-archive fill suggestion hook（v2.0.1）**：archive 后扫描 `iteration.json`，找出 `status="planned"` 且 blocker 已 archived 的 change，输出 fill 建议（不自动调用 `guide-plan fill`）

**菜单示例**：

```
Status 阶段

📋 所有 Changes 状态:
| 变更 | 模式 / 工作区 | 任务进度 | 状态 |
|-----|---------------|---------|------|
| fix-ns-pollution | worktree: .rddf/wt/fix-ns-pollution | 3/3 ✅ | 可归档 |
| add-stream-pipes | 轻量分支: openspec/add-stream-pipes | 2/5 🔄 | 进行中 |

请选择:
1. 归档 fix-ns-pollution（merge → archive）
2. 查看 add-stream-pipes 进度（继续执行）
3. 📊 全局概览（所有 change + 工作区）
4. 🔍 详细检测（同步问题等）
5. ↩️ 返回 Execute 阶段
i. 其他输入
```

**推荐方式**（使用项目自带 helper；`guide-ship` 自动检测模式并选择正确路径）：

```bash
# 🔀 worktree 模式：在主仓库 master 分支上调用
source skills/_lib/archive.sh
archive_change "<change-name>"
```

> `archive_change` 是 **worktree 模式专属 helper**——它假设存在对应 `.rddf/wt/<name>` 路径。轻量模式下该 helper 不适用，详见下方轻量归档路径。

`archive_change` 内部执行：
1. **Pre-merge check**：worktree 存在 + 干净 + 在正确分支
2. **Checkout default branch**（动态检测 main/master/develop）+ **fast-forward merge**（如不可 FF，回退到 `--no-ff`）
3. **`openspec archive "<name>" --yes`**：移动 change 到 `openspec/changes/archive/<date>-<name>/`
4. **Worktree remove** + **branch delete**（自动）

**手动方式**（debug/特殊场景；按模式分别给出）：

🔀 worktree 模式手动归档：

```bash
cd "$PROJECT_ROOT"
DEFAULT_BRANCH=$(find_default_branch)  # 来自 skills/_lib/worktree.sh
git checkout "$DEFAULT_BRANCH"
git merge --ff-only "openspec/${CHANGE_NAME}"
openspec archive "${CHANGE_NAME}" --yes
git worktree remove ".rddf/wt/${CHANGE_NAME}"   # 仅 worktree 模式需要
git branch -d "openspec/${CHANGE_NAME}"
```

⚡ 轻量模式手动归档（**没有 worktree**——无需 `git worktree remove`）：

```bash
cd "$PROJECT_ROOT"
DEFAULT_BRANCH=$(find_default_branch)  # 来自 skills/_lib/worktree.sh
git checkout "$DEFAULT_BRANCH"
git merge --ff-only "openspec/${CHANGE_NAME}" || \
    git merge --no-ff "openspec/${CHANGE_NAME}" -m "merge: ${CHANGE_NAME} change"
openspec archive "${CHANGE_NAME}" --yes
git branch -d "openspec/${CHANGE_NAME}" || \
    [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ] && git branch -D "openspec/${CHANGE_NAME}"
# 轻量模式下没有 .rddf/wt/<name> 路径，无需 worktree remove
```

> 实际生产中 `guide-ship` 会自动检测模式（Phase 3 模式检测）并选择正确路径，上方两段仅供理解 + debug 场景使用。

### Phase 4 — Cleanup（worktree / branch 清理）

所有 archive 完成后，批量清理剩余的 worktree（worktree 模式产物）和 `openspec/*` branches（worktree + 轻量模式都会留下 branch）。轻量模式没有 `.rddf/wt/<name>` 路径，无需 `git worktree remove`，仅需 `git branch -d openspec/<name>`。

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

**rddf-session 关闭 hook（ADR-0017）**：所有 changes 归档完成后，将 `stage_ship` rddf-session 标记为 `completed`，`end_reason="ship-done"`。

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
2. 回到 plan 端 (skill_use("guide-plan")) — 创建更多 changes
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
→ Plan 阶段 → Phase 1 自动检测 → 2 个 change，无其他 worktree → 🔀 worktree 模式
→ 创建 fix-ns-pollution worktree
→ 选择 🔓 分离执行
→ 切换 add-stream-pipes → 创建 worktree
→ 选择 🔓 分离执行
→ 进入 Execute 监控模式

（主控 session 保持可操作，可继续其他操作或等待）
```

**Terminal B（fix-ns-pollution worktree 模式执行）**：

```
cd "$PROJECT_ROOT/.rddf/wt/fix-ns-pollution"
skill_use("execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

**Terminal C（add-stream-pipes worktree 模式执行）**：

```
cd "$PROJECT_ROOT/.rddf/wt/add-stream-pipes"
skill_use("execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

> 轻量模式并行的等价写法（仅 1 个 change 时 `guide-ship` 自动选 ⚡）：
> ```
> cd "$PROJECT_ROOT"
> git checkout openspec/<name>
> skill_use("execute")
> ```

**回到 Terminal A**：

```
skill_use("guide-ship")
→ Execute 监控模式检测到 tasks.md 进度已更新
→ 显示最新进度
→ 可选择归档或继续监控
```

---

## 测试基础设施

> rdd-workflow 验证的测试组织与运行约定。

### 工具链

| 工具 | 用途 | 版本要求 |
|------|------|---------|
| `bats-core` | bash 自动化测试框架 | 1.10+（推荐 1.13+） |
| `git` | 测试工作树管理 | 2.25+ |
| `openspec` CLI | 验证 change artifacts | 1.3.1+ |

### 目录结构

> 当前实测（用 `ls tests/unit/*.py | wc -l` 等命令验证；数字随仓库演进会变化）：

| 层级 | 数量 | 工具 |
|------|------|------|
| `tests/unit/*.py` | 45 个 Python 单元测试 | pytest |
| `tests/integration/*.bats` | 47 个 bats 集成测试 | bats-core |
| `tests/integration/*.py` | 9 个 Python 集成测试 | pytest（loop / gate / phase_switch / iteration_lifecycle / iteration_archive_hook / guide_ship_iteration_hook / deps_analysis / hook_boundary / trigger_e2e） |

```
tests/
├── README.md                       # 测试说明
├── test_helper.bash                # setup/teardown + `load_lib` 解析器
├── conftest.py                     # 把项目根加进 sys.path (让 `import skills._lib.*` 可解析)
├── smoke.bats                      # 快速冒烟（7 个 smoke cases，npm test 会跑）
├── _lib/                           # 共享 bash 辅助 + bats 单元测试
│   ├── skill.bash                  # skill frontmatter/metadata/commands/section 解析
│   ├── deps-subagent.bash          # deps subagent Step 3 验证
│   ├── test_skill.bats             # skill.bash 单元测试（8 cases）
│   ├── test_state.bats             # skills/_lib/state.sh stub 锁定
│   └── test_worktree.bats          # skills/_lib/worktree.sh 单元测试
├── unit/                           # ~45 个 Python 单元测试 (pytest, 含 v2.0.1 新增: test_iteration / test_roadmap_sprint / test_deps_output / test_rddf_session / test_arch_handoff_schema / test_discover_arch_artifacts / test_arch_quality_gate / test_change_alignment / test_iteration_concurrency 等)
└── integration/                    # ~56 个集成测试 (47 .bats + 9 .py)
    ├── test_<issue-id>.bats        # P0/P1/P2/P3 fix 的回归锁
    ├── test_*_skill.bats           # 每个 skill 的结构/metadata 覆盖（含 feature / rddf-session）
    ├── test_*_subagent.bats        # subagent 集成测试
    ├── test_skill_metadata_consistency.bats  # package.json ↔ skills/ ↔ smoke.bats 一致性
    ├── test_adr_directory.bats     # docs/adr/ 完整性
    ├── test_archive_dedup.bats     # 归档去重
    ├── test_arch_discovery_contract.bats  # ADR-0016 工件发现契约
    ├── test_iteration_*.bats/.py   # iteration.json 生命周期
    ├── test_review_phase*.bats     # Phase 2.5 review
    ├── test_phase_numbering.bats   # 阶段编号一致性
    ├── test_usage_freshness.bats   # USAGE.md 新鲜度
    ├── test_loop_flow.py           # Loop 引擎集成（Python）
    ├── test_gate_transition.py     # 门控切换集成（Python）
    ├── test_phase_switch.py        # 阶段切换集成（Python）
    └── ...
```

### 运行测试

> ⚠️ **`npm test` 陷阱**：`npm test` 只跑 `bats tests/`，**不会**捕获 Python 测试失败。改完任何 Python 代码后必须显式 `pytest tests/`，CI 才会捕获。
>
> ⚠️ **`guide-arch` 首次因 `.gitignore` 失败**：运行检查器打印的 `fix_command` 后重新执行。

```bash
# === bats（npm test 等价命令，仅覆盖 shell 测试）===
npm test                                # 等价于 bats tests/，不跑 Python
bats tests/smoke.bats                   # 快速冒烟（7 个 smoke cases）
bats tests/_lib/test_skill.bats         # skill.bash parser（8 cases）

# === Python（必须显式调用，npm test 不会自动跑）===
python3 -m pytest tests/unit/ -q --tb=short         # Python 单元测试
python3 -m pytest tests/integration/ -q --tb=short  # Python 集成测试
python3 -m pytest tests/ -q --tb=short              # 一把跑全部 Python 测试

# === 安装 Python 依赖 ===
pip install -r requirements.txt   # PyYAML, jsonschema, pytest
```

CI 在 `.github/workflows/test.yml`，按序执行：安装 deps → **断言质量门控**（`grep -rn "assert.*or True\|assert True" tests/` 命中即 FAIL）→ Python unit → Python integration → bats smoke → bats static 子集 → bats git-worktree 子集。

### 编写新测试的约定

- **共享辅助函数**放在 `tests/_lib/*.bash`（被 `@load "<filename>"` 引用）
- **单元测试**在 `tests/_lib/test_*.bats`（直接调用 `_lib` 内的 bash 函数）
- **集成测试**在 `tests/integration/test_*.bats`（创建完整 OpenSpec change 进行端到端验证）
- **bats @test 命名**：`"模块: 场景描述"`，如 `@test "skill: metadata has name, version, evolved-from"`

详见 [tests/README.md](./tests/README.md)。

---

## ADR 生命周期

> 所有架构决策应记录为 ADR，按 `docs/adr/` 目录下的命名约定演进。

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

ADR 状态字段遵循 `docs/adr/README.md` 的五状态生命周期：

| 状态 | 含义 |
|------|------|
| **待定** | 已起草但尚未正式采纳 |
| **已采纳** | 当前生效 |
| **已拒绝** | 评估后未采纳（保留以记录历史） |
| **已弃用** | 曾生效但已被新决策替代 |
| **已替代为 ADR-NNN** | 显式指向替代者 |

### 何时写 ADR

- ✅ 引入新 phase/category（roadmap 变更）
- ✅ 拆分/合并技能（如 v2.0 重构 spec 端为 `guide-arch` + `guide-plan`）
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
| worktree 目录冲突 | `-d .rddf/wt/<name>` 但 `git worktree list` 未注册 | 提示 `rm -rf .rddf/wt/<name>` |
| tasks.md 不同步 | tasks.md 进度与 state 不一致 | Guide 入口时自动从 tasks.md 同步 |
| worktree 分支冲突 | `git worktree add` 失败 | 提供 `git worktree list` 查看现有 |
| 未 plan 就 status | `.rddf/plans/<name>.md` 不存在 | 提示先执行 plan |
| execute 不在工作区内 | `git branch --show-current` 非 `openspec/<name>`（轻量模式）/ 不在 `.rddf/wt/<name>`（worktree 模式） | 提示先 `cd` 到正确工作区（worktree 模式：`cd "$PROJECT_ROOT/.rddf/wt/<name>"`；轻量模式：`cd "$PROJECT_ROOT" && git checkout openspec/<name>`）或使用分离执行 |
| rdd-workflow-writing-plans 生成失败 | `.rddf/plans/<name>.md` 未生成 | 检查 worktree 内 skills 是否完整安装；手动触发 `skill_use("rdd-workflow-writing-plans")` |
| bats-core 缺失 | `bats --version` 失败 | 提示安装 bats-core 1.10+ |
| ADR 引用格式错误 | `grep -E "ADR-[0-9]+ §[0-9]+" proposal.md` 无匹配 | 提示按 ADR-NNN §N.M 格式补充 |

---

## 关键约束提醒

1. **COMMIT GATE**：工作区创建前必须 commit（worktree 模式：`git worktree add` 看不到 artifacts；轻量模式：`git checkout openspec/<name>` 需要 artifacts 在 HEAD 上）
2. **Branch 检查**：`git branch --show-current` 必须是 default branch（master/main/develop，由 `find_default_branch()` 动态检测）才能创建工作区
3. **不同步处理**：用 `awk index()` 直接修改 `tasks.md`，不重新 run plan（会覆盖 `.rddf/plans/`）
4. **Execute 主要写 `tasks.md`**：execute 不做 `git commit` / `git push`；它会把每个 Task 的进度写回 `tasks.md`，并经由 `skills/_lib/iteration.py` 触发 `iteration.json` 的状态变更（derived view hook）。`.rddf/state/deps-analysis.json` **不是** execute 产物——它只在 `guide-plan` deps 阶段 / Review 自动增量时被写入。
5. **任何时候可返回 Plan**：Execute 菜单有「返回 Plan 阶段」选项，可添加更多工作区（worktree 或轻量分支）
6. **ADR 是契约**：`docs/adr/ADR-*.md` 一旦 `已采纳`，必须由 `propose` 阶段的扫描器拾取并转化为 change
7. **Skill metadata 只读**：所有 skill 文件的 `name`/`version`/`compatibility`/`metadata` 前置字段不可修改
8. **execute 阶段不 commit/push**：plan 中明确 `Executor stops after the summary report`，commit 留到 archive 阶段

## On-main Mode Caveats

`tools/archive_on_main.sh` 是 archive 的 **OFF-HAPPY-PATH 旁路**——在 main 分支直接归档 change，跳过 worktree 隔离。默认 **拒绝** 执行；必须显式传 `--confirm-main` 才放行。本节说明与 worktree 模式的差异、iteration.json 契约、以及何时该用（不该用）这个旁路。

### 与 worktree 模式的差异

| 维度 | worktree 模式（`archive.sh::archive_change`） | on-main 模式（`tools/archive_on_main.sh`） |
|------|--------------------------------------------|------------------------------------------|
| 隔离 | 完整 worktree，独立 working tree | 直接在当前 git working tree 操作 |
| 分支 | 隐式创建 `openspec/<name>` 临时分支 | 不创建分支，直接改 default branch |
| 守护 | `archive_gate_check` 校验 task 进度 | 不做 task 进度校验（off-happy-path） |
| 触发 | `guide-ship` Phase 3 自动 | 用户手动调用 |
| 适用 | 标准 ship 流程（推荐） | 紧急 / 修复 incomplete change / 一次性清理 |
| 撤销 | `git reset --hard` 即可 | 需手动 `mv` archive dir 回 changes/ + 改 iteration.json |

### iteration.json sync 契约

on-main 模式在 `mv` 之后会调用 `sync_iteration_after_archive`（`skills/_lib/iteration/post_archive.py`），把 change entry 写为：

```json
{
  "status": "archived",
  "archived_at": "<ISO 8601 UTC>",
  "archive_commit_sha": "<--archive-commit-sha 参数值，或 git rev-parse HEAD>",
  "tasks_done": "<archive/<date>-<name>/tasks.md 的 [x] 数>",
  "plan_path": ".rddf/plans/<name>.md"
}
```

幂等保证：
- `archived_at` 已存在时**不覆盖**（防止 race condition 双调用）
- `archive_commit_sha` 已存在时不覆盖
- helper 失败（非零返回）时脚本 print warning 但**不滚回** archive mv——archive 成功是首要目标，iteration 漂移可后续 `rddf status --check-archive-sync` 修复

### 推荐用法

**✅ 适用场景**：

- 紧急修复已 archive 但 iteration.json 没同步的历史 stale entry
- `archive_gate_check` 因 tasks.md 未全部 `[x]` 阻断 standard flow，需绕过
- 一次性清理（demo / 临时仓库 / 内部工具）
- `add-archive-post-commit-hook` 还没安装的项目，裸 `git mv` 救场

**❌ 不该用**：

- 正常 ship 流程——请用 `archive.sh::archive_change`（worktree 模式，附 gate check）
- 多 change 并行——on-main 是串行，worktree 模式可并发
- CI/自动化——旁路缺 audit trail，应走 `guide-ship` Phase 3 统一管线

### 用法速查

```bash
# 1. 拒绝执行（必须 --confirm-main）
tools/archive_on_main.sh my-change
# → exit 2, "⚠️  OFF-HAPPY-PATH. Pass --confirm-main to archive without worktree."

# 2. 标准 on-main archive
tools/archive_on_main.sh my-change --confirm-main

# 3. 显式指定 archive commit SHA（避免 $GIT_HEAD 在 mv 之后漂移）
tools/archive_on_main.sh my-change --confirm-main --archive-commit-sha $(git rev-parse HEAD)

# 4. 失败回滚
mv openspec/changes/archive/2026-08-05-my-change openspec/changes/my-change
# 然后用 rddf status --check-archive-sync 修正 iteration.json
```

**⚠️ 警告**：本旁路是 archive-on-main 流程的 OFF-HAPPY-PATH。标准 ship 流程见 `guide-ship/SKILL.md` Phase 3（worktree 模式）。批量 archive / 自动化场景请用标准流程。

---

## 架构参考

最新架构决策详见 [ADR-0003](./docs/adr/ADR-0003-three-phase-architecture.md)。历史演进记录见 `docs/adr/` 与 `CHANGELOG.md`。
