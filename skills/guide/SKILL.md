---
name: guide
description: 交互式工作流入口——扫描项目当前状态，展示可选菜单（含 rddf-session 管理），用户可选菜单项执行或进入自由讨论模式咨询后再决定。详见 ADR-0017 (rddf-session) 和 ADR-0003 (三阶段架构)。
license: MIT
compatibility: Requires git 2.25+
metadata:
  version: "2.1"   # source-of-truth (latest semver)
  author: sisyphus
  evolved-from: "split from guide.md v3.0; v1.1 added rddf-session binding scan (spec 2026-07-14); v2.1 extracted entry script to scripts/guide_entry.sh"
  user-invocable: true
---

# OpenSpec 工作流 — 交互式入口

## 用途

`guide` 是**交互式工作流入口**。它扫描项目完整状态，向用户展示包含所有可选操作的菜单（含 ⭐ 推荐选项和 rddf-session 管理），用户选择后自动执行对应的动作。

**不持久化任何状态，不调用 openspec CLI，不修改任何文件。** 纯只读扫描 + 交互式引导。

## 流程

```
skill_use("guide")
    ↓
1. 运行 bash scanner (scan-state.sh) → 获取 RECOMMEND + REASON
2. 运行 Python synthesizer → 获取结构化推荐 + all_options（全部可选操作）
    ↓
3. AI 解析输出,构建交互菜单,通过 question tool 展示给用户
4. 用户选择 → AI 执行对应 skill_use()
    ↓
   对应的 guide-skill / rddf-session 命令自动处理 session 生命周期
```

## 扫描操作（AI 必须执行）

v2.1 起扫描入口已抽到 `skills/guide/scripts/guide_entry.sh` (含 4-tier 路径解析 fallback,处理 `bash -c` 上下文 BASH_SOURCE 失效)。**AI 不再直接复制 64 行 bash 代码**,改为以下 1 行调用:

```bash
SKILL_DIR=/workspace/project/rdd-workflow/skills/guide \
  bash -c 'source "$SKILL_DIR/scripts/guide_entry.sh" && guide_entry'
```

支持的参数:
- `guide_entry` (无参) — 人类可读输出
- `guide_entry --json` — 追加 `---BEGIN_RECO_JSON---...---END_RECO_JSON---` 块(供脚本消费)
- `guide_entry --no-binding` — 跳过 rddf-session binding 扫描
- `guide_entry --help` — 帮助

执行后导出 env vars (供 AI 解析菜单):
- `RECOMMEND` / `REASON` / `CONFIDENCE` — 推荐项
- `ALL_OPTIONS_JSON` — 所有菜单项 JSON 数组
- `WT_ISSUES_JSON` — 工作树干净度问题(`[]` 表示无)
- `BINDING_LINES` (bash 数组) — session 绑定信息

完整实现见 `skills/guide/scripts/guide_entry.sh` (~180 行,含详细注释 + 4-tier fallback)。脚本内部依次调用:
1. `scan-state.sh::scan_state()` — 13-path 决策树,产出 baseline `RECOMMEND`/`REASON`
2. `skills/_lib/workflow_synthesizer.py::synthesize()` — 结构化推荐(若可用,覆盖 baseline;失败时回退到 scan_state 结果)
3. `scan-state.sh::scan_session_binding()` — rddf-session binding 扫描(若未指定 `--no-binding`)

**扫描后**：你（AI）将扫描输出的结构化数据（`RECO_JSON` / `ALL_OPTIONS_JSON`）解析为菜单。扫描状态变量包括：
- `RECOMMEND` — 推荐的操作（如 `guide-plan`）
- `REASON` — 推荐原因（中文）
- `CONFIDENCE` — 置信度（high/medium/low）
- `ALL_OPTIONS_JSON` — 所有可选项的 JSON 数组
- `BINDING_LINES` — session 绑定信息数组（可能为空）
- `WT_ISSUES_JSON` — 工作树干净度问题列表（`wt_issues` 字段），每个 issue 含 `category`, `severity`, `auto_fixable`, `fix_command`, `detail`

### 工作树清理分析（AI 必须执行）

当 `WT_ISSUES_JSON` 非空时，你（AI）必须在展示菜单前执行清理分析。按 `severity` 分组，用你的判断力给出建议：

1. **safe_auto_fix**（可安全自动修复）：
   - 例如：已归档的 deleted 文件、build 产物目录
   - **AI 行为**：列出这些 issue，建议一键修复的命令
   - 示例输出：`🔧 可安全修复 (3): git rm -r openspec/changes/v1-0-release-prep/ openspec/changes/version-policy-adr/ && echo "build-*/" >> .gitignore`

