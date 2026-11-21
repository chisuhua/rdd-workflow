# 围栏式豁免 —— 机制扩展台账（2026-11-21）

> 定位：change `extend-spec-residue-fence-annotation`。
> 本台账记录 **1 行 / 2 处** 的围栏式豁免处置 + 机制扩展的证据。
> `line` 列是**改前**行号。

## 1. 处置

| file | line | requirement_title | matched_token | disposition | code | evidence |
|---|---|---|---|---|---|---|
| `openspec/specs/dashboard-verification-status/spec.md` | 50 | Verification status schema SHALL be explicit and versioned | guide-ship | ANNOTATE（围栏位置） | `enum` | 该 token 是 `route` 字段的**真实取值集合**成员：`_lib/schemas/verifier_loop_schema.json` 的 `properties.route.enum` 今天仍含 `guide-ship` / `guide-plan`（存量 `.rddf/state/verifier/*.json` 必须可加载，`loop_state.py` save 时强制校验 enum）⇒ **不能改指** |
| 同上 | 50 | 同上 | guide-plan | 同上 | `enum` | 同上 |

**标注落点**：围栏 `45`（` ```json `）～ `57`（` ``` `）的**结束行之后**（新第 58 行）。

## 2. 为什么只能豁免、不能改指

| 选项 | 结论 | 理由 |
|---|---|---|
| 改指成 v4 名（`rdd-builder` 等） | ✗ | `route` 的取值是**状态机路由**，不是 stage 名。`guide-ship` / `guide-plan` 是存量 state 的合法值 ⇒ 改指会让存量 state 加载失败 |
| 删掉这两个值 | ✗ | 围栏是 `route` 字段的**取值集合示例**；删掉它们会让示例**漏列**合法值，与 schema 不一致 |
| 行内标注（插围栏内） | ✗ | 污染读者会照抄的示例 |
| 标注放围栏后（行位置） | ✗ | 前一行是 ` ``` `、无 token ⇒ 报 `stale allow` |
| **围栏位置标注** | ✓ | 唯一能让「标注在内容之后」与「不污染示例」同时成立的形态 |

## 3. 机制扩展的四个限制条件（可机判）

| # | 限制 | 实现 | 验证 |
|---|---|---|---|
| 1 | 局部性：必须紧跟围栏**结束行** | `_scan_fences` 的 `closed` 表（close_line → (open, close)） | `test_r4_fence_annotation_exempts_whole_block` |
| 2 | `code` 限 `enum` / `guard` | `FENCE_ALLOW_CODES`；其它 code 记 `fence_rejected` 且**不豁免** | `test_r4_fence_annotation_rejects_non_enum_guard_codes`（3 个参数化） |
| 3 | 可见性：进台账「围栏式豁免清单」 | `ScanResult.fence_allows` → `gen_spec_residue_census.py` 渲染 | 本台账 + census 的清单段（1 条） |
| 4 | 逐行 disposition | 人工台账（本文件）逐行记 | 本表 |

## 4. 顺带修的两处既有缺陷

| 缺陷 | 原行为 | 新行为 | 影响面 |
|---|---|---|---|
| 围栏**内**的标注被当成标注 | 豁免它前一行（也在围栏内） | 不生效 + 报 `in_fence` | 实测全仓 **0 处** ⇒ 零数字影响 |
| 未闭合围栏的正文被静默逐出扫描 | `_split_blocks` 只在围栏闭合时 flush `fence_buf` ⇒ EOF 前正文不进入 block ⇒ 内容不可见且无诊断 | 改由 `_scan_fences` 的 `in_fence` 驱动（单一真源）⇒ 未闭合围栏的正文**也**被扫描 | 实测全仓 **0 处**未闭合围栏 ⇒ 零回归 |

## 5. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 未豁免 | 44 处 / 36 块 / 16 份 | **42 处 / 35 块 / 15 份** |
| 含已豁免 | 325 / 176 / 46 | **325 / 176 / 46（不变）** |
| 已登记豁免 | 281 | **283**（+2 围栏式） |
| 全仓标注行 | 195 | **196** |
| `stale allow` / `invalid` / `ignored_inline` | 0 / 0 / 0 | **0 / 0 / 0** |
| `fence_rejected` / `in_fence` | —（新字段） | **0 / 0** |
| `fence_allows` | —（新字段） | **1** |
| `files_scanned` | 165 | **165** |
| `doctor --category v4-residue` | 36 WARNING | **35 WARNING** |
| `openspec validate --all` ERROR | 11 | **11** |

## 6. 记 tail（范围外，本 change 不改）

1. **`dashboard-verification-status` 的围栏示例与 schema 脱节** —— 缺 `rdd-builder` / `pending-agent`，
   且含 schema 枚举外的 `null`。围栏式标注只豁免旧名，**不修**这个脱节（那是文本修正专项）。
2. **围栏式 `enum` 的 schema 机检交叉校验**（critic 第 1 轮 SF-7 的可选项）—— 会让扫描器耦合
   `_lib/schemas/`，破坏「能在任何有 `openspec/specs` 的项目上独立跑」的设计。
   当前替代 = 本台账 + census 清单的 `tokens` 列供人工核对。
3. **该 spec 的 `## Purpose` 是 TBD 占位**（`validate --strict` 的既有 WARNING）—— 属
   「150/165 spec 的 Purpose TBD」这条既有 tail。
4. **批 6 / 批 7**（剩余 42 处 / 15 份）—— 见 `.rddf/reviews/spec-residue-remaining-forms-2026-11-21.md`。

## 7. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | REJECT（1 plan BLOCKER + 7 SF + 3 NITS） | 全部处置，详见 `proposal.md` 的「审查链」段与 `.rddf/reviews/extend-spec-residue-fence-annotation-verify.md` |

## 8. 回滚

- 扫描器 / 报告 / 台账生成器 / 测试 / 文档：`git revert <sha>`（tracked）。
- spec 标注：`openspec/` 是 **gitignored** ⇒ 回滚凭据是 T0 快照
  （`/tmp/opencode/specs-fa-before/dashboard-verification-status.md`）—— 或直接删除新增的第 58 行。
