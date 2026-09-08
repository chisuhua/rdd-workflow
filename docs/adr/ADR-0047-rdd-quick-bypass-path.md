# ADR-0047: rdd-quick bypass path — 无 openspec change 的快速执行路径

> **状态**: 已采纳
> **日期**: 2026-09-07
> **决策者**: rdd-workflow maintainer
> **关联**: ADR-0028 (role model), ADR-0045 (verifier self-contained pattern)

## 背景

四阶段流程（`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`，ADR-0003 / ADR-0043）以 openspec change 为每一环的载体：

```
rdd-planner    → 写 openspec/changes/<name>/proposal.md
rdd-builder P0 → 读 proposal.md，写 openspec/specs/<name>/spec.md
rdd-builder P1 → 写 design.md + tasks.md + .rddf/plans/<name>.md
rdd-builder P2 → execute 消费 plan，回写 tasks.md
rdd-verifier   → AC 从 proposal.md 的 ## 验收标准 段提取
```

一个只改 1-2 个文件的小改动，走完整四阶段需要创建 improvement 提案、注册索引、审批落盘、生成 specs/design/tasks、建 worktree、执行、merge、archive。用户「有个想法直接干掉」的诉求在当前架构中无处安放；手动绕过流程又失去 TDD 约束与 AC 验证，质量不可控。

## 决策

新增独立 skill `skills/rdd-quick/`，提供一条**不以 openspec change 为载体、但仍保留 TDD 纪律与 AC 验证**的快速执行路径。

### D1 — 归属：独立 skill `rdd-quick`

**新建独立 skill**，不挂在 `rdd-planner` 之下。理由：`rdd-planner` frontmatter `role.boundaries.not_owns` 显式列出 `.rddf/plans/<name>.md` 与 `.rddf/state/builder/<name>.json`。rdd-quick 的核心动作（生成计划 + 执行 + 验证）全部落在 rdd-planner 的 not_owns 范围内，按 ADR-0028 角色模型必须独立。

### D2 — 计划文件路径：`.rddf/plans/quick-<name>.md`

共用 `.rddf/plans/` 目录（git 追踪）+ `quick-` 前缀隔离。理由：`skills/rdd-doctor/scripts/checks/plan_tdd_check.py` 扫描整个 `.rddf/plans/` 目录校验 5 个 TDD marker，必须复用该契约；`quick-` 前缀避免与正式 change 同名文件撞车。

### D3 — 复杂度门槛：无硬阈值

**AI agent 综合判断**，SKILL.md 列判定信号清单供参考（≥4 复杂信号 + ≥4 简单信号）。理由：硬阈值会让"小改"和"伪装成小改的大改"被一刀切；agent 综合判断 + 向用户说明依据更稳健。

### D4 — Oracle / Metis 形态：prose spawn 指令

**SKILL.md 内联指令**，不引入程序化 subagent。理由：项目内 Oracle / Metis / Momus 均不是程序化 subagent，仅作为评审角色名出现。沿用 `rdd-verifier` v2.0（ADR-0045）的既定模式 —— 执行 skill 的 AI agent 自身就是 LLM，verdict 协议内联在 SKILL.md 内。

### D5 — 验证协议：复用 rdd-verifier verdict JSON

**直接复用 `VERDICT_ITEM_SCHEMA` 字段**（ac_id / description / status / confidence / evidence / reasoning），AC 来源改为计划文件 `## Acceptance` 段（而非 `proposal.md` 的 `## 验收标准` 段）。理由：verdict 协议已成熟（ADR-0045），复用降低认知负担；AC 来源切换是唯一改动。

### D6 — 失败处理：有界重试 + 引导升级

**3 次上限 + stdout 升级摘要**，不自动落盘 change。理由：(a) 自动生成的 proposal 质量存疑 (b) 升级本身是能力边界信号 (c) 让人工把关。

### D7 — 追溯：独立审计日志

`.rddf/state/.quick-history.jsonl` append-only 11 字段原子写，**不接入** `iteration.json` / `sessions.json` / `roadmap-state.json`。理由：零污染正式流程视图。

### D8 — 零污染契约：可验证

**spec Scenario 锁文件 hash**：`select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh` / `rdd-planner/SKILL.md::role:` 块的 sha256 必须不变。理由：把"零污染"从文字承诺变成机器可验的 AC，实施时一旦触碰立即失败。

### 五阶段状态机

```
P0 plan 生成     → .rddf/plans/quick-<name>.md (TDD 5 marker + ## Acceptance)
P1 复杂度判定    → AI 综合判断；复杂则 Metis + Oracle 双审 + 用户确认
P2 就地执行     → 当前分支，无 worktree，按 plan TDD 5 步执行
P3 Oracle 验证  → 从 plan ## Acceptance 段读 AC，按 rdd-verifier verdict 协议判定
P4 完成 / 重试 / 升级  → 全 pass: append history / 有 fail: 重试 ≤3 / 超限: stdout 升级摘要
```

## 与既有"轻"概念的区分表

| 概念 | 位置 | 与 rdd-quick 关系 |
|------|------|------------------|
| `execution_mode: lightweight` | `_lib/builder_deps.py::decide_execution_mode` | 仍需完整 openspec change；rdd-quick 完全跳过 change |
| `git.openspec_tracked: false` | `_lib/archive.sh` L546 分支 | 仍走 `openspec archive`；rdd-quick 不调 archive |
| serial / parallel | `_lib/ship_execution_mode.sh` | 与 change 存在性无关；rdd-quick 完全无 ship |
| `QUICK_FINISH_DETECTED` env var | rdd-builder P1.5 | 已被占用；rdd-quick 用 `RDDF_QUICK_*` 前缀 |
| `SKIP_PROMETHEUS_PLANNING` env var | rdd-builder P1 | 已被占用；rdd-quick 禁止读写 |

