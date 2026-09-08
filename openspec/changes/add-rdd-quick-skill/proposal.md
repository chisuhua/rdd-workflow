## Why

用户提出：现有四阶段流程（`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`）对小改动过重。一个只改 1-2 个文件的改动，需要创建 improvement 提案、注册索引、审批落盘 `proposal.md`、生成 `specs/` + `design.md` + `tasks.md`、建 worktree、执行、merge、archive。「有个想法直接干掉」的诉求在当前架构中无处安放。

**根因**：四阶段架构（ADR-0003 / ADR-0043）的每一环都以 openspec change 为载体：

```
rdd-planner    → 写 openspec/changes/<name>/proposal.md
rdd-builder P0 → 读 proposal.md，写 openspec/specs/<name>/spec.md
rdd-builder P1 → 写 design.md + tasks.md + .rddf/plans/<name>.md
rdd-builder P2 → execute 消费 plan，回写 tasks.md
rdd-verifier   → AC 从 proposal.md 的 ## 验收标准 段提取
```

缺少一条**不以 change 为载体、但仍保留 TDD 纪律与 AC 验证**的执行路径。用户手动绕过流程时，既无 TDD 约束也无 AC 验证，质量不可控。

**现有三个"轻"概念都不满足该诉求**（探索确认）：

| 既有概念 | 位置 | 语义 | 为何不满足 |
|---|---|---|---|
| `execution_mode: lightweight` | `_lib/builder_deps.py::decide_execution_mode` | 跳过 worktree，主仓库就地执行 | 仍需完整 openspec change |
| `git.openspec_tracked: false` | `_lib/archive.sh` L546 分支 | archive 时跳过 git merge/commit | 仍走 `openspec archive`，仍需 change 目录 |
| serial / parallel | `_lib/ship_execution_mode.sh` | 同 change 内多 wave 串并行 | 与 change 存在性无关 |

**与已有未批准提案 `guide-ship-quick-finish`（P2, 2026-07-24）是不同场景**：

| 维度 | `guide-ship-quick-finish`（既有，未批准） | `rdd-quick`（本 change） |
|---|---|---|
| 起点 | 已有 change，剩余任务 ≤2 且均为文档/状态更新 | 无 change，仅一段自然语言提案文本 |
| 跳过 | worktree + plan 生成 + execute | openspec change 创建 + worktree |
| 计划文件 | 明确不产出（其技术约束第 3 条） | 产出 `.rddf/plans/quick-<name>.md` |
| 终点 | review → archive | Oracle 验证 → 完成（无 archive） |

两者互不覆盖，长期共存。本 change 不合并、不修改该提案。

**Oracle / Metis 的可用形态**（探索确认）：项目内 Oracle / Metis / Momus 均**不是**程序化 subagent，仅作为评审角色名出现在 ADR 与 design.md 的评审记录中。唯一的程序化 subagent 调用是 `skills/deps/SKILL.md` Step 3e 的 `task(subagent_type=...)`，且该调用本身也是写给 AI agent 读的 SKILL.md 指令。因此审查与验证只能实现为 **SKILL.md 内的 prose 指令**，由执行 skill 的 AI agent 自行 spawn —— 这与 `rdd-verifier` v2.0（ADR-0045「执行验证的 AI agent 自身就是 LLM」）的既定做法完全一致，不引入新范式。

**角色边界依据（ADR-0028）**：`rdd-planner` frontmatter 的 `role.boundaries.not_owns` 显式列出 `.rddf/plans/<name>.md` 与 `.rddf/state/builder/<name>.json`。本 change 的核心动作（生成计划 + 执行 + 验证）全部落在 `rdd-planner` 的 not_owns 范围内，故必须新建独立 skill。

**Why now**：项目已完成 v4 四阶段收敛（ADR-0043/0044）与 verifier 自包含化（ADR-0045）。verifier 的 verdict 协议成熟可复用，`plan_tdd_check` 已能守住计划文件质量下限 —— 两块基础设施都已就位，实现的边际成本最低。

## What Changes

### 新建 `skills/rdd-quick/` skill

**SKILL.md** 含 frontmatter（`name` / `description` / `license` / `compatibility` / `metadata` / `role`），`role.boundaries` 按 ADR-0028：

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
      - ".rddf/plans/<name>.md"
    human_involvement: "medium"
