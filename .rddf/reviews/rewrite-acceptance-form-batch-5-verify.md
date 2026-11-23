# rewrite-acceptance-form-batch-5 验收报告

**change**: `rewrite-acceptance-form-batch-5`（`acceptance-N` 系列**最后一批**）
**判据来源**: `openspec/changes/rewrite-acceptance-form-batch-5/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-10）
**已用轮次**: 1（critic 第 1 轮 APPROVE_WITH_CONDITIONS → 处置 → 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 2 份 spec 的 `acceptance-N` / `capability-N` / 恒真 WHEN = 0 | **PASS** | 逐份 `grep -c`：`env-bootstrap` 0/0/0 · `objective-tracking` 0/0/0 |
| **AC-2** **24** 条改写断言逐条有守卫背书 + 逐条可核实为真 | **PASS** | 台账「组 A'」77 行逐条台账；组 C 表（**24 行**）由 spec 实际内容重建，机械对账脚本 `/tmp/opencode/reconcile.py` 核验：**Requirement 名与 Scenario 数逐条一致 + 守卫名逐字存在 + spec 无未列出的 Requirement**。critic 第 1 轮独立核实 42 条退役与 24 条契约的守卫背书，唯一发现的措辞偏强（SF-1）**已处置** |
| **AC-3** **42** 条退役逐条有理由 + **16** 组合并逐条给出去向 | **PASS** | 分类统计**从台账实际重算**（非手填）：无守卫 17 · 元断言 10 · 否定断言 1 · 相对断言 3 · 过程性/状态快照 10 · 实现细节 1 = **42**；合并 **16**（逐条给出去向）。退役不丢原文（归档 change 的 `## Acceptance` 段） |
| **AC-4** 2 份的 `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate <2 份>` 各自只输出 `Specification '<x>' is valid`，**无 Purpose WARNING**（改前各 1 条） |
| **AC-5** 清单 `compliant` 10 → 12、`pending` 2 → 0；守卫全绿 + 负向验证 | **PASS** | `tests/unit/spec_form_compliant.json`：`compliant` = **12** 份 · `pending` = **0** 份 · `class_total` = 12。`pytest tests/unit/test_spec_requirement_form.py -q` ⇒ **5 passed**。**负向验证**：把 `env-bootstrap` 退回 `pending` ⇒ `test_pending_specs_still_declare_the_acceptance_form` **变红**（1 failed / 4 passed）⇒ 还原后复跑 5 passed ⇒ **promote 被守卫锁住** |
| **AC-6** `validate --all --json` 只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用**准确基线**（两份归档 delta 重建；delta 条数 == 改前 live 条数 ⇒ 无需应用裁剪）比对新旧 ⇒ **改前 211 条 / 改后 209 条**；`新增: 无`；`消失: 2 条 Purpose WARNING`；`very long: 62 → 62`；`validate --all` **ERROR 11 → 11** |
| **AC-7** 残留扫描器未豁免命中数不变（0/0/0）；含已豁免不增 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`（不变）；含已豁免 **297/157/40 → 297/157/40**（**完全不变** —— 本批未触碰任何 stage token，冻结常量 `test_v4_residue_check.py` 无需更新） |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3535 passed, 3 skipped**；`ruff check skills/_lib/` ⇒ **All checks passed!**；相关 bats **28 例全绿**（`test_env_bootstrap` · `test_objective_lifecycle` · `test_objective_structure` · `test_rdd_planner_objective`） |
| **AC-9** `./test.sh --full --regression` 全绿 | **PASS** | `GATE_RC=0` · `✅ ALL PASSED` · 未评估 **0** · 新增失败 **0**（已知失败 10 = 基线）· bats 442s / pytest unit 129s / integration 138s |
| **AC-10** **全仓** `acceptance-N` = 0 · `capability-N` = 0 · 恒真 WHEN = 0 | **PASS** | `grep -rh '^### Requirement: acceptance-' openspec/specs/` ⇒ **0**；`capability-` ⇒ **0**；`'the change is applied'` ⇒ **0**（全仓 165 份 spec / **747** 条 Requirement（本批净减 53：800 − 77 + 24））⇒ **形态系列 12/12 收口** |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：**GATE_RC=0**（`✅ ALL PASSED`）。

| 指标 | 值 |
|---|---|
| 未评估文件 | **0** 个 |
| 已知失败（`tests/KNOWN_FAILURES.txt` 基线） | **10** |
| **新增失败** | **0**（`✅ 0 新增失败`） |
| bats regression（baseline-aware） | ✅ OK（442s） |
| pytest unit | ✅ OK（129s） |
| pytest integration | ✅ OK（138s） |
| rdd-doctor structural gate | ✅ 10 categories 全过（2 个带 warning） |
| ruff / mypy strict | ✅ 全绿 |

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
| 未采纳的 finding | 无（5 SHOULD_FIX + 2 NIT **全部采纳并实施**；critic 标 `scope_exceeded: true` 的 SF-5 记 backlog） |
| **proposal 与 spec 的一致性** | 机械对账脚本保证（组 C 表 24 行 vs spec 24 条逐条一致，含 Scenario 数） |
| **台账与 proposal 的一致性** | 脚本核验（77 行 = 19 改写 + 16 合并 + 42 退役） |
| **清单改动已还原** | 负向验证的临时改动已 `cp` 还原并复跑 5 passed |

## 实施期教训

1. **⑦ 按「形态类」计数，不要按「文件名模式」计数**（第 4 批学）。
2. **⑧ 判「无守卫」前必须先查文件名，不能只 grep 内容**（第 4 批学）。
3. **⑨ spec 断言不得强于守卫** —— 尤其**否定断言**（「SHALL **NOT** fail with an X」需要守卫断言 X
   **缺席**，而守卫通常只断言它**在场**）。
4. **⑩ 退役理由必须可核实** —— 「全仓 grep 0 处」这类措辞要写成「tests/ 无守卫（机制/引用存在）」。
   critic 抓到我在两条台账里写「全仓 grep `fix-decisions` 0 处」/「全仓 grep 无命中」，
   实际前者命中 **8 个文件**、后者 `SKILL.md:144` 字面就写着那句话 ⇒ **退役决定成立，但理由是错的**。

## 路由建议

无需返工。本批可归档，形态系列收口。
`openspec/` 是否取消 gitignore、`rddf archive` 确认门、形态清单升级为「按形态类」+ 全仓扫描守卫
三项需用户决策（均已记 tail）。
