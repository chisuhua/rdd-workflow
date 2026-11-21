# 验收报告 — rewrite-spec-residue-batch7b2

- **change**：`openspec/changes/rewrite-spec-residue-batch7b2/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 **第七批（7b-2）** —— 判据核心仍为真（或需纠正）
  但机制形态已变 ⇒ **改写**判据正文 + Scenario。
- **范围**：**12 行 / 4 份**（`skeleton-planning` 3 · `spec-validation-gates` 4 ·
  `state-management` 2 · `rfc-rddf-project-yaml-config-i10` 3）。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT**（2 BLOCKER + 2 SHOULD_FIX + 1 NIT）；`mergeable: no` | **BLOCKER-1**（A 组）：保留的 L24-25 与分类机制矛盾 —— `_lib/discover_ship_changes.py:89` 的 `artifact_complete = proposal and design` + `:212-213` ⇒ **分类由工件完整性驱动、不看 status** ⇒ L25 为假、L24 机制上不被 status 保证、且与新 L11 两套坐标系 ⇒ **已同步改写 L24-25** + L11 尾巴缩成 `classified executable`。**BLOCKER-2**（B 组）：L169「MUST write `.plan-handoff.json`」未删 ⇒ 假 ⇒ 已删并与 `exit 0` 合并。**SF-1** `lib/`→`_lib/`；**SF-2** A 会跨 500 ⇒ 短措辞（实测 **458**，反短 1 字符）；**NIT** 常数以实测为准 ⇒ 已回填 4/2/1 + 307/161/42。 |

⚠️ critic 的**通过项**：C 组（删 event log 正确 —— `phase0_approval.sh` 全文 0 处 event 写入、
`store.set_status` 无 event log）、D 组（删除 vs 注记的取舍成立 —— 判据被 `builder_deps.py:42` 反证、
同主题正确判据已存在）、焦点 2（块数算术）、焦点 4（C 组自洽）。

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 12 行全部消失；全仓 4/2/1 | **pass** | `scan_specs` ⇒ **4 处 / 2 块 / 1 份**（只剩 `general/spec.md`） |
| AC-2 改写文本逐行等于设计表 | **pass** | 实施脚本用**内容断言**（`assert old in text` + `count == 1`）⇒ 5 + 10 + 3 处替换全部精确匹配；删除 `acceptance-3` 整块（8 行） |
| AC-3 含已豁免 319→307/170→161/44→42；豁免 303 不变 | **pass** | 实测 **307 / 161 / 42**；豁免 **303** |
| AC-4 诊断全 0 | **pass** | `stale`/`invalid`/`in_fence`/`fence_rejected` 全 **0** |
| AC-5 issue 多重集只减不增；不新增 very long；ERROR 11 | **pass** | `--json` 比对：**224 → 224**（新增 0 / 消失 0）；`very long` **62 → 62**；ERROR **11** |
| AC-6 台账覆盖 12 行 | **pass** | `.rddf/reviews/spec-residue-rewrite-batch7b2-2026-11-21.md`（改前/改后/依据 + 配套删除 + 实测数字） |
| AC-7 形态台账 | **pass** | 更新为「7b-2 完成 / **剩余 4 行 = general 专项**」 |
| AC-8 pytest + ruff | **pass** | 3 个测试文件 **67 passed**；`ruff` 全绿；census 幂等（`unset` **4** / 豁免 **303**）；常数同步 4/2/1 + 307/161/42 |
| AC-9 全量门 | **pass** | `./test.sh --full --regression` ⇒ **GATE_RC=0** + 未评估 0 + 新增失败 0 |

## 实施期发现

**1. critic 抓到 2 个 BLOCKER，都是「假判据会冻结进已采纳 spec」**：
- **A 组**：`_lib/discover_ship_changes.py:89` 的 `artifact_complete = proposal and design` ⇒
  分类**完全由工件完整性驱动**，status 只是旁路条件 ⇒ 保留的 L24-25（status 口径）**为假**
  ⇒ 且与新 L11（classification 口径）**两套坐标系**。
  ⇒ 这是我**只改命中行、不动配套行**的直接后果 —— 教训：**改写一个 Requirement 必须保证内部自洽**，
  不能只改「被扫描器标记的那一行」。
- **B 组**：Scenario 2 的 `THEN the gate MUST write .plan-handoff.json` 未删 ⇒ 假（CI 从不写）。
  ⇒ 同源问题：我只盯着「含 token 的行」，漏了**同一 Scenario 里不含 token 但同样为假的行**。

**2. 常数又估错了**：预测「含已豁免 307/170/44」，实测 **307/161/42**（块 −9、份 −2）。
⇒ 这是**连续第三次**（批 7a / 7b-1 / 本批）在常数上凭直觉估错。
⇒ 已固化为纪律：**常数一律以实跑 `scan_specs` 为准，不写预测值**。

**3. A 组改后反而短了 1 字符**（459 → 458）⇒ critic 的「会跨 500」担忧解除。

## 遗留清扫

- 本次范围内：无 TODO / 半截改写；12 行全部处置（3 处配套删除 + 1 个整块删除）。
- **未处置项**（范围外）：`general/spec.md` 的 4 行 / 2 块（**Phase 1 的最后一块**，需
  「改测试 → 改文档 → 改 spec」三方联动）· `rfc-rddf` 的其余 14 个 `acceptance-N`（delta 形态专项）·
  既有 62 条 `very long`（冻结）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**1 轮**（REJECT → 全部处置；0 剩余 BLOCKER ⇒ 按预算规则无需复审）
- **验收轮次**：1 轮
