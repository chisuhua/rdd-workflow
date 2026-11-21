# spec `very long` 基线台账 —— 判据缺口修复（2026-11-21）

> 定位：change `fix-spec-very-long-verification-gap`。
> 把「`very long` 增量」从「靠人工比对文本输出」变成**常驻、可机判**的守卫。

## 1. 判据缺口（发现）

批 7a 收尾时实测发现：**`openspec validate` 的文本输出不显示 `requirements[N]` 这类 issue** ——
只有 `--json` 才报。

```
$ openspec validate roadmap-proposal-guidance          # 文本输出：只有 Purpose 占位警告
$ openspec validate roadmap-proposal-guidance --json   # JSON：多了 requirements[3] / [4] 的 very long
```

⇒ 批 3 / 4 / 5（及 `align-spec-residue-prior-18`）的验收判据写的是
「`openspec validate` 输出**逐字节相同**」，而那用的是**文本输出** ⇒
**`very long` 增量从未被任何验证覆盖**。

## 2. 实测归因（还原法，口径交给 openspec 自己）

**还原法**：把全部注入内容（4 类形态，见 §5）从 spec 里去掉 ⇒ 在临时项目里跑
`openspec validate --all --json` ⇒ 与当前清单求差集 ⇒ 差集 = 注入造成的。

| 指标 | 值 |
|---|---|
| Requirement 总数 | 863 |
| 注入**前**就 very long（**存量固有**） | **37** 条 / 28 spec |
| 注入**后** very long | **62** 条 / 38 spec |
| **注入造成的新增** | **25** 条 / 13 spec |

⚠️ 第一版还原法只识别 3 类形态（漏了「`> **RETIRED ...` 引用块」）⇒ 测出「仅 +7」；
补上第 4 类后才是真实的 **+25**。⇒ **教训**：归因必须先穷举注入形态，否则会低估。

## 3. 25 条注入的来源归并（行号级证据）

| 来源 change | 条数 | 明细 |
|---|---|---|
| `retire-spec-musts-pointing-at-retired-objects`（2026-11-20） | **8** | `project-setup-check[8]`、`ship-done-orphan-cleanup[2]`、`three-phase-skills[0]`、`workflow-design-phase[0,2,3,4,6]` |
| `fix-spec-residue-batch2-dead-intake`（2026-11-20） | **6** | `iterative-plan-fill[1,2,3,4,5]`、`plan-intake-bootstrap[1]` |
| 批 7a（2026-11-21） | **4** | `openspec-version-degradation[0]`、`roadmap-incremental[0]`、`roadmap-proposal-guidance[3,4]` |
| `annotate-spec-residue-guard-batch4`（2026-11-21） | **3** | `archive-gate-verification[3]`、`inline-ac-verifier-into-rdd-verifier[6,7]` |
| `align-spec-residue-prior-18`（2026-11-20） | **2** | `roadmap-feature-fragment[3]`、`ship-done-orphan-cleanup[4]` |
| `retire-execute-skill`（2026-11-20） | **2** | `worktree-context-persistence[0,2]` |

⚠️ **批 3 与批 5 贡献 0 条**（它们的注记形态较短 / 落在 Scenario 区）⇒
原先「批 3/4/5 都引入了」的猜测**不成立**，实际数据以本表为准。

### ⭐ 关键结论：代价主要来自「整份 spec 退役」型长注记

两个「整份退役」专项 change（`retire-spec-musts-pointing-at-retired-objects` +
`fix-spec-residue-batch2-dead-intake`）合计 **14 / 25 = 56%**。

它们的注记是**长引用块**（200–600 字符，描述整份 spec 的退役理由），落在 Requirement 正文里 ⇒
直接推高长度。**残留处置批次**（批 3/4/5/7a）用的是短标注 + 短注记 ⇒ 贡献小。

