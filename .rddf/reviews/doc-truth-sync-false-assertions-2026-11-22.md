# fix-doc-truth-sync-false-assertions 台账（2026-11-22）

## 范围

`openspec/specs/doc-truth-sync/spec.md` 的 **12 组假断言** + `docs/migration/v1-to-v2.md`
的当前态路径 + `README.md` / `AGENTS.md` 的构成计数 name-free 化 + 4 个新守卫。

## 为什么这批值得做

`doc-truth-sync/spec.md` 是「文档跟随实现」这条契约的**判据所在**。
上一批（`fix-docs-match-code-assertions`，`a2e670cf`）修了 `general/spec.md` + 7 份文档，
**漏掉了 `doc-truth-sync/spec.md` 本身** ⇒ 两个 spec 直接互相矛盾：

| 判据 | 主张 | 实际 |
|---|---|---|
| `general/spec.md::general-docs-match-code`（上批已改） | `npm test` 跑 bats **+ pytest** | ✓ 与实现一致 |
| `doc-truth-sync/spec.md::D5`（本批） | `npm test` **只**跑 bats | ✗ **与实现相反** |

实现侧证据：`package.json::scripts.test` = `npm run test:bats && npm run test:python`；
`tests/unit/test_doc_contracts.py::test_npm_test_trap_caveat_locked` 锁的就是「两者都跑」。

⇒ 上一批的教训「**判据 surface 必须覆盖同类文本**」在下一批**立刻复发**。
本批守卫把同类文本全部纳入射程。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 5 SF + 3 NIT），`mergeable: yes` / `scope_exceeded: true` | 5 SF + 3 NIT **全部采纳** |
| 2（复审） | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 1 SF + 2 NIT），`mergeable: yes` / `scope_exceeded: false` | SF 与 NIT-2 已修；NIT-1 记 tail |

**评审预算已用满 2 轮** ⇒ 第 3 轮须用户明确批准。

### 第 1 轮 5 SF + 3 NIT 处置

| # | finding | 处置 |
|---|---|---|
| SF-1 | AGENTS.md 同类漂移点漏排期（`:133/:155/:157/:171/:183`）；二选一后果：守卫覆盖则 T4.7 必红，不覆盖则留洞 | 全部 name-free 化（实测 `_lib/*.sh`=20、`skills/_lib/*.sh`=16、`docs/adr/ADR-*.md`=64、`openspec/specs/`=165、`_lib/cli/*.py`=41）。**且实施时的宽口径扫描又找出 15 处同类** ⇒ 组 D 共 **28 处** |
| SF-2 | 弃用表不切列无依据（`:419` 替代列 `guide-arch.md`+`guide-plan.md` 今天也不存在） | 弃用表也加「当前路径（v4.0+）」列 |
| SF-3 | 同文档未声明的死链接/失效命令（`:673-676` 3 个死链接、`:597` `skill_use("guide-plan")`） | 一并吸收 |
| SF-4 | 守卫 #2 的「条目」定义有歧义（占位符 / 非 skill 条目） | 显式定义条目抽取规则 + 占位符豁免 |
| SF-5 | A2 / A3 是 prose-only 判据 | 各配一个守卫（守卫 3 → 4 个） |
| NIT-1 | `AGENTS.md:134` `28 个 rddf 子命令` 仍会再漂 | name-free |
| NIT-2 | proposal A1 行「ADR 列表表」笔误 | 改「ADR 列表的表格」 |
| NIT-3 | C3 守卫不得误伤 `AGENTS.md:145` / `:183` | 豁免清单 + AUTO 段豁免 |

### 第 2 轮 1 SF + 2 NIT 处置

