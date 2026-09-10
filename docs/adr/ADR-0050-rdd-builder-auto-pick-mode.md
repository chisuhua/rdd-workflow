# ADR-0050: rdd-builder / rdd-quick 全自动决策模式 (per 用户 UX 需求)

> **Date**: 2026-09-10
> **Status**: 待采纳
> **Supersedes**: (none)
> **Amends**: [ADR-0048 §Decision 3](ADR-0048-v4-stage-merge-revision.md), [ADR-0049](ADR-0049-rdd-builder-phase0-llm-integration.md)
> **Author**: rdd-builder evolution

## Context

ADR-0048 v4.0.1 + ADR-0049 引入 5-option HARD pause + LLM-augmented P0。AI 代理在 HARD pause 处停下显示 5-option 菜单，等待用户输入 1-5。

**用户诉求 (2026-09-10)**:
> "我希望 SKILL.md 里启动 1-5 的选择判断，用户没有知识可以选择 prose 输入。rdd-builder/rdd-quick 我希望用户不接入，全程自动推进。"

设计目标：
- **用户不主动介入**：AI 代理基于所有信号（planner advisory + LLM assessment + AC count）自动选 1-5
- **用户没知识也能跟上**：AI 在 prose 中输出完整决策说明（不阻断流程，仅展示）
- **rdd-builder / rdd-quick 全程自动推进**：从 P0 入口到 archive 流程不卡用户输入

## Decision

### Decision 1: 默认模式 auto-pick（无需用户输入）

P0 入口的 decision logic 重写：

```
IF --auto-approve CLI flag:
    → case 1 (approve)
ELIF --dispatch-quick CLI flag:
    IF recommended_route != "simple":
        → ERROR exit 2 (硬验证不变)
    ELSE:
        → case 5 (dispatch-quick)
ELIF RDDF_REQUIRE_USER_CONFIRM=yes OR --require-confirm CLI flag:
    → ASK USER (read input)
ELSE (default auto-pick):
    IF recommended_route == "simple" AND AC_count ≤ 2:
        → case 5 (dispatch-quick)
    ELSE:
        → case 1 (approve)
```

### Decision 2: Auto-pick decision table (9 行, per SKILL.md 阶段 0.0.5)

| Planner advisory | LLM assessment | AC count | AI 自动选 |
|---|---|---|---|
| `simple` | `simple` | ≤ 2 | **case 5 (dispatch-quick)** |
| `simple` | `simple` | > 2 | **case 1 (approve)** |
| `simple` | `complex` | 任意 | **case 1 (approve)** |
| `simple` | `unknown` | 任意 | **case 1 (approve)** |
| `complex` | 任意 | 任意 | **case 1 (approve)** |
| `unknown` | `unknown` | 任意 | **暂停问用户** |
| 任意 | `complex` AND advisory 不一致 | 任意 | **暂停问用户** |
| 任意 | `simple` 但 advisor=complex | 任意 | **暂停问用户** |
| `unknown` | `simple` | 任意 | **暂停问用户** |

### Decision 3: 用户介入门控（仅低置信度触发）

**默认 OFF**: AI 代理全自动推进

**触发用户介入的条件**（任一满足）：
- `planner-handoff.json::recommended_route == "unknown"`（planner 信号缺失）
- `LLM assessment == "unknown"`（LLM 也不能判定）
- LLM 与 planner advisory 冲突（`Agreement: no`）
- LLM 检测到 `complexity_confirmed == "complex"` AND 与 advisory 不一致
- 环境变量 `RDDF_REQUIRE_USER_CONFIRM=yes`（强制用户确认）

### Decision 4: Auto-pick prose 输出（让用户能跟上）

即使全自动，AI 代理仍在 prose 中输出一段决策说明（让用户能 review）：

```
🤖 Auto-pick (default): option 5 (dispatch-quick)
   理由: advisory=simple + AC ≤ 2 → 走 rdd-quick 路径
   (如需用户介入, 设 RDDF_REQUIRE_USER_CONFIRM=yes)
```

或：