```

**P0–P4 五阶段状态机**（SKILL.md prose 指令 + 少量 bash helper）：

| Phase | 动作 |
|---|---|
| P0 | 收集提案内容（自然语言），确定 kebab-case 名称生成 `.rddf/plans/quick-<name>.md` |
| P1 | 复杂度判定（AI agent 综合判断，无硬阈值）→ 简单进 P2；复杂则 Metis 审歧义 + Oracle 审方案 → 用户确认 |
| P2 | 就地执行（当前分支，无 worktree），按计划文件 TDD 5 步逐 task 执行 |
| P3 | Oracle 验证：按 rdd-verifier verdict JSON 协议逐条 AC 判定 |
| P4 | 全 pass → 追加审计日志完成；有 fail → 有界重试（≤3）；超限 → 输出升级摘要引导 rdd-planner |

**复杂度判定原则**（写入 SKILL.md，AI agent 综合判断，无硬阈值）：

判定「复杂」的信号（任一命中即建议走审查）：涉及公共接口 / 跨模块契约变更；需修改既有 gate、handoff schema、状态文件 schema；有数据迁移 / 破坏性变更 / 回滚风险；改动横跨 3 个以上模块或触及 `_lib/core/`、`_lib/schemas/`；用户描述本身存在多种合理解读。

判定「简单」的信号（全部满足才可直接执行）：改动局限单一模块内部；无公共接口变更；有明确可自动验证的成功标准；失败可 `git checkout` 无损回滚。

### 计划文件格式 `.rddf/plans/quick-<name>.md`

- git 追踪（`.rddf/plans/` 已在 `.gitignore` 第 9 行声明为 tracked）
- `quick-` 前缀避免与正式路径 change 同名文件撞车
- **必须含 TDD 5 步标记** —— `skills/rdd-doctor/scripts/checks/plan_tdd_check.py` 扫描整个 `.rddf/plans/` 目录并校验 5 个固定 marker：`Write the failing test` / `Run test to verify it fails` / `Write minimal implementation` / `Run test to verify it passes` / `Defer commit`
- 必须含 `## Acceptance` 段（P3 验证的 AC 来源，取代正式路径的 `proposal.md` `## 验收标准`）

### 审计日志 `.rddf/state/.quick-history.jsonl`

append-only JSONL，每次执行追加一行，原子写（temp + rename）：

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

schema 落盘 `_lib/schemas/quick_history_schema.json`（version 1）；读写实现 `_lib/quick_history.py`。

### 升级摘要（P4 重试超限）

输出到 stdout，**不落盘 change**。含原始提案文本、已做改动清单（`git diff --stat`）、失败的 AC 及其 verdict reasoning、建议的 AC 修正方向、`skill_use("rdd-planner")` 下一步提示。审计日志 `outcome` 记 `escalated`。

### rdd-planner 加一行指向提示

仅在 `skills/rdd-planner/SKILL.md` 的 `## See also` 段追加一行指向 `skills/rdd-quick/`。**不修改** `role.boundaries` 与其他任何段落。

### 文档

- 新 ADR `docs/adr/ADR-0047-rdd-quick-bypass-path.md`（当前最大值 ADR-0046 + 1），含四概念区分表 + 与 `guide-ship-quick-finish` 边界说明
- `AGENTS.md` 加 rdd-quick 段（四概念区分表 + 环境变量清单）
- `README.md` 技能列表加 `rdd-quick/SKILL.md` 一行

## Capabilities

### New Capabilities

