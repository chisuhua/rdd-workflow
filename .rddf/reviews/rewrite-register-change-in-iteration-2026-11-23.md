# rewrite-register-change-in-iteration-spec 台账（2026-11-23）

## 范围

`openspec/specs/register-change-in-iteration/spec.md` 的 **9 条 `acceptance-N` Requirement**
⇒ **退役 2 条元断言 + 改写 6 条**为有语义的契约；`## Purpose` 写实；
新增 **tracked 清单** `tests/unit/spec_form_compliant.json` + 形态守卫
`tests/unit/test_spec_requirement_form.py`；扩展 1 个既有 bats 用例（幂等守卫）。

**本批是 `acceptance-N` 系列的试点**（12 份 spec / 218 条中的 1 份）。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 4 SHOULD_FIX + 4 NIT），`mergeable: yes` / `scope_exceeded: false` | 4 SF + 4 NIT **全部采纳** |

### 第 1 轮 finding 处置

| # | finding | 处置 |
|---|---|---|
| **SF-1** | `phase0-approve-is-idempotent` 的 `archived_at` / `archive_commit_sha` 子句**无守卫**（两个 bats 用例只 seed/断言 `tasks_done`/`tasks_total`/`status`/`added_at`）⇒ 该子句核实不了 | **采纳「扩测试」**：`tests/integration/test_phase0_iteration_register.bats` 的幂等用例已扩展为 re-approve 前 seed `archived_at="2026-01-02T03:04:05+00:00"` / `archive_commit_sha="deadbeefcafe"` 并断言二者不变 ⇒ **契约现在有守卫**（实测 7/7 pass）。避免「把一句无守卫的契约冻进主 spec」—— 那正是本系列要消灭的退化形态的变体 |
| **SF-2** | CI structural gate 只挡 **CRITICAL** 级新增 finding（`doctor_main.py:60-61` 注释明示 WARNING 不 fail）⇒ 退役后在 WARNING 级无人看守 | **采纳**：退役结论不变（WARNING 级本来就没有可判定契约），但该精度**写进 AC-10 试点结论**。另注：归档 AC-9 的 category 名 `state-schema` 是**非正式名**，真实名是 `state`（`doctor_main.py:28`） |
| **SF-3** | CI 空转取舍必须落纸面 | **采纳**：清单改为 **tracked 文件** `tests/unit/spec_form_compliant.json` ⇒ CI 可判「schema / 无重复 / 两段不交 / 并集 == 已知全集 / **只增不减**（靠 git 历史）」⇒ 把「有人从 pending 删掉却不 promote」变成 CI 可见。`openspec/` 是否取消 gitignore ⇒ 记 backlog |
| **SF-4** | AC-10 试点结论模板 | **采纳**：台账的试点结论分三格 |
| **NIT-1** | `archive-sync` 的守卫只列了 2 个 | **采纳**：补列 3 个（`marks_status_archived` / `propagates_tasks_done` / `idempotent`）。⚠️ **实读后修正了契约语义**（见下「归档 AC-2 已不准确」） |
| **NIT-2** | `phases-suite` 守卫是 fail-open（`iteration.json` 不存在 ⇒ 打印 `clean` 直接通过） | **采纳**：已标注 |
| **NIT-3** | `iteration-json-problems` 相比归档 AC-4 收窄了（去掉「锁超时」） | **采纳**：显式说明是**收窄而非遗漏**（无守卫 ⇒ 不冻结） |
| **NIT-4** | `state-schema` 名错误 | **采纳**：见 SF-2 |

## 归档 AC-2 已不准确（实读发现）

归档 AC-2 说「不再返回 `"missing from iteration.json"` warning」——
**那个字符串全仓不存在**（`grep` 零命中），且实现已改成**磁盘自动恢复**：

| 情形 | 实际行为 | 守卫 |
|---|---|---|
| entry 存在 | 更新（status→`archived` + `archived_at`；`tasks_done` 传播；重复调用不覆写 `archived_at`） | `marks_status_archived` / `propagates_tasks_done` / `idempotent` |
| entry 缺失但磁盘有 archive 目录 | **自动重建 entry**（status=`archived`），**不报 warning** | `missing_entry_recovers_via_disk` |
| `iteration.json` 整个不存在 | 返回 warning，**不抛** | `missing_iteration_returns_warning` |

⇒ 新契约按**实现的真实行为**写（5 个 Scenario，逐条有守卫），而不是照抄归档 AC。

## 改写清单（9 → 6）

