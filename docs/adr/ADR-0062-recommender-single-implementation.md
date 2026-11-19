# ADR-0062: 推荐器决策树收敛到单一实现

> **Status**: 已采纳（2026-11-19，oracle + critic 双审通过）
> **Date**: 2026-11-19
> **Author**: architect
> **Parent**: (none)
> **关联 change**: `openspec/changes/archive/2026-11-19-consolidate-recommender-implementation/`（已归档 2026-11-19；验收报告 `.rddf/reviews/consolidate-recommender-implementation-verify.md`）
> **AC 映射**: 见该 change 的 `proposal.md` `## Acceptance` 段 AC-1 ~ AC-9 —— AC-1 单一决策阶梯（Python 侧旧入口名 0 命中 + bash 侧已随 ADR-0063 归档）/ AC-2 结构断言（能返回 ≥3 个 stage 字面量的函数恰有 1 个）/ AC-3 消费者可导入 / AC-4 两消费者 (action, reason) 一致 / AC-5 confidence 与菜单只对 synthesizer 断言 / AC-6 异常注入不抛栈且 fallback 可区分 / AC-7 fallback 菜单 v4 标签 / AC-8 proposal 列的 3 个测试文件全绿（验收实跑 4 个，含新增的结构断言文件）/ AC-9 全量门。**注**：本仓 `openspec/` 不随 git 分发，故此处保留判据摘要索引 —— proposal 的 AC 变更时须同步本行
> **审稿报告**: `.rddf/reviews/adr-0062.md`（收口时誊写）
> **Amends**: ADR-0044（其「deferred follow-up」清单中被本 ADR 收口的部分）

## 背景与问题

「下一步该做什么」的推荐逻辑在仓库里有**三份互不 import、独立演化的实现**：

| # | 实现 | 消费者 | 规模 |
|---|---|---|---|
| ① | `skills/guide/scripts/scan-state.sh::scan_state`（bash） | `skills/guide/scripts/guide_entry.sh` | 文件 710 行（含非决策树部分） |
| ② | `_lib/cli/guide_cmd.py::_scan_state`（Python） | `rddf guide` | L161-323（~163 行） |
| ③ | `_lib/workflow_synthesizer.py::_decision_tree`（Python） | `guide_entry.sh`、`rddf monitor` | L847-964（~118 行） |

### 漂移已经产生过真实缺陷

`ab7c3ac1`（2026-11-04）的提交说明原文：

> Stage recommendation had **three independent implementations, and the last one overrode the other two**. All three read the v3 `.plan-handoff.json` / `.design-handoff.json` names and looked for an `active_changes` field that `planner-handoff-v1` does not define — so it always resolved to 0 and **every v4 project was reported as a leftover**.

即：三份实现同时读错同一组字段名，导致所有 v4 项目的阶段推荐错误，且 ①②③ 之间还互相覆盖。修复需要一次 1085 行、跨 16 文件的提交手工对齐三份。

### 为什么现有约束没拦住

- `tests/unit/test_stage_consumers_agreement.py`（239 行）是**漂移发生之后**补的一致性测试，不是预防机制。
- 三份实现没有任何共享代码路径，一致性只能靠测试断言「三者输出相同」，无法阻止字段名/分支顺序的独立演化。
- ADR-0044 把这类残留列为 deferred follow-up（「runtime harmless if not triggered」），实际证明并不 harmless。

## Decision

**推荐器决策树只保留一份实现；所有消费者 import 同一函数，不再各自维护分支。**

具体：

1. **单一真源**：抽出独立的 Python 模块（`_lib/recommender.py` 或等价命名）承载 `_scan_state` 的优先级阶梯，返回 `(suggested_action, reason, confidence)` 及菜单数据。
2. **消费者收敛**：
   - `rddf guide`（`_lib/cli/guide_cmd.py`）改为调用该模块，删除自身 `_scan_state`。
   - `_lib/workflow_synthesizer.py::_decision_tree` 删除，`synthesize()` 改为调用该模块后组装 `WorkflowRecommendation`。
