# add-rdd-quick-skill

**优先级**: P1 | **来源**: 2026-09-07 用户提出 — 现有四阶段流程对小改动过重，缺少「有想法直接干」的执行路径
**阶段**: v2.2 | **分类**: arch-design
**类型**: feature
**主题**: 编排能力完善

> **症状**：一个只改 1-2 个文件的小改动，走完整四阶段（rdd-arch → rdd-planner → rdd-builder → rdd-verifier）需要创建 improvement 提案、注册索引、审批落盘 proposal.md、生成 specs/design/tasks、建 worktree、执行、merge、archive。用户「有个想法直接干掉」的诉求无处安放。
> **根因**：四阶段架构（ADR-0003 / ADR-0043）的每一环都以 openspec change 为载体。缺少一条不以 change 为载体、但仍保留 TDD 纪律与 AC 验证的执行路径。

## 架构依据

**症状（2026-09-07 用户诉求）**：

用户希望「除了目前走 rdd-planner / rdd-builder / rdd-verifier 之外，另外添加一个轻量执行路径」，具体要求：

1. 不创建 openspec change
2. 直接根据输入的提案内容创建计划文件
3. 不创建 worktree
4. 计划复杂就调用 Oracle + Metis 审查计划，不复杂就直接执行
5. 执行后再通过 Oracle 验证

**现有三个"轻"概念都不满足该诉求**：

| 既有概念 | 位置 | 语义 | 为何不满足 |
|---|---|---|---|
| `execution_mode: lightweight` | `_lib/builder_deps.py::decide_execution_mode` | 跳过 worktree，在主仓库就地执行 | 仍需完整 openspec change（proposal/design/tasks/specs） |
| `git.openspec_tracked: false` | `_lib/archive.sh` L546 分支 | archive 时跳过 git merge/commit | 仍走 `openspec archive`，仍需 change 目录 |
| serial / parallel | `_lib/ship_execution_mode.sh` | 同 change 内多 wave 的串并行 | 与 change 存在性无关 |

**已有未批准提案 `guide-ship-quick-finish`（P2, 2026-07-24）是不同场景**：

| 维度 | `guide-ship-quick-finish`（既有提案，未批准） | `rdd-quick`（本提案） |
|---|---|---|
| 起点 | 已有 openspec change，剩余任务 ≤2 且均为文档/状态更新 | 无 change，仅一段自然语言提案文本 |
| 跳过 | worktree + plan 生成 + execute | openspec change 创建 + worktree |
| 计划文件 | 明确不产出（其技术约束第 3 条） | 产出 `.rddf/plans/quick-<name>.md` |
| 终点 | review → archive | Oracle 验证 → 完成（无 archive） |
| 验证 | 依赖既有 archive gate | 复用 rdd-verifier verdict 协议，AC 来自计划文件 |

两者互不覆盖，可长期共存。本提案在 Out Scope 显式声明不合并、不修改该提案。

**根因分析**：

四阶段流程的每一环都硬依赖 `openspec/changes/<name>/`：

```
rdd-planner  → 写 openspec/changes/<name>/proposal.md
rdd-builder P0 → 读 proposal.md，写 openspec/specs/<name>/spec.md
rdd-builder P1 → 写 design.md + tasks.md + .rddf/plans/<name>.md
rdd-builder P2 → execute 消费 plan，回写 tasks.md
rdd-verifier   → AC 从 proposal.md 的 ## 验收标准 段提取
```

现有执行器/验证器的三个硬阻断点（探索确认）：

| 位置 | 阻断行为 |
|---|---|
| `skills/execute/scripts/select_worktree.sh:28-31` | 当前分支不匹配 `openspec/*` 即 `return 1` |
| `skills/execute/scripts/tasks_writeback.sh:31` | `openspec/changes/<name>/tasks.md` 不存在即 `return 1` |
| `skills/rdd-verifier/SKILL.md` LLM Protocol Step 1 | AC 从 `proposal.md` 的 `## 验收标准` 段正则提取 |

`update_roadmap_progress.sh:34` 与 `execute_step7.py` 均为 graceful skip，不构成阻断。

**Oracle / Metis 的可用形态**（探索确认）：

项目内 Oracle / Metis / Momus 均**不是**程序化 subagent，仅作为评审角色名出现在 ADR 与 design.md 的评审记录中。唯一的程序化 subagent 调用是 `skills/deps/SKILL.md` Step 3e 的 `task(subagent_type=..., ...)`，且该调用本身也是写给 AI agent 读的 SKILL.md 指令，bash 无法直接触发。

