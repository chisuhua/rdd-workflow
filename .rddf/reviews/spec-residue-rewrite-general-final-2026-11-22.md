# spec 残留处置台账 — Phase 1 收尾批（general 专项，2026-11-22）

> 定位：change `rewrite-spec-residue-general-final`。
> **4 处命中 / 2 块**（`general/spec.md`）+ **2 处紧邻的同类假断言** + 1 份文档 + 1 个测试文件。
> **Phase 1 在本批收口**：全仓未豁免命中 **0 处 / 0 块 / 0 份**。

## 0. 为什么这一份不能用「标注 / 纯 token 替换」

| 障碍 | 事实 |
|---|---|
| **测试锁死** | `tests/unit/test_doc_contracts.py:67-68` 断言 spec 里**必须出现** `guide-arch` / `guide-plan`（退役名）⇒ 只动 spec 必然让测试红 |
| **断言本身为假** | A 组断言 ADR-0001 的 phase 列表 = `setup/adr-create/architecture/roadmap-define/arch-done` + 7 个 ship 子阶段；B 组断言的 6 个消费者与文档实际清单**无一相同** ⇒ 纯 token 替换只会把假断言换个说法 |
| **文档同源** | `docs/improvement-suggestions-format.md` 的消费者清单是 `guide-design`/`guide-plan`/`propose`/`dashboard` ⇒ B 组判据与文档**互相矛盾** ⇒ 必须同步改文档 |

⇒ 处置 = **三方联动**（改 spec 判据 → 改文档 → 改测试）。

## 1. 命中处置（4 处 / 2 块）

### A 组 —— `general/spec.md` L123-130（重写）

**改前**

```
#### Scenario: ADR-0001 reflects actual three-phase architecture

- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its Decision section SHALL list spec-side as 5 phases
  (setup/adr-create/architecture/roadmap-define/arch-done per `guide-arch`)
  and ship-side as **7 numbered subphases (Phase 1, 1.5, 2, 2.5, 3, 4, 5)**
- **AND** it SHALL list current subskills including `feature` and
  `rddf-session` (13 on disk total, 13 in package.json publish set — Decision 3 = A)
```

**改后**

```
#### Scenario: superseded ADR-0001 is marked as superseded in the ADR index

- **WHEN** `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` is read
- **THEN** its status line SHALL state it is superseded by ADR-0002 + ADR-0003
- **AND** `docs/adr/README.md` SHALL list ADR-0001 with the same superseded status
```

**依据**

| 断言 | 实测 | 判定 |
|---|---|---|
| ADR-0001 spec 端 5 phase = `setup/adr-create/architecture/roadmap-define/arch-done` | `docs/adr/ADR-0001-propose-plan-execute-state-machine.md:48` 写的是 `setup/roadmap/propose/deps/spec-done`（per `guide-spec.md`） | **假** |
| ADR-0001 ship 端 = 7 numbered subphases | 同文件 `:58` 写的是 `5 阶段 + 1 退出`（plan/execute/archive/cleanup + ship-done） | **假** |
| ADR-0001 列出现行子技能（含 `feature`/`rddf-session`，13 个） | 同文件 `:18`/`:35`/`:43` 写的是 9 / 10 个子技能，不含这两个；disk 实测 **26** 个 canonical skill | **假** |

**现行不变量（可长期成立）**：ADR-0001 `:6` = `> **状态**: 已替代为 ADR-0002 + ADR-0003（已实施）`；
`docs/adr/README.md:30` 同行同标注 ⇒ 「已替代 ADR 必须在自身与索引里同时标注」。

> **critic 认可**（focus 1）：原判据是「假代理」—— 历史 ADR 已被替代 4 代
> （ADR-0001 → ADR-0003 → ADR-0025 → ADR-0034 → v4），现行架构真值由 ADR-0003 +
> ADR-0043/0048 补丁链与 `docs/architecture/` 快照承载；原判据丢弃**无实质损失**，
> 且**不要在本批**恢复 architecture-truth 覆盖。

### B 组 —— `general/spec.md` L142-148（重写）

**改前**

```
- **THEN** the consumer list SHALL include `propose`, `guide-arch`,
  `guide-plan`, `guide`, `status`, and `deps`
- **AND** it SHALL NOT list `guide-spec` (removed in v2.0)
- **AND** `roadmap` SHALL be listed if it consumes the format
```

**改后**

```
- **THEN** its consumer list SHALL name only skills that have a
  `skills/<name>/SKILL.md` on disk
- **AND** it SHALL include `rdd-planner`, `rdd-builder`, `propose`, and `add-improve`
```

