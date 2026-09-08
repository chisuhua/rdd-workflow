## Why

四阶段流程（rdd-arch → rdd-planner → rdd-builder → rdd-verifier）对小改动过重：1-2 个文件的修改需要走 improvement 提案 → 审批落盘 proposal.md → 生成 specs/design/tasks → 建 worktree → 执行 → merge → archive 全套仪式。用户「有个想法直接干掉」的诉求无安放之处，手动绕过又失去 TDD 约束与 AC 验证。

本 change 新增独立 skill `skills/rdd-quick/`，提供一条**不以 openspec change 为载体、但仍保留 TDD 纪律与 AC 验证**的快速执行路径。

详细 Why 见 `proposal.md`。本文件聚焦 architectural design。

## What Changes

### 架构决策汇总

| Decision | 裁决 | 理由 |
|----------|------|------|
| D1 — 归属：独立 skill `rdd-quick` | **新建独立 skill** | rdd-planner frontmatter `role.boundaries.not_owns` 显式列出 `.rddf/plans/<name>.md`；挂载会破坏 ADR-0028 角色模型 |
| D2 — 计划文件路径：`.rddf/plans/quick-<name>.md` | **共用目录 + 前缀隔离** | rdd-doctor `plan_tdd_check.py` 扫描整个目录，必须含 TDD 5 marker；`quick-` 前缀避免与正式 change 同名撞车 |
| D3 — 复杂度门槛：无硬阈值 | **AI agent 综合判断** | 硬阈值会让"小改"和"伪装成小改的大改"被一刀切；SKILL.md 列判定信号清单供 agent 参考 + 向用户说明依据 |
| D4 — Oracle/Metis 形态：prose spawn 指令 | **SKILL.md 内联指令** | 项目内 Oracle/Metis 不是程序化 subagent，唯一可执行的 `task(subagent_type=...)` 调用也是写在 SKILL.md 给 agent 读的指令。沿用 rdd-verifier v2.0 (ADR-0045) 模式 |
| D5 — 验证协议：复用 rdd-verifier verdict JSON | **直接复用 `VERDICT_ITEM_SCHEMA` 字段** | AC 来源改为计划文件 `## Acceptance` 段（而非 `proposal.md` `## 验收标准`）；其他字段（ac_id / status / confidence / evidence / reasoning）一字不动 |
| D6 — 失败处理：有界重试 + 引导升级 | **3 次上限 + stdout 升级摘要** | 不自动落盘 change，理由：(a) 自动生成的 proposal 质量存疑 (b) 升级本身就是能力边界信号 (c) 让人工把关 |
| D7 — 追溯：独立审计日志 | **`.rddf/state/.quick-history.jsonl`** | append-only 11 字段，原子写；不接入 `iteration.json` / `sessions.json` / `roadmap-state.json`，零污染正式流程视图 |
| D8 — 零污染契约：可验证 | **spec Scenario 锁文件 hash** | spec 中 4 个 Scenario 锁住 `select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh` / `rdd-planner role:` 段的 hash 不变；实施时一旦触碰立即失败 |

### 路径对比表

| 路径 | rdd-quick | 正式 openspec 路径 |
|---|---|---|
| openspec change | ❌ 不创建 | ✅ 必有 |
| worktree | ❌ 不创建 | ✅ light/worktree |
| plan 文件 | ✅ `.rddf/plans/quick-<name>.md` | ✅ `.rddf/plans/<name>.md` |
| tasks.md | ❌ 不写 | ✅ 必有 |
| TDD 5 marker | ✅ 必有 | ✅ 必有 |
| AC 来源 | 计划文件 `## Acceptance` 段 | proposal.md `## 验收标准` 段 |
| 验证协议 | rdd-verifier verdict JSON (复用) | rdd-verifier verdict JSON |
| 重试上限 | 3 (RDDF_QUICK_MAX_RETRIES 可覆盖) | 3 (RDDF_VERIFIER_MAX_LOOPS) |
| archive | ❌ 不调 openspec archive | ✅ 必有 |
| 审计入口 | `.rddf/state/.quick-history.jsonl` | iteration.json / sessions.json / archive |

### 与既有"轻"概念的边界

| 概念 | 位置 | rdd-quick 与其关系 |
|---|---|---|
| `execution_mode: lightweight` | `_lib/builder_deps.py::decide_execution_mode` | 仍需完整 openspec change；rdd-quick 完全跳过 change |
| `git.openspec_tracked: false` | `_lib/archive.sh` L546 分支 | 仍需 change 目录 + `openspec archive` 调用；rdd-quick 不调 archive |
| serial / parallel | `_lib/ship_execution_mode.sh` | 与 change 存在性无关；rdd-quick 完全无 ship 阶段 |