## 与 `guide-ship-quick-finish` 提案的边界

| 维度 | `guide-ship-quick-finish`（P2, unapproved） | `rdd-quick`（本 ADR） |
|------|------------------------------------------|---------------------|
| 起点 | 已有 change，剩余任务 ≤2 且均为文档/状态更新 | 无 change，仅一段自然语言提案文本 |
| 跳过 | worktree + plan 生成 + execute | openspec change 创建 + worktree |
| 计划文件 | 明确不产出（其技术约束第 3 条） | 必产出 `.rddf/plans/quick-<name>.md` |
| 终点 | review → archive | Oracle 验证 → 完成（无 archive） |

**不合并、不修改、不废弃** `.rddf/improvements/guide-ship-quick-finish.md`。两个场景互补，长期共存。

## 环境变量契约

| 变量 | 默认 | 语义 |
|------|------|------|
| `RDDF_QUICK_MAX_RETRIES` | `3` | P4 重试上限 |
| `RDDF_QUICK_PLAN_DIR` | `.rddf/plans` | 计划文件目录 |
| `RDDF_QUICK_HISTORY_FILE` | `.rddf/state/.quick-history.jsonl` | 审计日志路径 |
| `RDDF_QUICK_SKIP_REVIEW` | `false` | 跳过 P1 Metis/Oracle 审查（紧急） |
| `SKIP_RDDF_QUICK_VERIFY` | `false` | 跳过 P3 验证（紧急） |

**明确禁止读写**（见 `skills/rdd-quick/SKILL.md` frontmatter `metadata.forbidden_env_vars`）：`QUICK_FINISH_DETECTED`、`SKIP_PROMETHEUS_PLANNING`（rdd-builder 占用）。

## 审计日志 schema v1

`.rddf/state/.quick-history.jsonl` 11 字段，schema 落盘 `_lib/schemas/quick_history_schema.json`：

```json
{
  "name": "quick-<name>",
  "started_at": "2026-09-07T10:00:00Z",
  "ended_at": "2026-09-07T10:25:00Z",
  "plan_file": ".rddf/plans/quick-<name>.md",
  "complexity": "simple|complex",
  "reviewed_by": ["metis", "oracle"],
  "verdict_summary": { "total": 3, "pass": 3, "fail": 0 },
  "retry_count": 0,
  "outcome": "completed|escalated|unverified",
  "commit_sha": "abc1234",
  "upgraded_to_change": null
}
```

## Consequences

### 正面

- 小改动的仪式成本从 ~ 12h 降到 ~ 5min
- 保留 TDD 5 步与 AC 验证纪律，质量下限不降
- 复杂改动经 Metis + Oracle 双审，避免"快速路径变成绕过审查的后门"
- 验证失败超限时引导升级到正式流程，快速路径认清能力边界

### 负面

- 新增 skill 维护负担（SKILL.md 演进 + 11 字段 schema 演进）
- 升级路径非自动，用户需手动走 rdd-planner
- AI agent 的复杂度判定本身可能有偏差，需要复盘校准

### 风险与缓解

| 风险 | 缓解 |
|------|------|
| 快速路径被滥用为绕过审查的后门 | P1 综合判定 + Metis/Oracle 双审 + 3 次重试上限 + 升级引导，四道防线 |
| 与三个既有"轻"概念混淆 | 命名用 `rdd-quick` 而非 `lightweight`；环境变量用 `RDDF_QUICK_` 前缀；spec 显式区分表 |
| 与 `guide-ship-quick-finish` 提案混淆 | 边界对照表写入提案与 ADR；两提案并存不合并 |
| AI agent 的复杂度判定偏差 | SKILL.md 列出判定信号清单；agent 需向用户说明依据；升级路径兜底 |
| 审计日志膨胀 | append-only JSONL，每行 < 1KB；无清理机制（建议后续提案加 retention policy） |
| 计划文件污染 `.rddf/plans/` | `quick-` 前缀隔离；`rdd-doctor plan_tdd_check` 同时校验两类文件 |

## 实现状态

- `openspec/changes/add-rdd-quick-skill/` — 提案 + design + tasks + spec + plan
- `skills/rdd-quick/SKILL.md` — P0-P4 prose 状态机
- `skills/rdd-quick/scripts/scaffold_plan.sh` — TDD 5 marker + ## Acceptance 脚手架
- `skills/rdd-quick/scripts/append_history.py` — 原子追加审计日志
- `_lib/quick_history.py` + `_lib/schemas/quick_history_schema.json` — 数据层
- `tests/unit/test_quick_history.py` — 9 单测
- `tests/integration/test_rdd_quick.bats` — 14 集成测试
- `tests/integration/test_rdd_quick_isolation.bats` — 4 零污染 hash 锁定测试

## 参考

- 上游 improvement：`.rddf/improvements/add-rdd-quick-skill.md`
- 相关 ADR：ADR-0003 / ADR-0028 / ADR-0034 / ADR-0043 / ADR-0044 / ADR-0045
- 共存提案：`.rddf/improvements/guide-ship-quick-finish.md`
- 复用协议：`skills/rdd-verifier/SKILL.md` § LLM Verification Protocol
- 约束来源：`skills/rdd-doctor/scripts/checks/plan_tdd_check.py`