因此 Oracle/Metis 审查与 Oracle 验证只能实现为 **SKILL.md 内的 prose 指令**，由执行本 skill 的 AI agent 自行 spawn。这与 `rdd-verifier` v2.0（ADR-0045）的既定做法完全一致 —— 该 ADR 明确"执行验证的 AI agent 自身就是 LLM"，将 LLM 验证协议内联进 SKILL.md 而非依赖外部进程。本提案沿用同一模式，不引入新范式。

**角色边界依据（ADR-0028）**：

`rdd-planner` frontmatter 的 `role.boundaries.not_owns` 显式列出 `.rddf/plans/<name>.md` 与 `.rddf/state/builder/<name>.json`。本提案的核心动作（生成计划 + 执行 + 验证）全部落在 `rdd-planner` 的 not_owns 范围内，故必须新建独立 skill，不得挂在 `rdd-planner` 之下。

**影响范围**：

- 小改动（改 1-2 文件、修 typo 级逻辑、补一个 helper）不再需要走完整四阶段
- 保留 TDD 纪律与 AC 验证，不牺牲质量下限
- 复杂改动经 Metis + Oracle 双审，避免"快速路径变成绕过审查的后门"
- 验证失败超限时引导升级到正式流程，快速路径不承担超出其能力的任务

## 范围

### In Scope

**A. 新建 `skills/rdd-quick/SKILL.md`**：

含 frontmatter（`name` / `description` / `license` / `compatibility` / `metadata` / `role`），`role.boundaries` 按 ADR-0028 定义：

```yaml
role:
  title: "Quick Executor (快速执行者)"
  perspective: "Bypass openspec change ceremony for small, well-scoped changes while preserving TDD discipline and AC verification."
  boundaries:
    owns:
      - ".rddf/plans/quick-*.md"
      - ".rddf/state/.quick-history.jsonl"
    not_owns:
      - "openspec/changes/<name>/"
      - "openspec/specs/<name>/"
      - ".rddf/wt/<name>/"
      - "docs/adr/ADR-*.md"
      - ".rddf/state/iteration.json"
      - ".rddf/state/sessions.json"
      - ".rddf/plans/<name>.md"   # 无 quick- 前缀者归 rdd-builder
    human_involvement: "medium"
```

**B. 5 个 Phase 的状态机**（全部为 SKILL.md prose 指令 + 少量 bash helper）：

| Phase | 动作 |
|---|---|
| P0 | 收集提案内容（自然语言），确定 kebab-case 名称，生成 `.rddf/plans/quick-<name>.md` |
| P1 | 复杂度判定（AI agent 综合判断，无硬阈值）→ 简单直接进 P2；复杂则 Metis 审歧义 + Oracle 审方案 → 用户确认 |
| P2 | 就地执行（当前分支，无 worktree），按计划文件的 TDD 5 步逐 task 执行 |
| P3 | Oracle 验证：按 rdd-verifier verdict JSON 协议逐条 AC 判定 |
| P4 | 全 pass → 追加审计日志完成；有 fail → 有界重试（≤3）；超限 → 输出升级摘要引导 rdd-planner |

**C. 计划文件格式 `.rddf/plans/quick-<name>.md`**：

- git 追踪（`.rddf/plans/` 已在 `.gitignore` 第 9 行注释中声明为 tracked）
- `quick-` 前缀避免与正式路径的 change 同名文件撞车
- **必须含 TDD 5 步标记**（`skills/rdd-doctor/scripts/checks/plan_tdd_check.py` 会扫描整个 `.rddf/plans/` 目录并校验 5 个固定 marker：`Write the failing test` / `Run test to verify it fails` / `Write minimal implementation` / `Run test to verify it passes` / `Defer commit`）
- 必须含 `## Acceptance` 段（P3 验证的 AC 来源，取代正式路径的 `proposal.md` `## 验收标准`）

**D. 复杂度判定原则**（写入 SKILL.md，由 AI agent 综合判断）：

判定为「复杂」的信号（任一命中即建议走审查）：
- 涉及公共接口 / 跨模块契约变更
- 需要修改既有 gate、handoff schema、或状态文件 schema
- 有数据迁移 / 破坏性变更 / 回滚风险
- 改动横跨 3 个以上模块，或触及 `_lib/core/`、`_lib/schemas/`
- 用户描述本身存在多种合理解读

