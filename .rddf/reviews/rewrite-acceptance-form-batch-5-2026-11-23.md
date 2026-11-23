# rewrite-acceptance-form-batch-5 台账（2026-11-23）— `acceptance-N` 系列**最后一批**

## 范围

**12 份 spec 的形态退化系列收口**。本批覆盖最后 **2 份 / 77 条 AC** ⇒
**24 条 Requirement（覆盖 35 条 AC，其中 16 组被合并）+ 42 条退役**。

| spec | 改前 | 改后 |
|---|---|---|
| `env-bootstrap` | 44 | **12** |
| `objective-tracking` | 33 | **12** |

⇒ 处置后：**全仓 `acceptance-N` = 0 · `capability-N` = 0 · 恒真 WHEN = 0**。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **APPROVE_WITH_CONDITIONS**（plan 0 BLOCKER + 5 SHOULD_FIX + 2 NIT）；`mergeable: yes` / `scope_exceeded: true` | 4 条 SHOULD_FIX + 2 NIT **全部采纳并实施**；第 5 条（AC-10 持久化守卫）属本 change 声明的范围外 ⇒ 记 backlog |

### 第 1 轮处置

| # | finding | 处置 |
|---|---|---|
| **SF-1** | R5 的 Scenario 2「SHALL **NOT** fail with an "not initialized" error」是**否定断言**；守卫只断言 exit 3 + 输出含 `not a rdd-workflow project`（**不**断言该字符串缺席）⇒ spec 强于守卫 | **删除该 Scenario**（Scenario 1 已覆盖守卫的全部断言）⇒ R5 降为 1 个 Scenario，组 C 表同步 |
| **SF-2** | proposal 的 AC-2 写「**19** 条」与组 C 表的 24 条、tasks.md 的 T4.2 矛盾 | **改为 24 条** |
| **SF-3** | 台账两处「全仓 grep 0 处 / 无命中」**与事实不符** —— `fix-decisions` 命中 **8 个文件**（含 `skills/rdd-env-bootstrap/SKILL.md` 与 `scripts/guided_fix.py`）；`skills/rdd-planner/SKILL.md:144` 字面就是「### 何时建 feature vs objective」 | **理由措辞更正**为「机制/引用**存在**，但 `tests/` 无守卫」—— 退役**决定**不变（确实无测试断言），但理由必须**可核实** |
| **SF-4** | 台账 env AC-16 的去向写「并入 R6 正文」，而 R6 正文只列 git / 语言 / AI 配置三项 | **去向更正**为「子句退役（机制在、tests/ 无守卫），R6 收窄为有守卫的三项检测」 |
| **SF-5** | AC-10 要成为 durable 不变量，需在 `test_spec_requirement_form.py` 加一条全仓扫描（该文件现在只扫**有界集合** `ACCEPTANCE_FORM_SPECS` 12 份 ⇒ 第 13 份退化 spec 不咬） | **属本 change 声明的范围外**（形态清单升级为「按形态类」）⇒ **记 backlog** |
| **NIT-1** | R1「SHALL **state** what the skill owns」偏内容断言（守卫只 grep 标签**存在**） | 措辞收紧为「SHALL **declare**」 |
| **NIT-2** | 台账 env AC-6 应注明 `owner_opencode_session_id` 归属 ADR-0017 | **已注明** |

### 第 1 轮 focus 结论（要点）

- **focus 1（42 条退役）**：点名的 10 组**全部站得住** —— AC-18/20/21/22/24/26/33 在两个守卫文件
  及全仓 grep 均无命中；AC-7/9 经核实 `test_roadmap_skill.bats:22-33` **只数子命令存在性**；
  AC-10 经核实**无任何测试读** `objective_schema.json`（且其 `version` 实为 `{"const": "v1"}`，
  原 AC 措辞本身就不准）；AC-13 确认是实现细节（`_lib/cli/__main__.py:221`），行为由 R5 覆盖。
