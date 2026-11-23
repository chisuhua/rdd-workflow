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
| 专项（`general`） | 4 行 / 2 块 | 测试锁定 + 断言漂移 | **rewrite**（重写判据 + 同步文档 + 同步测试） | ✅ 已完成（`rewrite-spec-residue-general-final`） |

**当前剩余**：**0 处 / 0 行 / 0 份** —— ✅ **Phase 1 收口**（专项 `general` 已完成）。

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

## 专项（4 行 / 2 块）—— ✅ 已完成（2026-11-22，`rewrite-spec-residue-general-final`）

> 原判「不可动」——因为 `:145-146` 被 `tests/unit/test_doc_contracts.py:67-68` 的**子串断言**锁定
> （必须含 `guide-arch` / `guide-plan`），且 `:127-128` 对 ADR-0001 的断言**已漂移**。
> ⇒ 实际处置 = **三方联动**（改 spec 判据 → 改文档 `docs/improvement-suggestions-format.md` →
> 改测试断言），外加 2 处紧邻的同类假断言（硬编码 `disk count (13)` / `skills/propose.md` 不存在）。
>
> 处置结果：A 组重写为「已替代 ADR 必须在 ADR 索引里同样标注」；
> B 组重写为「消费者清单只列磁盘上存在的 skill」+ 具名 4 个当前消费者；
> C 组删掉硬编码计数；D 组改指到 `skills/propose/scripts/propose_quality_check.py:53`。
> critic 第 1 轮 = **APPROVE_WITH_CONDITIONS**（0 BLOCKER）⇒ 直接实施。

| spec | 行 | 原判定 | 实际处置 |
|---|---|---|---|
| `general` | 127 | **断言已漂移（今天为假）**：`general/spec.md:127-128` 断言 ADR-0001 的 Decision 「spec-side 5 phases (setup/adr-create/architecture/roadmap-define/arch-done per `guide-arch`) + ship-side 7 numbered subphases」；实测 ADR-0001 实际写的是 `guide-spec.md` 的 **5 phase (setup/roadmap/propose/deps/spec-done)** 与 ship 端 **「5 阶段 + 1 退出」** ⇒ 两处 phase 名单都对不上 ⇒ 这是**失效断言**，**不能**按 `history` 豁免（豁免一条假断言 = 给假通过发通行证）⇒ 需文本处置或批 7 的 RETIRED 注记形态 | rewrite（判据 + 文档 + 测试） |
| `general` | 145 | **三方锁定**：`tests/unit/test_doc_contracts.py:67-68` 断言 `"guide-arch" in spec` 且 `"guide-plan" in spec`（子串锁）⇒ 改指就红测；且它描述的 `docs/improvement-suggestions-format.md` **本身仍是 v3 名**（实测 `:9` 仍写 `guide-design` / `guide-plan`）⇒ 需专项（改测试 → 改文档 → 改 spec 三方联动） | rewrite（判据 + 文档 + 测试） |
| `general` | 146 | 同上 | rewrite（判据 + 文档 + 测试） |
| `general` | 147 | 同上（`:147` 的 `guide-spec` 是**阴性**断言「SHALL NOT list」，不受 `:46-59` 的 active-reference 正则约束 ⇒ 不构成额外锁定） | rewrite（判据 + 文档 + 测试） |

## 记 tail（范围外）

1. ✅ **已处置（2026-11-22，`retire-general-status-guide-requirement`）** —— `general/spec.md` 的 `general-status-guide-skill-revision` Requirement（88 行 / 14 条 Scenario）**整条退役**（主体 `skills/guide.md` 与 `skills/status.md` 都已归档到 `docs/legacy/skills/`，`skills/_lib/scan-state.sh` 不存在，Scenario 11 点名的 12 个 bats 有 11 个不存在）。连带修正 `general-harden-doc-consistency` 里点名同一批已归档文件的死判据（Group B），并修复 `test_frontmatter_dupkey.bats` 的 glob 塌陷（覆盖 1 → 26）。台账：`.rddf/reviews/retire-general-status-guide-2026-11-22.md`。
   - **退役暴露的两条实现缺口**（原 spec 要求、successor 侧未实现）：
     - ~~**`rddf status` 缺 `review` 状态渲染**~~ —— ✅ **已处置（2026-11-22，`fix-rddf-status-icon-coverage`）**，但**结论与我原先记的不一样**：`rddf status` **不读 `iteration.json`**（`_lib/cli/status_cmd.py:26-30` 模块 docstring 明写「No `iteration.json` involvement」）⇒ 它的状态一律由 `_disk_change_status()` 推导（值域 planned/in_worktree/committed）+ 硬编码的 archived ⇒ **`review` 永远不会出现在它的渲染路径上** ⇒ 原先记的「缺 `review` 键 ⇒ 渲染成 `?`」**不成立**。真正的问题是**两个词汇域漂移**：本批把 iteration.json 域（schema enum 7 值）与 disk-derived 域（6 值）各归其真源，`archived_partial` 的归档口径统一为 14 处，并加 6 个守卫（schema 判据取自 tracked 的 `_lib/schemas/iteration_schema.json` ⇒ CI 有牙齿）。台账：`.rddf/reviews/rddf-status-icon-coverage-2026-11-22.md`。
     - **`rddf archive` 缺交互确认门** —— `_lib/archive.sh:1025` 无条件 `openspec archive "$name" --yes`，原 Mode C 的「确认先于 archive + `-y` 旁路」语义丢失，且无测试锁。
     - ⇒ 两条均属 `implementation_gap`（不是文档缺口），独立立项评估。
