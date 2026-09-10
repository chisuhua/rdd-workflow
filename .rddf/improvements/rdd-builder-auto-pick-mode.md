---
name: rdd-builder-auto-pick-mode
priority: P1
theme_ref: rdd-builder-evolution
roadmap_ref:
  project_id: rdd-workflow
  phase: phase-3
  theme: rdd-builder-evolution
---

## Why

ADR-0048 v4.0.1 + ADR-0049 引入 5-option HARD pause + LLM-augmented P0。AI 代理在 HARD pause 处停下显示 5-option 菜单，等待用户输入 1-5。

但用户实际场景：rdd-builder / rdd-quick 应该**用户不接入，全自动推进**。没有 rdd-workflow 知识的用户难以判断 1-5 哪个合适，反而卡在 HARD pause。

## What

引入 rdd-builder / rdd-quick **全自动决策模式**（默认 ON）：

1. AI 代理基于所有信号自动选 1-5，无需用户输入
2. 仅在低置信度场景暂停问用户（planner 信号缺失 / LLM 与 advisory 冲突 / 强制确认 env var）
3. Auto-pick 输出 prose 含 reasoning，让用户即使不介入也能跟上
4. 保留 `--auto-approve` / `--dispatch-quick` / `--require-confirm` CLI flags 作为 override

## How

### SKILL.md 改造

- 阶段 0.0.5 全自动决策逻辑（NEW，~80 行）
- 阶段 0.1 菜单改为决策上下文（仅低置信度展示）
- 阶段 0.2/0.3 case 加"全自动 note"

### phase0_approval.sh 改造

- 新增 `RDDF_REQUIRE_USER_CONFIRM` env var（default no）
- 新增 `--require-confirm` CLI flag
- 新增 AC count fallback（improvement file when proposal.md missing）
- 新增 auto-pick decision logic + prose 输出

## Acceptance

| # | AC | 验证 |
|---|---|---|
| 1 | SKILL.md 阶段 0.0.5 段含 9-row auto-pick 决策表 | bats test 19, 20 |
| 2 | SKILL.md 文档 RDDF_REQUIRE_USER_CONFIRM env var | bats test 21 |
| 3 | SKILL.md 文档 用户介入门控 | bats test 22 |
| 4 | phase0_approval.sh 默认 auto-pick | bats test 1-8 |
| 5 | RDDF_REQUIRE_USER_CONFIRM=yes 强制用户输入 | bats test 9-11 |
| 6 | --auto-approve / --dispatch-quick / --require-confirm CLI flags | bats test 12-15 |
| 7 | ADR-0048 + ADR-0049 零 regression | regression |

## Capabilities

### MUST

1. 默认模式不需要用户输入 1-5
2. AI 代理基于 planner advisory + AC count 自动选 1/5
3. 低置信度场景（planner=unknown / LLM 冲突 / 强制确认）暂停问用户
4. Auto-pick 输出含 reasoning prose
5. `--auto-approve` / `--dispatch-quick` / `--require-confirm` CLI flags override

### MUST NOT

1. 不改变 `--dispatch-quick` CLI 硬验证 `recommended_route=simple` 行为
2. 不改变 `_compute_rerelated_route` 启发式
3. 不改变 P2.5 review HARD pause
4. 不让 LLM 替代用户做不可逆操作（archive 仍需 rdd-verifier 验证）