**依据**（真实消费者，全部带行号）

| skill | 证据 |
|---|---|
| `rdd-planner` | `skills/rdd-planner/SKILL.md:30-31` owns `improvement-suggestions.md` + `improvement-approved.md`；`:46` 术语澄清 |
| `rdd-builder` | `skills/rdd-builder/scripts/phase0_approval.sh:56` `IMPROVEMENT_FILE=.rddf/improvements/<name>.md`；`:61` 读取；`:147`；`:163` 写 `openspec/changes/<name>/proposal.md` |
| `propose` | `skills/propose/SKILL.md:47` / `:52` 读；`:156-160` 更新索引 |
| `add-improve` | `skills/add-improve/SKILL.md:32` 「注册到 improvement-suggestions.md」；`:40` 索引模版 |

四个名字在 disk 上都有 `skills/<name>/SKILL.md` ✓（canonical skill 共 26 个）。

⚠️ **critic 纠正的关键事实**：`rdd-builder` **不碰** `improvement-suggestions.md`
（`skills/rdd-builder/` 全目录 grep = **0 命中**），它消费的是**被链接的**草稿
⇒ 文档 Consumers 段的前提必须放宽（见 E 组 L159）。

## 2. 关联修正（2 处 —— 同一 Requirement 内、紧邻、同样为假）

| 组 | 位置 | 改前 | 改后 | 依据 |
|---|---|---|---|---|
| C | `general/spec.md:138-140` | `SHALL include the disk count (13) matching` | `SHALL include the disk count matching` | disk canonical = **26**（`skills/*/SKILL.md`，排除 `metadata: deprecated:`）；`package.json::skills[]` = 26；`skills/INSTALL.md` description = 「全部 26 个子技能」⇒ 硬编码 `13` 为假；删数字后恒真且不会再次漂移 |
| D | `general/spec.md:146-151` | 标题 `propose.md uses 4-digit ADR pattern` + `WHEN \`skills/propose.md\` L193 is read` | 标题 `propose uses 4-digit ADR pattern` + `WHEN \`skills/propose/scripts/propose_quality_check.py\` L53 is read` | `skills/propose.md` **不存在**（skills 已目录化）；真实 4 位 ADR 正则在 `skills/propose/scripts/propose_quality_check.py:53` `_ADR_PATTERN = re.compile(r"ADR-\d{4}")`（`:99` 用它校验 proposal.md 至少引用 1 个 ADR）⇒ **新落点存在 + 行为等价 + 行号级证据** 三项齐备（改指判定纪律）；`docs/adr/README.md:209` 的 `ADR-NNNN-<slug>.md` 约定仍在 |

## 3. E 组 —— `docs/improvement-suggestions-format.md`（16 处）