2. ✅ **已处置（2026-11-22，`fix-doc-truth-sync-false-assertions`）** —— `doc-truth-sync/spec.md` 的 path 形态漂移已随该批一并清理：该 spec 当时共有 **12 组**假断言（不止这 3 处 path）—— 包括 **D5 与实现相反**（说「npm test 只跑 bats」而实现是 bats+pytest 都跑，**与上一批改过的 `general/spec.md` 直接矛盾**）、ADR 计数「19」（实际 64）、`docs/v2-api-summary.md` / `docs/v2-api-reference.md` / `docs/v2-loop-engine.md` **不存在**、`openspec/specs/` 「15 个目录」（实际 165）、D7 要求 README flag 重复 ADR-0013（真实守卫查的是磁盘）、D3/D1 Scenario 前提已过时。⇒ 全部改判据或退役，并新增 4 个守卫锁住。台账：`.rddf/reviews/doc-truth-sync-false-assertions-2026-11-22.md`。
   - **该批遗留（记 tail）**：`doc-truth-sync` 的 **Requirement 主题划分** —— 「历史路径映射」判据挂在 `migration-guide-no-fictional-cli` 名下，主题错位（critic 第 2 轮 NIT-1）。拆分需再动 `very long` 冻结清单 + 重新过审（该批 critic 预算已满 2 轮）⇒ 独立立项。