2. **needs_review**（需人工判断）：
   - 例如：修改的配置文件、未暂存的代码变更、未关联归档的删除
   - **AI 行为**：解释为什么需要人工审查（可能丢失工作、可能影响其他流程），不自动执行
   - 示例输出：`⚠️ 需审查: .rddf/state/.plan-handoff.json 有本地修改 — 可能包含未保存的状态变更`

3. **info**（信息提示）：
   - 不需要立即行动的项目
   - **AI 行为**：简单列出，不阻塞主流程

AI 必须在分析后将清理建议展示给用户，但**不自动执行任何命令**。用户确认后（输入 `y` 或选择清理菜单项），AI 才执行。

> **阶段命令门控联动**：清理分析结果不仅用于菜单展示前的分析，也用于阶段命令门控（见下方"阶段命令门控（工作树检查）"步骤）。门控步骤在"执行选择"阶段触发，使用相同的 `WT_ISSUES_JSON` 数据，不重新扫描。

## 输入模式判别

AI 必须根据场景选择合适的输入收集方式：

**`question` 工具适用场景**：
- 阶段选择（guide-arch / guide-design / guide-plan / guide-ship）
- session 选择（resume rds_xxx）
- 固定结构化选项（优先级 P0/P1/P2）

**`question` 工具不适用场景**：
- 用户首次描述需求（必须用纯文本 prompt）
- 用户主动要求自由输入时
- 初始需求收集阶段

**判别决策树**：
1. 用户输入是菜单编号或选项名称？→ 视为选中，执行对应 action
2. 用户输入是自然语言问题？→ 进入自由讨论模式
3. 用户连续 2 次未选择明确类别？→ 切换到开放 prompt
4. 否则 → 默认使用 question 工具

## 交互菜单（AI 必须执行）

解析 `ALL_OPTIONS_JSON` 后，使用 `question` 工具向用户展示菜单。

### 菜单模板

```json
ALL_OPTIONS_JSON 结构:
[
  {"id": "guide-plan", "label": "guide-plan", "description": "进入变更生成阶段...",
   "action": "guide-plan", "group": "recommended"},
  ...
]
```

每个 option 的 `group` 决定展示位置：
- `recommended` — ⭐ 推荐（第 1 项,高亮）
- `stages` — 工作流阶段选项
- `session` — session 管理
- `utilities` — 其他工具

### 展示格式

向用户展示的菜单格式：

```
📋 Workflow Entry — 选择操作:

  ⭐ 1. {recommended.label} — {recommended.description}

  === Workflow Stages ===
  {N}. guide-arch    — setup → ADR → roadmap → arch-done
  {N+1}. guide-design — 创建/审查改进提案 → design-done
  {N+2}. guide-plan  — scan → propose → deps → plan-done
  {N+3}. guide-ship  — plan → execute → archive → cleanup

  === Session Management / Utilities ===
  ...（按 all_options 动态生成）

  === Other ===
  0. 💬 自由讨论 — 咨询项目状态,了解细节后再决定

选择 (0-{N}):
```

`question` 工具的选项列表为 `all_options` 中每项的 `label` + `description`，额外追加"💬 自由讨论"选项（推荐置于第 0 项或最后一项）。第一个选项（recommended）默认高亮。

### 自由讨论模式

当用户的选择不是菜单编号（或选择"自由讨论"）时，你进入 **自由讨论模式**：

1. 用户可以在该模式下自由对话：
   - 询问项目状态细节（"当前有哪些活跃 changes？"）
   - 咨询工作流含义（"arch 阶段具体做什么？"）
   - 讨论下一步策略（"你觉得先做哪个 change 比较好？"）
   - 查看 session 信息（"有哪些 orphaned session？"）
   - 任何与项目相关的开放性问题