| 归档 AC | 处置 | 新 Requirement 名 | 守卫 |
|---|---|---|---|
| 1 | 改写（**剔除后半句**） | `phase0-approve-registers-change-in-iteration` | `phase0: approve registers the change in iteration.json` |
| 2 | 改写（语义按实现修正） | `archive-sync-updates-registered-change`（5 Scenario） | `test_archive_iteration_sync.py` 的 5 个测试 |
| 3 | 改写 | `phase0-approve-is-idempotent` | `phase0: registering is idempotent and preserves existing fields` + `phase0: re-approving does not downgrade an entry that is already under way` |
| 4 + 5 | **合并**改写 | `iteration-json-problems-do-not-block-approve`（3 Scenario） | `phase0: missing iteration.json warns, keeps exit 0 and creates no file` / `...corrupt...` / `...schema-invalid...` |
| 6 | 改写 | `dispatch-quick-does-not-register-change` | `phase0: dispatch-quick (choice=5) does not register a change` |
| 7 | 改写 | `phases-suite-leaves-repo-iteration-untouched` | `test_rdd_builder_phases.bats:131` |
| 8 | **退役** | — | 元断言（「既有行为不回归」不是能力契约） |
| 9 | **退役** | — | 相对断言（「无**新增** finding」依赖基线）；CRITICAL 级由 CI structural gate 持续保证（`roadmap-feature` = `doctor_main.py:74`、`state` = `:70`，均 blocking） |

⚠️ **AC-1 后半句被剔除**：「`rddf status <name>` 能从磁盘列出该 change」—— `rddf status`
**不读 `iteration.json`**（`_lib/cli/status_cmd.py:26-31` 模块 docstring「No `iteration.json`
involvement」）⇒ change 目录落盘即被列出 ⇒ 该子句**与本 change 无关**
（那是 `rddf-status-based-on-improvements` 的成果）。

⚠️ **AC-4 + AC-5 合并**：两条的守卫分别是「缺失 ⇒ warn + exit 0 + 不建文件」与「缺失 ⇒ 不建文件」
—— **同一条 bats 用例** ⇒ 拆成两条 Requirement 会让同一测试背两条契约 ⇒ 合并为一个
Requirement 的 3 个 Scenario（缺失 / 损坏 / schema-invalid）。

## 组 D —— 守卫（形态判据 + tracked 清单）

**`tests/unit/spec_form_compliant.json`（tracked）**：
`compliant` = 1 份 · `pending` = 11 份 · `class_total` = 12。

**`tests/unit/test_spec_requirement_form.py`（5 个测试）**：

| 判据 | 内容 | CI 可判 |
|---|---|---|
| ① | 清单 schema / 无重复 / 两段不交 / **并集 == 已知全集 12 份** / `compliant` 非空 | ✅ |
| ② | `compliant` **只增不减**（`git show HEAD:tests/unit/spec_form_compliant.json` 对比） | ✅ |
| ③ | `compliant` 里不得再有 `### Requirement: acceptance-N` | ❌（需 openspec/） |
| ④ | `compliant` 里不得再有恒真 WHEN（`the change is applied` 之类） | ❌（需 openspec/） |
| ⑤ | `pending` 里的 spec **确实**还是 acceptance-N 形态（否则清单腐化） | ❌（需 openspec/） |

**判别力（负向验证）**：插入 `acceptance-N` Requirement 名 ✅抓到 / 插入恒真 WHEN ✅抓到。

⚠️ **CI 空转的取舍（落纸面）**：形态判据 ③④⑤ 需要 `openspec/specs/`，而 `openspec/` 整树
gitignore（`git ls-files openspec/` = 0）⇒ **CI 上 skip** ⇒ 本系列的**内容级**防回归能力
本质上是**本地态**的；**清单级**（①②）才有 CI 牙齿。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 该 spec 的 `acceptance-N` Requirement 数 | 9 | **0** |
| 该 spec 的恒真 WHEN 数 | 9 | **0** |
| 该 spec 的 Requirement 数 | 9 | **6** |
| `openspec validate register-change-in-iteration` | 1 条 Purpose WARNING | **无 WARNING** |
| `openspec validate --all --json` issue（**准确基线**） | 221 | **220**（新增 0；消失 1 条 Purpose WARNING） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |
| `pytest tests/unit/` | 3529 | **3533 passed / 4 skipped**（+4 守卫 +1 skip） |
| `ruff check skills/_lib/` | 绿 | **绿** |
| `bats test_phase0_iteration_register.bats` | 7/7 | **7/7**（幂等用例已扩展） |

**准确基线的重建**：`openspec/` 整树 gitignored ⇒ 无 git diff 可比。改前内容由
**归档 change 的 delta**（`openspec/changes/archive/2026-11-17-register-change-in-iteration/specs/`
—— 该 spec 就是那个 change 归档时创建的）精确重建 ⇒ 重建脚本
`/tmp/opencode/rebuild_baseline.py`，基线树 `/tmp/opencode/specs-baseline-rci/`。