3. **bash 实现退役**：`skills/guide/scripts/scan-state.sh` 不再承担推荐决策。`guide_entry.sh` 若要保留，必须调用 Python 模块（`python3 -c`），不得内联 bash 决策树。**该退役随 ADR-0063 的 `skills/guide` 归档一并完成**；本 ADR 只规定「不允许存在第二份决策树」。
4. **行为冻结基准**：收敛后三个消费者的可观察输出以 **`guide_cmd._scan_state` 的现状为冻结基准**（`ab7c3ac1` 的提交标题即 "CLI main chain"，工程上它就是主链路）。三份实现**本就存在分歧**，收敛必然对齐它们 —— 这属于「既定行为对齐」，不是策略变更。已知分歧与对齐后行为：

   | 分歧点 | 现状 ② CLI | 现状 ③ synthesizer | 收敛后（= 基准） |
   |---|---|---|---|
   | 无 `.arch-handoff.json` | 穿透到 worktree/roadmap 分支 | `rdd-arch` / high（Path 1） | 按 ② 穿透 |
   | v3-plan stale 交叉校验 | 返回 `rdd-arch "plan-handoff stale…"` | 不做该校验 | 按 ② 校验 |
   | `1c` corrupt 诊断 | 有专属 reason | 走 Path 3 泛化 reason | 按 ② 诊断 |
   | `_fallback_recommendation` 菜单 | — | 三条 `MenuOption` 均为 `id="rdd-builder"`（「设计阶段」「变更生成」是 v3 概念） | 修正为 v4 菜单 |
5. **错误契约保持**：`cmd_guide` 的「errors are non-fatal」行为（`guide_cmd.py:334-336`）不得因改为直调共享模块而破坏 —— 共享模块必须 never-raises，或由 `cmd_guide` 保留 try/except 兜底（二选一，在 change 的 design.md 里定）。
6. **落地顺序**：本 ADR 与 ADR-0063 同窗立项；**执行顺序为 ADR-0063（归档 `skills/guide`）→ 本 ADR（收敛剩余两份 Python）**。理由：0063 先落地让 bash 实现自然消失（三份 → 两份），本 ADR 再收敛到一份；反序会留下「②③ 已删、① 仍在内联决策树」的更差中间态。
7. **一致性测试改契约**：`test_stage_consumers_agreement.py` 从「三份实现输出相同」改为「单一实现 + 两个消费者输出相同」，并新增「模块内只有一处决策阶梯」的结构断言（例如 `grep -c 'def .*decision_tree\|def _scan_state'` = 1）。

### 影响范围

- **In Scope**：新建共享推荐模块；`_lib/cli/guide_cmd.py`；`_lib/workflow_synthesizer.py`；`skills/guide/scripts/guide_entry.sh`（改为调用 Python 模块，或随 ADR-0063 一起归档）；相关测试。
- **Out Scope**：推荐**内容**的变更（哪些情况推荐哪个 skill 由现有行为冻结，本 ADR 不改策略）；`rddf status` / `rddf monitor` 的其他输出；ADR-0063 的 stage_guide 退役与 skill 归档本身。

### 选项对比表

| 方案 | 结论 | 理由 |
|---|---|---|
| **A. 收敛到单一 Python 模块，消费者 import**（选中） | 采用 | 消除漂移根因；Python 是 ②③ 与 `guide_entry.sh` 的现有调用语言，无跨语言桥接 |
| B. 保留三份，加强一致性测试 | 拒绝 | `ab7c3ac1` 已证明「事后加测试」跟不上独立演化；测试只能发现漂移，不能阻止维护成本 |
| C. 收敛到 bash 单一实现 | 拒绝 | ②③ 与 `rddf monitor` 都是 Python 进程，每次推荐都要 `subprocess` 调 bash，增加故障面且无法复用 `state_reader` |
| D. 只删 bash，保留两份 Python | 拒绝 | 漂移面从 3 降到 2 而非归零；`ab7c3ac1` 的缺陷正是两份 Python 也各自读错字段 |
| E. 让 `workflow_synthesizer` 成为唯一实现，`guide_cmd` 调它 | 可接受但次优 | synthesizer 承担菜单/`child_progress`/`sessions` 聚合，职责过重。硬证据三条：(a) 其 `synthesize()` 的 catch-all 会把任何失败降级为 `rdd-builder` fallback，若 `rddf guide` 走它，`1c` corrupt 专属诊断会被遮蔽；(b) `_fallback_recommendation` 的菜单自身已漂移 —— 「设计阶段」「变更生成」两条 `MenuOption` 都是 `id="rdd-builder"`（`workflow_synthesizer.py:1124-1125`，v3 概念），正是「聚合职责漏改」的实证；(c) `rddf guide` 会白付 sessions/events.jsonl/git 目录遍历的 IO |