| 行 | 改前 | 改后 | 依据 |
|---|---|---|---|
| 9 | 清单 `guide-design`/`guide-plan`/`propose`/`dashboard` | `rdd-planner`/`rdd-builder`/`propose`/`add-improve` | B 组依据 |
| 24 | `guide-design` 逐个审查…批准后**直接落盘** `openspec/changes/<name>/proposal.md` | `rdd-planner` 逐个审查…批准后写 `improvement-approved.md`；`proposal.md` 由 `rdd-builder` P0 从草稿落盘 | `skills/rdd-planner/SKILL.md:38` 把 `openspec/changes/<name>/proposal.md` 列在 **not_owns**；`phase0_approval.sh:163` |
| 92 | manually or by `guide-arch` gap analysis | manually or by `add-improve` | `skills/rdd-arch/SKILL.md:494`「删除原 Phase 3 architecture（差距分析）」 |
| 100 | `### 3. Review flow (\`guide-design\` Phase 3)` | `### 3. Review flow (\`rdd-planner\`)` | `skills/rdd-planner/SKILL.md:78` Phase 0 / `:264` Phase Exit，无 Phase 3 |
| 102 | `guide-design` reads `improvement-suggestions.md` via `list_improvements()` | `rdd-planner` reads `improvement-suggestions.md` and the `.rddf/improvements/*.md` drafts (via `read_improvement_entries()`) | `_lib/state.sh:110-127` 的 `list_improvements()` 读 `.rddf/improvements/` 目录，**不是** suggestions 表；`_lib/state_reader.py:346` 才是解析 improvement 文件的（planner 侧经 `dashboard.collect_pending` → `_lib/dashboard/__init__.py:653`） |
| 105-107 | design approval 直接创建 `{proposal.md,.openspec.yaml,roadmap-meta.yaml}` | design approval 不落盘 change；`rdd-builder` P0 从草稿落盘 `proposal.md` | `phase0_approval.sh:147-183` |
| 111 | `### 4. Consumption flow (\`guide-plan\` propose)` | `### 4. Consumption flow (\`rdd-builder\` P0 intake)` | 同上 |
| 113 | `guide-plan` reads `improvement-approved.md` via `list_approved()` | `rdd-builder` P0 receives the approved set via `.rddf/state/.planner-handoff.json` | `phase0_approval.sh:40-45` 读 `.rddf/state/.planner-handoff.json`；`:56,61,147` 读 improvement 草稿 |
| 125 | `list_improvements` \| Parse suggestions table. Returns `name\|priority\|source` | `list_improvements` \| List `.rddf/improvements/*.md`. Returns `name\|priority\|source\|status` | `_lib/state.sh:110-127`（实际返回 4 字段） |
| **159** | All skills that touch `improvement-suggestions.md` MUST read it as a Markdown table … | All skills that touch `improvement-suggestions.md` **or the linked `.rddf/improvements/*.md` drafts** MUST read the index as a Markdown table … | **critic SHOULD_FIX-2**：新判据下 `rdd-builder` 只消费被链接的草稿 ⇒ 原前提会与新清单矛盾 |
| 164 | `guide-design.md` \| Phase 3 … | `rdd-planner` \| 提案池治理 … | B 组依据 |
| 165 | `guide-plan.md` \| Phase 0 intake (read `improvement-approved.md` and `.design-handoff.json`…) | `rdd-builder` \| Phase 0 intake (read `.rddf/state/.planner-handoff.json` and each `.rddf/improvements/<name>.md` draft) | `.design-handoff.json` 的 intake-skip 语义继任者是 `.planner-handoff.json`（`phase0_approval.sh:43`），**不是** `.plan-handoff.json`（后者是 builder P1.5 的 `execution_mode_decisions`） |
| 166 | `propose.md` \| … | `propose` \| … | 消费者清单统一用**裸 skill 名**（与判据「skill 目录名」一致） |
| 167 | `dashboard` \| Pending section | `add-improve` \| 创建 improvement 草稿并注册进索引 | `skills/add-improve/SKILL.md:32,40` |
| 169-170 | The helper in `skills/_lib/state.sh::list_improvements()` centralizes the parsing logic | …lists `.rddf/improvements/*.md` with parsed metadata | 同 L125 |
| 178 | `populate-state.json` v2 schema is used by `guide-arch` Phase 6 internal Roadmap Sync step | `populate-state.json` v2 schema is **owned** by `rdd-planner` per ADR-0048 (since v4 `rdd-arch` no longer writes it) | `skills/rdd-arch/SKILL.md:112`「不写 `.rddf/state/.populate-state.json`（per ADR-0048, 移交给 `rdd-planner`）」；`:553` 原 Roadmap Sync 已删；**critic SHOULD_FIX-1**：`_lib/populate_lib.py:953,987` 的读写函数生产代码**零调用方** ⇒ 「used by Phase 0」不可证 ⇒ 改写为**维护权**表述 |

## 4. F 组 —— `tests/unit/test_doc_contracts.py`（1 换 3 新）

| 改动 | 内容 |
|---|---|
| 替换 `:64-68` | `test_general_spec_consumers_drop_guide_spec_add_arch_plan` → `test_general_spec_names_current_improvement_consumers`：断言 spec 含 `rdd-planner`/`rdd-builder`/`propose`/`add-improve` |
| 新增 | `test_improvement_suggestions_format_consumer_list_current`：解析文档 `## Consumers` 表第一列 ⇒ 每个名字必须有 `skills/<name>/SKILL.md`，且必须含 4 个当前消费者 |
| 新增 | `test_improvement_suggestions_format_no_retired_stage_names`：文档正文不得出现 `guide-spec`/`guide-arch`/`guide-plan`/`guide-ship`/`guide-design` |
| 新增 | `test_superseded_adr_0001_marked_in_index`：ADR-0001 与 ADR 索引都必须写「已替代为 ADR-0002 + ADR-0003」 |