判定为「简单」的信号（全部满足才可直接执行）：
- 改动局限在单一模块内部
- 无公共接口变更
- 有明确的、可自动验证的成功标准
- 失败可通过 `git checkout` 无损回滚

**E. 审计日志 `.rddf/state/.quick-history.jsonl`**：

append-only JSONL，每次执行追加一行：

```json
{
  "name": "quick-<name>",
  "started_at": "2026-09-07T10:00:00Z",
  "ended_at": "2026-09-07T10:25:00Z",
  "plan_file": ".rddf/plans/quick-<name>.md",
  "complexity": "simple",
  "reviewed_by": [],
  "verdict_summary": { "total": 3, "pass": 3, "fail": 0 },
  "retry_count": 0,
  "outcome": "completed",
  "commit_sha": "abc1234",
  "upgraded_to_change": null
}
```

schema 落盘 `_lib/schemas/quick_history_schema.json`（version 1）。

**F. 升级摘要**（P4 重试超限时输出到 stdout，不落盘 change）：

含原始提案文本、已做的改动清单（`git diff --stat`）、失败的 AC 及其 verdict reasoning、建议的 AC 修正方向、以及 `skill_use("rdd-planner")` 的下一步提示。审计日志 `outcome` 记为 `escalated`。

**G. `rdd-planner/SKILL.md` 加一行指向提示**：

仅在其 `## See also` 段追加一行指向 `skills/rdd-quick/`。**不修改** `rdd-planner` 的 `role.boundaries` 与其他任何段落。

**H. 测试**：

- `tests/unit/test_quick_history.py` — 审计日志 schema + 读写（≥6 case）
- `tests/integration/test_rdd_quick.bats` — SKILL.md 结构 + role 边界 + 计划文件 TDD marker + 审计日志 append（≥8 case）
- `tests/integration/test_rdd_quick_isolation.bats` — 零污染验证：确认不写 `openspec/`、`.rddf/wt/`、`iteration.json`、`sessions.json`（≥4 case）

**I. 文档**：

- 新 ADR（`docs/adr/ADR-NNNN-rdd-quick-bypass-path.md`，编号取 `docs/adr/` 当前最大值 +1）
- `AGENTS.md` 加 rdd-quick 段（含与三个既有"轻"概念的区分表）
- `README.md` 技能列表加 `rdd-quick/SKILL.md` 一行

### Out Scope

- **不修改** `skills/execute/scripts/select_worktree.sh`（rdd-quick 自行处理工作区，不复用该脚本）
- **不修改** `skills/execute/scripts/tasks_writeback.sh`（rdd-quick 不写 `tasks.md`）
- **不修改** `_lib/archive.sh`（rdd-quick 无 archive 阶段，不调 `openspec archive`）
- **不修改** `rdd-planner` 的 `role.boundaries`（仅在 `## See also` 加一行）
- **不修改** `rdd-builder` / `rdd-verifier` / `rdd-arch` 的任何 Phase 逻辑
- **不合并、不修改、不废弃** `.rddf/improvements/guide-ship-quick-finish.md`（不同场景，各自演进）
- **不复用** `QUICK_FINISH_DETECTED` / `SKIP_PROMETHEUS_PLANNING` 环境变量（已被 rdd-builder 占用，rdd-quick 用 `RDDF_QUICK_*` 前缀）
- **不实现** 自动升级为正式 change（P4 仅输出引导摘要，由用户手动走 rdd-planner）
- **不实现** 硬编码的复杂度阈值（判定原则写入 SKILL.md 供 AI agent 综合判断）
- **不接入** `iteration.json` / `sessions.json` / `roadmap-state.json`（零污染正式流程视图）
- **不实现** worktree 隔离（就地执行是本路径的定义特征）

## 关键场景

### 场景 1: 简单改动直接执行

- **GIVEN** 用户调用 `skill_use("rdd-quick")` 并描述「给 `_lib/state.sh` 的 `count_pending_suggestions` 加一个空文件的边界处理」
- **WHEN** P0 生成 `.rddf/plans/quick-fix-count-pending-empty.md`，P1 判定为简单（单模块 / 无接口变更 / 可回滚）
- **THEN** 跳过 Metis + Oracle 审查，直接进 P2 就地执行 TDD 5 步
- **AND** P3 Oracle 验证全 pass，P4 追加 `.quick-history.jsonl` 一行，`outcome: completed`
- **AND** 未创建 `openspec/changes/`、未创建 `.rddf/wt/`、未改 `iteration.json`