## 后果 / 代价

### 正面

- 推荐逻辑只有一处需要跟随 handoff schema 变更，ADR-0044 遗留的「三份都要改」维护成本归零。
- `rddf guide` 与 `rddf monitor` 的推荐不再可能分叉；`ab7c3ac1` 类缺陷的结构性成因消失。
- 决策树可被单测直接覆盖，不需要启动 bash 子进程。

### 负面 / 风险

- 一次性重构触及 `guide_cmd.py`（381 行）与 `workflow_synthesizer.py`（1129 行）的内部边界，若 `synthesize()` 的异常兜底（`_fallback_recommendation`）行为被改变，会破坏「never raises」契约。
- `guide_entry.sh` 改为调 Python 后，若目标环境无 `python3`，推荐退化为不可用 —— 现状下 `scan-state.sh` 在无 python3 时也有降级路径（`ab7c3ac1` 注明「result is marked non-authoritative」），需保持同等降级。
- 结转期存在「旧实现已删、新模块未对齐」的中间态，必须由测试锁住行为不变，不能靠人工比对。

### 回滚

本 ADR 是未实施的一次性重构，无数据迁移、无持久化格式变更。回滚 = `git revert <change 的提交>`；证伪「已回滚」的判据是 V-4 的三个测试文件恢复为「三实现输出相同」的旧断言并通过。若只部分回滚（保留共享模块但恢复某消费者），必须同时恢复 V-1 的计数断言，否则「单一决策阶梯」承诺失效而测试不报。

## Verification

- [ ] **V-1** 全仓 `grep -rn 'def _scan_state\|def _decision_tree\|def .*decision_tree' _lib/ skills/` ⇒ 命中 **1** 处；且 bash 侧 `grep -c 'RECOMMEND=' skills/guide/scripts/scan-state.sh` ⇒ 0（或该文件不存在 = ADR-0063 已落地）
- [ ] **V-2** `python3 -c "from skills._lib.cli.guide_cmd import cmd_guide"` 与 `python3 -c "from skills._lib.workflow_synthesizer import synthesize"` 均可导入（消费者未被破坏）
- [ ] **V-3** 状态矩阵下 `rddf guide` 与 `synthesize()` 的 **RECOMMEND / REASON / CONFIDENCE / 菜单项集合**完全一致。矩阵至少覆盖：`test_stage_consumers_agreement.py::V4_STATES` 的 4 态 + **无 `.arch-handoff.json`** + v3-design + corrupt-planner-handoff + non-object handoff（后 4 个是现测试未覆盖、且三份实现当前分歧的点）
- [ ] **V-4** `python3 -m pytest tests/unit/test_stage_consumers_agreement.py tests/unit/test_cli_guide.py tests/unit/test_workflow_synthesizer.py -q` ⇒ 全绿
- [ ] **V-5** 注入异常使共享模块抛错时，`synthesize()` 仍返回 `confidence="low"` 的 fallback，且 `cmd_guide` 不抛栈（never-raises / non-fatal 契约不破）
- [ ] **V-6** `skills/guide/scripts/guide_entry.sh` 中不再存在内联决策阶梯：`grep -c 'RECOMMEND=' skills/guide/scripts/guide_entry.sh` ⇒ 0（若该脚本随 ADR-0063 归档则本项由「文件不存在」满足）

## References

- ADR-0044 —— v4 Wave 3 硬移除（其 deferred follow-up 清单）
- ADR-0051 —— skill description 单一职责（反触发集中于 guide 推荐器）
- `ab7c3ac1` —— 三实现漂移的修复提交（本 ADR 的触发来源）
- `tests/unit/test_stage_consumers_agreement.py` —— 现有三实现一致性测试