## 5. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| **未豁免** | 4 处 / 2 块 / 1 份 | **0 处 / 0 块 / 0 份** ✅ |
| 含已豁免 | 307 / 161 / 42 | **303 / 159 / 41** |
| 已登记豁免 | 303 | **303（不变）** |
| `stale` / `invalid` / `in_fence` / `fence_rejected` | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| `openspec validate --all --json` 的 issue 多重集 | 224 条 | **224 条（新增 0 / 消失 0）** |
| `very long` | 62 条 | **62 条（未新增）** |
| `validate --all` ERROR | 11 | **11** |
| `doctor --category v4-residue` | 2 WARNING | **0 WARNING / 0 CRITICAL** |
| census `disposition=unset` | 4 | **0** |

⚠️ **含已豁免 −4 处 / −2 块 / −1 份**：4 个退役 token **真的消失**（与批 7b-1 的「标注 ⇒ 含已豁免不变」不同）。
−2 块 = A、B 两块各自清空；−1 份 = `general/spec.md` 完全退出命中文件集合。

## 6. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**；`mergeable: yes` / `scope_exceeded: false`；**0 BLOCKER** + 3 SHOULD_FIX + NITS | **SHOULD_FIX-1**（E 组 L178）：`populate_lib` 的读写函数生产代码零调用方 ⇒ 「used by Phase 0」不可证 ⇒ 改写为**维护权**表述（**已改**）。**SHOULD_FIX-2**（E 组 L159）：`rdd-builder` 不碰索引表 ⇒ Consumers 前提放宽（**已改**，E 组 14 → 16 处）。**SHOULD_FIX-3**（B 组判据单向性）：**记入 tail**，本批不实施。**NIT**（E165 依据）：继任者是 `.planner-handoff.json`（**已改依据**）。**NIT**（E102 依据）：补 `collect_pending`（**已补依据**）。**范围外观察**：`docs/improvement-approved-format.md:3` 旧机制描述 ⇒ **记 tail**。 |

⚠️ critic 的**通过项**：A 组新判据可长期成立（focus 1a）· 原判据丢弃无实质损失（focus 1b）·
字面串脆性可接受（focus 1c）· C/D 边界不越界（focus 3）· B 组单向性为「本批目标下的机判折衷」·
无 BLOCKER。

## 6.5 全量门首跑的 1 个「新增失败」（已复核 = 网络 flake）

失败用例：`tests/integration/test_cross_repo_impact_detection.bats:168`
`04_multi_contract_match_returns_stakeholders_union`
—— 它用 `gh api -X PUT` 把 contract 推到**真实 GitHub Hub 仓库**再回读
（推送失败被 `|| true` 吞掉 ⇒ 仓库内 contract 不足 2 份 ⇒ `.matches | length` 断言失败）。

| 复核动作 | 结果 |
|---|---|
| 单独跑该文件 | **4/4 pass** |
| 输入与本次改动的交集 | **无**（本次只动 `general/spec.md` / `docs/improvement-suggestions-format.md` / `tests/unit/test_doc_contracts.py` / `tests/unit/test_v4_residue_check.py` / `.rddf/reviews/**`） |
| 全量门重跑一次 | **GATE_RC=0 · 新增失败 0 · 未评估 0** |

⇒ 判定为**环境（网络）信号**，非实现回归 ⇒ 不做代码改动，仅记录。

## 7. Phase 1 状态

**✅ Phase 1 收口** —— 全仓未豁免残留命中 **0 处 / 0 块 / 0 份**。
`openspec/specs/**` 里已无任何退役 stage 名。

## 8. 记 tail（范围外，已进形态台账）

1. **`general/spec.md` 的 `general-docs-match-code` 其余假断言**（未被残留扫描器命中）：
   `:102-103` `ls skills/*.md`（应 `skills/*/SKILL.md`）· `:110-114` `skills/status.md`（文件不存在）·
   `:118-121` 过时 glob · `:165-173` `scripts.test` 断言与实现相反 · `:156-163` `tests/README.md` 未核验。
2. **`docs/improvement-approved-format.md:3`** 头部仍是旧机制描述（同主题、已知为假）。
3. **B 组判据单向性硬化**（critic SHOULD_FIX-3）—— 守卫应改为「文档清单 == 代码级消费方检测结果」的封闭判据。
4. `rfc-rddf` 的其余 14 个 `acceptance-N`（delta 形态垃圾结构）。
5. 既有 62 条 `very long`（已接受并冻结，守卫阻止新增）。
6. CI 上 `openspec/` 不存在 ⇒ spec 校验在 CI 整体空转（既有缺口，独立立项）。

## 9. 回滚

- 台账 / 测试 / 文档：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 =
  `/tmp/opencode/general-final-before/general-spec.md`（改前快照）
  + `/tmp/opencode/specs-backup-general-final-<ts>/`（165 份整树）。