## 回滚凭据

- 基线树：`/tmp/opencode/specs-baseline-rci/`（165 份，改前状态）
- 改后 spec：`openspec/specs/register-change-in-iteration/spec.md`
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述基线是唯一回滚凭据

## AC-10 试点结论（三格）

### ① 工作量基线

| 指标 | 实测 |
|---|---|
| 1 份 spec（9 条 Requirement）的**调查**（读守卫 + 逐条核实 + 读归档原文） | ≈ 25 min |
| 1 份 spec 的**改写**（含 Purpose + 6 条 Requirement + 11 个 Scenario） | ≈ 20 min |
| **守卫 + tracked 清单**（一次性，后续每份只加一行清单） | ≈ 40 min（一次性） |
| **代码侧补守卫**（扩展幂等用例，让 `archived_at`/`archive_commit_sha` 有背书） | ≈ 10 min（一次性） |
| ⇒ **每份 spec 的边际成本**（第 2 份起） | **≈ 30–45 min** |
| ⇒ **剩余 11 份的总成本** | **≈ 6–9 h**（可拆 11 批，每批 1 份） |

### ② 全量化路径

1. **清单逐批 promote**：每批改 1 份 spec → 把它从 `pending` 移到 `compliant`（判据 ①② CI 可见）。
2. **判据 ①②（清单级）始终有 CI 牙齿** ⇒ 「清单停滞 / 从 pending 删掉不 promote」立刻红。
3. **形态判据 ③④⑤ 仍是本地态** ⇒ 若要内容级 CI 牙齿，唯一路径是
   **取消 `openspec/` 的 gitignore**（`git.openspec_tracked=true`）—— 那是**更大的决策**，
   本系列不擅自做 ⇒ 记 backlog。
4. **退役 vs 改写的分流判据**（本批验证过的）：
   - 该 Requirement 的**正文是否指向真实存在、可核实的机制**？
     - 否（`acceptance-8` 的「别退化」/ `acceptance-9` 的「无新增 finding」）⇒ **退役**
       （元断言、相对断言 ⇒ 不是能力契约）
     - 是 ⇒ **改写**，且每条断言必须能指到**一个具体的守卫测试名**
   - 归档 AC 的**文字**不可信（AC-2 引用的字符串已不存在）⇒ **必须实读实现与守卫**再写契约

### ③ 退役 vs 改写取舍结论

**改写优于退役**，但**有前提**：

| 条件 | 结论 |
|---|---|
| 能力的机制**仍在**，且有**逐条可机判的守卫** | **改写**（本批 6 条都是） |
| 断言是**元断言**（「别退化」）或**相对断言**（「无新增 finding」） | **退役**（本批 2 条） |
| 能力**已消失**（机制不存在） | **退役**（若正文引用的字符串/文件全仓不存在 ⇒ 该断言已不准确） |
| 机制在但**无守卫** | **先补守卫**（本批 `archived_at`/`archive_commit_sha` 就是这样处理的）；补不了才**收窄契约** |

⇒ **退役不会丢内容**：原文永远在 `openspec/changes/archive/<date>-<name>/proposal.md` 的
`## Acceptance` 段（实测 `2026-11-17-register-change-in-iteration/proposal.md:64-77`）。

## 进 tail（本批不处置）

1. **剩余 11 份 `acceptance-N` spec**（`env-bootstrap` 44 · `objective-tracking` 33 ·
   `fix-skill-post-install-discoverability` 31 · `fix-bats-per-file-timeout` 22 ·
   `rddf-layout-manifest` 16 · `fix-script-project-root-anchoring` 16 ·
   `rfc-rddf-project-yaml-config-i10` 14 · `fix-phase3-cleanup-wiring` 13 ·
   `fix-p3-verifier-gate` 12 · `fix-worktree-archive-path` 10 · `fix-flow-drift-batch-1` 9）
   ⇒ 按 AC-10 ① 的基线（约 30–45 min/份）立项，拆 11 批。
2. **`openspec/` 是否取消 gitignore**（`git.openspec_tracked=true`）—— 决定本系列的形态守卫
   能否获得 CI 牙齿 ⇒ 更大的决策，不在本批。
3. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）：`_lib/archive.sh:1025` 无条件
   `openspec archive "$name" --yes` ⇒ 会卡住 `rdd-builder` P3 → `archive.sh` 的无 TTY 自动化链路。
4. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**（165 份中 150 份命中）。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）·
   CI 上 `openspec/` 不存在导致 spec 校验空转。
