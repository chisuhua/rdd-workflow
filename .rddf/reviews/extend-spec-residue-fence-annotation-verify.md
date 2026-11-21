# 验收报告 — extend-spec-residue-fence-annotation

- **change**：`openspec/changes/extend-spec-residue-fence-annotation/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 **机制缺口**修复 —— 豁免机制加「围栏位置」。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-12）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT**（1 plan BLOCKER + 7 SHOULD_FIX + 3 NITS）；`mergeable: no` / `scope_exceeded: true` | 全部处置：**BLOCKER**（AC-6 与 T6.2 自相矛盾）⇒ 改为「281 处**行级**豁免一处不丢 + 新增 2 处围栏式 ⇒ 总 283」+「含已豁免不变」单独写死。**SF-1~SF-7** 与 **NIT-1~3** 逐条处置，明细见 `proposal.md` 的「审查链」段。critic 独立验算了 AC-7 常数（确认 42/35/15 + 325/176/46 不变 + 283），与实测一致 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 围栏式豁免整块（含一行多 token） | **pass** | `test_r4_fence_annotation_exempts_whole_block`：fixture 一行含 `guide-ship|guide-plan` ⇒ `hits` 2 处全部 `category=enum`、未豁免 0；`fence_allows[0]` = `(3, 5, "enum", ("guide-plan","guide-ship"))`；R4 WARNING 0 |
| AC-2 code 限 `enum`/`guard` | **pass** | `test_r4_fence_annotation_rejects_non_enum_guard_codes` 参数化 3 个 code（`history` / `proposal-name` / `rename-history`）⇒ 每个都报 `fence-position allow code` **且**命中仍以「1 处已退役」出现（不豁免） |
| AC-3 未闭合围栏 | **pass** | (a) `test_r4_unclosed_fence_hits_still_reported` ⇒ 未闭合围栏内 `guide-ship` **仍被报告**（此前 `_split_blocks` 会把 EOF 前正文静默逐出扫描）；(b) `test_r4_unclosed_fence_annotation_is_in_fence` ⇒ 报 `in_fence` 且命中仍报 |
| AC-4 围栏式无 token ⇒ stale | **pass** | `test_r4_fence_annotation_without_token_is_stale`：围栏内 `{"route": "clean"}` + `enum` 标注 ⇒ 报 `stale allow` |
| AC-5 围栏内标注不生效 + 报 `in_fence` | **pass** | `test_r4_annotation_inside_fence_is_not_metadata`：标注紧跟围栏内命中行 ⇒ 报 `围栏内` **且**命中仍报「1 处已退役」 |
| AC-6 行级零回归 / 总数 283 / 含已豁免不变 | **pass** | 实测：既有 281 处**行级**豁免一处未丢（改前 281 全为行级）；总数 **283**（+2 围栏式）；含已豁免 **325 / 176 / 46 不变** |
| AC-7 42/35/15 + 三个诊断全 0 | **pass** | `scan_specs(REPO_ROOT)` ⇒ 未豁免 **42 处 / 35 块 / 15 份**；`stale_allows`=0、`fence_rejected`=0、`in_fence_annotations`=0；`fence_allows`=1；`files_scanned`=165 不变；dashboard 未豁免 2 → **0** |
| AC-8 单测 + ruff | **pass** | `pytest tests/unit/test_v4_residue_check.py tests/unit/test_spec_residue_census.py -q` ⇒ **65 passed**；`ruff check`（5 个改动文件）⇒ All checks passed |
| AC-9 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229 评估、未评估 0、新增失败 0**；`./test.sh --gates` ALL PASSED |
| AC-10 文档同步 | **pass** | `spec_residue_scan.py` docstring 的 Exemptions 段重写（两个位置 + 四个限制 + 未闭合围栏 fail-closed + 围栏内标注不是元数据 + Purpose 内围栏 no-op corner）；`skills/rdd-doctor/SKILL.md` 的 R4 段同步（外层用 4 个反引号避免嵌套围栏渲染错乱） |
| AC-11 台账 | **pass** | `.rddf/reviews/spec-residue-fence-annotation-2026-11-21.md`：1 行 / 2 处逐行处置 + 「为什么只能豁免不能改指」选项表 + 四个限制的可机判映射 + 两处顺带修的既有缺陷 + 实测数字 + 回滚凭据 |
| AC-12 census 幂等 + 清单段 + 常数 | **pass** | 两次生成 `diff` 为空；新增「围栏式豁免清单」段含 1 条（`dashboard-verification-status/spec.md` 45–57 `enum` `guide-plan, guide-ship`）；`test_r4_repo_residue_constant` 更新为 42/35/15 + 325/176/46 + `fence_allows == ["enum"]` 护栏 |

## 实施期发现

**无判据缺陷。** 与 batch5 不同，本次 AC-7 的常数在实施前后**完全一致**（critic 的独立验算也一致）——
因为口径已在 batch5 的教训后写死：「标注不消除命中」「块数 = 未豁免 block 数」「份数 = 仍有未豁免命中的文件数」。

**唯一实施期调整**：census 围栏清单的 `file` 列改为反引号包裹（`` `openspec/specs/…` ``），
否则测试辅助 `_rows()`（`line.startswith("| openspec/")`）会把审计表的行当成待办行捕获 ——
这是**测试契约**层面的细节，不是判据变更。

## 遗留清扫

- 本次范围内（T7.9）：无 TODO / FIXME / 调试 `print`（`gen_spec_residue_census.py:283` 的 `print` 是 CLI 正常输出）；
  无半截实现；三个新字段全部有消费方（`v4_residue_check.py` 渲染 2 个 + `gen_spec_residue_census.py` 渲染 1 个）。
- **范围外历史遗留（只记录，未动）**：`spec_residue_scan.py:488` 的 `hit_lines` 是死变量（改前就存在，
  只 `add` 从不读）。本次未删 —— 属改动最小化边界。
- **记 tail（4 条）**：见台账第 6 段（围栏示例与 schema 脱节 / enum 机检 backlog / Purpose TBD / 批 6·7）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-12 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：1 轮（REJECT → 全部处置；未用满 2 轮上限）
- **验收轮次**：1 轮