- **无 change 计划生成**：从自然语言提案内容直接生成 `.rddf/plans/quick-<name>.md`，含 TDD 5 步 + `## Acceptance` 段，不读取也不创建 `openspec/changes/`
- **AI 综合复杂度判定**：无硬编码阈值，SKILL.md 提供简单/复杂各 ≥4 条判定信号清单，由 AI agent 综合判断并向用户说明依据
- **Metis + Oracle 双审**：复杂时 spawn Metis 审歧义 + Oracle 审方案，输出各自结论后经 `question` 请用户确认（prose 指令，对齐 ADR-0045 模式）
- **就地执行**：当前分支直接改，不创建 worktree、不创建 `openspec/*` 分支、不写 `tasks.md`
- **计划文件 AC 验证**：复用 rdd-verifier verdict JSON 协议（`ac_id` / `description` / `status` / `confidence` / `evidence` / `reasoning`），但 AC 来源改为计划文件的 `## Acceptance` 段
- **有界重试 + 引导升级**：验证失败重试 ≤3（`RDDF_QUICK_MAX_RETRIES` 可覆盖，默认对齐 `RDDF_VERIFIER_MAX_LOOPS`）；超限输出升级摘要，不自动落盘 change
- **独立审计日志**：`.rddf/state/.quick-history.jsonl` 11 字段 append-only 原子写，不接入 `iteration.json` / `sessions.json` / `roadmap-state.json`

### Modified Capabilities

- **`rdd-planner` SKILL.md**：仅 `## See also` 段增一行指向 `rdd-quick`；`role:` 段与其余全部段落逐字节不变

## Impact

Affected code:
- `skills/rdd-quick/SKILL.md` (NEW) — P0–P4 状态机 + 复杂度判定原则 + Metis/Oracle spawn 指令 + verdict 协议
- `skills/rdd-quick/scripts/` (NEW) — 计划文件脚手架生成、审计日志追加、零污染自检
- `_lib/quick_history.py` (NEW) — 审计日志 append + 读取 + schema 校验
- `_lib/schemas/quick_history_schema.json` (NEW) — version 1
- `skills/rdd-planner/SKILL.md` — `## See also` 段 +1 行（其余逐字节不变）
- `tests/unit/test_quick_history.py` (NEW) — ≥6 case
- `tests/integration/test_rdd_quick.bats` (NEW) — ≥8 case
- `tests/integration/test_rdd_quick_isolation.bats` (NEW) — ≥4 case（零污染验证）

Affected docs:
- `docs/adr/ADR-0047-rdd-quick-bypass-path.md` (NEW)
- `AGENTS.md` — 加 rdd-quick 段
- `README.md` — 技能列表 +1 行

**明确不修改**（零污染契约，以文件 hash 不变为 AC）:
- `skills/execute/scripts/select_worktree.sh`（rdd-quick 自行处理工作区）
- `skills/execute/scripts/tasks_writeback.sh`（rdd-quick 不写 `tasks.md`）
- `_lib/archive.sh`（rdd-quick 无 archive 阶段，不调 `openspec archive`）
- `skills/rdd-planner/SKILL.md` 的 `role:` 段
- `rdd-builder` / `rdd-verifier` / `rdd-arch` 的任何 Phase 逻辑
- `.rddf/improvements/guide-ship-quick-finish.md`

Backward compatibility:
- 实现完全 additive —— 既有四阶段流程零行为变化
- `.rddf/plans/` 下既有 60+ 正式路径计划文件不被读取或覆盖（`quick-` 前缀隔离）
- `rdd-doctor` 5 类校验对既有文件的结论不变
- 环境变量统一 `RDDF_QUICK_` 前缀，不复用已被 rdd-builder 占用的 `QUICK_FINISH_DETECTED` / `SKIP_PROMETHEUS_PLANNING`

Migration:
- 无用户面破坏性变更，新增可选路径
- 用户通过 `skill_use("rdd-quick")` 主动进入，不影响既有工作流入口

## Reference

- 上游 improvement：`.rddf/improvements/add-rdd-quick-skill.md`（P1 / arch-design / 主题「编排能力完善」，已过 brainstorm HARD-GATE）
- 相关 ADR：ADR-0003（三阶段架构奠基）、ADR-0028（role model per phase）、ADR-0034（rdd-verifier 5th phase）、ADR-0043/0044（v4 stage-merge）、ADR-0045（inline LLM verification，本 change 沿用其 prose-instruction 模式）
- 共存提案：`.rddf/improvements/guide-ship-quick-finish.md`（P2，不同场景，不合并）
- 复用协议：`skills/rdd-verifier/SKILL.md` § LLM Verification Protocol 的 `VERDICT_ITEM_SCHEMA`
- 约束来源：`skills/rdd-doctor/scripts/checks/plan_tdd_check.py`（TDD 5 marker 校验）