### 与 `guide-ship-quick-finish` 提案的边界（已共存，不合并）

| 维度 | guide-ship-quick-finish (P2, unapproved) | rdd-quick (本 change) |
|---|---|---|
| 起点 | 已有 change，剩余任务 ≤2 且均为文档/状态更新 | 无 change，仅一段自然语言提案文本 |
| 跳过 | worktree + plan 生成 + execute | openspec change 创建 + worktree |
| 计划文件 | 明确不产出 | 必产出 |
| 终点 | review → archive | Oracle 验证 → 完成 |

### 五阶段状态机（P0-P4）

```
[P0 plan 生成]
  AI 收集自然语言提案 → 写 .rddf/plans/quick-<name>.md (含 TDD 5 marker + ## Acceptance)
    ↓
[P1 复杂度判定 + 可选审查]
  AI 综合判定：
  ├─ 简单 → 直入 P2
  └─ 复杂 → spawn Metis 审歧义 + Oracle 审方案
          → question 工具请用户确认
          → 直入 P2
    ↓
[P2 就地执行]
  当前分支直接改（不创建 openspec/* 分支）
  按计划文件 TDD 5 步逐 task 执行
    ↓
[P3 Oracle 验证]
  从 .rddf/plans/quick-<name>.md 的 ## Acceptance 段提取 AC
  按 rdd-verifier verdict JSON 协议逐条判定
  输出 verdict 数组 [{ac_id, description, status, confidence, evidence, reasoning}]
    ↓
[P4 完成 or 重试 or 升级]
  ├─ 全 pass → 追加 .quick-history.jsonl, outcome=completed
  ├─ 有 fail 且 retry_count < 3 → 修正后重 P2/P3, retry_count += 1
  └─ 有 fail 且 retry_count == 3 → 输出升级摘要到 stdout
                                 outcome=escalated
                                 提示 skill_use("rdd-planner")
                                 （不落盘任何 openspec/changes/ 文件）
```

### 文件清单与契约

**新增文件**：

| 路径 | 类型 | 行数预算 | 责任 |
|---|---|---|---|
| `skills/rdd-quick/SKILL.md` | SKILL | ~250 | P0-P4 prose 指令 + role.boundaries |
| `skills/rdd-quick/scripts/scaffold_plan.sh` | bash | ~60 | 脚手架生成 quick-*.md（不含 TDD 内容，仅模板） |
| `skills/rdd-quick/scripts/append_history.py` | Python | ~80 | 原子追加 .quick-history.jsonl，含 schema 校验 |
| `_lib/quick_history.py` | Python | ~100 | 读写 + schema 校验公共 API |
| `_lib/schemas/quick_history_schema.json` | JSON schema | ~50 | v1，11 字段 |
| `tests/unit/test_quick_history.py` | pytest | ~150 | ≥6 case |
| `tests/integration/test_rdd_quick.bats` | bats | ~200 | ≥8 case |
| `tests/integration/test_rdd_quick_isolation.bats` | bats | ~150 | ≥4 case（零污染） |
| `docs/adr/ADR-0047-rdd-quick-bypass-path.md` | ADR | ~120 | 新 ADR，含四概念区分表 |

**修改文件**（每个都限制为最小侵入）：

| 路径 | 改动 |
|---|---|
| `skills/rdd-planner/SKILL.md` | `## See also` 段 +1 行 |
| `AGENTS.md` | 加 rdd-quick 段 |
| `README.md` | 技能列表 +1 行 |

**严格不动**（spec Scenario 锁 hash）：
- `skills/execute/scripts/select_worktree.sh`
- `skills/execute/scripts/tasks_writeback.sh`
- `_lib/archive.sh`
- `rdd-planner/SKILL.md` 的 `role:` 段

### 不复用 rdd-quick 内部的现有 helper

为避免循环依赖与零污染模糊边界，rdd-quick **不 source** 任何现有 `_lib/*.sh`，也不 **import** `skills._lib.*`。两个 helper 直接调标准库：
- `scaffold_plan.sh` 调 python3 + sys + json + tempfile（std only）
- `append_history.py` 调 std only

`_lib/quick_history.py` 是给 rdd-quick 自身的公共 API（提供校验函数），但**外部消费者**（如未来要给 status 命令加 quick 列）走 `from _lib import quick_history`，不走 skills._lib。这是 P1-1b 身份合并的现行规范。

### 状态文件 schema v1 字段