| # | finding | 处置 |
|---|---|---|
| SF-1 | `README.md:161-162`「+ **36** rddf CLI」×2 —— 我只去掉了「个/子命令」三个字，**数值 36 仍在**（实测 41）；且守卫后缀表不含 `CLI`/`subcommands` ⇒ 既漏改也漏防 | 两行改「+ rddf CLI 面」；守卫 `_COUNT_CLAIM` 后缀表补 `CLI`/`subcommands?`/`子命令`/`commands?`。**补齐后又抓出 `README.md:406`**「7 subcommands + 2 doctor categories」（两者实测**为真**，但仍是会漂移的硬编码计数）⇒ 一并 name-free |
| NIT-1 | A4 Scenario 挂在 `migration-guide-no-fictional-cli` 名下，主题错位 | **不采纳**：改 Requirement 结构会再次移动 `very long` 序号 + 需再动冻结清单，且结构变更应重新过审 —— **critic 预算已满 2 轮**。⇒ 记 tail |
| NIT-2 | 迁移指南 `:564`「遗留演示」块内一句自相抵牾（既说 `sync_state.py` 在库层维护，又说已删除） | 已修：改为「**当时**（v2.0 过渡期）…（`skills/_lib/sync_state.py`，已删除）」 |

## 12 组假断言逐条核算

| # | 位置 | 断言 | 实测 | 处置 |
|---|---|---|---|---|
| A1 | `:11` | ADR 0002-0012 状态 ∈ {✅已实施, ⚠️部分实施, ❌未实施} | 实际词表 `已采纳` / `已采纳（v2.0 奠基 ADR）` / `模板（v3.0 候选占位）` / `✅ 已采纳 + 已实施（…）` | 改判据为「每个 ADR 文件 SHALL 出现在 ADR 列表的表格 + 状态非空 + 与生成器字节一致」 |
| A2 | `:16-20` + `:25-27` | ADR count SHALL read "19"；`docs/v2-adr-summary.md` | `docs/adr/` = **64** 个；该文档**不存在** | Requirement 改名 `adr-index-covers-all-real-adrs`；计数由 disk 派生、不得硬编码 |
| A3 | `:45` | 迁移指南 SHALL be **zero** references to 虚构 CLI | 6 处，**全部**是「规划中，v2.1 实现」标记 ⇒ 与自身 AND 子句矛盾 | 改判据为「每处引用 SHALL 带 planned 标记」+ 守卫 #4 |
| A4 | `:48-51` | dangling 路径已修 | 3 张表仍列 6 个已移动/已归档的文件为「必须存在」 | **改文档**（3 张表加列）+ 改判据 + 守卫 |
| A5 | `:90-98` | 修 `docs/v2-api-reference.md` 与 `docs/v2-loop-engine.md` | **两个文件都不存在**（critic 考古：2026-08-07 docs-restructure 中被 `rm`，非改名；内容并入 `docs/architecture/`，successor 无 `session_v20.py` 残留） | **退役整条 Requirement** |
| A6 | `:102-105` | `openspec/specs/` SHALL include **15** directories | 实际 **165** | 改名 `promoted-specs-remain-promoted`；只要求 4 个被提升目录在列，不再钉总数 |
| A7 | `:132-134`（D5 bullet）**+ `:198-204`（D5 Scenario）** | `scripts.test` MUST contain **exactly** `bats tests/`；Scenario 要求 stderr 提醒「npm test MUST only run bats」 | 实现两者都跑 | 改判据（**两处**）—— 守卫 #1 在实施中抓到了我漏改的 Scenario |
| A8 | `:146` | D5 守卫住在 bats 文件 | 实际在 `tests/unit/test_doc_contracts.py` | 改判据 |
| A9 | `:140-142` + `:220-226`（D7） | README SHALL flag 重复的 ADR-0013 | README **无**此 flag；真实守卫查**磁盘**（`test_adr_index.bats:29` + `test_doc_contracts.py:337`） | 改判据为「磁盘上 SHALL 只有一个 ADR-0013」 |
| A10 | `:180-187`（D3） | 前提：general/spec.md 仍断言 "5 阶段 + 1 退出" | 上批已改为 7，且 general/spec.md 现在**明确禁止**该措辞 | 改判据（前提改为「两侧不一致」） |
| A11 | `:246-253` | 前提：USAGE.md 与 general/spec.md 都说 5 阶段 | 两者现在都是 **7** | 改判据 |
| A12 | `:156-162`（D1） | 「contributor adds `skills/foo.md`」 | skills 已目录化 ⇒ `skills/foo/SKILL.md` | 改判据 |

Requirement 数 **8 → 7**。

## 组 B —— 迁移指南的当前态路径

三张表各加「当前路径（v4.0+）」列，**14 个当前路径全部实测存在于 disk**：

