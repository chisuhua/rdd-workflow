# fix-rddf-status-icon-coverage 台账（2026-11-22）

## 范围

change 生命周期状态的**两个词汇域**对齐 + `archived_partial` 的归档口径统一 + 6 个守卫。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（plan 1 BLOCKER + 2 SF + 1 NIT；build 0 BLOCKER），`mergeable: no` | BLOCKER 成立 ⇒ **整篇重写**（不是修补） |
| 2（复审） | **REJECT**（plan 1 BLOCKER + 3 SF + 2 NIT；build 1 BLOCKER），`mergeable: no` | 2 BLOCKER 均成立 ⇒ 按其结论修；critic 明示「修完可直接实施，**无需第 3 轮**」 |

**评审预算已用满 2 轮** ⇒ 第 3 轮须用户明确批准。

### 第 1 轮 BLOCKER —— 我的「活缺陷」判断是错的

我原 proposal 断言「`rddf status` 把 `proposed` / `review` 渲染成 `?`」并据此设计 AC-2。
critic 核出两个事实错误：

1. **`rddf status` 不读 `iteration.json`** —— `_lib/cli/status_cmd.py:26-30` 的模块 docstring
   明写「**No `iteration.json` involvement**」⇒ Mode A/Mode B 的状态一律来自
   `_disk_change_status()`（`:109-118`，值域 **3** 值：`in_worktree`/`committed`/`planned`）
   ⇒ `proposed`/`review`/`archived_partial` **永远到不了** `_STATUS_ICON.get(status, "?")`
   ⇒ 我的 AC-2 **修复前后都平凡满足**，且 prescribed 的实测永远不可能通过；
2. **`builder_cmd.py:30-35` 的 `PHASES_SCRIPT_MAP` 是 phase→脚本文件名后缀映射**
   （`:133`/`:221` 的 `f"{phase}_{PHASES_SCRIPT_MAP[phase]}.sh"`）⇒ `phase2.5 → review`
   指的是 `phase2.5_review.sh`，**不是状态写入方**。

⇒ 我原计划给 `status_cmd._STATUS_ICON` 补 `proposed`/`review`/`archived_partial` —— 那是
**永不命中的死键**，写进 spec 就是**造死契约**。

### 重写后的关键认知：状态集合有**两个词汇域**，不是一个

| 域 | 真源 | 派生集合 | 值域 |
|---|---|---|---|
| **iteration.json 域** | `_lib/schemas/iteration_schema.json` 的 `status` enum（**tracked ⇒ CI 有牙齿**） | `_VALID_STATUSES` · `renderer._STATUS_ICON` · `renderer._STATUS_ICON_PLAIN` | **7**：`planned` `proposed` `in_worktree` `review` `completed` `archived` `archived_partial` |
| **disk-derived 域** | `_disk_change_status()` 值域 ∪ {`:257` 硬编码的 `archived`, 兜底 `unknown`} | `status_cmd._STATUS_ICON` | **6**：`planned` `in_worktree` `completed` `archived` `committed` `unknown` |

`committed` 在 disk 域但**不在** enum 内 ⇒ 两域本就不同 ⇒ `status_cmd.py:53` 的
「与 dashboard 同步」**从一开始就不成立**。

### 第 2 轮 2 BLOCKER 处置

| # | finding | 处置 |
|---|---|---|
| **BLOCKER-1** | 我的「现状（实测）」块写 `_STATUS_ICON` 有 5 key，实际 6（自相矛盾）；且按我自己的死键哲学，`completed` 是死键 ⇒ 判据 ④「恰好等于 5 值」第一天就抓红 ⇒ **AC-1 在只实施组 A 的前提下不可能通过**，要过必须有一个**未声明的**改动（删 `completed`） | **不改代码**：判据 ④ 改为 **6 值**（`completed`/`unknown` 作为**防御键** —— status 不读 iteration.json ⇒ 当前产不出，但删掉会让将来的这些状态渲染成 `?`）。判据 ④ 的**死键检测能力不受影响**（仍能抓住「多出 6 值以外的键」）⇒ 负向验证已实测 |
| **BLOCKER-2** | D2 漏了 plain 渲染路径：`renderer.py:806-807`（`_p_section_changes`，`_STATUS_ICON_PLAIN` ASCII 路径）与 `:455-456`（emoji 路径）**逐行同构** ⇒ 只改前者时 plain 模式下 `archived_partial` 仍归入 active ⇒ AC-3 的目标场景在 plain 路径依然失败，且若只断言终端路径会**平凡满足** | **采纳**：D2 扩为覆盖两条路径；AC-3 显式声明覆盖 terminal + plain |

### 第 2 轮 3 SHOULD_FIX + 2 NIT 处置