`_lib/schemas/quick_history_schema.json`：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "quick-history-entry",
  "version": 1,
  "required": [
    "name", "started_at", "ended_at", "plan_file",
    "complexity", "reviewed_by", "verdict_summary",
    "retry_count", "outcome", "commit_sha", "upgraded_to_change"
  ],
  "properties": {
    "name": { "type": "string", "pattern": "^quick-[a-z0-9-]+$" },
    "started_at": { "type": "string", "format": "date-time" },
    "ended_at": { "type": "string", "format": "date-time" },
    "plan_file": { "type": "string", "pattern": "^\\.rddf/plans/quick-.*\\.md$" },
    "complexity": { "enum": ["simple", "complex"] },
    "reviewed_by": { "type": "array", "items": { "enum": ["metis", "oracle"] } },
    "verdict_summary": {
      "type": "object",
      "required": ["total", "pass", "fail"],
      "properties": {
        "total": { "type": "integer", "minimum": 0 },
        "pass": { "type": "integer", "minimum": 0 },
        "fail": { "type": "integer", "minimum": 0 }
      }
    },
    "retry_count": { "type": "integer", "minimum": 0, "maximum": 3 },
    "outcome": { "enum": ["completed", "escalated", "unverified"] },
    "commit_sha": { "type": ["string", "null"], "pattern": "^[0-9a-f]{7,40}$|^$" },
    "upgraded_to_change": { "type": ["string", "null"] }
  }
}
```

### 环境变量规范（`RDDF_QUICK_` 前缀）

| 变量 | 默认值 | 语义 |
|---|---|---|
| `RDDF_QUICK_MAX_RETRIES` | `3` | P4 重试上限 |
| `RDDF_QUICK_PLAN_DIR` | `.rddf/plans` | 计划文件目录 |
| `RDDF_QUICK_HISTORY_FILE` | `.rddf/state/.quick-history.jsonl` | 审计日志路径 |
| `RDDF_QUICK_SKIP_REVIEW` | `false` | 跳过 P1 Metis/Oracle 双审（仅紧急） |
| `SKIP_RDDF_QUICK_VERIFY` | `false` | 跳过 P3 验证（仅紧急，audit 记 `unverified`） |

**明确禁止读写**：`QUICK_FINISH_DETECTED`（rdd-builder 已用）、`SKIP_PROMETHEUS_PLANNING`（rdd-builder 已用）。

### ADR-0047 大纲

```markdown
# ADR-0047: rdd-quick bypass path — 无 openspec change 的快速执行路径

## 状态
已采纳 (2026-09-07)

## 背景
四阶段流程对小改动过重（...proposal.md Why 段摘要...）

## 决策
新增独立 skill `skills/rdd-quick/`（D1-D8 八项决策摘要）

## 区分表
| 概念 | 与 rdd-quick 关系 |

## 与 guide-ship-quick-finish 提案的边界
（边界说明）

## Consequences
**正面**：小改动的仪式成本从 ~12h 降到 ~5min；保留 TDD/AC 纪律；复杂改动仍走双审。
**负面**：新增 skill 维护负担（SKILL.md 演进 + 11 字段 schema 演进）；升级路径非自动，用户需手动走 rdd-planner。
**风险**：快速路径可能被滥用为绕过审查的后门 → 已用 P1 综合判定 + 双审 + 重试上限 + 升级引导四道防线缓解。
```

## Impact

### In Scope

- 新增：`skills/rdd-quick/SKILL.md` + 2 个 helper + `_lib/quick_history.py` + `_lib/schemas/quick_history_schema.json` + ADR-0047 + 3 个测试文件
- 修改：`skills/rdd-planner/SKILL.md`（仅 `## See also` 段）+1 行、`AGENTS.md` 加段、`README.md` 列表 +1 行

### Out of Scope

- 不修改 `select_worktree.sh` / `tasks_writeback.sh` / `archive.sh`（spec 锁 hash）
- 不修改 `rdd-planner` 的 `role.boundaries` 与其他任何段落
- 不修改 `rdd-builder` / `rdd-verifier` / `rdd-arch` 任何 Phase 逻辑
- 不合并 / 不修改 / 不废弃 `.rddf/improvements/guide-ship-quick-finish.md`
- 不实现自动升级为正式 change（升级仅引导）
- 不接入 `iteration.json` / `sessions.json` / `roadmap-state.json`
- 不引入新依赖（仅 Python stdlib + bash）

### 兼容性

- 既有四阶段流程行为零变化（additive-only）
- `.rddf/plans/` 下既有 60+ 正式路径计划文件不受影响（`quick-` 前缀隔离）
- `rdd-doctor` 5 类校验对既有文件的结论不变
- `skills/rdd-doctor/scripts/checks/plan_tdd_check.py` 对 `quick-*.md` 立即生效（5 marker 校验）