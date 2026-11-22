# rewrite-acceptance-form-batch-3 验收报告

**change**: `rewrite-acceptance-form-batch-3`
**判据来源**: `openspec/changes/rewrite-acceptance-form-batch-3/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）
**已用轮次**: 1（critic 1 轮 REJECT → 修正 → 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 3 份 spec 的 `acceptance-N` = 0、恒真 WHEN = 0 | **PASS** | 逐份 `grep -c`：`fix-phase3-cleanup-wiring` 0/0 · `fix-script-project-root-anchoring` 0/0 · `rfc-rddf-project-yaml-config-i10` 0/0；守卫形态判据 A/B 全绿 |
| **AC-2** **15** 条改写断言逐条有守卫背书 + 逐条可核实为真 | **PASS** | 台账「34 条 AC 的分流」表逐条列出守卫测试名。critic 第 1 轮独立核实 **14 条覆盖充分**；唯一缺口（缓存写入从句）**已补列** `tests/unit/test_rdd_verify_cmd.py::test_run_one_change_passed_writes_cache_and_state`（SF-1）。另 critic 确认 `post-archive-cleanup-works-without-a-project-lib` 的担忧**不成立**（守卫同时断言了「定位」与「同步」） |
| **AC-3** **19** 条退役逐条有理由 | **PASS** | 台账逐条记录：8 条元断言/相对断言 · 2 条**无守卫** · 1 条**已被 batch7b2 签批删除** · 1 条**与实现相反**（BLOCKER-1）· 5 条过程性/里程碑过程 · 1 条过程性（新建 ADR）。原文仍在 `openspec/changes/archive/<date>-<name>/proposal.md` |
| **AC-4** 3 份的 `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate <3 份>` 各自只输出 `Specification '<x>' is valid`，**无 Purpose WARNING**（改前各 1 条） |
| **AC-5** 清单 `compliant` 4 → 7、`pending` 8 → 5；守卫全绿 + 负向验证 | **PASS** | `tests/unit/spec_form_compliant.json`：`compliant` = 7 份 · `pending` = 5 份 · `class_total` = 12。`pytest tests/unit/test_spec_requirement_form.py -q` ⇒ **5 passed**（含 git-history 的「只增不减」判据） |
| **AC-6** `validate --all --json` 只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用**准确基线**（由 3 份 spec 各自的归档 delta 重建；`rfc-rddf` 额外删掉 batch7b2 已删的 `acceptance-3` ⇒ 15 → 14）比对新旧 ⇒ **改前 217 条 / 改后 214 条**；`新增: 无`；`消失: 3 条 Purpose WARNING`；`very long: 62 → 62`；ERROR **11 → 11** |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41` |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3534 passed, 3 skipped**；`ruff check skills/_lib/` ⇒ **All checks passed!**；相关 bats（`test_phase_root_anchoring` · `test_post_archive_cleanup_guard` · `test_ship_execution_mode_reads_project_yaml` · `test_rdd_verifier_hook_provider`，共 28 例）**全绿** |
| **AC-9** `./test.sh --full --regression` 全绿 | **见下** | 见「全量门」 |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：见「全量门」段。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（脚本在 `/tmp/opencode/`） |
| 被 skip 的测试 | 无新增 skip |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | 无（2 BLOCKER + 3 SF + 1 NIT 全部采纳并实施；NIT 记 backlog） |

## 实施期教训

1. **不能照抄归档 AC 的措辞 —— 它描述的是过去。** 归档 AC 说「`git.openspec_tracked: false`
   时强制轻量模式」，我改写时写成「强制 serial 且**不可覆盖**」⇒ **与实现相反**
   （实现优先级是 CLI flag > project.yaml > env）⇒ 而且**我自己引的守卫
   `CLI flag --parallel wins over project.yaml` 就在反证它**。
   ⇒ 改写必须**实读实现 + 守卫**，不是润色归档文字。
2. **「spec 里没有」有两种成因，处置相反**：
   - **归档工件缺陷**（`AC-G2`：14 条 AC ⇒ 13 条 delta，AC-G2 生成时整丢了）⇒ **补回**；
   - **已签批删除**（`acceptance-3`：batch7b2 §D 有意删除，理由是判据被 v4 反证 +
     正确判据已在 `complete-project-yaml-config-gaps`）⇒ **不补回**。
   ⇒ 判据要看**归档 delta 与 live spec 的差异记录**，不能只看「有没有守卫」。
3. **合并多条 AC 到一条 Requirement 时，要逐个 Scenario 核守卫强度** —— SF-2 就是合并后某条
   正向从句没有守卫（守卫只断言「真仓零 worktree」，脚本提前失败照样绿）⇒ 收窄到守卫实际断言的内容。
4. **退役的两个方向都要核** —— 第 2 批学的是「退役理由不准确 ⇒ 结论仍可能对」；
   本批是**反过来**：退役结论也错了（我补回了一条已被签批删除且被 v4 反证的判据）。

## 路由建议

无需返工。本批可归档。剩余 5 份按「每批 3 份」继续（剩 ≈3–5 h，拆 2 批 3+2）。
`openspec/` 是否取消 gitignore 与 `rddf archive` 确认门需用户决策。