1.5. **意图路由规则**（AI 必须执行）：当用户在自由讨论中表达以下意图时，AI 必须将意图路由到对应的标准技能，而非自行处理：

   | 用户意图 | 触发关键词 | 路由目标 | 禁止行为 |
   |---------|-----------|---------|---------|
   | 创建改进提案 | "创建改进提案"、"improvement"、"add-improve"、"添加改进"、"提出改进" | `skill_use("add-improve")` | **禁止手动创建 improvements/ 文件** — 必须通过 add-improve 交互式流程 |
   | 创建新 change | "创建提案"、"新建 change"、"propose"、"提一个 change"、"新增提案" | `skill_use("propose")` | **禁止手动创建文件**（mkdir + write proposal.md/tasks.md 等） |
   | 执行 change | "执行"、"开始做"、"ship"、"实施" + change 名称 | `skill_use("guide-ship")` | **禁止直接操作 worktree 或执行 plan** |
   | 设计审查 | "设计"、"design"、"提案"、"改进提案"、"改进" | `skill_use("guide-design")` | 禁止手动修改 proposal 文件 |
   | 变更规划 | "规划"、"plan"、"生成计划"、"扫描 change" | `skill_use("guide-plan")` | 禁止手动创建 plan 文件 |
   | 查看状态 | "查看状态"、"status"、"进度" | `skill_use("status")` | — |
   | 查看依赖 | "deps"、"依赖"、"依赖关系" | `skill_use("deps")` | — |
   | 查看 feature | "feature"、"功能视图" | `skill_use("feature")` | — |
   | session 管理 | "session"、"恢复"、"resume" | `skill_use("rddf-session", ...)` | — |

   **核心原则**：任何涉及创建或修改项目状态的意图，必须通过标准 workflow skill 执行，AI 不得自行处理。AI 检测到上述意图后，应提示用户并自动执行路由，而非在自由讨论中手动完成。

2. **每次回答完后，主动重新展示简版菜单**（不需要等用户要求）：
   ```
   ⭐ guide-plan / guide-design / guide-arch / guide-ship / resume rds_xxx / feature / status
   继续自由讨论 (输入 0 或直接提问)
   ```
   简版菜单只列选项名称（`label`），不列详细描述。保持一行紧凑格式，不给用户增加阅读负担。

3. 当用户输入菜单编号或对应选项名称时，视为选中，执行对应 `action`：
   - **阶段命令**（`group` 为 `recommended` 或 `stages`：`guide-arch`、`guide-design`、`guide-plan`、`guide-ship`、`rddf-session resume rds_xxx`）→ 执行后 guide 模式结束。
   - **工具命令**（`group` 为 `session` 或 `utilities`：`rddf-session list`、`rddf-session current`、`feature`、`status` 等）→ 执行后**重新展示完整菜单**（AI 回到步骤 1：运行 bash 扫描 + Python 合成器 + 重新展示菜单），不结束 guide 模式。

### 阶段命令门控（工作树检查）

当用户选择阶段命令（`guide-arch` / `guide-design` / `guide-plan` / `guide-ship`）时，AI 必须在执行 `skill_use()` 前检查 `WT_ISSUES_JSON`：

- 如果 `WT_ISSUES_JSON` 为空或仅含 `info` 级别 issue -> 直接执行，无提示
- 如果 `WT_ISSUES_JSON` 非空且包含非 `info` 级别 issue -> 展示提示：

  ```
  ⚠️ 工作树有 N 个待处理问题（M 删除 + K 修改）
  建议先清理再进入工作流阶段。

  1. 🧹 先清理（进入清理菜单）
  2. ⏭️  跳过，直接进入 [阶段名]
  ```

- 用户选择"跳过"后正常执行 `skill_use()`
- 用户选择"清理"后，引导用户选择 `🧹 清理 (N issues)` 菜单项

> **数据来源**：`WT_ISSUES_JSON` 由上方"工作树清理分析"步骤产出，此处复用相同数据，不重新扫描。

### 执行选择

> **前置门控**：执行下方任一阶段命令前，必须先完成"阶段命令门控（工作树检查）"步骤。

用户选择后，AI 执行对应 `action`。根据 action 类型，post-action 行为不同：

**阶段命令**（执行后 guide 模式结束，进入对应阶段状态机）：
- `"guide-arch"` → `skill_use("guide-arch")` — 该 skill 自动处理 rddf-session entry hook
- `"guide-design"` → `skill_use("guide-design")` — 同上
- `"guide-plan"` → `skill_use("guide-plan")` — 同上
- `"guide-ship"` → `skill_use("guide-ship")` — 同上
- `"rddf-session resume rds_xxx"` → 先调 `skill_use("rddf-session", "resume", "rds_xxx")` 恢复 session，然后根据 session kind 调对应的 guide skill

**工具命令**（执行后重新展示完整菜单，循环不退出）：
- `"rddf-session list"` → `skill_use("rddf-session", "list")` → **展示结果后，AI 重新运行 bash 扫描 + Python 合成器 + 重新展示完整菜单**
- `"rddf-session current"` → 同上
- `"feature"` → `skill_use("feature")` → **同上**
- `"status"` → `skill_use("status")` → **同上**

