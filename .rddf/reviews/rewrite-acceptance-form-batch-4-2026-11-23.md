# rewrite-acceptance-form-batch-4 台账（2026-11-23）

## 范围

`acceptance-N` / `capability-N` 系列**第 4 批**（3 份 spec / **78 条 AC**）⇒
**36 条 Requirement（覆盖 51 条 AC，其中 15 组被合并）+ 27 条退役**（另有 3 个子句级退役）；
清单 promote 7 → **10** 份。

| spec | 改前 | 改后 |
|---|---|---|
| `rddf-layout-manifest` | 25（18 `acceptance-N` + 7 `capability-N`） | **12** |
| `fix-bats-per-file-timeout` | 22 | **11** |
| `fix-skill-post-install-discoverability` | 31 | **13** |

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（plan 5 BLOCKER + 2 SHOULD_FIX + 1 NIT）；`mergeable: no` / `scope_exceeded: true` | 5 BLOCKER **全部成立**，逐条修正 |
| 2 | **REJECT**（2 新 BLOCKER + 1 半闭合 + 1 SHOULD_FIX + 3 NIT）；`mergeable: no` / `scope_exceeded: false` | 2 BLOCKER **全部成立**；上轮 BLOCKER-4 半闭合已补 |

⇒ 预算 2 轮已用尽；本批**不再调第 3 轮 critic**（规则要求用户明确批准）。

### 第 1 轮 5 BLOCKER 处置

| # | finding | 处置 |
|---|---|---|
| **1** | AC-4「报告须打印采集 scope」被误判为无守卫 | `test_regression_gate_evaluation.bats:267` 的 `report: scope 声明（采集范围 + 仓内其它 .bats 不在本门范围）` **精确覆盖** ⇒ **移回改写**为 `regression-report-states-its-scope` |
| **2** | AC-2「collect 中途死 ⇒ report 失败且不打印 ✅」被误判为无守卫 | `report_regression.sh:68-74` + 两条守卫（`:278` summary 缺失 / `:298` infra error）**机制等价地覆盖** ⇒ **移回改写**为 `regression-report-fails-when-the-collector-dies` |
| **3** | `install-default-...` 的 Layer-0 子句无守卫 | 守卫只断言「不建 docs/」；且 `install.sh` **无 Layer-0 部署路径** ⇒ **退役该子句**，改名 `install-default-copies-no-documentation` |
| **4** | `rddf-init-suggests-...` 的 `ends with` 强于守卫 | 降级为 `includes`（守卫 `test_rddf_init_hint.bats:18` 只断言包含） |
| **5** | 处置计数算术不自洽 + proposal 无逐条台账 | 根因：**把「合并掉的 AC」当成「退役」** ⇒ 重建为逐条台账（现 **78 行**） |

### 第 2 轮处置

| # | finding | 处置 |
|---|---|---|
| **B-1（新）** | AC-23 的退役理由「`test_layer0_sentinel_order.bats` 文件不存在」**为假** —— 该文件**存在**（2026-09-21，3 用例），且其行为未被任何改写 Requirement 覆盖 ⇒ 按判据 ⑥ 应改写 | **改为改写** ⇒ 新增 R13 `layer-0-and-hub-sentinels-coexist-deterministically`（3 Scenario）。退役 28 → **27**、改写 35 → **36**、覆盖 AC 50 → **51** |
| **B-2（新）** | R1 的 reader/writer Scenario clause 1 是**全称量化**（manifest 里 `write_by` 不含 rdd 的有 **9** 个），守卫只钉 `reviews` 一个 ⇒ spec 强于守卫；且「read-only」措辞与 manifest 值域（`user`/`agent`/`git`/`external-tool`）不符 | **扩守卫**：新增 `tests/unit/test_rddf_layout.py::test_non_rdd_entries_name_their_actual_writer` —— 逐条钉住全部 9 个条目及其真实写入方；spec 措辞改为「every entry the rdd does not write SHALL name exactly the owner that writes it」⇒ **等强** |
| **B-3（上轮 #4 半闭合）** | Scenario 正文已降级为 `include`，**标题**仍是「ends with」 | 标题改为「the init output **includes** the setup hint」 |
| **SF-1** | 「R1 第 4 个 Scenario」—— 实际 3 个 | 更正为第 3 个 |
| **NIT-1** | 台账守卫名缺 `test_` 前缀 | 补齐（3 个 + 新增的第 4 个） |
| **NIT-2** | 「2 处 stage 名残留」与冻结常数的口径（「块 / 处」）不一致 | 改为「**2 块 / 6 处**」 |