| v2.0 时期路径 | 当前路径（v4.0+） |
|---|---|
| `skills/guide-arch.md` | `skills/rdd-arch/SKILL.md`（ADR-0042） |
| `skills/guide-plan.md` / `skills/guide-ship.md` | `skills/rdd-builder/SKILL.md`（ADR-0043 stage-merge） |
| `skills/loop_engine.py` | `skills/loop_engine.py`（未变，向后兼容 shim） |
| `skills/_lib/state_vector.py` | `_lib/core/state_vector.py`（commit c3a90fe flatten） |
| `skills/_lib/event_log.py` | `_lib/core/event_log.py` |
| `skills/_lib/session.py` | `_lib/session.py` |
| `skills/propose.md` | `skills/propose/SKILL.md` |
| `skills/execute.md` | 已归档 `docs/legacy/skills/execute`（ADR-0063） |
| `skills/status.md` | 已归档 `docs/legacy/skills/status`；能力改由 `rddf status` CLI 承载 |
| `skills/roadmap.md` | `skills/roadmap/SKILL.md` |

另修：3 个死链接（`v2-loop-engine-guide.md` / `v2-config-schema.md` / `v2-adr-summary.md`）
→ `../architecture/loop-engine.md` / `../schemas/README.md` / `../adr/README.md`；
2 处 `skill_use("guide-plan")` → `skill_use("rdd-builder")`；
`:675` `skill_use("loop", …)` → 指向主题文档；2 处 v1→v2 映射表加 note。

**不动**（已核实是显式标注的历史记录）：`:552-557` `sync_state.py`（有「已被删除」「遗留演示」标记）·
`:554` `v2_to_v3.py`（未来）· `:786` `_lib/actions.py`（未来工作说明）。

## 组 D —— 构成计数 name-free 化（28 处）

**判据**：这些计数随**每次新增文件/测试**漂移；每漂移一次就要改文档 + 改守卫 = 成本不对称
（沿用上一批教训「主 spec / 文档不冻闭集」）。按 truth-source hierarchy（L4 跟随 L2），
活文档里的计数快照本身就是被禁的漂移类。

**豁免清单**（守卫不拦）：

| 豁免 | 理由 |
|---|---|
| `26 个子技能` / `26 SKILL.md` | skill 计数 —— 已由既有守卫 `test_skill_count_in_narrative_docs_matches_disk` **动态**锁定（活的断言） |
| `门(4 道)` | 本地门数量 = CI 契约 |
| `4 phases: detect→diagnose→suggest→guided-fix` | phase **名字就在同行** ⇒ 可派生 |
| `TDD 5 步` | 同上 |
| AGENTS.md 的 AUTO 段 | 由 `rddf roadmap --update-agent-md` 自动生成 ⇒ 不可手改 |

**README 树**：去掉 dangling 的 `guide/SKILL.md`（ADR-0063 已归档）、补上 disk 上有而树里缺的
`rdd-session-bootstrap/SKILL.md` 与 `session-lesson-mining/SKILL.md` ⇒ **0 dangling + 0 遗漏**。

## 组 C —— 4 个新守卫（`tests/unit/test_doc_contracts.py`）

| 守卫 | 锁什么 |
|---|---|
| `test_doc_truth_sync_spec_npm_test_assertion_matches_package_json` | D5 与 `package.json::scripts.test` 同向 |
| `test_readme_skills_tree_entries_match_disk` | README 树双向一致（占位符豁免） |
| `test_docs_do_not_hardcode_directory_composition_counts` | 禁硬编码构成/规模计数（AUTO 段 + 豁免清单） |
| `test_migration_guide_fictional_cli_refs_carry_planned_marker` | 迁移指南每处虚构 CLI 引用带 planned 标记 |

**负向验证**（5 个变体全部被抓到）：dangling 条目 ✅ / 遗漏 skill ✅ / 硬编码计数 ✅ /
planned 标记被删 ✅ / D5 反向断言 ✅；且 2 个豁免**不误报**（占位符、skill 计数）。

**守卫在实施中抓到了我漏改的一处**：A7 我最初只改了 D5 的 **bullet**，漏了 **Scenario** 里的
`stderr reminds: "npm test MUST only run bats; pytest is a separate command"` ⇒ 守卫红 ⇒ 已补改。
⇒ 「改写一个 Requirement 必须保证内部自洽」的复现。

