# spec 残留 —— 剩余部分的形态抽样台账（2026-11-21，批 6 后）

> **定位**：`fix-spec-residue-guard` 的 Phase 1 批次地图。
> 本台账是**逐行形态判定 + 实现事实证据**，不是机器普查台账（后者见 `spec-residue-census-2026-11-20-full.md`）。
> `line` 列是**截至批 7a 后的当前行号**（后续批次插入会漂移 ⇒ 动手前用 scanner 重取）。

## 进度

| 批次 | 行 | 形态 | 处置 | 状态 |
|---|---|---|---|---|
| 批 5 | 13 | A / B / D | 纯标注（`history` 9 / `guard` 4） | ✅ 已完成（`1e914476`） |
| 围栏式机制 | 1 | C | 新增围栏位置豁免 + 用它标掉 | ✅ 已完成（`172ecd91`） |
| 批 6 | 6 + 1 配套 | E / F | 文本改指 | ✅ 已完成 |
| 批 7a | 9 块 / 11 行 | G | `RETIRED` 注记 + `allow=history` 标注 | ✅ 已完成 |
| 批 7b-1 | 9 行 / 6 份 | G | 围栏式 `RETIRED` 注记 + `allow=history`（**very long 零增量**） | ✅ 已完成 |
| 批 7b-2 | 12 行 / 4 份 | G + 移交 | **rewrite**（重写判据正文 + Scenario + 删被反证的 `acceptance-3`） | ✅ 已完成 |
| 专项 | 4 | — | 测试锁定 + 断言漂移 | ⏳ 待办 |

**当前剩余**：4 处 / 4 行 / 1 份（**只剩 `general/spec.md` 的专项**）。

## 批 7b-2 —— 12 行 / 4 份（rewrite）—— ✅ 已完成（2026-11-21）

> ✅ **本表已逐行全仓复核（2026-11-21）** —— 复核前的分类（「按句子形态」猜测）**几乎全错**：原判 `annotate` 14 / 改指 6 / rewrite 1，实际是 **rewrite 12 / 注记 9 / 改指 0**。
>
> 复核用到的纪律（批 7a 的三轮 critic 教训）：「存在 / 不存在 / 无调用方」类断言必须**全仓** grep（含 `.github/workflows/*.yml`、`.yaml`、`.md`），且必须指到**行为载体**的 `file:line`；「函数存在」≠「机制活着」⇒ 还要查**调用方**。
>
> **最关键的一条**：`skeleton-planning` 的 `planned → fill` 机制在 v4 **没有活实现** —— `list_ready_for_fill`（`_lib/iteration/store.py:446`）只有定义 + 导出 + 单测，**无生产调用方**；`skills/rdd-builder/scripts/phase1_plan.sh` 对 `planned`/`skeleton` **零命中**；`wave_scheduler.py`（把 planned 归入 fill 波）同样**无活调用方**（批次 2 的 critic 已查过同一件事）。⇒ 原先「planned 的 fill 仍活 ⇒ 可改指」的判断不成立。

> **为什么不能改指**：改指会让「已死的判据」看起来正常，比残留更危险 —— 读者会照着实现一个不存在的流程。（批 6 的 `rfc-rddf` 三行就是实例：我原判「机械改指」，critic 查出落点证据是事实错误。）

| spec | 行 | 处置 | token | 证据 |
|---|---|---|---|---|

合计 0 行（`annotate` 0 / `rewrite` 0 / 需改指 0）

## 批 6 的两次收缩（记录在案）

台账初判 **20 行**「E/F 机械改指」⇒ 逐行实现核实后 **9 行** ⇒ critic 第 1 轮 BLOCKER 后 **6 行**。

| 收缩 | 移出 | 理由 |
|---|---|---|
| 一（20→9） | 11 行 | 机制已变 / 已死（见上表证据列） |
| 二（9→6） | `rfc-rddf` 3 行 | 我原声明的落点「轻量模式判定在 `ship_execution_mode.sh:97`」**是事实错误** —— 那是 WAVE 串并行判定，注释明写「it says nothing about the execution mode」 |

### 两种注记形态并存（批 7a 确立首选）

| 形态 | NOTE 含退役名？ | 标注位置 | 采用者 |
|---|---|---|---|
| 批 5 先例（`complete-project-yaml-config-gaps:203`） | 是（`guide-ship/SKILL.md`） | NOTE **之后**（NOTE 自我豁免） | 历史形态 |
| **批 7a（本批）** | **否**（用「v3 design 阶段」等描述） | **命中行之后**（allow 落在被豁免行正下方） | ✅ **首选** |

批 7a 形态更优：allow 落在被豁免的命中行正下方，NOTE 不含旧名因而不需要「自我介绍后再自我豁免」的绕圈；且**追溯性不丢** —— 零原文改动保留了含旧名的命中行原文，读者 grep 旧名仍命中原文。

### ✅ 既有判据缺口 —— 已修（change `fix-spec-very-long-verification-gap`）