| # | finding | 处置 |
|---|---|---|
| SF-1 | `_lib/roadmap_sprint.py:50-54` 是**第三张**同域图标表，且 `:114-115` 的过滤同样硬编码 `== "archived"`；其 `in_worktree` 用 🔄 与另两表的 🔧 不一致 | ① `roadmap_sprint.py:115` **纳入 D2**；② 该表**不纳入**守卫判据 ②（它只覆盖 **active 集合的 3 个状态**，⊇ 判据对它不适用）；③ 🔄 与 🔧 的差异**有意保留**（sprint 表与 roadmap phase 图标 `in_progress: 🔄` 同族）⇒ 判据 ⑤ 只跨两张 emoji 表 |
| SF-2 | D1 放宽后读路径的 misclassification 面比设计列的大 | **采纳**：D2 清单**扩到 14 处**；另发现 critic 未列的 5 处（`discover_ship_changes.py:113` · `skills/feature/scripts/feature_view.py:318` · `skills/rdd-doctor/scripts/checks/plan_tdd_check.py:74` · `skills/reconcile-iteration.sh:110` / `:147`） |
| SF-3 | `renderer._STATUS_ICON` 实为**双域共用表**（iteration.json 7 值 + improvement 生命周期中文键）⇒ 「各有各的真源」对它不精确 | **采纳**：判据 ②③ 用 **⊇**（天然容忍 improvement 键）；守卫注释注明「双域共用表」 |
| NIT-1 | `renderer._STATUS_ICON` 相对自身域也有死键（`committed`/`done`/`unknown`）⇒ 注释里说明，防下一个人按 ④ 的严格逻辑去「清理」 | **采纳**：守卫文件注释写明「⊇ 允许 dashboard 别名与 improvement 键」 |
| NIT-2 | 判据 ④ 的 6 值集合是测试内的字面量（disk 域的第二个文字真源）—— 值得一句注释 | **采纳**：注释写明这是**有意为之**的耦合（fail-closed：词汇域扩张时强制同 PR 改守卫） |

## 实施内容（17 处代码改动 / 11 个文件 + 1 个新测试文件）

| # | 位置 | 改什么 |
|---|---|---|
| D1 | `_lib/iteration/schema.py` | `_VALID_STATUSES` 补 `archived_partial`（6 → 7 值，与 schema enum 一致） |
| D2 | **14 处** archived 过滤 | `== "archived"` → `in ("archived","archived_partial")`；`!= "archived"` → `not in (...)` |
| D3 | `_lib/dashboard/renderer.py` 两张图标表 | 补 `archived_partial` → `📦` / `-` |
| D4 | `_lib/cli/status_cmd.py:53` | 注释改为说明**两表服务不同词汇域**（本表 = disk-derived；dashboard 那张 = iteration.json） |

**D2 清单（改）**：`renderer.py:455/456`（emoji 路径）· `:806/807`（plain 路径）·
`store.py:433`（`list_archived`）· `:603`（`feature_progress` done 计数）·
`render.py:66`（`rddf iteration` archived 计数）· `roadmap_sprint.py:115` ·
`workflow_synthesizer.py:312`（archived 计数）/ `:557`（active 计数）·
`discover_ship_changes.py:113` · `skills/feature/scripts/feature_view.py:318` ·
`skills/rdd-doctor/scripts/checks/plan_tdd_check.py:74` ·
`skills/reconcile-iteration.sh:110` 与 `:147`（jq）

**D2 清单（不改，理由进守卫豁免清单）**：
`_lib/cli/status_cmd.py:222`（disk-derived 域）·
`_lib/iteration/repair.py:114`（`archived_partial → archived` 的**升级方向**是良性的）·
`_lib/roadmap_state.py:737`（`frag.status` 是 feature-fragment 状态，不是 change 状态）

## 组 B —— 守卫（`tests/unit/test_iteration_status_coverage.py`，6 个测试 / 7 条判据）

| 判据 | 内容 |
|---|---|
| ① | `_VALID_STATUSES`（集合）**==** schema enum |
| ② | `renderer._STATUS_ICON` ⊇ enum，每个值非空（⊇ 容忍双域共用表的 improvement 键 + 别名键） |
| ③ | `renderer._STATUS_ICON_PLAIN` ⊇ enum，每个值非空 |
| ④ | `status_cmd._STATUS_ICON` 的 key 集**恰好等于 6 值**（`completed`/`unknown` 为防御键） |
| ⑤ | 两域交集 `{planned, in_worktree, archived}` 在两张 emoji 表里 emoji 相同 |
| ⑥ | 全仓 `== "archived"` / `!= "archived"` 字面比较点**必须**同时识别 `archived_partial`（3 条显式豁免 + 配套测试断言「豁免仍然存在」） |