## 实施期发现：第一次全量门红（1 项新增失败）

```
GATE_RC=1
新增失败: 1
  + doc_truth_sync: AGENTS.md ADR table lists 0001-0020 with no dup annotation
```

`tests/integration/test_doc_contracts.bats:53` 断言 `AGENTS.md` 出现
`ADR-0001` / `ADR-0010` / `ADR-0019` / `ADR-0020` **字面量**。
组 D 把 `docs/adr/` 行从 `ADR-0001~0053 (53 个 ADR 编号, 54 个实体文件…)` 改成
「编号与数量以 disk 为准」时，**把 `ADR-0001` 这个字面量一起删了** ⇒ 守卫红。

**修法**（保留字面量、只去计数）：
`docs/adr/  # ADR 目录（ADR-0000 模板 + ADR-0001 起；编号与数量以 disk 为准；v2.0.2 重编号 ADR-0013 → ADR-0020）`

⇒ **教训**：name-free 化一个计数，可能连带删掉**别的守卫依赖的字面量**。
改文档前先 grep「这份文档被哪些测试引用」，区分守卫依赖的是**计数**还是**字面量**。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |
| `openspec validate --all --json` | 224 | **224**（新增 0；仅 `doc-truth-sync` 索引位移） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| `pytest tests/unit/` | 3518 | **3522 passed / 3 skipped**（+4 守卫） |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 迁移指南「当前路径」列 | — | **14/14 存在于 disk** |
| README 树 | dangling 1 / 遗漏 2 | **0 / 0** |
| `doc-truth-sync` Requirement 数 | 8 | **7** |

**连带**：`tests/unit/test_spec_requirement_length.py::FROZEN_VERY_LONG` 的 `doc-truth-sync`
索引由 `requirements[6],[7]` 改为 `requirements[5],[6]` —— 退役 Requirement 后序号整体前移 1，
**仍是同两条** Requirement，总数 **62 / 38 spec** 不变（该测试 docstring 明确要求
「在同一提交里更新冻结值并说明」）。

## 回滚凭据

- 整树备份：`/tmp/opencode/specs-backup-dts-<ts>/`（165 份）
- 单文件快照：`/tmp/opencode/dts-before/{spec.md,v1-to-v2.md,README.md,AGENTS.md}`
- 实施脚本：`/tmp/opencode/dts_apply.py` / `dts_apply2.py` / `dts_apply3.py`
  （内容匹配 + `count(old)==1` 断言，可 `--dry-run`）
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述备份是唯一回滚凭据

## 进 tail（本批不处置）

1. **5 个 placeholder Requirement** —— `general/spec.md` 3 个（`general-add-skill-bats-tests` /
   `general-implement-deps-subagent-analysis` / `general-init-adr-directory`）+
   `sync-agents-md-five-stage/spec.md` 1 个 + `sync-package-skills-to-disk/spec.md` 1 个；
   正文是自动生成的模板句，零信息量。
2. **`doc-truth-sync` 的 Requirement 主题划分**（critic 第 2 轮 NIT-1）—— A4 的「历史路径映射」
   挂在 `migration-guide-no-fictional-cli` 名下，主题错位；拆分需再动 `very long` 冻结清单
   + 重新过审 ⇒ 独立立项。
3. **`rddf status` 缺 `review` 状态渲染**（实现缺口）：`_lib/cli/status_cmd.py:58-65` 的
   `_STATUS_ICON` 无 `review` 键（iteration schema 枚举里仍有 `review`），磁盘推导 `:111-117` 只产三态。
4. **`rddf archive` 缺交互确认门**（实现缺口）：`_lib/archive.sh:1025` 无条件
   `openspec archive "$name" --yes` ⇒ 原 Mode C 的「确认先于 archive + `-y` 旁路」语义丢失。
5. `install.sh:27` 与 `_count_skill_files()` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` 旧机制描述 · `rfc-rddf` 的 14 个 `acceptance-N` ·
   62 条 `very long`（冻结）· CI 上 `openspec/` 不存在导致 spec 校验空转
   （本批新增的 2 个 spec 守卫在 CI 上会 **skip** —— 与既有 `requires_general_spec` 同模式）。
