# consolidate-recommender-implementation 验收报告

- **change**: `openspec/changes/consolidate-recommender-implementation/`
- **日期**: 2026-11-19
- **验收方式**: 本地验收（`rdd-verifier` skill 分流条件 2 不满足 —— `.rddf/state/iteration.json` 中本 change 为 `in_worktree`，P3 archive gate 未触发）
- **已用轮次**: 1
- **依据 ADR**: ADR-0062（推荐器决策树收敛到单一实现，已采纳）

## 判据来源

`openspec/changes/consolidate-recommender-implementation/proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-9），
叠加 ADR-0062 的 `## Verification` 段（V-1 ~ V-6）。

## 逐条判定

| AC | 判定 | 取证命令与结果 |
|---|---|---|
| AC-1 | **pass** | `grep -rn 'def _scan_state\|def _decision_tree' _lib/ skills/` ⇒ **0** 处（单一实现后两个旧入口名均已消失）；bash 侧 `ls skills/guide/scripts/scan-state.sh` ⇒ 不存在（C 已归档，ADR-0062 V-1 的「或该文件不存在」分支满足） |
| AC-2 | **pass** | `pytest tests/unit/test_recommender.py::TestSingleImplementationStructure` ⇒ 4 passed。AST 判据实测：`_lib/` + `skills/` 中「可返回 ≥3 个不同 stage 字面量」的函数恰有 1 个（`_lib/recommender.py::scan_state`）。同一判据在改造前会命中 4 个（含 `docs_consistency.py::check_role_frontmatter` 与 synthesizer 的两个菜单构造函数 —— 断言只认「返回值直接是 stage 字面量」的函数，菜单 `id=` 不算） |
| AC-3 | **pass** | `python3 -c "from skills._lib.cli.guide_cmd import cmd_guide; from skills._lib.workflow_synthesizer import synthesize"` ⇒ 两消费者均可导入 |
| AC-4 | **pass** | 单元断言 `pytest tests/unit/test_stage_consumers_agreement.py` ⇒ 10 passed（7 态矩阵 + 3 个专项）。**独立取证**（不复用测试 helper）：`/tmp/opencode/verify_b.py` 以**真实 CLI 子进程**（`python3 -m skills._lib.cli guide`）对比 `synthesize()`，8 状态 ⇒ **0 mismatch**，且每态都校验了 `reason != "fallback: synthesizer error"`（排除「fallback 冒充一致」的假阳性） |
| AC-5 | **pass** | confidence 与菜单项集合只对 synthesizer 侧断言：独立取证输出中 `conf=high` 仅在 synth 侧出现；CLI 侧输出经解析确认**不含** confidence / 菜单字段（`rddf guide` 的 stdout 格式本就不带这两项）—— 与 proposal 的 metis 修订一致 |
| AC-6 | **pass** | `pytest tests/unit/test_cli_guide.py::test_cmd_guide_does_not_raise_when_ladder_fails tests/unit/test_cli_guide.py::test_cmd_guide_fallback_text_is_distinguishable tests/unit/test_workflow_synthesizer.py::TestNeverRaises::test_ladder_failure_falls_back_without_raising` ⇒ 3 passed。实测行为：synth → `rdd-builder` / `confidence=low` / `reason="fallback: synthesizer error"`；CLI → `rc=0`，stderr `⚠️ state scan failed (forced)`，输出 `💡 建议: rdd-builder`。两者 fallback 文案**可区分**，均不抛栈 |
| AC-7 | **pass** | `pytest tests/unit/test_workflow_synthesizer.py::TestFallbackMenu` ⇒ 3 passed。实测 fallback 菜单 5 项，id 集合 `{rdd-builder, rdd-arch, rdd-planner, rdd-verifier, add-improve}` **无重复**；label 集合不含 v3 概念「设计阶段」「变更生成」（原实现三条 `MenuOption` 全部 `id="rdd-builder"`） |
| AC-8 | **pass** | `pytest tests/unit/test_stage_consumers_agreement.py tests/unit/test_cli_guide.py tests/unit/test_workflow_synthesizer.py tests/unit/test_recommender.py -q` ⇒ **89 passed** |
| AC-9 | **pass** | 全量门 `/tmp/opencode/b-full.log` ⇒ `rc=0` / `✅ ALL PASSED`：bats 回归门 **0 新增失败 / 11 已知失败 / 未评估 0**；`pytest unit` **3433 passed / 3 skipped**；`pytest integration` **196 passed**；静态门（隔离 / ruff / mypy strict / doctor structural）全绿 |

