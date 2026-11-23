# rewrite-acceptance-form-batch-4 验收报告

**change**: `rewrite-acceptance-form-batch-4`
**判据来源**: `openspec/changes/rewrite-acceptance-form-batch-4/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）
**已用轮次**: 2（critic 第 1 轮 REJECT → 修正 → 第 2 轮 REJECT → 修正 → 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 3 份 spec 的 `acceptance-N` = 0、恒真 WHEN = 0 | **PASS** | 逐份 `grep -c`：`rddf-layout-manifest` 0/0 · `fix-bats-per-file-timeout` 0/0 · `fix-skill-post-install-discoverability` 0/0。**追加核**：`capability-N` 也 = 0（3 份各 0）；形态守卫 `tests/unit/test_spec_requirement_form.py` 5 例全绿 |
| **AC-2** **36** 条改写断言逐条有守卫背书 + 逐条可核实为真；**7 条 `capability-N`** 处置逐条有去向 | **PASS** | 台账「78 条 AC 的逐条台账」（**78 行**，机械核验 36 改写 + 15 合并 + 27 退役 = 78）；组 C 表**从 spec 实际内容重建**（36 行），并由机械对账脚本 `/tmp/opencode/reconcile_b4.py` 核验：**名称与 Scenario 数逐条一致 + 守卫名逐字存在 + spec 无未列出的 Requirement**。critic 第 1、2 轮独立核实守卫背书（B-2 后**扩守卫**：`test_non_rdd_entries_name_their_actual_writer` 逐条钉住 9 个条目） |
| **AC-3** **27** 条退役逐条有理由；**15** 组合并逐条给出去向；另有 **3 个子句级退役**逐条列明 | **PASS** | 台账组 B 的分类统计表 + 组 A' 的 78 行逐条台账（每行给出处置与去向/理由）。退役**不丢原文** —— 原文在 `openspec/changes/archive/2026-11-16-rddf-layout-manifest` / `2026-11-18-fix-bats-per-file-timeout` / `2026-09-21-fix-skill-post-install-discoverability` 的 `proposal.md` 的 `## Acceptance` 段 |
| **AC-4** 3 份的 `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate <3 份>` 各自只输出 `Specification '<x>' is valid`，**无 Purpose WARNING**（改前各 1 条） |
| **AC-5** 清单 `compliant` 7 → 10、`pending` 8 → 2；守卫全绿 + 负向验证 | **PASS** | `tests/unit/spec_form_compliant.json`：`compliant` = 10 份 · `pending` = 2 份（`env-bootstrap` / `objective-tracking`）· `class_total` = 12。`pytest tests/unit/test_spec_requirement_form.py -q` ⇒ **5 passed**（含 git-history 的「只增不减」判据）。**负向验证**：新守卫 `test_non_rdd_entries_name_their_actual_writer` 实测会因 manifest 归属漂移而红（等值断言 `got == expected`） |
| **AC-6** `validate --all --json` 只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用**准确基线**（3 份各自的归档 delta 重建）比对新旧 ⇒ **改前 214 条 / 改后 211 条**；`新增: 无`；`消失: 3 条 Purpose WARNING`；`very long: 62 → 62`；`validate --all` **ERROR 11 → 11** |
| **AC-7** 残留扫描器**未豁免命中数不变（0/0/0）**；含已豁免不增 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`（**不变**）；含已豁免 **303/159/41 → 297/157/40**（**减少** 6/2/1）。差异归因已核实：`diff -rq /tmp/opencode/specs-baseline-b4 openspec/specs` ⇒ **只有本批 3 份不同，其余 162 份逐字节相同**；`rddf-layout-manifest` 的 stage token 由 2 处 → 0。**冻结常量已同提交更新**（`tests/unit/test_v4_residue_check.py` 303/159/41 → 297/157/40 + docstring 追加历史），`pytest tests/unit/test_v4_residue_check.py::test_r4_repo_residue_constant` ⇒ passed |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ ****3535 passed, 3 skipped****；`ruff check skills/_lib/` ⇒ **All checks passed!**；相关 bats **72 例全绿**（`test_doctor_layout` · `test_regression_gate_evaluation` · `test_known_failures_baseline` · `test_regression_baseline_shrink_only` · `test_skill_layer1_self_contained` · `test_install_with_docs` · `test_setup_ai_context` · `test_doctor_ai_context_bootstrap` · `test_layer0_sentinel_order` · `test_rddf_init_hint` · `test_rddf_setup_help` · `test_layer0_template_sso`） |
| **AC-9** `./test.sh --full --regression` 全绿 | **PASS** | `GATE_RC=0` · `✅ ALL PASSED` · 未评估 **0** · 新增失败 **0**（已知失败 10 = 基线）· bats 419s / pytest unit 127s / integration 141s |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：**GATE_RC=0**（`✅ ALL PASSED`）。

| 指标 | 值 |
|---|---|
| 未评估文件 | **0** 个 |
| 已知失败（`tests/KNOWN_FAILURES.txt` 基线） | **10** |
| **新增失败** | **0**（`✅ 0 新增失败`） |
| bats regression（baseline-aware） | ✅ OK（419s） |
| pytest unit | ✅ OK（127s） |
| pytest integration | ✅ OK（141s） |
| rdd-doctor structural gate | ✅ 10 categories 全过（2 个带 warning） |

⇒ **AC-9 PASS**。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（脚本在 `/tmp/opencode/`） |
| 被 skip 的测试 | 无新增 skip |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | 无（第 1 轮 5 BLOCKER + 2 SF + 1 NIT、第 2 轮 2 BLOCKER + 1 SF + 3 NIT **全部采纳并实施**；critic 标 `scope_exceeded: true` 的 1 条 NIT 记 backlog） |
| **proposal 与 spec 的一致性** | 已由机械对账脚本保证（组 C 表 36 行 vs spec 36 条逐条一致） |
| **台账与 proposal 的一致性** | 已由脚本核验（78 行 = 36 + 15 + 27） |

## 实施期教训

1. **⑦ 按「形态类」计数，不要按「文件名模式」计数** —— `acceptance-N` 与 `capability-N` 是同一族的两种命名；
   本批漏处置 7 条 `capability-N`，直到收口前自查才发现。
2. **⑧ 判「无守卫」前必须先查文件名，不能只 grep 内容** —— 本批误判 `test_layer0_sentinel_order.bats`
   「不存在」而它确实存在 ⇒ 错误退役 ⇒ critic 第 2 轮 BLOCKER-1。
3. **⑨ spec 断言不得强于守卫** —— 「**a** read-only artefact …」是全称量化而守卫只钉单例
   ⇒ 处置选**扩守卫**（逐条钉住 9 个条目）。
4. **改写若让 stage token 真的消失，必须同提交更新冻结常量** —— 否则 `pytest` 红 1 条。
5. **计数口径自查要双轨**：「Requirement 总数」与「按类名计数」是两个数。

## 路由建议

无需返工。本批可归档。剩余 2 份按单批做完（`env-bootstrap` 44 + `objective-tracking` 33 = 77 条）。
`openspec/` 是否取消 gitignore 与 `rddf archive` 确认门需用户决策。