### 场景 2: 复杂改动触发双审

- **GIVEN** 用户描述「重构 handoff schema 让 planner 和 builder 共用一个格式」
- **WHEN** P1 判定复杂（触及 `_lib/schemas/` + 跨模块契约 + 有兼容性风险）
- **THEN** spawn Metis 审歧义 + Oracle 审方案，输出各自结论
- **AND** 通过 `question` 工具请用户确认是否按审查意见修订计划后执行
- **AND** 审计日志 `complexity: "complex"`，`reviewed_by: ["metis", "oracle"]`

### 场景 3: 验证失败有界重试

- **GIVEN** P2 执行完成，P3 Oracle 验证发现 AC-2 状态为 `fail`
- **WHEN** P4 进入重试（`retry_count` 1 → 2 → 3）
- **THEN** 每轮按 verdict 的 `reasoning` 修正实现后重新验证
- **AND** 第 2 轮全 pass → `outcome: completed`，`retry_count: 2`

### 场景 4: 超限升级引导

- **GIVEN** P4 重试已达 3 次，AC-2 仍为 `fail`
- **WHEN** 触发升级路径
- **THEN** stdout 输出升级摘要（原始提案 + `git diff --stat` + 失败 AC + verdict reasoning + 建议 AC 修正）
- **AND** 提示 `skill_use("rdd-planner")` 走正式流程
- **AND** 审计日志 `outcome: "escalated"`，**不**创建 `openspec/changes/` 任何文件

### 场景 5: rdd-doctor 校验通过

- **GIVEN** `.rddf/plans/quick-<name>.md` 已生成
- **WHEN** 运行 `bash skills/rdd-doctor/scripts/doctor.sh --category plan-tdd`
- **THEN** 不产生该文件的 WARNING（5 个 TDD marker 齐全）

### 场景 6: 与正式路径同名不撞车

- **GIVEN** `.rddf/plans/` 已存在正式路径产物 `add-foo.md`
- **WHEN** rdd-quick 处理同名主题 `foo`
- **THEN** 写入 `.rddf/plans/quick-add-foo.md`，既有 `add-foo.md` 不被读取、不被覆盖

## 技术约束

- **MUST NOT**: 修改 `select_worktree.sh` / `tasks_writeback.sh` / `archive.sh` / `rdd-planner` 的 `role.boundaries`
- **MUST NOT**: 写入 `openspec/changes/` 或 `openspec/specs/` 任何路径
- **MUST NOT**: 创建 git worktree 或 `openspec/*` 分支
- **MUST NOT**: 写入 `iteration.json` / `sessions.json` / `roadmap-state.json` / `.plan-handoff.json` / `.planner-handoff.json`
- **MUST NOT**: 调用 `openspec archive` 或任何 `openspec` CLI 写操作
- **MUST NOT**: 复用 `QUICK_FINISH_DETECTED` / `SKIP_PROMETHEUS_PLANNING` 环境变量
- **MUST**: 计划文件含全部 5 个 TDD marker（通过 `plan_tdd_check.py` 校验）
- **MUST**: 计划文件含 `## Acceptance` 段且至少 1 条 checkbox（P3 的 AC 来源）
- **MUST**: 计划文件名以 `quick-` 前缀开头
- **MUST**: P3 verdict JSON 格式与 `rdd-verifier` 的 `VERDICT_ITEM_SCHEMA` 一致（`ac_id` / `description` / `status` / `confidence` / `evidence` / `reasoning`）
- **MUST**: 重试上限 3（对齐 `rdd-verifier` 的 `RDDF_VERIFIER_MAX_LOOPS` 默认值），可通过 `RDDF_QUICK_MAX_RETRIES` 覆盖
- **MUST**: 审计日志为 append-only，原子写（temp + rename）
- **MUST**: 环境变量统一 `RDDF_QUICK_` 前缀
- **MUST**: 遵守 env-var 传参模式，禁止 `python3 -c "...$VAR..."` 内联插值（Oracle C1）
- **SHOULD**: P1 复杂度判定原则以清单形式写入 SKILL.md，便于人工复核 AI 判断
- **SHOULD**: `SKIP_RDDF_QUICK_VERIFY=yes` 可跳过 P3（仅紧急，留审计痕迹 `outcome: "unverified"`）