**循环实现**：对于工具命令，AI 在 action 执行完毕后，自动回到 "bash 扫描 + Python 合成器 + 展示菜单" 步骤，不结束 guide 模式。用户可通过选择阶段命令或直接输入阶段命令名称退出循环。

Session 管理自动完成：guide skills 的 entry/close hooks 已在 `guide-arch.md` / `guide-design.md` / `guide-plan.md` / `guide-ship.md` 中实现，不需要额外操作。

### 完整流程示例

```
用户: skill_use("guide")
  ↓
AI 执行扫描 → 展示菜单:
  ⭐ 1. guide-design — 进入设计阶段（审查改进提案）
  2. guide-plan — 进入变更生成阶段
  3. guide-arch  ...
  4. guide-ship  ...
  4. rddf-session list — 查看所有 session
  0. 💬 自由讨论

用户: "当前有哪些活跃 changes？"  ← 非编号,自动进讨论
  ↓
[自由讨论模式]
AI: "有 3 个 changes: add-auth (proposed), fix-ns-pollution (in worktree), add-stream-pipes (proposed)..."
    ⭐ guide-plan / guide-arch / guide-ship / ...   ← 主动展示简版菜单

用户: "fix-ns-pollution 卡在哪？"   ← 继续讨论
  ↓
AI: "worktree 内 tasks.md 显示 2/5 完成,被 deps 分析标记为阻塞中..."
    ⭐ guide-design / guide-plan / guide-arch / guide-ship / ...   ← 再次展示

用户: "guide-plan"  ← 选中阶段命令
  ↓
AI 执行 skill_use("guide-plan") → 结束

---

用户: skill_use("guide")
  ↓
AI 执行扫描 → 展示菜单:
  ⭐ 1. guide-ship — 进入变更执行阶段
  2. guide-arch  ...
  3. guide-plan  ...
  4. rddf-session list — 查看所有 session
  5. feature — 查看 feature 视图
  0. 💬 自由讨论

用户: "4"  ← 选择工具命令 rddf-session list
  ↓
AI 执行 skill_use("rddf-session", "list") → 展示 session 列表
  ↓ (循环 — 不结束 guide 模式)
AI 重新运行扫描 → 重新展示完整菜单:
  ⭐ 1. guide-ship — 进入变更执行阶段
  ...

用户: "5"  ← 选择工具命令 feature
  ↓
AI 执行 skill_use("feature") → 展示 feature 视图
  ↓ (再次循环)
AI 重新运行扫描 → 重新展示完整菜单
  ...

用户: "1"  ← 选择阶段命令 guide-ship
  ↓
AI 执行 skill_use("guide-ship") → 结束
```

### 意图路由示例

```
[自由讨论模式]
用户: "创建一个修复 LSP 兼容性的提案"  ← 命中 propose 意图
  ↓
AI: "检测到创建提案意图，路由到 propose 标准流程 →"
    skill_use("propose")

用户: "开始执行 wave-1 的 fix-lsp-dash-bridge"  ← 命中 ship 意图
  ↓
AI: "检测到执行 change 意图，路由到 guide-ship →"
    skill_use("guide-ship")
```

## 输出格式（旧版兼容）

当 `--json` 未设置时，扫描器打印人类可读的状态概览：

```
📋 Workflow Entry — <project_name>
   ───────────────────────────────────────────
   roadmap.md: ✅
   .arch-handoff.json: ✅
   .plan-handoff.json: ❌
   📍 Current: rds_xxx (kind=stage_arch, started=2026-07-22T...)
```

当 `--json` 设置时，追加 JSON 块供脚本消费。

## 过期状态检测

`scan_state()` 末尾自动调用 `check_stale_workflow_state()`（在 `scan-state.sh` 中），检测遗留的 `workflow-state.md`。

## Cross-Reference

- **rddf-session** (`skills/rddf-session.md`) — session 管理 5 子命令（list/show/resume/abandon/archive-history）
- **ADR-0017** (`docs/adr/ADR-0017-rddf-session.md`) — rddf-session 数据模型、跨 OpenCode session 恢复语义
- **ADR-0003** (`docs/adr/ADR-0003-three-phase-architecture.md`) — arch → plan → ship 三阶段架构
- **scan-state.sh** (`scripts/scan-state.sh`) — 底层扫描脚本；13-path 决策树 + session binding 扫描