### ADR-0062 Verification 对照

| V | 判定 | 说明 |
|---|---|---|
| V-1 | pass | 同 AC-1（Python 侧命中数由「1 处」变为「0 处」—— 单一实现后旧函数名不再存在，判据的实质「只有一处决策阶梯」由 AC-2 的 AST 断言承接） |
| V-2 | pass | 同 AC-3 |
| V-3 | **部分** | 8 态矩阵下 RECOMMEND / REASON **完全一致**（0 mismatch）；CONFIDENCE 与菜单项集合在 CLI 侧**无对应输出**（`rddf guide` 的 stdout 格式本就不含）—— 该两项只对 synthesizer 侧断言。此为 ADR 判据字面表述与 CLI 实际输出面的差异，已在 metis 阶段写入 proposal 的 AC-5，非实现偏差 |
| V-4 | pass | 同 AC-8 |
| V-5 | pass | 同 AC-6 |
| V-6 | pass | `skills/guide/scripts/guide_entry.sh` 已随 C 归档到 `docs/legacy/skills/guide/scripts/guide_entry.sh` —— 判据的「文件不存在」分支满足 |

## 失败项

无。

## 遗留清扫结果

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK | 0（`grep` 全部改动文件） |
| 调试日志 / `breakpoint()` / `pdb` | 0 |
| 注释掉的代码 | 0 |
| 被 skip 的测试 | 无新增 |
| 未替换的 mock | 0（`_list_worktrees` / `_worktree_has_incomplete_tasks` / `_committed_change_in_head` / `_count_active_changes_on_disk` 四个旧 helper 连同其 monkeypatch 全部随实现迁走并改写） |
| 临时 fallback 分支 | 0 |
| 死代码 | `workflow_synthesizer._build_all_options` 的 `plan_h` 参数为**既有**未使用参数（改造前即如此，且集成测试按位置传参）—— 范围外，未动，已记录 |
| 命名歧义 | `synthesizer._count_active_changes(iteration)`（数台账）与 `recommender._count_active_changes(project_root)`（数磁盘）同名不同义 → 已重命名为 `_count_active_changes_in_iteration` |
| 测试污染 | 发现并清理 `improvement-suggestions.md` 末尾 2 行 `dirty e2e content` —— 来自 C 已删除的 `test_pre_checkout_warning.bats`（该测试直接往真实仓库文件追加内容）。已 `git checkout` 恢复 |

## 备注

1. **等价性另行验证**：实现期间用 `git show HEAD:_lib/cli/guide_cmd.py`（改动前的 CLI ladder）作参照，与新 `recommender.scan_state` 在 13 个状态上逐一对拍 ⇒ **0 diff**。该脚本是一次性验证工具，未入库。
2. **行为变更（预期）**：ADR-0062 Decision 4 的分歧表对齐了 3 处 —— 无 arch-handoff 时按 CLI 基准「穿透」、v3-plan stale 交叉校验纳入、`1c` corrupt 专属诊断纳入。表现为 `synthesize()` 的 `reason` 文案变化（`->` → `→`）与部分场景的推荐结果变化（无 arch-handoff 时由 `rdd-arch` 变为 CLI 的穿透结果）。这是「既定行为对齐」，非策略变更。
3. **`iteration.json` 登记**：本 change 与 `retire-guide-orchestrator` 已登记为 `in_worktree`；`cleanup-guide-star-residue` 已由 `rddf archive-sync --all` 补登记为 `archived`。
