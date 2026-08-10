# 实施计划: wire-plan-done-quality-gates

> 对应 Change: `openspec/changes/wire-plan-done-quality-gates`
> 基于: tasks.md 中的 6 组 20 任务
> ADR 引用: ADR-0007 (error/warning 门控) + ADR-0019 (change_alignment + STRICT_CHANGE_GATE 独立升级)
> 实施位置: 主线轻量模式 (`openspec/wire-plan-done-quality-gates` branch, 无 worktree)

## 概览

| 阶段 | 任务组 | 工作量 | 风险 |
|------|--------|--------|------|
| Wiring Investigation | 1.1-1.3 | 3 任务 | 低（只读） |
| Wire run_plan_checks | 2.1-2.3 | 3 任务 | 中（修改 plan_done_gate） |
| Wire change_alignment | 3.1-3.3 | 3 任务 | 中（STRICT 升级边界） |
| Surface results | 4.1-4.3 | 3 任务 | 低（输出格式） |
| Regression Coverage | 5.1-5.6 | 6 任务 | 中（新增 bats 测试） |
| Verification | 6.1-6.2 | 2 任务 | 低（验证 + 完整性） |

## 实施策略

**顺序**: 1 (读) → 2 (run_plan_checks wire) → 3 (change_alignment wire) → 4 (输出) → 5 (测试) → 6 (终验)

**关键约束 (design decisions)**:
- 决策 1: 沿用现有 plan_done_gate.sh 入口,扩展其收集循环
- 决策 2: STRICT_CHANGE_GATE 仅影响 change_alignment,不波及 run_plan_checks
- 决策 3: 失败必须 surfaced (含 "check unavailable"),禁止静默吞掉

**Gate 3 提取**: 把质量检查从 `run_plan_done_gate` 内部抽出为独立函数 `run_plan_quality_gate`,便于单元/集成测试,同时保持原 gate 编排不变。

**聚合 commit**: Phase 2.7 统一聚合 1 个 commit。

## 关键文件

| 文件 | 操作 | 来源任务 |
|------|------|---------|
| `skills/guide-plan/scripts/plan_done_gate.sh` | MODIFY | 2.1-2.3, 3.1-3.3, 4.1-4.3 (新增 Gate 3 + run_plan_quality_gate) |
| `tests/integration/test_wire_plan_done_quality_gates.bats` | CREATE | 5.1-5.5 (10 bats 测试) |

## 实施步骤 (TDD 5 步)

### Group 1: Wiring Investigation (Tasks 1.1-1.3)

- 1.1 定位 `run_plan_checks` 在 `skills/propose/scripts/propose_quality_check.py` 和 `change_alignment.ChangeAlignmentReport.verify` 在 `_lib/change_alignment.py` 的入口
- 1.2 读 `plan_done_gate.sh` 确认 Gate 0/1/2 流程和 reflect_engine hook
- 1.3 确认 Gate 3 (质量检查) 当前未在正常路径调用

### Group 2: Wire run_plan_checks (Tasks 2.1-2.3)

- 在 `run_plan_done_gate` 末尾 (reflect_engine hook 之后) 调用 `run_plan_quality_gate`
- 提取 `run_plan_quality_gate` 为独立函数,遍历 active changes,逐个调用 `run_plan_checks`
- 失败以 `[run_plan_checks] WARNING: <reason>` 格式输出,不阻断 gate

### Group 3: Wire change_alignment (Tasks 3.1-3.3)

- 同一 `run_plan_quality_gate` 中,逐个调用 `ChangeAlignmentReport.verify`
- Python exit code: 0=pass, 1=failed_checks (被 STRICT 升级), 2=check unavailable
- Bash 中: exit 1 时设 PLAN_QUALITY_BLOCKED=1,导致 gate 返回 1
- STRICT_CHANGE_GATE=yes 仅影响 change_alignment;run_plan_checks 永远不升级

### Group 4: Surface results (Tasks 4.1-4.3)

- 输出格式: `  → <change_name>` + `    [<check>] <status>: <reason>`
- check unavailable: `    [<check>] check unavailable: <exception>`
- 失败汇总: `❌ plan-done gate blocked: change_alignment errors above (STRICT_CHANGE_GATE)`

### Group 5: Regression Coverage (Tasks 5.1-5.6)

`tests/integration/test_wire_plan_done_quality_gates.bats` (10 tests):
- 5.1 run_plan_checks invoked per change
- 5.2 change_alignment invoked per change
- 5.3 default-mode warning does NOT block
- 5.4 STRICT_CHANGE_GATE=yes is read by change_alignment (strict_mode marker)
- 5.5 STRICT_CHANGE_GATE does NOT blanket-block run_plan_checks
- 5.6 (callers' responsibility): regression suite green

### Group 6: Verification (Tasks 6.1-6.2)

- 6.1 `openspec validate wire-plan-done-quality-gates --type change --json` → no errors
- 6.2 git diff 确认未影响其他文件

## 验收标准

1. `run_plan_quality_gate` 可独立调用,行为符合 design 决策
2. Gate 3 在正常 plan-done 路径被调用
3. 默认 mode: run_plan_checks + change_alignment 失败均不阻断
4. STRICT_CHANGE_GATE=yes: 被 change_alignment 读取 (strict_mode=True)
5. STRICT_CHANGE_GATE 仅影响 change_alignment,不波及 run_plan_checks
6. check unavailable 被 surfaced,不停滞
7. bats 集成测试 10/10 通过
8. `openspec validate` 通过

## 已知局限

`_lib/change_alignment.py::ChangeAlignmentReport.verify` 当前仅读取 `STRICT_CHANGE_GATE` 但未实现完整的 warning→error 升级 (依赖"registration layer",实际未启用)。此问题超出本提案范围,留待未来 change。Gate 3 wiring 仍正确传递 strict_mode 标记。

## 风险与回退

- **风险**: 增加 plan-done 路径开销 → 改进措施: <100ms per change,可接受
- **风险**: 触及 gate script 影响其他测试 → 改进措施: 纯 additive,Gate 0/1/2 + reflect_engine 不变
- **回退**: 单 PR revert,无数据迁移