**判别力**：守卫正是在改前备份的树上会红的那个东西（`archived_partial` 不可写 + 14 处口径不一）。
**负向验证（5 变体，逐个注入并复测）**：删 `_VALID_STATUSES` 的一个值 ✅ /
给 `status_cmd._STATUS_ICON` 加死键 `proposed` ✅（**这正是本批初版的错误做法**）/
把 renderer 的 archived 过滤退回 `== "archived"` ✅ /
删 renderer 图标表的 `archived_partial` ✅ / 改坏跨表 emoji 一致性 ✅。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| `store.set_status(..., "archived_partial")` | 抛 ValueError | **成功**（status 落为 `archived_partial`） |
| `store.list_archived()` 认 partial | ❌ | **✅**（实测 `['a','b']`） |
| `store.feature_progress()` done 计数认 partial | ❌ | **✅**（`{'b': (1,1)}`） |
| renderer 两张图标表的 partial | ❌ → `?` | **✅** `📦` / `-` |
| 全仓 archived 字面比较点未对齐 | 14 处 | **0** |
| `status_cmd._STATUS_ICON` key 集 | 6 | **6（不变）** |
| `pytest tests/unit/` | 3523 | **3529 passed / 3 skipped**（+6 守卫） |
| `ruff`（CI 范围 `skills/_lib/`） | 绿 | **绿** |
| `ruff`（我改的 11 个文件） | 3 errors | **3 errors（全是既有，无新增）** |
| 相关既有测试（status/dashboard/iteration/synthesizer/sprint） | — | **240 passed** |
| `openspec validate --all` issue | 224 | **224（不变，本批不改 spec）** |
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |

## 回滚凭据

- 文件快照：`/tmp/opencode/rsic-before/`（11 个文件）
- 实施脚本：`/tmp/opencode/rsic_apply.py`（内容匹配 + `count(old)==expect` 断言，可 `--dry-run`）
- 新测试文件：`tests/unit/test_iteration_status_coverage.py`（可删）

## 实施期教训

1. **「能渲染成 `?`」不等于「这个状态会走到渲染点」。** 我第一版断言「`rddf status` 把
   `proposed`/`review` 渲染成 `?`」—— 但 `rddf status` **不读 iteration.json** ⇒ 那三个状态
   **永远到不了**渲染点 ⇒ 我的 AC **平凡满足**、实测路径**不可能通过**。
   ⇒ 写 AC 前必须先问「**这个状态真的会被产生并流到这里吗**」，而不是「表里没这个键」。
2. **一个域不等于一张表，也不等于一个真源。** 我把 schema enum 当唯一真源、要求所有表 ⊇ enum
   —— 但 `status_cmd` 的表服务的是 **disk-derived 词汇**（含 enum 外的 `committed`）。
   ⇒ 「同一概念在几处出现」≠「它们该有同一个值域」。
3. **死键也是错。** 我原计划给 `status_cmd._STATUS_ICON` 补 3 个 enum 值 —— 那些键
   **永远不会被 `.get()` 命中**。写进 spec 就是造死契约。
   ⇒ 守卫判据 ④ 用「**恰好等于**」而非「⊇」⇒ 死键变成可机判的违规。
4. **同构代码要成对改。** `renderer.py` 的 emoji 路径（`:455-456`）与 plain 路径
   （`:806-807`）**逐行同构** ⇒ 只改一处 ⇒ 另一处的缺陷存活，且若 AC 只断言一处就会
   **平凡满足**。⇒ 守卫判据 ⑥ 用**全仓扫描**（而非逐个断言）⇒ 漏一处就红。
5. **豁免本身也要被守卫。** 3 处「不改」的理由（disk-derived 域 / 升级方向 / fragment 域）
   写进守卫的**豁免清单**，并有配套测试断言「豁免仍然存在」⇒ 豁免不会悄悄过期。

## 进 tail（本批不处置）

1. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）：`_lib/archive.sh:1025` 无条件
   `openspec archive "$name" --yes` ⇒ 会卡住 `rdd-builder` P3 → `archive.sh` 的无 TTY 自动化链路
   （`archive_gate_check` 已在前面当门）。
2. **`acceptance-N` 形态的 218 条 Requirement / 12 份 spec**（正文是真实断言，但 Requirement 名
   无语义、Scenario 名被截断、Scenario 的 WHEN 恒真）⇒ 需方向决策。
3. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**（165 份中 150 份命中）。
4. **`rddf status` 不读 `iteration.json`**：模块 docstring 说明是 per change
   `rddf-status-based-on-improvements` 的决定 ⇒ 不在本批处置；若将来改为读 iteration.json，
   判据 ④ 的 6 值域会变 ⇒ 守卫会红（这是期望行为）。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）·
   CI 上 `openspec/` 不存在导致 spec 校验空转。
