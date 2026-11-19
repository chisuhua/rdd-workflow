# cleanup-guide-star-residue 验收报告

- **change**: `openspec/changes/cleanup-guide-star-residue/`
- **日期**: 2026-11-19
- **验收方式**: 本地验收（`rdd-verifier` skill 分流条件 2 不满足 —— `.rddf/state/iteration.json` 中无本 change 记录，P3 archive gate 未触发）
- **已用轮次**: 1

## 判据来源

`openspec/changes/cleanup-guide-star-residue/proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-9）。

## 逐条判定

| AC | 判定 | 取证命令与结果 |
|---|---|---|
| AC-1 | **pass** | `python3 -c "...pyrightconfig roots..."` ⇒ `bad roots: []`（3 个不存在 root 已删；`skills/guide` 仍在，属 C 范围） |
| AC-2 | **pass** | `_lib/workflow_synthesizer.py` 的 `_fallback_recommendation` docstring 已改为 `rdd-builder`（1104 行附近无 `guide-ship` 声称；剩余的 623/625/656 是历史注释） |
| AC-3 | **pass** | `grep -c 'agents/skills/guide-plan\|guide-ship' tests/integration/test_global_install_external_project.bats` ⇒ `0` |
| AC-4 | **pass** | `grep -c 'skills/guide-' tests/scripts/check_wrap_grep.sh` ⇒ `0`；`tests/unit/test_design_done_gate.sh` 不存在（已删） |
| AC-5 | **pass** | `test_feedback_cli.py` 含 2 处 `--from guide-design`（legacy）+ 1 处 `--from rdd-builder`；`test_feedback_cmd.bats` 4 处覆盖 |
| AC-6 | **pass** | `pytest tests/unit/test_v4_residue_check.py -q` ⇒ 11 passed；`doctor.sh --category v4-residue` ⇒ rc=1（WARNING only，非 unknown-category 拒绝） |
| AC-7 | **pass** | `pytest ...::test_r2_or_idiom_is_flagged` ⇒ 1 passed |
| AC-8 | **pass** | `pytest tests/unit/ -q` ⇒ **3443 passed / 3 skipped**；`bats tests/_lib/test_skill.bats tests/smoke.bats` ⇒ 全 ok |
| AC-9 | **pass** | 全量门 `/tmp/opencode/a-full.log` ⇒ `✅ ALL PASSED`；增量回归门 ⇒ `0 新增失败 / 11 已知失败 / 未评估 0` |

## 失败项

无。

## 遗留清扫结果

| 项 | 结果 |
|---|---|
| TODO / 半截实现 | 无 |
| 注释掉的代码 | 无 |
| 临时调试日志 | 无 |
| 被 skip 的测试 | 无新增 |
| 未替换的 mock | 无 |
| 临时 fallback | 无 |
| 死代码 | 额外清除：`orphan_gates_check.py`（检查目标已不存在 ⇒ 恒返回空）+ `test_rdd_doctor.py`（整文件测它）+ `test_design_done_gate.sh`（被测函数全仓不存在） |

## 备注

1. **AC-6 的 rc=1 是预期**：`doctor --category v4-residue` 命中 `skills/guide/scripts/scan-state.sh:669` 1 条 WARNING。该 WARNING 由 `retire-guide-orchestrator` 归档 `skills/guide` 后自动消失（`_SCAN_ROOTS` 只扫 `_lib` / `skills`）。
2. **iteration.json 未登记本 change**：planner 阶段未写 `iteration.json` 条目，导致无法走 `rdd-verifier` skill 的 P3 gate 路径。不影响 AC 判定，但归档流程需补登记（已记录，交 builder 归档前处理）。
3. **范围外发现已纳入**：`orphan_gates_check.py` 恒返回空（假绿）不在原 AC 清单，但与 A 的主题（清恒假判据）同源，已在 `tasks.md` T1.4 记录并实施。