## 验收标准

### Skill 结构

- [ ] `skills/rdd-quick/SKILL.md` 存在，frontmatter 含 `name` / `description` / `license` / `compatibility` / `metadata` / `role` 全部字段
- [ ] `role.boundaries.owns` 含 `.rddf/plans/quick-*.md` 与 `.rddf/state/.quick-history.jsonl`
- [ ] `role.boundaries.not_owns` 含 `openspec/changes/<name>/`、`.rddf/wt/<name>/`、`docs/adr/ADR-*.md`、`.rddf/state/iteration.json`
- [ ] SKILL.md 含 P0–P4 五个 Phase 的完整指令
- [ ] SKILL.md 含复杂度判定原则清单（简单信号 + 复杂信号各 ≥4 条）
- [ ] SKILL.md 含 Metis + Oracle 审查的 spawn 指令（prose，对齐 ADR-0045 模式）
- [ ] SKILL.md 含 P3 verdict JSON 协议（与 rdd-verifier `VERDICT_ITEM_SCHEMA` 字段一致）

### 计划文件契约

- [ ] 生成的计划文件路径为 `.rddf/plans/quick-<name>.md`
- [ ] 计划文件含全部 5 个 TDD marker
- [ ] 计划文件含 `## Acceptance` 段且至少 1 条 checkbox
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category plan-tdd` 对该文件无 WARNING

### 审计日志

- [ ] `_lib/schemas/quick_history_schema.json` 存在，version 1
- [ ] `.rddf/state/.quick-history.jsonl` 为 append-only，每次执行追加 1 行
- [ ] 日志含 `name` / `started_at` / `ended_at` / `plan_file` / `complexity` / `reviewed_by` / `verdict_summary` / `retry_count` / `outcome` / `commit_sha` / `upgraded_to_change` 全部字段
- [ ] `outcome` 取值覆盖 `completed` / `escalated` / `unverified`
- [ ] 写入为原子操作（temp + rename）

### 零污染验证

- [ ] rdd-quick 全流程后 `git status` 显示未新增 `openspec/changes/` 任何文件
- [ ] 未创建 `.rddf/wt/` 任何目录
- [ ] `iteration.json` / `sessions.json` / `roadmap-state.json` 内容不变
- [ ] `select_worktree.sh` / `tasks_writeback.sh` / `archive.sh` 文件 hash 不变
- [ ] `rdd-planner/SKILL.md` 仅 `## See also` 段有增行，`role:` 段逐字节不变

### 测试

- [ ] `tests/unit/test_quick_history.py` ≥6 case 全绿
- [ ] `tests/integration/test_rdd_quick.bats` ≥8 case 全绿
- [ ] `tests/integration/test_rdd_quick_isolation.bats` ≥4 case 全绿
- [ ] `./test.sh --full --regression` 无新增失败（对齐 AGENTS.md 归档前回归门）

### 文档

- [ ] 新 ADR 落盘 `docs/adr/ADR-NNNN-rdd-quick-bypass-path.md`，编号为当前最大值 +1，状态「已采纳」
- [ ] ADR 含与 `execution_mode: lightweight` / `git.openspec_tracked: false` / serial-parallel 三者的区分表
- [ ] ADR 含与 `guide-ship-quick-finish` 提案的边界说明
- [ ] `AGENTS.md` 加 rdd-quick 段（含四概念区分表 + 环境变量清单）
- [ ] `README.md` 技能列表含 `rdd-quick/SKILL.md`

### 兼容性

- [ ] 既有四阶段流程行为零变化（arch / planner / builder / verifier 各自的 bats 全绿）
- [ ] `.rddf/plans/` 下既有 60+ 正式路径计划文件不受影响
- [ ] `rdd-doctor` 5 类校验对既有文件的结论不变

## Why

- **现状痛点**：小改动走完整四阶段的仪式成本远超改动本身。用户「有个想法直接干掉」的诉求在当前架构中无处安放，只能手动绕过流程 —— 而手动绕过既无 TDD 约束也无 AC 验证，质量不可控。
- **修复价值**：提供一条**有纪律的**快速路径 —— 省掉 openspec change 与 worktree 的仪式，但保留 TDD 5 步与 AC 验证。复杂时强制双审（Metis 审歧义 + Oracle 审方案），避免快速路径退化为绕过审查的后门。验证超限时引导升级，让路径认清自己的能力边界。
- **Why now**: 项目已完成 v4 四阶段收敛（ADR-0043/0044）与 verifier 自包含化（ADR-0045）。verifier 的 verdict 协议成熟可复用，`plan_tdd_check` 已能守住计划文件质量下限 —— 快速路径的两块基础设施都已就位，现在实现的边际成本最低。
- **P1 依据**：新增编排路径属核心能力扩展，直接影响日常工作流效率；且实现完全 additive（零修改既有路径），风险可控。

