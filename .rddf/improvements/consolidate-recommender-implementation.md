---
优先级: P2
来源: ADR-0062（推荐器决策树收敛到单一实现）
阶段: v4
分类: core-impl
类型: debt
主题: 架构收敛
---

## 架构依据

ADR-0062（2026-11-19 已采纳）。三份推荐实现（bash `scan-state.sh` / `guide_cmd._scan_state` / `workflow_synthesizer._decision_tree`）独立演化，`ab7c3ac1` 已实证三份同时读错 handoff 字段，导致所有 v4 项目阶段推荐错误。

**执行前置**：`retire-guide-orchestrator`（C）先落地 —— 它归档 `skills/guide` 从而消掉 bash 实现，把待收敛面从 3 份降到 2 份。

**metis 修订（2026-11-19）**：
- **一致性断言降级为 (action, reason)** —— `guide_cmd` 的 stdout 只有「💡 建议 / reason」（`guide_cmd.py:366-367`），**没有 confidence、没有菜单**；这两项只能对 `synthesize()` 断言。
- **承认 reason 文案变更** —— 两侧文案本来不同（`->` vs `→`、1c 诊断只在 ②）。以 ② 为基准，`synthesize().reason` 文本随之变化属**预期**，不是回归。
- **fallback 必须可区分** —— `synthesize()` 的 catch-all 会把任何异常吞成 `"fallback: synthesizer error"`；每条一致性断言前必须先排除该字符串，否则无法区分「决策树不一致」与「菜单构造崩了」。
- **AC-1 补 bash 侧** —— 只 grep Python 函数名可被改名绕过（`def recommend_v2` 照样通过）。

## 范围

### In Scope

1. 抽出单一 Python 推荐模块（建议 `_lib/recommender.py`），承载 `guide_cmd._scan_state` 的优先级阶梯，返回 `(action, reason)`。
2. `_lib/cli/guide_cmd.py`：删除自身 `_scan_state`，改为调用共享模块。
3. `_lib/workflow_synthesizer.py`：删除 `_decision_tree`，`synthesize()` 改为调用共享模块后组装 `WorkflowRecommendation`。
4. 行为冻结基准 = `guide_cmd._scan_state` 现状。按 ADR-0062 分歧表对齐：无 arch-handoff 穿透、v3-plan stale 校验、1c corrupt 诊断、`_fallback_recommendation` 的 v3 菜单标签。
5. `tests/unit/test_stage_consumers_agreement.py`：从「三份输出相同」改为「单一实现 + 两消费者 (action, reason) 相同」+ 结构断言。

### Out of Scope

- `retire-guide-orchestrator` 的归档与 stage_guide 退役。
- `cleanup-guide-star-residue` 的注释类残留。
- 推荐**策略**的显式重设计 —— 但 ADR-0062 分歧表第 1 行（无 arch-handoff 时按 ② 穿透）会**改变 ③ 的推荐结果**（例如「有 roadmap、无 arch-handoff、无 changes」从 `rdd-arch` 变 `rdd-builder`），这是收敛的既定对齐，不是新策略。
- **不实现 bash↔python 降级桥接** —— ADR-0062「负面风险」第 2 条（无 python3 时 `guide_entry.sh` 的降级）随 C 归档自动消解。
- `rddf status` / `rddf monitor` 的其他输出。

## 关键场景

- **GIVEN** 状态矩阵（`V4_STATES` 4 态 + 无 arch-handoff + v3-design + corrupt + non-object），**WHEN** 分别跑 `rddf guide` 与 `synthesize()`，**THEN** `action` 与 `reason` 完全一致，且 `reason != "fallback: synthesizer error"`。
- **GIVEN** 共享模块抛异常，**WHEN** `synthesize()` / `rddf guide` 被调用，**THEN** 各自返回 fallback / 不抛栈，且 fallback 文案可被识别。
- **GIVEN** 共享模块抛异常，**WHEN** `synthesize()` 被调用，**THEN** 返回 `confidence="low"` 的 fallback 与修正后的 v4 菜单。

## 技术约束

- 共享模块必须 never-raises，或 `cmd_guide` 保留 try/except 兜底（二选一写进 `design.md`）。
- 不得改变 `WorkflowRecommendation` 的字段集合。
- `synthesize().reason` 的文案变化是预期行为，需在 `design.md` 列出变化清单，不得为「保持文本不变」而保留两份实现。

## 验收标准

- [ ] AC-1: Python 侧 `grep -rn 'def _scan_state\|def _decision_tree' _lib/ skills/` ⇒ 1 处；bash 侧 `grep -c 'RECOMMEND=' skills/guide/scripts/scan-state.sh` ⇒ 0（C 已归档时由「文件不存在」满足）
- [ ] AC-2: 结构断言：`_lib/` 中能返回 ≥3 个不同 stage 字面量的函数恰有 1 个（防改名绕过）
- [ ] AC-3: `python3 -c "from skills._lib.cli.guide_cmd import cmd_guide"` 与 `python3 -c "from skills._lib.workflow_synthesizer import synthesize"` 均可导入
- [ ] AC-4: 状态矩阵下 `rddf guide` 与 `synthesize()` 的 `(action, reason)` 一致，且每条断言前 `reason != "fallback: synthesizer error"`
- [ ] AC-5: `synthesize()` 的 `confidence` 与菜单项集合只对 synthesizer 侧断言（CLI 侧无这两项）
- [ ] AC-6: 注入异常时 `synthesize()` 返回 `confidence="low"` fallback，`cmd_guide` 不抛栈；两者 fallback 文案可区分
- [ ] AC-7: `_fallback_recommendation` 菜单不再含重复挂在 `rdd-builder` 上的 v3 概念标签
- [ ] AC-8: `python3 -m pytest tests/unit/test_stage_consumers_agreement.py tests/unit/test_cli_guide.py tests/unit/test_workflow_synthesizer.py -q` 全绿
- [ ] AC-9: 全量门 `./test.sh --full --regression` ⇒ 未评估 0 + 新增失败 0
