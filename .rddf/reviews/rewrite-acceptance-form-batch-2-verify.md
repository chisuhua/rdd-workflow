# rewrite-acceptance-form-batch-2 验收报告

**change**: `rewrite-acceptance-form-batch-2`
**判据来源**: `openspec/changes/rewrite-acceptance-form-batch-2/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）
**已用轮次**: 1（critic 1 轮 + 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 3 份 spec 的 `acceptance-N` = 0、恒真 WHEN = 0 | **PASS** | 逐份 `grep -c`：`fix-flow-drift-batch-1` 0/0 · `fix-worktree-archive-path` 0/0 · `fix-p3-verifier-gate` 0/0；守卫 `tests/unit/test_spec_requirement_form.py` 的形态判据 A/B 全绿 |
| **AC-2** 19 条改写断言逐条有守卫背书 + 逐条可核实为真 | **PASS** | 台账「27 条 AC 的分流」表逐条列出守卫测试名。critic 第 1 轮独立核实 **16 条为真**；3 处缺口（branch 删除 / 消息三条出路 / tracked 路径的 grep 级守卫）**已在本批补齐或改引更强守卫**。另：本批**扩展 2 个既有 bats 用例**（见 AC-2b） |
| **AC-2b**（critic SF-1 / SF-2 的落实）无守卫子句已补上守卫 | **PASS** | ① `test_phase3_archives_in_main_repo.bats` 的 cleanup 用例加 `git rev-parse --verify --quiet refs/heads/openspec/demo` ⇒ 断言分支不存在；② `test_rdd_builder_phase3_archive.bats` 的 missing-cache 用例加 `rddf rdd-verify` / `SKIP_RDD_VERIFIER` / `.ac-verdict-demo.json` 三条断言 ⇒ 三条出路有守卫。两个文件实测**全绿** |
| **AC-3** 8 条退役逐条有理由 | **PASS** | 台账逐条记录：5 条元断言 · 1 条**已被推翻**（`.rddf/improvements/fix-lightweight-branch-and-archive.md:233-235`）· 1 条**无守卫**（spec 合流；critic 核出全仓唯一相关断言是 mock 型 e2e）· 1 条**没有流程级守卫**（`archive_path` 全仓无守卫 + untracked 路径传空 sha）。原文仍在 `openspec/changes/archive/<date>-<name>/proposal.md` |
| **AC-4** 3 份的 `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate <3 份>` 各自只输出 `Specification '<x>' is valid`，**无 Purpose WARNING**（改前各 1 条） |
| **AC-5** 清单 `compliant` 1 → 4、`pending` 11 → 8；守卫全绿 + 负向验证 | **PASS** | `tests/unit/spec_form_compliant.json`：`compliant` = 4 份 · `pending` = 8 份 · `class_total` = 12。`pytest tests/unit/test_spec_requirement_form.py -q` ⇒ **5 passed**（含 git-history 的「只增不减」判据 —— 入库后已生效，不再 skip） |
| **AC-6** `validate --all --json` 只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用**准确基线**（由 3 份 spec 各自的归档 delta 重建：`/tmp/opencode/specs-baseline-b2/`，165 份）比对新旧 ⇒ **改前 220 条 / 改后 217 条**；`新增: 无`；`消失: 3 条 Purpose WARNING`；`very long: 62 → 62`；`openspec validate --all` ERROR **11 → 11** |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`（本批不涉及退役 stage 名） |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3534 passed, 3 skipped**（3529 + 5 个清单/形态守卫）；`ruff check skills/_lib/` ⇒ **All checks passed!**；被扩展的 2 个 bats 文件**全绿** |
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
| 被 skip 的测试 | 无新增 skip（本批之后清单的 git-history 判据已从 skip 转为 pass） |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | 无（4 SF + 3 NIT 全部采纳并实施） |

## 实施期教训

1. **「无守卫子句」优先补守卫，而不是削契约。** 本批 2 处都是「行为是真的、守卫是缺的」⇒
   补守卫保住了契约强度。⚠️ 补之前先确认**断言非空转**：branch 那条依赖 fixture 用
   `-b openspec/demo` 真建了分支。
2. **退役理由本身要经得起核 —— 理由错 ≠ 结论错。** 我写「没有测试断言 `archive_commit_sha`
   被写入」，critic 核出**有** helper 级与 lightweight 级守卫 ⇒ 退役结论不变，但理由必须改成
   「**没有流程级守卫**断言 worktree/untracked 路径写入它」。
3. **守卫引用要核对「夹具是什么」。** `test_rdd_builder_phase3_archive.bats` 的夹具是
   **lightweight 模式** ⇒ 拿它当「untracked-openspec 路径」的守卫是引错了。
4. **mock 型 e2e 不算行为守卫。** 全仓唯一断言「归档后 spec 存在」的 `test_rdd_builder_e2e.bats:89`
   由 `scenarios/b_e9.json:12` 直接铺文件 ⇒ 不能当「spec 合流」的背书。
5. **「已被推翻」是退役的一类独立理由。** `fix-worktree-archive-path` 的 AC-8 被
   `fix-lightweight-branch-and-archive` **有意变更** ⇒ 它已不是现行契约；而新行为已落在
   `archive-openspec-tracked-skip-commit/spec.md` 与 `archive-auto-commit/spec.md` ⇒ **退役不丢信息**
   （critic focus 4 核实）。

## 路由建议

无需返工。本批可归档。剩余 8 份按「每批 3 份」继续（剩 ≈4–6 h）。
`openspec/` 是否取消 gitignore 与 `rddf archive` 确认门需用户决策。