## What Changes

- `skills/rdd-quick/SKILL.md`: 新建（P0–P4 状态机 + 复杂度判定原则 + Metis/Oracle spawn 指令 + verdict 协议）
- `skills/rdd-quick/scripts/`: 新建辅助脚本（计划文件脚手架生成、审计日志追加、零污染自检）
- `_lib/schemas/quick_history_schema.json`: 新建（version 1）
- `_lib/quick_history.py`: 新建（审计日志 append + 读取 + schema 校验）
- `skills/rdd-planner/SKILL.md`: `## See also` 段加一行（其余逐字节不变）
- `docs/adr/ADR-NNNN-rdd-quick-bypass-path.md`: 新 ADR
- `AGENTS.md`: 加 rdd-quick 段
- `README.md`: 技能列表加一行
- `tests/unit/test_quick_history.py`: 新建
- `tests/integration/test_rdd_quick.bats`: 新建
- `tests/integration/test_rdd_quick_isolation.bats`: 新建

## Capabilities

- MUST: 从自然语言提案内容直接生成 `.rddf/plans/quick-<name>.md`（含 TDD 5 步 + `## Acceptance`）
- MUST: 由 AI agent 综合判定复杂度，复杂时 spawn Metis + Oracle 审查并请用户确认
- MUST: 就地执行（当前分支，无 worktree，不写 `tasks.md`）
- MUST: 执行后按 rdd-verifier verdict 协议逐条验证 AC
- MUST: 验证失败有界重试（≤3），超限输出升级摘要引导 rdd-planner
- MUST: 每次执行追加 `.rddf/state/.quick-history.jsonl` 审计行
- MUST NOT: 创建 openspec change / worktree / `openspec/*` 分支
- MUST NOT: 修改既有四阶段任何 Phase 逻辑或 `rdd-planner` 的 role 边界
- MUST NOT: 自动落盘正式 change（升级仅引导，不代劳）

## Impact

- MUST: 既有四阶段流程零行为变化（additive-only 实现）
- MUST: `.rddf/plans/` 下既有正式路径文件不被读取或覆盖（`quick-` 前缀隔离）
- MUST: 不污染 `iteration.json` / `sessions.json` / `roadmap-state.json` 等正式流程视图
- MUST: 计划文件通过 `rdd-doctor --category plan-tdd` 校验（共用目录的代价）
- SHOULD: 复用 rdd-verifier verdict 协议而非另造，降低认知负担
- MUST NOT: 引入新的 KNOWN_FAILURES 条目

## Acceptance

- [ ] `skills/rdd-quick/SKILL.md` 含 P0–P4 五 Phase + 复杂度判定原则 + Metis/Oracle spawn 指令 + verdict 协议，`role.boundaries` 符合 ADR-0028
- [ ] 简单改动路径：生成 `.rddf/plans/quick-<name>.md` → 直接执行 → Oracle 验证全 pass → 追加审计日志，全程零 openspec/worktree 产物
- [ ] 复杂改动路径：触发 Metis + Oracle 双审 + 用户确认，审计日志 `complexity: "complex"` 且 `reviewed_by` 记录两者
- [ ] 验证失败重试 ≤3 次；超限输出升级摘要且 `outcome: "escalated"`，不创建任何 `openspec/changes/` 文件
- [ ] 生成的计划文件含全部 5 个 TDD marker，`rdd-doctor --category plan-tdd` 无 WARNING
- [ ] 零污染验证：`select_worktree.sh` / `tasks_writeback.sh` / `archive.sh` hash 不变，`rdd-planner/SKILL.md` 的 `role:` 段逐字节不变
- [ ] `_lib/schemas/quick_history_schema.json` v1 + 审计日志 11 字段齐全 + 原子写
- [ ] 6 单元测试 + 12 集成测试全绿，`./test.sh --full --regression` 无新增失败
- [ ] 新 ADR（含四概念区分表 + 与 `guide-ship-quick-finish` 边界说明）+ AGENTS.md 段 + README 一行
