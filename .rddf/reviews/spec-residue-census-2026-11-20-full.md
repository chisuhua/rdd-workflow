# spec 残留普查台账（机器生成）

> 生成器：`skills/rdd-doctor/scripts/gen_spec_residue_census.py` — **不要手编辑本文件**。
> 台账 = **清理待办清单**（`disposition=unset` 的行归零 = Phase 1 的完成判据）+ 可复算基线 + 证据。
> 签批记录的权威落点**不是这里** —— 见下方「既有签批」段。

## 口径（冻结常量）

扫描根 `openspec/specs/*/spec.md`（恰为一层，非递归；**不扫** `openspec/changes/**`）。
normative 段 = `### Requirement:` 标题+正文 / `#### Scenario:` 标题+正文 / 正文内 fenced code block；
**不含** `## Purpose` 等散文段。命中按**块**归类。

词边界：`(?<![\w-])(guide-arch|guide-design|guide-plan|guide-ship|guide-spec|ac-verifier)(?![\w-])`
（token 后不得再跟 `-`，否则 `guide-plan-quick-finish` 这类**提案名**会被前缀命中）。

| `code_block_in` × `title_in` | 命中处数 | 命中块数 | 命中 spec 份数 |
|---|---|---|---|
| `True` × `True` ← 选定（冻结） | 307 | 161 | 42 |
| `True` × `False` | 287 | 160 | 42 |
| `False` × `True` | 305 | 160 | 41 |
| `False` × `False` | 285 | 159 | 41 |

## 基线（选定口径）

- 扫描 spec 文件：**165** 份
- 命中实例：**307** 处（其中未被豁免 **4** 处）
- 命中块：**161** 块
- 命中 spec：**42** 份
- `stale allow`（过期豁免）：**0** 处

## 既有签批（不由本台账合并）

| 批次 | 台账 | 覆盖 spec |
|---|---|---|
| 第一批（13 份 / 34 处） | `.rddf/reviews/spec-residue-census-2026-11-20.md` | 见该文件 |
| 第二批（5 份 / 37 处） | `.rddf/reviews/spec-residue-census-2026-11-20-batch2.md` | 见该文件 |

这 18 份已**全部处置完毕**（0 个命中行）—— 逐行判定与标注见
`.rddf/reviews/spec-residue-align-18-2026-11-20.md`（change `align-spec-residue-prior-18`）。

## 残留清单

| file | line | requirement_title | matched_token | category | disposition | owner | signoff | date |
|---|---|---|---|---|---|---|---|---|
| openspec/specs/general/spec.md | 127 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 145 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 146 | general-docs-match-code | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 147 | general-docs-match-code | guide-spec | unclassified | unset |  |  |  |

## 围栏式豁免清单

> 紧跟围栏**结束行**的 `allow` 标注会豁免该围栏内**全部**行 —— 它与被豁免的文本
> 物理分离（中间隔着围栏），且本台账不列已豁免行 ⇒ 若不留这份清单，
> 它就只存在于一个没人读的注释里。`tokens` 列供人工核对「code 声明是否成立」。

| file | 围栏行范围 | code | tokens |
|---|---|---|---|
| `openspec/specs/dashboard-verification-status/spec.md` | 45–57 | `enum` | guide-plan, guide-ship |

## 合计

- `disposition=unset`：**4** 条命中记录（Phase 1 的待办量）
- 已登记豁免（标注）：**303** 处
- 命中 token 分布：
  - `guide-arch`: 2
  - `guide-plan`: 1
  - `guide-spec`: 1