```
🤖 Auto-pick (default): option 1 (approve)
   理由: advisory=complex, AC=5 → 走完整 P1-P3 路径
```

### Decision 5: AC count 数据源 (per ADR-0049 Decision 4)

**Primary**: `openspec/changes/<change>/proposal.md`（如存在）
**Fallback**: `.rddf/improvements/<change>.md`（proposal.md 缺失时）

### Boundary Preservation (per ADR-0048 + ADR-0049)

- ✅ `--dispatch-quick` CLI flag 仍硬验证 `recommended_route=simple`（不变）
- ✅ `_compute_recommended_route` 启发式不变（deterministic）
- ✅ planner-handoff.json::recommended_route schema 不变
- ✅ `--auto-approve` / `--dispatch-quick` CLI flag 行为不变
- ✅ LLM 仍然做 Pre-flight Reasoning + feedback body + hidden complexity check
- ✅ rdd-quick P1 仍然读 `.planner-handoff.json::recommended_route`（不变）
- ✅ rdd-quick P4 outcome handling 不变（completed / escalated / unverified）

### Disruption to "HARD pause" 契约 (ADR-0048 spec §5.2)

- 旧: HARD pause at P0 / P2.5（用户必须显式选择,不能跳过）
- 新: HARD pause 仅在低置信度场景生效（用户介入门控）；默认 auto-pick（无 HARD pause）
- P2.5 review HARD pause **保持不变**（per ADR-0048 spec §5.2）

## Schema Changes

**无新 schema 字段**。完全利用 ADR-0048 + ADR-0049 既有 schema。

## SKILL.md Changes (per ADR-0050 Decision)

### 阶段 0.0 — LLM Pre-flight Reasoning
更新 Decision 3 注释：冲突时"暂停问用户"（不是用户始终决策者）

### 阶段 0.0.5 — 全自动决策逻辑（NEW, ~50 行）
- 自动决策表（9 行）
- 用户介入门控（4 触发条件）
- Auto-pick prose 输出格式

### 阶段 0.1 — 5-option 决策上下文
从 "5-option 菜单展示 (HARD pause)" 改为 "5-option 决策上下文 (仅低置信度展示)"

### 阶段 0.2 — Case 2/3/4
加 `> 全自动 note` 提示用户：默认 AI 自动选 2/3/4，不需要输入

### 阶段 0.3 — Case 5
加 `> 全自动 note` 提示用户：默认 AI 自动选 5，不需要输入

## Script Changes

### `skills/rdd-builder/scripts/phase0_approval.sh`

```
新增 env var: RDDF_REQUIRE_USER_CONFIRM (default no)
新增 CLI flag: --require-confirm (override RDDF_REQUIRE_USER_CONFIRM=yes)
新增 AC count fallback: improvement file (.rddf/improvements/) when proposal.md missing
新增 auto-pick decision logic (Decision 1)
新增 prose 输出 "🤖 Auto-pick (default): option X (action)" with reasoning
```

### rdd-quick SKILL.md

**不需要改动**：rdd-quick 已经按 `--from-builder` 模式跑，自动接 case 5 派发的 change。

## Test Strategy

### bats integration tests (NEW file: `tests/integration/test_rdd_builder_phase0_auto_pick.bats`)

24 cases 覆盖：
- 9 个 default mode auto-pick scenarios (test 1-8 + test 18)
- 3 个 RDDF_REQUIRE_USER_CONFIRM=yes mode (test 9-11)
- 4 个 CLI flag overrides (test 12-15)
- 3 个 UX assertions (test 16-18)
- 6 个 SKILL.md documentation assertions (test 19-24)

### 验证 ADR-0048 + ADR-0049 零 regression
- ADR-0048 bats: 16 cases pass (包括 test 14 `--dispatch-quick still hard-validates`)
- ADR-0049 bats: 16 cases pass
- pytest: 66 cases pass (test_dispatch_quick_review + test_builder_handoff + test_recommended_route)

## Acceptance Criteria

