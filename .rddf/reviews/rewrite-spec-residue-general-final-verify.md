# 验收报告 — rewrite-spec-residue-general-final

- **change**：`openspec/changes/rewrite-spec-residue-general-final/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 **收尾批** —— `general/spec.md` 的残留处置。
- **范围**：命中 **4 处 / 2 块** + 关联修正 **2 处** + 文档 1 份（16 处）+ 测试 1 个文件（1 换 3 新）+ 常数同步。
- **验收时间**：2026-11-22
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**；`mergeable: yes` / `scope_exceeded: false`；**0 BLOCKER** + 3 SHOULD_FIX + NITS | **SHOULD_FIX-1**（E 组 L178「used by Phase 0」不可证 ⇒ 改维护权表述）**已改**；**SHOULD_FIX-2**（E 组 L159 前提与新清单矛盾 ⇒ 放宽）**已改**（E 组 14 → 16 处）；**SHOULD_FIX-3**（B 组判据单向性）**记 tail**；**NIT**（E165 依据 = `.planner-handoff.json`；E102 依据补 `collect_pending`）**已改依据**；**范围外**（`docs/improvement-approved-format.md:3`）**记 tail**。 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 4 处命中全消失；全仓未豁免 0/0/0 | **pass** | `scan_specs` ⇒ 未豁免 **0 处 / 0 块 / 0 份**（`files_scanned = 165`） |
| AC-2 改写文本逐条等于设计表（A/B/C/D + E 16 处 + F 4 处） | **pass** | 实施脚本用**内容断言**（`count(old) == 1`）⇒ spec 4 处 + doc 16 处 + test 1 处全部精确匹配，无静默跳过 |
| AC-3 含已豁免下降；已登记豁免不变 | **pass** | 含已豁免 **307 → 303 处 / 161 → 159 块 / 42 → 41 份**；已登记豁免 **303（不变）** |
| AC-4 四项诊断全 0 | **pass** | `stale` / `invalid` / `in_fence` / `fence_rejected` 全 **0** |
| AC-5 issue 多重集只减不增；very long 不新增；ERROR 不增 | **pass** | `--json` 比对：**224 → 224**（新增 0 / 消失 0）；`very long` **62 → 62**；ERROR **11 → 11** |
| AC-6 台账覆盖 A–F 六组 | **pass** | `.rddf/reviews/spec-residue-rewrite-general-final-2026-11-22.md`（逐行改前/改后/依据 + 实测数字 + 审查链 + tail） |
| AC-7 常数同步为实跑值 | **pass** | `tests/unit/test_v4_residue_check.py`：未豁免 **0/0/0**；含已豁免 **303/159/41** |
| AC-8 pytest + ruff | **pass** | 4 个测试文件 **83 passed**；`ruff` 全绿；census **幂等**（`disposition=unset` **0** / 豁免 **303**）；doctor `v4-residue` **0 WARNING** |
| AC-9 全量门 | **pass** | `./test.sh --full --regression` ⇒ **GATE_RC=0** + 未评估 0 + 新增失败 0（重跑一次，见下「实施期发现 5」） |

## 实施期发现

**1. critic 抓到一个我漏掉的事实**：`rdd-builder` **不碰** `improvement-suggestions.md`
（`skills/rdd-builder/` 全目录 grep = **0 命中**）—— 它消费的是**被链接的**草稿
`.rddf/improvements/<name>.md`。⇒ 文档 Consumers 段原前提「All skills that **touch
`improvement-suggestions.md`**」与新清单**自相矛盾**（按前提它不该进表）⇒ 前提放宽为
「touch 索引 **or** 被链接的草稿」。
⇒ 教训：**判据里点名一个组件时，必须分清「它消费的是索引」还是「它消费的是索引指向的东西」**。

**2. 另一条「存在 ≠ 活着」的实例**：`populate-state.json` 的读写函数
（`_lib/populate_lib.py:953,987`）**生产代码零调用方** ⇒ 我原拟的「used by `rdd-planner` Phase 0」
不可证 ⇒ 改写为**维护权**表述（`owned by` per ADR-0048）。
⇒ 与批 7a/7b-1 的教训同源：**函数存在 ≠ 机制活着**。

**3. 改指判据三件套齐备**：`skills/propose.md` 不存在 ⇒ 真实 4 位 ADR 正则在
`skills/propose/scripts/propose_quality_check.py:53` `_ADR_PATTERN = re.compile(r"ADR-\d{4}")`
⇒ 新落点存在 ✓ + 行为等价 ✓ + 行号级证据 ✓。

**5. 全量门首跑出现 1 个「新增失败」，复核为网络 flake**：失败用例是
`tests/integration/test_cross_repo_impact_detection.bats:168`
（`04_multi_contract_match_returns_stakeholders_union`）—— 它通过 `gh api -X PUT` 把
contract **推到真实 GitHub Hub 仓库**再回读（推送失败被 `|| true` 吞掉 ⇒ 仓库里 contract
不足 2 份 ⇒ `.matches | length` 断言失败）。
- 单独跑该文件：**4/4 pass**；
- 该用例的输入（`skills/add-improve/scripts/detect_cross_repo_impact.py` + Hub 仓库）
  **与本次改动无任何交集**（本次只动 `general/spec.md` / 1 份 docs / 1 个 unit 测试 / 常数）；
- 全量门**重跑一次 ⇒ GATE_RC=0 / 新增失败 0 / 未评估 0**。
⇒ 判定为**环境（网络）信号**，非实现回归。已在台账记录，不做代码改动。

**4. 常数再次以实跑为准**：本批**没有预测**任何数字，全部在实施后实跑 `scan_specs` 回填
（307/161/42 → 303/159/41）。

## 遗留清扫

- 本次范围内：无 TODO / 半截实现；4 处命中全部处置；E 组 16 处全部落盘；
  测试守卫 1 换 3 新，无被 skip 的新测试、无临时日志、无未替换的 mock。
- **未处置项（范围外，已进形态台账 tail）**：
  `general/spec.md` `general-docs-match-code` 的其余假断言（`:102-103` / `:110-114` / `:118-121` /
  `:165-173` / `:156-163`）· `docs/improvement-approved-format.md:3` 旧机制描述 ·
  B 组判据单向性硬化（critic SHOULD_FIX-3）· `rfc-rddf` 其余 14 个 `acceptance-N` ·
  既有 62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**1 轮**（APPROVE_WITH_CONDITIONS，0 BLOCKER ⇒ 按预算规则无需复审）
- **验收轮次**：1 轮