⇒ **对批 7b 的直接启示**：批 7b 的 14 行 `annotate` 若沿用批 7a 的引用块注记形态
（约 200–430 字符），**会新增 very long** ⇒ 守卫会红 ⇒ 必须显式决策。**围栏形态**
（` ``` ` 包裹）不计入 Requirement 正文 ⇒ 不产生增量（`extractRequirementBody` 跳过 fence 内）。

## 4. 守卫设计

**文件**：`tests/unit/test_spec_requirement_length.py`

| 断言 | 内容 | 抓什么 |
|---|---|---|
| **A** | 当前 `very long` 的 (spec, `requirements[N]`) 多重集 == 冻结清单（**62** 条 / 38 spec） | 任何 very long 的**出现 / 消失 / 换位** |
| **B** | 「注入造成的增量」== 冻结清单（**25** 条 / 13 spec） | **直接针对判据缺口**：任何批次的新注记若把 Requirement 推过 500 ⇒ 红 |

- **口径完全交给 openspec 自己**（CI 装 `@fission-ai/openspec@1.14.3`，与本仓一致）⇒
  **零口径漂移**（不在 Python 里复刻 openspec 的 parser）。
- ⚠️ **执法点是本地，不是 CI**：本仓 `openspec/` 整树被 `.gitignore:45` 排除 ⇒ CI 的 fresh checkout
  里**没有** `openspec/specs/` ⇒ 守卫在 CI 上恒 `skip`（**预期行为** —— CI 上没有可校验的 spec，
  让它 fail 只会让 CI 恒红）。⇒ 守卫在**本地执行批次时**生效。
  （附带发现：CI 的 "Spec validation gate" step 遍历 `openspec/changes/*/` 在 CI 上**同样是空集**
  —— 那是**既有**问题，不在本 change 范围，记入 §8。）
- ⚠️ **归因漂移边界**：若新增的 `very long` 来自**新形态**的注记（剥除规则不认得），断言 B 不会红
  （增量被算进 baseline 侧）⇒ 只更新 `FROZEN_VERY_LONG` 就能转绿，而「注入 / 存量」归因静默腐化。
  ⇒ **规则**：断言 A 红且增量疑似来自新注记形态时，**必须同步扩展剥除规则**，不得只改冻结值。
- 只取 `type == "spec"` 的 item ⇒ **不受活跃 change 影响**（否则每批 change 存续期间清单都漂移）。
- 只比 issue，**不比** `durationMs`（每次都变）。
- **skip-not-fail**：openspec CLI 不可用时 `pytest.skip`（仓库既有先例：
  `tests/unit/test_cross_repo_schemas.py`）。

### AC-3 实证（守卫是否真能抓住变化 —— 否则可能只是「永绿的空壳」）

| 实证 | 手法 | 期望 | 实测 |
|---|---|---|---|
| 1 | 在 `roadmap-proposal-guidance` 的一个 ≤500 的 Requirement 里插一行 **605 字符的普通英文句**（非注入形态） | **A 红**、B 绿 | ✅ A 红（`very long 总数变了：期望 62，实际 63`）、B 绿 |
| 2 | 同一位置插一行 **646 字符的 `> **RETIRED ...` 引用块**（注入形态） | **A 红 + B 红** | ✅ 两条断言均 FAILED |
| 3 | 撤销 | **绿**，spec 逐字节回原状 | ✅ `2 passed` + sha256 一致 |

⇒ 断言 A 抓「任何变化」，断言 B 精确抓「注入造成的增量」，两者**互补**（A 兜底 B 的口径漏识别）。

## 5. 「注入内容」的 4 类识别规则（全仓实测）

| # | 形态 | 规则 | 计数 |
|---|---|---|---|
| ① | 标注 | `^<!-- v4-residue:allow=[a-z-]+ -->$`（独占行） | 207 |
| ② | 批 5 先例 | `^- \*\*NOTE\*\* \(retired `（独占行） | 2 |
| ③ | 批 7a 注记 | `^> \*\*已退役（YYYY-MM-DD）`（独占行） | 5 |
| ④ | 「整份退役」型注记 | `^> \*\*(RETIRED\|已退役)` 开头的**引用块序列** | 45 块 |

**④「引用块序列」**：从 `> **RETIRED|已退役` 行起，**连续**的 `>` 行与 `<!-- v4-residue:allow=… -->`
标注行属**同一注记单元** ⇒ 整段剥除；**空行中断**（隔空的独立说明性引用块保留 —— 可能是正常内容）。

⚠️ ④ 必须**整段**去掉 —— 只去首行会低估注入贡献（§2 的教训）。

⚠️ **第 5 类形态（实测存在）**：`iterative-plan-fill/spec.md:45-47` 的
`> 保留原文与 Scenario 作为历史记录。` 紧跟在标注行之后、被标注行**打断**了 `>` 连续段
⇒ 第一版规则（只吃连续 `>` 行）漏剥了它。改进后的「引用块序列」规则把它一并剥除
（实测**只多剥这一行**，且 baseline 的 very long 判定与增量清单**完全不变** ⇒ 无误剥）。
**规则表不是「已穷举」的承诺** —— 新形态出现时必须扩展规则（见 §4 的归因漂移边界）。

⚠️ **不属注入、不得去掉**：
- `- **THEN** （已退役）...` / `- **AND** （已退役）...`（6 处）—— 这些是**被替换的判据行**
  （原文已改写成退役提示），去掉会**丢原文**；
- 批 6 的**改指**（换 token）—— 两版都带改指后的 token ⇒ 对差值无影响。

## 6. 处置决策：接受并冻结（不消除既有 25 条）

**理由**：

1. 它们是 **advisory**（WARNING 级），`openspec validate --all` 的 **ERROR 数仍是 11**（不变）。
2. 消除需重写 **25+ 处**历史注记（跨 **12+ 份已采纳 spec**）⇒ 改动面远大于本 change，
   且这些 spec 大多**整份已退役**（原文只是历史档案）。
3. 消除会牺牲「读者读判据**之前**先看到退役警告」的可读性 —— 这正是批 7a 选注记形态的理由。

⇒ **接受 + 冻结 + 由守卫阻止新增**。

## 7. 存量 37 条（注入前就 very long，与残留处置工作无关）

| spec | path |
|---|---|
| `add-plan-done-reflect-hook` | `requirements[0]` |
| `add-skill-layer-resolve-project-root-helper` | `requirements[0]` |
| `agent-interface-contracts` | `requirements[5]` |
| `archive-auto-commit` | `requirements[0]` |
| `archive-iteration-sync` | `requirements[0]`, `requirements[3]` |
| `c-layer-4-skills` | `requirements[0]` |
| `consolidate-resolve-project-root-helpers` | `requirements[0]` |
| `design-content-review` | `requirements[2]` |
| `design-proposal-creation` | `requirements[0]` |
| `diagnose-changes` | `requirements[1]` |
| `doc-architecture-v4-sync` | `requirements[0]` |
| `doc-truth-sync` | `requirements[6]`, `requirements[7]` |
| `external-testbed-coop` | `requirements[0]` |
| `fix-33-handlers-project-root-anti-pattern` | `requirements[0]` |
| `fix-skill-layer-project-root-anti-pattern` | `requirements[0]` |
| `fix-skill-layer-resolution-bash` | `requirements[0]` |
| `iterative-plan-fill` | `requirements[0]` |
| `mcp-trace` | `requirements[4]` |
| `post-archive-cleanup-hook` | `requirements[0]`, `requirements[1]`, `requirements[3]`, `requirements[4]`, `requirements[5]` |
| `proposal-lifecycle-sync` | `requirements[0]`, `requirements[1]`, `requirements[2]`, `requirements[3]` |
| `rdd-hub-bootstrap` | `requirements[2]` |
| `skeleton-planning` | `requirements[2]` |
| `skill-role-model` | `requirements[1]` |
| `spec-validation-gates` | `requirements[4]` |
| `three-phase-skills` | `requirements[1]` |
| `verifier-lifecycle` | `requirements[1]` |
| `verifier-v2-hardening` | `requirements[9]` |
| `workflow-design-phase` | `requirements[1]` |
| `worktree-context-persistence` | — （`[0]`/`[2]` 属注入 ⇒ 见 §3） |

## 8. 记 tail（范围外）

1. **批 7b（21 行 / 9 份）** —— 注记形态需重新决策（见 §3 的启示）：
   引用块形态 ⇒ 守卫红（必须显式接受）；围栏形态 ⇒ 不产生增量。
2. **openspec 的 `very long` 存量 37 条** —— 与本工作无关，但值得单独立项
   （openspec 自己的建议是「把示例移进 scenario，或拆成多个 Requirement」）。
3. **CI 上 `openspec/` 不存在 ⇒ 既有的 spec 校验在 CI 上整体空转** —— 本仓 `openspec/` 整树被
   `.gitignore:45` 排除（`git.openspec_tracked=false` 是有意为之）⇒ CI 的 fresh checkout 里
   既没有 `openspec/specs/`（本守卫恒 skip），`.github/workflows/test.yml:113-127` 的
   「Spec validation gate (baseline + delta targets)」遍历 `openspec/changes/*/` **也是空集**
   ⇒ **CI 从未真正校验过任何 spec**。⚠️ 这是**既有**缺口，修它需要决策「spec 是否该进 git」
   （或 CI 里重建 spec）—— 属独立立项，不在本 change 范围。
4. **delta 形态垃圾结构** / **围栏示例与 schema 脱节** —— 各自专项。
5. 批 3 / 4 / 5 的历史 verify 报告 —— **审计痕迹不改写**（缺口由新守卫覆盖）。

## 9. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 4 SHOULD_FIX + 4 NITS）；`mergeable: yes` / `scope_exceeded: false` | 4 SF + 4 NIT **全部处置**（逐条见 `openspec/changes/fix-spec-very-long-verification-gap/proposal.md` 的「审查链」表）。其中 critic 独立验算出 **25 条 / 13 spec**（我原写 14，已修正），并实测出第 5 类注入形态 ⇒ 剥除规则改为「引用块序列」。 |

⚠️ critic 的会话 **shell 被拒** ⇒ 62 / 25 的 CLI 实测由本方完成（`gen_frozen.py` +
`strip_compare.py`），critic 只做了静态核验（逐键数冻结字典 = 62 / 25 ✓、归因表逐条吻合 ✓）。