3. **`docs/improvement-approved-format.md:3` 头部仍是旧机制描述** —— 「`guide-design` 批准后直接落盘…`guide-plan` intake…`.design-handoff.json` v2」（与 `rewrite-spec-residue-general-final` 同主题、已知为假）⇒ 独立立项。
4. **B 组判据单向性硬化**（critic SHOULD_FIX-3）—— 「consumer list SHALL name only skills that have `skills/<name>/SKILL.md`」**不排斥**「存在但不消费」的 skill、也**不要求完备**⇒ 下一个改名周期会复 drift ⇒ 硬化方向：守卫改为「文档清单 == 代码级消费方检测结果」的封闭判据。
5. **delta 形态垃圾结构** —— 9 份 spec 首行是 `## ADDED Requirements`（未合并的 change delta 被误归档为 capability spec）；`post-flow-analysis` / `rfc-rddf-*` 的 Requirement 名是自动生成的（`fix-adr-0027-cli-optin-gate` / `acceptance-3`）⇒ 需专项重写，不是残留名问题。
   - ✅ **其中的 placeholder Requirement（零信息量）已处置（2026-11-22，`retire-placeholder-spec-requirements`）** —— 5 个（`general/spec.md` 3 个 + `sync-agents-md-five-stage/spec.md` 1 个 + `sync-package-skills-to-disk/spec.md` 1 个）⇒ **1 个退役**（`general-add-skill-bats-tests`：一次性建设型能力，无持续可机械核实的行为契约）+ **4 个改写**为对现有实现的断言（`general-deps-subagent-semantic-analysis` 8 守卫 / `general-adr-directory-structure` 14 守卫 / `sync-agents-md-five-stage` 5 守卫 / `sync-package-skills-to-disk` 2 守卫文件）；并新增 placeholder 守卫（判据实现在已跟踪的 `skills/rdd-doctor/scripts/spec_residue_scan.py::scan_placeholder_requirements`）。台账：`.rddf/reviews/retire-placeholder-spec-requirements-2026-11-22.md`。
   - ⚠️ **该守卫在 CI 上空转** —— 根因是 `openspec/` 整树 gitignore（`git ls-files openspec/` = 0）⇒ CI 上不存在 `openspec/specs/` ⇒ 与既有 `requires_general_spec` 同款。⇒ **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**这件事**在 CI 上没有任何守卫**，且逐份写实无法机械替换 ⇒ 独立立项。
   - ✅ **`acceptance-N` 形态的 218 条 Requirement / 12 份 spec —— 试点已完成（2026-11-23，`rewrite-register-change-in-iteration-spec`）**：`register-change-in-iteration`（9 条）⇒ **退役 2 条元断言 + 改写 6 条**为有语义的契约（Requirement 语义名 / 正文不截断 / Scenario 名不截断 / WHEN 具体化）+ Purpose 写实。台账：`.rddf/reviews/rewrite-register-change-in-iteration-2026-11-23.md`。
     - **该类比 placeholder 更危险**：placeholder 是**零信息**，而 `acceptance-N` 是**把一句真话截成半句**（例：acceptance-2 的「不再返回」丢了宾语，且引用的 `"missing from iteration.json"` 字符串**全仓已不存在** ⇒ 那是一条**已不准确**的断言）。
     - **分流判据**（试点验证过）：机制的**机制是否还在** + 有**逐条可机判的守卫** ⇒ 改写；**元断言**（「别退化」）/ **相对断言**（「无新增 finding」）⇒ 退役；机制在但**无守卫** ⇒ 先补守卫（试点就补了一个：幂等用例 seed + 断言 `archived_at`/`archive_commit_sha` 不变），补不了才收窄契约。
     - **退役不丢内容**：原文永远在 `openspec/changes/archive/<date>-<name>/proposal.md` 的 `## Acceptance` 段。
     - **工作量基线**（试点实测）：每份 spec 边际成本 **≈30–45 min** ⇒ 剩余 11 份 **≈6–9 h**，可拆 11 批每批 1 份。
   - ✅ **第 2 批已完成（2026-11-23，`rewrite-acceptance-form-batch-2`）** —— 3 份 / 27 条 AC ⇒ **19 条契约 + 8 条退役**：`fix-flow-drift-batch-1`（8→6）· `fix-worktree-archive-path`（10→6）· `fix-p3-verifier-gate`（9→7）。清单 `compliant` 1 → **4** 份、`pending` 11 → **8** 份。台账：`.rddf/reviews/rewrite-acceptance-form-batch-2-2026-11-23.md`。
     - **新发现的两类退役理由**（试点没有的）：① **已被推翻** —— `fix-worktree-archive-path` 的 AC-8 被 `fix-lightweight-branch-and-archive` **有意变更**（推翻登记在 `.rddf/improvements/fix-lightweight-branch-and-archive.md:233-235`）；新行为已落在 `archive-openspec-tracked-skip-commit/spec.md` 与 `archive-auto-commit/spec.md` ⇒ 退役不丢信息。② **没有流程级守卫** —— `archive_path` 字段**全仓无守卫**，且 untracked 路径 `_lib/archive.sh:1034` 传**空 sha** ⇒ 退役。
     - **补 2 处守卫**（critic SF-1/SF-2 指出的「无守卫子句」）：优先**补守卫**而不是削契约（行为是真的、守卫是缺的）；补之前先确认断言**非空转**。
     - **两条方法论教训**：③ 守卫引用要核对**夹具是什么**（`test_rdd_builder_phase3_archive.bats` 的夹具是 lightweight 模式，拿它当 untracked 路径的守卫是引错了）；④ **mock 型 e2e 不算行为守卫**（全仓唯一断言「归档后 spec 存在」的 `test_rdd_builder_e2e.bats:89` 由 `scenarios/b_e9.json:12` 直接铺文件）。
   - ✅ **第 3 批已完成（2026-11-23，`rewrite-acceptance-form-batch-3`）** —— 3 份 / 34 条 AC ⇒ **15 条契约 + 19 条退役**：`fix-phase3-cleanup-wiring`（7→5）· `fix-script-project-root-anchoring`（13→7）· `rfc-rddf-project-yaml-config-i10`（14→3）。清单 `compliant` 4 → **7** 份、`pending` 8 → **5** 份。台账：`.rddf/reviews/rewrite-acceptance-form-batch-3-2026-11-23.md`。
     - ⚠️ **两条新的方法论教训**（本批特有）：
       ⑤ **不能照抄归档 AC 的措辞 —— 它描述的是过去**。归档 AC 说「`git.openspec_tracked: false` 时强制轻量模式」，我改写成「强制 serial 且**不可覆盖**」⇒ **与实现相反**（实现优先级 CLI flag > project.yaml > env）⇒ 而且**我自己引的守卫就在反证它**（`CLI flag --parallel wins over project.yaml`）。⇒ 改写必须**实读实现 + 守卫**。
       ⑥ **「spec 里没有」有两种成因，处置相反**：**归档工件缺陷**（AC-G2：14 条 AC ⇒ 13 条 delta，生成时整丢）⇒ **补回**；**已签批删除**（`acceptance-3`：batch7b2 §D 有意删除，理由是判据被 v4 反证 + 正确判据已在 `complete-project-yaml-config-gaps`）⇒ **不补回**。⇒ 判据要看**归档 delta 与 live spec 的差异记录**，不能只看「有没有守卫」。
     - **防回归形态**：tracked 清单 `tests/unit/spec_form_compliant.json`（`compliant` / `pending` / `class_total`）+ 守卫 `tests/unit/test_spec_requirement_form.py`。**清单级**判据（并集 == 已知全集 / 只增不减）在 **CI 上有牙齿**；**形态级**判据（无语义名 / 恒真 WHEN）需 `openspec/specs/` ⇒ **CI 上 skip**（`openspec/` gitignore 的必然结果）。
   - ✅ **第 4 批已完成（2026-11-23，`rewrite-acceptance-form-batch-4`）** —— 3 份 / **78 条 AC** ⇒ **36 条契约 + 27 条退役 + 15 组合并**：`rddf-layout-manifest`（25→12）· `fix-bats-per-file-timeout`（22→11）· `fix-skill-post-install-discoverability`（31→13）。清单 `compliant` 7 → **10** 份、`pending` 8 → **2** 份（`env-bootstrap` 44 · `objective-tracking` 33）。台账：`.rddf/reviews/rewrite-acceptance-form-batch-4-2026-11-23.md`。
     - ⚠️ **三条新的方法论教训**（本批特有）：
       ⑦ **按「形态类」计数，不要按「文件名模式」计数**。`acceptance-N` 与 `capability-N` 是**同一形态退化族的两种命名**（自动生成名 + 恒真 WHEN + `is enforced` 结尾）—— 只治理前者会整类漏掉后者。本批 `rddf-layout-manifest` 的 `capability-19~25`（7 条）前 4 轮**全漏**，直到收口前自查才发现 ⇒ 台账口径由 71 条更正为 **78 条**。⇒ 后续守卫应按**形态**（无语义名 / 恒真 WHEN / `is enforced` 结尾）登记，而非按类名前缀。
       ⑧ **判「无守卫」前必须先查文件名，不能只 grep 内容**。本批我把 AC-23 判成「`test_layer0_sentinel_order.bats` 文件不存在」⇒ **实际存在**（2026-09-21，3 个用例）⇒ 按判据 ⑥ 应**改写**而非退役 ⇒ critic 第 2 轮 BLOCKER-1。这与第 1 轮的 BLOCKER-1/2 是**同一缺陷类**（误判守卫存在性 ⇒ 错误退役 ⇒ 丢契约）。⇒ 「无守卫」的判定要**先列文件、再列用例名**。
       ⑨ **spec 断言不得强于守卫**（全称量化 vs 单实例）。本批我写「**a** read-only artefact SHALL list no rdd writer」—— 守卫只钉 `reviews` 一个，而 manifest 里 `write_by` 不含 rdd 的有 **9** 个 ⇒ 若 `config` 明天混入 rdd writer，全部守卫仍绿而 spec 已违约。⇒ 处置：**扩守卫**（新增 `test_non_rdd_entries_name_their_actual_writer` 逐条钉住 9 个条目）+ spec 措辞与之等强。
     - ⚠️ **一条工程约束**：改写若让 stage token **真的消失**，必须**同提交**更新冻结常量 `tests/unit/test_v4_residue_check.py::test_r4_repo_residue_constant`（303/159/41 → **297/157/40**；该测试 docstring 明写此规则）。本批漏改 ⇒ pytest 红 1 条。
6. **`dashboard-verification-status` 围栏示例与 schema 脱节** —— 缺 `rdd-builder` / `pending-agent`，含 enum 外的 `null` ⇒ 文本修正专项（围栏式标注只豁免旧名，不修脱节）。
7. **围栏式 `enum` 的 schema 机检交叉校验** —— backlog（会让扫描器耦合 `_lib/schemas/`，破坏「能在任何有 `openspec/specs` 的项目上独立跑」的设计）。
8. **`spec_residue_scan.py:488` 的 `hit_lines` 是死变量** —— 改前就存在（只 `add` 从不读），本次未删（改动最小化边界）。