## 7 条 `capability-N` 的处置（收口前自查发现）

`rddf-layout-manifest` 改前 live spec 是 **25 条**（18 `acceptance-N` + **7 `capability-N`**）——
后者是**同一形态退化族的另一形态**（自动生成名 + `WHEN the change is applied` 恒真 + `is enforced` 结尾），
前 4 轮按类计数**全漏**。

| AC | 处置 | 依据 |
|---|---|---|
| `capability-19` | 合并进 R5；**前半「`RDFF_LAYOUT` 是唯一声明点」子句级退役** | 前半无守卫 |
| `capability-20` | 合并进 R1（后半 ⇒ 新增 Scenario）；**前半「提交说明给出 `file:line`」子句级退役** | 前半过程性 |
| `capability-21` | 合并进 R1 / R8 / R11 | class 两分类 + ADR-0026 |
| `capability-22` | **整条退役** | 机制在（`layout_check.py:114` 一层 `iterdir`；只读 `git check-ignore -q`），但无「不修改文件 / 只扫一层」的断言 |
| `capability-23` | 合并进 R2；**后半「不承诺 import 路径稳定」子句级退役** | 后半无守卫 |
| `capability-24` | **整条退役** | 机制在（`layout_check.py:118` 非 `always` 直接跳过），但无测试 |
| `capability-25` | **整条退役** | 机制在（`layout_check.py:80` 的 `<path>/.probe`），但 `test_rddf_layout.py` 里的 `probe` 是**测试自己的**探针 |

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 3 份的 `acceptance-N` Requirement 名 | 71 | **0** |
| 3 份的 `capability-N` Requirement 名 | 7 | **0** |
| 3 份的恒真 WHEN | 78 | **0** |
| 3 份的 Requirement 数 | 78 | **36** |
| `openspec validate <3 份>` | 各 1 条 Purpose WARNING | **无 WARNING** |
| `openspec validate --all --json` issue | 214 | **211**（新增 **0**；消失 3 条 Purpose WARNING） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免） | 0/0/0 | **0/0/0** |
| 残留扫描器（含已豁免） | 303/159/41 | **297/157/40**（少 6/2/1 —— 本批移除 2 块 / 6 处 stage token；`diff -rq` 验证其余 162 份逐字节相同） |
| `pytest tests/unit/` | 3534 passed | ****3535 passed, 3 skipped**** |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 相关 bats | — | **72 例全绿**（12 个文件） |
| 机械对账（`/tmp/opencode/reconcile_b4.py`） | — | **组 C 表 36 行 vs 3 份 spec 36 条逐条一致；守卫名逐字存在** |
| `./test.sh --full --regression` | — | **GATE_RC=0**（未评估 0 · 已知失败 10 = 基线 · **新增失败 0** · `✅ ALL PASSED`） |
| 负向验证（新守卫的牙齿） | — | 注入 `config` 的 `write_by` 混入 `rdd` ⇒ **仅** `test_non_rdd_entries_name_their_actual_writer` 变红（其余 10 例仍绿）⇒ 实证 critic B-2：单例守卫抓不住归属漂移 |

### 本批改动的 tracked 文件