- **focus 2（合并子句）**：AC-10 的守卫无效判定**属实**（`test_env_bootstrap.bats:116` 的注释自认
  「Clean project has 0 findings → Phase 4 is empty regardless of mode」）；AC-25 白名单经核实
  `guided_fix.py` 的 run 路径**不对分类做限制** ⇒ 保留的子句与守卫等强。
- **focus 3（措辞等强）**：五处里四处等强（git 单向断言、malformed skip、PoC doctor、R4 的
  「carry 四 phase」由 `build_report_produces_all_required_fields` 用**空 phase_4** 输入断言全 key）；
  一处偏强 = SF-1。
- **focus 4（AC-10）**：可机判、当前为真、**新增退化 spec 是 true positive**（不会假红）；
  durable 化的缺口 = SF-5（范围外 backlog）。

## 77 条 AC 的分流

逐条台账见 `openspec/changes/rewrite-acceptance-form-batch-5/proposal.md` 的「组 A'」段（**77 行**，
每行给出处置与去向/理由）。

### 退役 42 条的分类统计（**从台账实际重算**，非手填）

| 类别 | 条数 |
|---|---|
| **无守卫**（机制在但没有可机判的断言） | 17 |
| **元断言**（「≥N cases 全绿」/「全量门通过」/「单元测试覆盖」） | 10 |
| **否定断言**（「❌ 不实现 X」） | 1 |
| **相对断言**（「零变化」/「不修改」/「结论不变」） | 3 |
| **过程性 / 状态快照**（新建 ADR / 改文档 / 某文件的当前内容 / 项目进度） | 10 |
| **实现细节**（注册到 `_NO_STATE_CHECK` 一类） | 1 |
| **合计退役**（整条级） | **42** |
| **合并**（内容进了对应 Requirement，不是退役） | **16** |

⇒ 退役**不丢原文** —— 原文在 `openspec/changes/archive/2026-09-21-add-env-bootstrap-skill` /
`2026-09-22-add-objective-tracking` 的 `proposal.md` 的 `## Acceptance` 段。

### 24 条改写契约（组 C 表）

| spec | 条数 | 守卫文件 |
|---|---|---|
| `env-bootstrap` | 12 | `tests/integration/test_env_bootstrap.bats`（10 例）· `tests/unit/test_env_bootstrap_report.py`（13 例） |
| `objective-tracking` | 12 | `tests/unit/test_objective.py`（31 例）· `tests/unit/test_objective_parser.py`（9 例）· `tests/unit/test_roadmap_state_objectives_index.py`（6 例）· `tests/integration/test_objective_lifecycle.bats`（5 例）· `test_objective_structure.bats`（5 例）· `test_rdd_planner_objective.bats`（8 例） |

## 清单 promote

`tests/unit/spec_form_compliant.json`：`compliant` 10 → **12** 份 · `pending` 2 → **0** 份
⇒ **`class_total` 12 份全部整改完毕**。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 2 份的 `acceptance-N` Requirement 名 | 77 | **0** |
| 2 份的 `capability-N` Requirement 名 | 0 | **0** |
| 2 份的恒真 WHEN | 77 | **0** |
| 2 份的 Requirement 数 | 77 | **24** |
| `openspec validate <2 份>` | 各 1 条 Purpose WARNING | **无 WARNING** |
| `openspec validate --all --json` issue | 211 | **209**（新增 **0**；消失 2 条 Purpose WARNING） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免） | 0/0/0 | **0/0/0** |
| 残留扫描器（含已豁免） | 297/157/40 | **297/157/40**（**完全不变** —— 本批未触碰任何 stage token） |
| `pytest tests/unit/` | 3534 passed | **3535 passed / 3 skipped** |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 相关 bats | — | **28 例全绿**（4 个文件） |
| 机械对账（`/tmp/opencode/reconcile.py`） | — | **组 C 表 24 行 vs 2 份 spec 24 条逐条一致（含 Scenario 数）；守卫名逐字存在** |
| 负向验证（清单 promote 被守卫锁住） | — | 把 `env-bootstrap` 退回 `pending` ⇒ `test_pending_specs_still_declare_the_acceptance_form` **变红** ⇒ 还原后 5 passed |
| `./test.sh --full --regression` | — | **GATE_RC=0**（未评估 0 · 已知失败 10 = 基线 · **新增失败 0** · `✅ ALL PASSED`） |

