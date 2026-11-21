# 验收报告 — fix-spec-very-long-verification-gap

- **change**：`openspec/changes/fix-spec-very-long-verification-gap/`
- **定位**：把「`very long` 增量」从「靠人工比对文本输出」变成**常驻、可机判**的守卫。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 4 SHOULD_FIX + 4 NITS）；`mergeable: yes` / `scope_exceeded: false` | **SF-1**（CI 行为表述与事实不符：`openspec/` 被 gitignore ⇒ CI 上守卫恒 skip ⇒ 执法点是**本地**）→ proposal / SKILL.md / 测试 docstring 三处已改。**SF-2**（归因漂移边界未文档化）→ 断言消息 + SKILL.md 已写明「A 红且增量疑似来自新注记形态 ⇒ 必须同步扩展剥除规则，**不得只改冻结值**」。**SF-3**（「4 类已穷举」不严格成立：实测第 5 类形态 `iterative-plan-fill:47`）→ 剥除规则改为「引用块序列」（实测只多剥这 1 行、baseline 与增量清单**完全不变** ⇒ 无误剥）+ 规则表如实记录 + 「规则表不是穷举承诺」。**SF-4**（临时项目不拷 `openspec/config.yaml`）→ docstring 记录该前提 + 漂移条件。**NIT-1**「25 条 / 14 spec」→ 实为 **13 spec**，已全量修正。**NIT-2**「2 次 CLI」→ 实为 **3 次**，已修正。**NIT-3**（两个近重复 helper）→ 合并为 `_very_long_for(specs_dir)`。**NIT-4**（total 先于 dict）→ 保留（diff 输出友好）。 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 守卫文件存在，含断言 A 与 B | **pass** | `tests/unit/test_spec_requirement_length.py`（约 300 行）：`test_very_long_issue_set_is_frozen` + `test_injected_very_long_increment_is_frozen` |
| AC-2 冻结清单 = A 62/38、B 25/13 | **pass** | `gen_frozen.py` 实测：当前 62 条 / 38 spec；无注入 37 条 / 28 spec；**注入造成 25 条 / 13 spec**。冻结字典键数实测：A=38 键/62 条、B=13 键/25 条 |
| AC-3 ⭐ 守卫实证有效 | **pass** | 实证 1（插 605 字符**普通英文句**，非注入形态）⇒ 断言 A **红**（`very long 总数变了：期望 62，实际 63`）、B 绿；实证 2（插 646 字符 `> **RETIRED ...` 引用块，注入形态）⇒ **A + B 双红**；实证 3（撤销）⇒ `2 passed` + **sha256 一致**（spec 逐字节回原状） |
| AC-4 skip-not-fail | **pass** | `shutil.which("openspec") is None` ⇒ `pytest.skip`；`SPECS_DIR.is_dir()` 为假 ⇒ `pytest.skip`（含 CI fresh checkout 场景） |
| AC-5 台账含归因 + 存量 + CI 说明 | **pass** | `.rddf/reviews/spec-very-long-baseline-2026-11-21.md`：§2 归因（37→62⇒25）、§3 来源 change 归并（6 个来源 + 逐条行号级证据）、§4 守卫设计 + CI 执法点 + 归因漂移边界、§5 规则表（含第 5 类形态）、§7 存量 37 条清单、§8 tail |
| AC-6 SKILL.md 补充 | **pass** | 「标注的已知副作用」段新增：`--json` 比对要求（含 jq 示例）+ 守卫名 + 冻结值 + **CI 执法点说明** + **归因漂移边界** |
| AC-7 critic 的 4 SF + 4 NIT 全部处置 | **pass** | 逐条见「审查链」表；`tasks.md` 的 T4.1–T4.8 逐项勾选 |
| AC-8 pytest + ruff + 无回归 | **pass** | `pytest tests/unit/test_spec_requirement_length.py -q` ⇒ **2 passed**；`ruff` ⇒ All checks passed；`pytest tests/unit/ -q` ⇒ **3511 passed / 3 skipped**（无回归） |
| AC-9 全量门 | **pass** | `./test.sh --full --regression` ⇒ **GATE_RC=0** + 未评估 0 + 新增失败 0（首跑因隔离门红 ⇒ 修 `mkdtemp` → `tmp_path` 后二次绿，见「实施期发现 6」） |