| 文件 | 改动 | 理由 |
|---|---|---|
| `tests/unit/spec_form_compliant.json` | `compliant` 7 → 10，`pending` 8 → 2 | 清单 promote |
| `tests/unit/test_v4_residue_check.py` | 冻结常量 303/159/41 → **297/157/40** + docstring 追加一条历史 | 该测试 docstring 明写「每个改动都必须在同一提交更新这些常数」；本批改写让 2 块 / 6 处 stage token **真的消失**（与 `rewrite-spec-residue-batch7b2` 的先例同构） |
| `tests/unit/test_rddf_layout.py` | **新增** `test_non_rdd_entries_name_their_actual_writer` | critic 第 2 轮 B-2：把 reader/writer 事实从**单例**断言扩成**逐条**断言（9 个条目），使 spec 断言与守卫等强 |

### 准确基线的重建

`openspec/` 整树 gitignored ⇒ 无 git diff 可比。3 份 spec 各由**唯一的**归档 change 以
`## ADDED Requirements` delta 创建 ⇒ 改前内容由 delta 精确重建；
重建脚本 `/tmp/opencode/rebuild_baseline_b4.py`，基线树 `/tmp/opencode/specs-baseline-b4/`（165 份）。

⚠️ **一处曾被我误判**：「`rddf-layout-manifest` 改前 live spec 是 18 条、归档 delta 是 25 条
⇒ 中间被裁过 7 条」—— **不成立**。改前 live spec 本就是 **25 条**（18 `acceptance-N` + 7 `capability-N`），
与 delta 一致 ⇒ **基线脚本正确，无需修正**；差异来自
`grep -c '^### Requirement: acceptance-'` **只数 `acceptance-N`** 的口径混淆。

## 回滚凭据

- 基线树：`/tmp/opencode/specs-baseline-b3/`（batch-3 结束时的全树，含本批 3 份的**改前**版本）
  与 `/tmp/opencode/specs-baseline-b4/`（由归档 delta 重建）
- 清单改前：`git show HEAD:tests/unit/spec_form_compliant.json`
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述基线树是唯一回滚凭据

## 实施期教训

1. **不能照抄归档 AC 的措辞 —— 它描述的是过去**（第 3 批学）。
2. **「spec 里没有」有两种成因，处置相反**（第 3 批学）。
3. **⑦ 按「形态类」计数，不要按「文件名模式」计数** —— `acceptance-N` 与 `capability-N` 是同一族的两种命名；
   只治理前者会整类漏掉后者（本批漏了 7 条，直到收口前自查才发现）。
4. **⑧ 判「无守卫」前必须先查文件名，不能只 grep 内容** —— 本批把 AC-23 判成「文件不存在」而它**确实存在**
   ⇒ 错误退役 ⇒ critic 第 2 轮 BLOCKER-1。这与第 1 轮的 BLOCKER-1/2 是**同一缺陷类**。
5. **⑨ spec 断言不得强于守卫**（全称量化 vs 单实例）—— 处置要么收窄 spec，要么**扩守卫**；
   本批选扩守卫（更符合 capability-20「逐条有代码依据」的原意）。
6. **改写若让 stage token 真的消失，必须同提交更新冻结常量** —— 否则 `pytest` 红 1 条（本批踩到）。
7. **计数口径自查要双轨**：「Requirement 总数」与「按类名计数」是两个数 ——
   `rddf-layout-manifest` 25 条里有 7 条是 `capability-N` ⇒ 只看 `acceptance-N` 会漏。

## 进 tail（本批不处置）

1. **剩余 2 份 `acceptance-N` spec**（`env-bootstrap` 44 · `objective-tracking` 33 = **77 条**）
   ⇒ 下一批单批做完（按基线 ≈3–4 h）。
2. **`openspec/` 是否取消 gitignore** —— 用户已定「暂不决定，继续现状」⇒ 内容级守卫仍只在本地生效。
3. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）。
4. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）。
6. **形态清单应从「按文件」升级为「按形态类」**（本批教训 ⑦ 的直接产物）——
   `spec_form_compliant.json` 现在只覆盖 `acceptance-N` 一类，建议加 `capability-N` / 恒真 WHEN 类，
   并补一条「**全仓**恒真 WHEN = 0」的守卫（现只剩 77 条，且 100% 集中在剩余 2 份 spec 里）。
