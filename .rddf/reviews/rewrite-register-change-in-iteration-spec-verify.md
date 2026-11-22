# rewrite-register-change-in-iteration-spec 验收报告

**change**: `rewrite-register-change-in-iteration-spec`
**判据来源**: `openspec/changes/rewrite-register-change-in-iteration-spec/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-11）
**已用轮次**: 1（critic 1 轮 + 本验收）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 该 spec 无 `acceptance-N` Requirement 名（= 0） | **PASS** | `grep -c '^### Requirement: acceptance-' openspec/specs/register-change-in-iteration/spec.md` ⇒ **0**；`pytest tests/unit/test_spec_requirement_form.py` 的形态判据 A 通过 |
| **AC-2** 该 spec 无恒真 WHEN（= 0） | **PASS** | 形态判据 B 通过（`test_compliant_specs_have_no_tautological_scenario_when`）；改写后 11 个 Scenario 的 WHEN 全部是具体触发条件（如「`phase0_approval.sh` approves a change whose improvement draft exists」） |
| **AC-3** **6** 条改写断言逐条有守卫背书 + 逐条可核实为真 | **PASS** | 台账「改写清单」表逐条列出守卫测试名。实读核验：`test_phase0_iteration_register.bats` 7 例（全部实读）、`tests/unit/test_archive_iteration_sync.py` 5 例（`:79`/`:94`/`:109`/`:134`/`:164`）、`test_rdd_builder_phases.bats:131`。⚠️ 实读发现**归档 AC-2 的语义已过时**（引用的 `"missing from iteration.json"` 字符串全仓不存在；实现已改为磁盘自动恢复）⇒ 新契约按实现的真实行为写 |
| **AC-4** `## Purpose` 不再是 `TBD` 占位 | **PASS** | `openspec validate register-change-in-iteration` ⇒ `Specification 'register-change-in-iteration' is valid`，**无 Purpose WARNING**（改前有 1 条） |
| **AC-5** 新守卫全绿 + 负向验证 | **PASS** | `pytest tests/unit/test_spec_requirement_form.py -q` ⇒ **4 passed, 1 skipped**（skip 是 git-history 判据，改前 manifest 未入库）。**负向验证**：插入 `acceptance-N` Requirement 名 ✅抓到 / 插入恒真 WHEN ✅抓到；恢复正常后全绿 |
| **AC-5b** 幂等契约的 `archived_at` / `archive_commit_sha` 子句**有守卫** | **PASS** | `tests/integration/test_phase0_iteration_register.bats` 的幂等用例已扩展：re-approve 前 seed `archived_at="2026-01-02T03:04:05+00:00"` / `archive_commit_sha="deadbeefcafe"`，断言二者不变 ⇒ 该子句从「核实不了」变成**有守卫**（critic SF-1）。实测 `bats` ⇒ **7/7 pass** |
| **AC-6** `validate --all --json` 只减不增；`very long` 不新增；ERROR 不增 | **PASS** | 用**准确基线**（由归档 change 的 delta 重建：`/tmp/opencode/specs-baseline-rci/`，165 份）比对新旧 ⇒ **改前 221 条 / 改后 220 条**；`新增: 无`；`消失: 1 条 register-change-in-iteration 的 Purpose WARNING`；`very long: 62 → 62`；`openspec validate --all` ERROR **11 → 11** |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`（本批不涉及退役 stage 名） |
| **AC-8** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3533 passed, 4 skipped**（3529 + 4 守卫；+1 skip = git-history 判据，manifest 入库后生效）；`ruff check skills/_lib/` ⇒ **All checks passed!** |
| **AC-9** `./test.sh --full --regression` 全绿 | **见下** | 见「全量门」 |
| **AC-10** 试点结论已记录（三格） | **PASS** | 台账 `.rddf/reviews/rewrite-register-change-in-iteration-2026-11-23.md` 的「AC-10 试点结论（三格）」段：① 工作量基线（每份 spec 边际成本 ≈30–45 min，剩余 11 份 ≈6–9 h）② 全量化路径（清单逐批 promote + 判据 ①② 的 CI 牙齿 + 内容级守卫需取消 gitignore）③ 退役 vs 改写的分流判据（4 行表格） |
| **AC-11** 清单是 **tracked** 且判据 ①② 在 CI 上可判 | **PASS** | `tests/unit/spec_form_compliant.json` 是新增的 tracked 文件（`git status` 可见）；判据 ①（schema / 无重复 / 不交 / 并集 == 已知全集 12 份 / 非空）与 ②（`git show HEAD:…` 对比 ⇒ **只增不减**）**只读该 tracked 文件** ⇒ CI 上可判。形态判据 ③④⑤ 需 `openspec/specs/` ⇒ CI skip（已在台账与 proposal 落纸面） |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：见「全量门」段。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（脚本在 `/tmp/opencode/`） |
| 被 skip 的测试 | +1（`test_manifest_compliant_is_monotonic_in_history` 在 manifest 入库前 skip ⇒ 入库后生效；这是设计内行为） |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 未采纳的 finding | 无（4 SF + 4 NIT 全部采纳并实施） |

## 实施期教训

1. **归档 AC 的文字不可信 —— 必须实读实现与守卫再写契约。**
   归档 AC-2 写「不再返回 `"missing from iteration.json"` warning」，但**那个字符串全仓不存在**，
   且实现已改成**磁盘自动恢复**（entry 缺失但磁盘有 archive 目录 ⇒ 重建 entry、不报 warning）。
   ⇒ 照抄归档 AC 会把一句**已不准确**的断言固化下来。
2. **「元断言」不是能力契约。** `acceptance-8`（「既有行为不回归」）与 `acceptance-9`
   （「doctor 无**新增** finding」）—— 前者是「别退化」的期望，后者依赖基线 ⇒ 都不可判定
   ⇒ 退役（**原文仍在 archive 里**，不丢内容）。
3. **无守卫的子句不能进 spec。** critic 抓到幂等契约的 `archived_at` / `archive_commit_sha`
   子句**没有任何测试 set 过** ⇒ 两条出路：扩测试（采纳）或收窄契约。
   ⇒ 扩测试的成本（约 10 min）远低于「在主 spec 里冻一句没人守的话」。
4. **「退役 vs 改写」的分流判据是「机制是否还在 + 是否有逐条可机判的守卫」**，
   不是「名字像不像能力名」。本批 9 条里 6 条改写、2 条退役（且 2 条退役的都是元/相对断言）。
5. **清单型守卫要能看见「停滞」。** 手工维护的清单最现实的失败模式是「永远停在 1 份」⇒
   清单做成 **tracked 文件** + 「并集 == 已知全集」「只增不减（git 历史）」两条判据
   ⇒ 停滞与误删都变成 CI 可见。

## 路由建议

无需返工。本批可归档。剩余 11 份按 AC-10 ① 的基线立项（每批 1 份）。
`openspec/` 是否取消 gitignore 与 `rddf archive` 确认门需用户决策。