## 实施期发现

**1. 判据缺口的真实规模比预估大**：原先以为只有批 3/4/5 引入了几条，实测（还原法）——
**历史批次合计引入了 25 条** `very long`，全部无人验过。归因显示 **56%（14/25）来自两个
「整份 spec 退役」型专项 change**（`retire-spec-musts-pointing-at-retired-objects` 8 +
`fix-spec-residue-batch2-dead-intake` 6）—— 它们的注记是 200–600 字符的长引用块。
⚠️ **批 3 与批 5 各贡献 0 条**（我原先的猜测**不成立**）。

**2. 还原法第一版低估了 4 倍**：只识别 ①②③ 三类形态时测出「仅 +7」；补上第 4 类
（`> **RETIRED ...` 引用块）才是真实的 **+25**。⇒ **教训**：归因必须先穷举注入形态。

**3. 规则表不是「已穷举」的承诺**：critic 静态核验时实测出第 5 类形态
（`iterative-plan-fill/spec.md:45-47` 的 `> 保留原文与 Scenario 作为历史记录。` 被中间的标注行
**打断**了 `>` 连续段）⇒ 第一版规则漏剥它。⇒ 已把规则改为「引用块序列」（含中间夹标注行，
**空行中断**）⇒ 实测**只多剥这 1 行**、baseline 与增量清单**完全不变** ⇒ 无误剥。

**4. ⚠️ CI 上 spec 校验整体空转（既有缺口，非本 change 引入）**：本仓 `openspec/` 整树被
`.gitignore:45` 排除 ⇒ CI 的 fresh checkout 里没有 `openspec/specs/` ⇒ 本守卫在 CI 上恒 skip；
`.github/workflows/test.yml:113-127` 的「Spec validation gate」遍历 `openspec/changes/*/`
**同样是空集** ⇒ **CI 从未真正校验过任何 spec**。⇒ 已记入台账 tail（独立立项）。
⚠️ 本守卫的**执法点是本地批次执行时**，不是 CI —— 三处文档已如实标注。

**5. 冻结清单不会挡清理路**：将来清理存量 37 条 ⇒ 断言 A 红 ⇒ 走「显式更新冻结值」流程即可
（摩擦是设计意图）。

**6. ⚠️ 全量门首跑红 —— 测试隔离门抓到了 `tempfile.mkdtemp()`**：我最初用
`tempfile.mkdtemp(prefix="noinject-")` 造「无注入版」副本（**无自动清理**）⇒ 隔离门判
「cross-test pollution」⇒ `GATE_RC=1`。
⇒ 改用 pytest 的 `tmp_path` fixture（`_noinject_dir(root)`）⇒ 二次跑 `GATE_RC=0`。
⚠️ 教训：**新测试文件必须用 `tmp_path` fixture**，不能自己 `mkdtemp`
（隔离门在 `--gates` 的第一步就会拦下，比全量门早 4 分钟）。

## 遗留清扫

- 本次范围内：无 TODO / 半截实现 / 临时调试输出；两个 helper 已合并（NIT-3）。
- **未处置项**（范围外，已在 proposal 的 Out of Scope 与台账 tail 明确移交）：
  既有 25 条 `very long` 的消除 · 收窄未来注记形态（围栏化）· CI 上 `openspec/` 可用化 ·
  存量 37 条 · 批 3/4/5 的历史 verify 报告（审计痕迹不改写）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**1 轮**（APPROVE_WITH_CONDITIONS，0 BLOCKER ⇒ 无需复审）
- **验收轮次**：1 轮