| # | AC | 验证 |
|---|---|---|
| 1 | SKILL.md 阶段 0.0.5 段 (≥ 50 行) 含 9-row auto-pick 决策表 | bats test 19, 20 |
| 2 | SKILL.md 文档 RDDF_REQUIRE_USER_CONFIRM env var | bats test 21 |
| 3 | SKILL.md 文档 用户介入门控（4 触发条件） | bats test 22 |
| 4 | SKILL.md case 5 段含 全自动 note | bats test 23 |
| 5 | SKILL.md case 2/3/4 段含 全自动 note | bats test 24 |
| 6 | phase0_approval.sh 默认 auto-pick（advisory=simple + AC ≤ 2 → case 5） | bats test 1, 2 |
| 7 | phase0_approval.sh 默认 auto-pick（advisory=simple + AC > 2 → case 1） | bats test 3, 4 |
| 8 | phase0_approval.sh 默认 auto-pick（advisory=complex → case 1） | bats test 5, 6 |
| 9 | phase0_approval.sh 默认 auto-pick（advisory=unknown → case 1 conservative） | bats test 7 |
| 10 | phase0_approval.sh AC count 从 improvement 文件 fallback | bats test 8 |
| 11 | RDDF_REQUIRE_USER_CONFIRM=yes 强制用户输入 | bats test 9, 10, 11 |
| 12 | --auto-approve CLI 强制 case 1 | bats test 12 |
| 13 | --dispatch-quick CLI 强制 case 5（仍硬验证 simple） | bats test 13, 14 |
| 14 | --require-confirm CLI 强制用户输入 | bats test 15 |
| 15 | 默认模式不显示 "Choose [1-5]"（无 user prompt） | bats test 16 |
| 16 | Auto-pick 输出含 reasoning prose | bats test 17, 18 |
| 17 | ADR-0048 bats 16/16 零 regression | regression |
| 18 | ADR-0049 bats 16/16 零 regression | regression |
| 19 | pytest 66/66 零 regression | regression |
| 20 | docs (workflow-phases.md + v4-pipeline-data-flow.md) 同步 | review |

## Alternatives Considered

### Alt 1: 始终问用户（保留 HARD pause）
**否决理由**：与用户 UX 需求"用户不接入"明确冲突。

### Alt 2: 完全无门控（无 RDDF_REQUIRE_USER_CONFIRM）
**否决理由**：低置信度场景（planner 信号缺失、LLM 与 advisory 冲突）AI 可能错决策，需要给用户介入通道。

### Alt 3: 使用 LLM 决策 vs 启发式
**否决理由**：LLM 决策需要 token 消耗且不确定性高；用 planner advisory（deterministic）+ AC count（精确数字）+ LLM assessment（prose 提示）作为组合信号比纯 LLM 决策更稳健。

### Alt 4: 用 ask_user_question tool 替代 bash read
**否决理由**：ask_user_question 是 OpenCode UI tool, 不能保证 AI 代理运行环境支持；bash read 是 POSIX 标准且始终可用。

## Cross-references

- ADR-0048 §Decision 3 (5-option P0 + dispatch-quick) — AMENDED by ADR-0050 (HARD pause 条件放宽)
- ADR-0049 (LLM-augmented P0) — EXTENDED by ADR-0050 (auto-pick decision table)
- ADR-0045 (executing AI agent IS the LLM) — Pattern reused for auto-pick
- ADR-0017 (rddf-session lifecycle) — Phase entry/exit hooks unchanged
- ADR-0025 (design proposal creation D1/D2) — proposal.md creation order preserved

## Migration / Backwards Compat

**No breaking changes**:
- `--auto-approve` CLI flag 行为不变（仍强制 case 1）
- `--dispatch-quick` CLI flag 行为不变（仍硬验证 simple + 强制 case 5）
- `RDDF_REQUIRE_USER_CONFIRM=yes` env var 可强制原行为（HARD pause）
- 现有 CI / scripts 调用 `--dispatch-quick` 或 `--auto-approve` 不受影响

**Behavior change**:
- 无 CLI flag / 无 env var 的 default 行为：从 HARD pause + user input → auto-pick
- 如果下游有依赖用户输入 1-5 的脚本，必须显式设 `RDDF_REQUIRE_USER_CONFIRM=yes`