### 准确基线

本批两份的**归档 delta 条数 == 改前 live spec 条数**（44 / 33）⇒ 基线由 delta 直接重建，
**无需**像第 3/4 批那样再应用一次裁剪（第 3/4 批都曾在这里踩坑）。
重建脚本 `/tmp/opencode/rebuild_baseline_b5.py`，基线树 `/tmp/opencode/specs-baseline-b5/`（165 份）。

## 回滚凭据

- 基线树：`/tmp/opencode/specs-baseline-b4/`（batch-4 结束时的全树，含本批 2 份的**改前**版本）
  与 `/tmp/opencode/specs-baseline-b5/`（由归档 delta 重建）
- 清单改前：`git show HEAD:tests/unit/spec_form_compliant.json`
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述基线树是唯一回滚凭据

## 实施期教训

1. **⑦ 按「形态类」计数，不要按「文件名模式」计数**（第 4 批学）。
2. **⑧ 判「无守卫」前必须先查文件名，不能只 grep 内容**（第 4 批学）。
3. **⑨ spec 断言不得强于守卫**（全称量化 vs 单实例；否定断言尤其危险）—— 第 4 批 B-2 + 本批 SF-1
   （「SHALL **NOT** fail with an X」需要守卫断言 X **缺席**，而守卫只断言它**在场**）。
4. **⑩ 退役理由必须可核实 —— 「全仓 grep 0 处」这类断言要写成「tests/ 无守卫（机制/引用存在）」**。
   本批 critic 抓到我在两条台账里写「全仓 grep `fix-decisions` 0 处」/「全仓 grep 无命中」，
   实际前者命中 **8 个文件**、后者 `SKILL.md:144` 字面就写着那句话 ⇒ **退役决定成立，但理由是错的**。
   ⇒ 写「无守卫」时要说清是「**机制不存在**」还是「**机制存在但 tests/ 没断言**」——
   后者更常见，且措辞不能夸张。
5. **元断言的退役也要逐条核** —— 本批 10 条「≥N cases 全绿 / 全量门通过 / 单元测试覆盖」，
   其中 2 条还附带了「文件不存在」（`tests/unit/test_env_bootstrap.py` · `tests/unit/test_objective_schema.py`）
   ⇒ 与第 4 批 B-1 同一个陷阱：**先查文件名**。

## 收口声明

**`acceptance-N` / `capability-N` 形态系列 12/12 全部整改完毕**：
全仓 165 份 spec / **747** 条 Requirement（本批净减 53：800 − 77 + 24） 中，`acceptance-N` **0** 条、`capability-N` **0** 条、
恒真 WHEN **0** 条。

## 进 tail（本批不处置）

1. **形态清单升级为「按形态类」**（本批教训 ⑦⑩ 的直接产物）——
   `tests/unit/spec_form_compliant.json` 现在只按**文件**登记 `acceptance-N` 一类 ⇒
   ① 建议加 `capability-N` / 恒真 WHEN 类；② **建议加一条全仓扫描守卫**
   （critic SF-5：`test_spec_requirement_form.py` 只扫**有界集合** `ACCEPTANCE_FORM_SPECS` 12 份
   ⇒ 第 13 份退化 spec 不咬；加一条全仓扫描约 10 行，与现有 `requires_specs_dir` 同 skip 语义）。
2. **`openspec/` 是否取消 gitignore** —— 用户已定「暂不决定，继续现状」⇒ 内容级守卫仍只在本地生效。
3. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）。
4. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）。