`openspec validate` 的**文本输出不显示** `requirements[N]` 这类 issue —— 只有 `--json` 才报。⇒ 批 3/4/5 的「validate 逐字节相同」判据**没有覆盖** `very long` 增量（批 5 在 `skills/rdd-doctor/SKILL.md` 记录过这个副作用，但验证口径漏了它）。

**实测归因**（还原法，口径交给 openspec 自己）：注入前 **37** → 注入后 **62** ⇒ **注入造成 25 条**。来源：`retire-spec-musts-pointing-at-retired-objects` 8 / `fix-spec-residue-batch2-dead-intake` 6 / 批 7a 4 / 批 4 3 / align-18 2 / `retire-execute-skill` 2（**批 3 与批 5 各 0 条** —— 原先的猜测不成立）。

**修复**：常驻守卫 `tests/unit/test_spec_requirement_length.py` 冻结了 `very long` 清单（62 条 / 38 spec）与「注入造成的增量」（25 条 / 14 spec）⇒ 后续任何批次让 Requirement 跨过 500 ⇒ 守卫红 ⇒ 必须显式更新冻结值并说明「新增的 very long 是否可接受」。台账：`.rddf/reviews/spec-very-long-baseline-2026-11-21.md`。

⚠️ **对批 7b 的直接启示**：代价主要来自「整份 spec 退役」型的**长引用块注记**（200–600 字符，落在 Requirement 正文里）⇒ 批 7b 的 14 行 `annotate` 若沿用批 7a 的引用块形态（200–430 字符）**会新增 very long** ⇒ 守卫会红 ⇒ 必须显式决策。**围栏形态**（``` 包裹）不计入 Requirement 正文（`extractRequirementBody` 跳过 fence 内）⇒ 不产生增量。

**教训**：改指的前提是「新落点在 v4 真实存在且行为等价」。仅凭「路径存在」或「句子形态像改指」不构成理由 —— 必须指到**行为载体**的 `file:line`。

## 专项（4 行，不可动）

| spec | 行 | 理由 |
|---|---|---|
| `general` | 127 | **断言已漂移（今天为假）**：`general/spec.md:127-128` 断言 ADR-0001 的 Decision 「spec-side 5 phases (setup/adr-create/architecture/roadmap-define/arch-done per `guide-arch`) + ship-side 7 numbered subphases」；实测 ADR-0001 实际写的是 `guide-spec.md` 的 **5 phase (setup/roadmap/propose/deps/spec-done)** 与 ship 端 **「5 阶段 + 1 退出」** ⇒ 两处 phase 名单都对不上 ⇒ 这是**失效断言**，**不能**按 `history` 豁免（豁免一条假断言 = 给假通过发通行证）⇒ 需文本处置或批 7 的 RETIRED 注记形态 |
| `general` | 145 | **三方锁定**：`tests/unit/test_doc_contracts.py:67-68` 断言 `"guide-arch" in spec` 且 `"guide-plan" in spec`（子串锁）⇒ 改指就红测；且它描述的 `docs/improvement-suggestions-format.md` **本身仍是 v3 名**（实测 `:9` 仍写 `guide-design` / `guide-plan`）⇒ 需专项（改测试 → 改文档 → 改 spec 三方联动） |
| `general` | 146 | 同上 |
| `general` | 147 | 同上（`:147` 的 `guide-spec` 是**阴性**断言「SHALL NOT list」，不受 `:46-59` 的 active-reference 正则约束 ⇒ 不构成额外锁定） |

## 记 tail（范围外）

1. **`general/spec.md`（4 行）** —— `:145-146` 被 `tests/unit/test_doc_contracts.py:67-68` 的子串断言锁定；`:127-128` 对 ADR-0001 的断言**已漂移**（实测 ADR-0001 写的是 `guide-spec` 的 5 phase + ship 端「5 阶段 + 1 退出」）⇒ 需「改测试 → 改文档 → 改 spec」三方联动专项。
2. **delta 形态垃圾结构** —— 9 份 spec 首行是 `## ADDED Requirements`（未合并的 change delta 被误归档为 capability spec）；`post-flow-analysis` / `rfc-rddf-*` 的 Requirement 名是自动生成的（`fix-adr-0027-cli-optin-gate` / `acceptance-3`）⇒ 需专项重写，不是残留名问题。
3. **`dashboard-verification-status` 围栏示例与 schema 脱节** —— 缺 `rdd-builder` / `pending-agent`，含 enum 外的 `null` ⇒ 文本修正专项（围栏式标注只豁免旧名，不修脱节）。
4. **围栏式 `enum` 的 schema 机检交叉校验** —— backlog（会让扫描器耦合 `_lib/schemas/`，破坏「能在任何有 `openspec/specs` 的项目上独立跑」的设计）。
5. **`spec_residue_scan.py:488` 的 `hit_lines` 是死变量** —— 改前就存在（只 `add` 从不读），本次未删（改动最小化边界）。

