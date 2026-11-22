# rewrite-acceptance-form-batch-3 台账（2026-11-23）

## 范围

`acceptance-N` 系列**第 3 批**（3 份 spec / 34 条 AC）⇒ **15 条契约 + 19 条退役**；
清单 promote 4 → **7** 份。

## 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（plan 2 BLOCKER + 3 SHOULD_FIX + 1 NIT），`mergeable: no` | 2 BLOCKER **均成立**，逐条修正 |

### 第 1 轮 2 BLOCKER 处置

| # | finding | 处置 |
|---|---|---|
| **BLOCKER-1** | `untracked-openspec-forces-the-serial-ship-mode` 与实现**相反** —— 我写「no CLI flag or environment variable SHALL override it」，但实现优先级是 **CLI flag > project.yaml > env**（`complete-project-yaml-config-gaps/spec.md:213` 同款），且**我自己引的守卫** `test_ship_execution_mode_reads_project_yaml.bats` 的 `CLI flag --parallel wins over project.yaml` **就在反证它**；措辞又与同文件 `:198` `guide-ship-phase-1-detect-lightweight`（`openspec_tracked` SHALL NOT influence the execution mode）二义 | **该 Requirement 退役，不补回**（理由见下「组 C-2」）。教训：**改写时不能照抄归档 AC 的措辞** —— 归档 AC 描述的是 v2/v3 时期的行为，v4 已反证 |
| **BLOCKER-2** | 处置计数与分类错误：退役 18 → 实为 **19**；`rfc-rddf` 实为「改写 3 + 退役 11」；组 C 把 `acceptance-3` 记成「丢条目的痕迹」**是错的** | 计数全部更正；组 C 更正为「**batch7b2（2026-11-22 归档）§D 有意删除**」的出处，并**回应**其理由（不再套「有守卫就补回」的默认规则） |

### 第 1 轮 3 SHOULD_FIX + 1 NIT 处置

| # | finding | 处置 |
|---|---|---|
| SF-1 | `verifier-can-delegate` 的「verdict 写入缓存」从句**无守卫**（hook-provider 的 3 个用例只断言 rc 映射与白名单拒绝） | **补列** `tests/unit/test_rdd_verify_cmd.py::test_run_one_change_passed_writes_cache_and_state`（行为为真：`_lib/cli/rdd_verify_cmd.py:302-307` 的 provider 无关写缓存路径） |
| SF-2 | `phase2-fallback-worktree` 的正向从句「worktree 建在 `PROJECT_ROOT`」**无守卫**（`test_phase_root_anchoring.bats:138-148` 只断言真仓零 worktree，**不断言** `$status`、**不断言**假仓 worktree 建成 ⇒ 脚本提前失败照样绿） | **收窄**为守卫实际断言的内容：「the working directory's repository SHALL NOT gain a worktree for that change」 |
| SF-3 | 豁免 Scenario 未显式化 AC-F 的变异语义 | **补一句**「removing that exemption SHALL make the gate report the line again」（原由两个用例隐式联合覆盖） |
| NIT | batch-2 尾注的待办计数口径不一致（历史 note 噪声） | 记 backlog，不动 |

### 第 1 轮 focus 结论（要点）

- **focus 1（19 条退役）**：两条「无守卫」退役**成立** —— critic 核出 AC-3 的近邻
  `test_lightweight_branch_and_archive.bats:407` 断言的是 `cleanup_worktree_and_branch`
  的失败语义，与 `post_archive_cleanup` 无关；「过程性」「里程碑过程」两类**够格退役**
  （其内容已固化：ADR-0036 已存在、里程碑早已合入；留在 spec 层只会重建本系列正在消除的元断言形态）。
- **focus 2（AC-G2 补回）**：**恰当，且不应与负例合并** —— 归档 delta 只有 13 条
  （14 条 AC ⇒ 13 条）⇒ AC-G2 是**归档工件缺陷**，不是「有意不纳入」。
- **focus 3（守卫背书）**：15 条里 14 条**覆盖充分**；`post-archive-cleanup-works-without-a-project-lib`
  的担忧**不成立**（`test_post_archive_cleanup_guard.bats:60-71` 不只断言「能定位」——
  它还 grep 了 `improvement-approved.md` 中已移入「已实施」的行并断言无 WARN）。
- **focus 4（编号断裂）**：critic 指出我的诊断**错了** ⇒ 已更正（见「组 C-2」）。

## 组 C —— 两处「spec 里没有的归档 AC」，处置**相反**

**C-1 `fix-script-project-root-anchoring` / AC-G2 ⇒ 补回**：
归档 delta **只有 13 条** Requirement（14 条 AC ⇒ 13 条 delta）⇒ AC-G2 在生成 delta 时整丢了
⇒ **归档工件缺陷**，不是「有意不纳入」；守卫真实存在
（`test_phase_root_anchoring.bats` → `gate: 新 check 单独跑在本仓 ⇒ exit 0（修完之后）`）
⇒ 补回为 `isolation-gate-passes-on-this-repository`（**不**与负例合并：正例自检 vs 负例拒绝是两个独立契约）。

**C-2 `rfc-rddf-project-yaml-config-i10` / `acceptance-3` ⇒ 不补回，退役**：
该条**不是**「丢条目的痕迹」——
`openspec/changes/archive/2026-11-22-rewrite-spec-residue-batch7b2/proposal.md` §D 记录了
**有意删除**，理由是「判据『`git.openspec_tracked: false` 时强制轻量模式』**被 v4 反证** ——
`_lib/builder_deps.py:42 decide_execution_mode(file_count, task_count, risk_keywords)`
**不看** `git.openspec_tracked`；同主题的**正确**判据已存在于 `complete-project-yaml-config-gaps`」。
⇒ 正确判据由 `complete-project-yaml-config-gaps` 独家持有：
`ship-execution-mode-project-yaml-priority`（`:213`，优先级 CLI > project.yaml > env）
+ `guide-ship-phase-1-detect-lightweight`（`:198`，`openspec_tracked` SHALL NOT influence
the execution mode）⇒ 本 spec **不重复持有**。

## 34 条 AC 的分流

### `fix-phase3-cleanup-wiring`（7 → 5）

| AC | 处置 | 新 Requirement 名 | 守卫（`tests/integration/test_post_archive_cleanup_guard.bats`） |
|---|---|---|---|
| 1 | 改写 | `post-archive-cleanup-library-fails-loudly-when-executed-directly` | `cleanup: executing the library directly fails loudly instead of doing nothing` |
| 2 | 改写 | `post-archive-cleanup-warns-when-state-sh-is-missing` | `cleanup: warns when state.sh cannot be found anywhere` |
| 3 | **退役** | — | **无守卫**（近邻 `test_lightweight_branch_and_archive.bats:407` 断言的是 `cleanup_worktree_and_branch`，与 `post_archive_cleanup` 无关） |
| 4 | 改写 | `post-archive-cleanup-syncs-improvement-approved` | `cleanup: the correct call syncs improvement-approved.md (e2e)` |
| 5 | 改写 | `post-archive-cleanup-is-idempotent` | `cleanup: repeated calls stay idempotent (no duplicate rows)` |
| 6 | 改写 | `post-archive-cleanup-works-without-a-project-lib` | `cleanup: global-install shape (no project _lib) still syncs via self-discovery` |
| 7 | **退役** | — | 元断言（全绿） |

### `fix-script-project-root-anchoring`（13 → 7）

| AC | 处置 | 新 Requirement 名 | 守卫（`tests/integration/test_phase_root_anchoring.bats`） |
|---|---|---|---|
| A + B | **合并**改写 | `phase1-plan-reads-and-writes-under-project-root`（2 Scenario） | `phase1_plan: PROJECT_ROOT 指向假仓 ⇒ 读假仓的 proposal（改前报 not found）` + `phase1_plan: 写落点跟随 PROJECT_ROOT ⇒ 真仓零写入` |
| C | 改写 | `phase1-5-reads-plan-handoff-from-project-root` | `phase1_5_deps: legacy plan-handoff 从 PROJECT_ROOT 读（真仓那份作对照）` |
| D | 改写（**SF-2 收窄**） | `phase2-fallback-worktree-is-created-under-project-root` | `phase2: lightweight 降级回 worktree 时，worktree 建在 PROJECT_ROOT（不是 cwd）` |
| E + F + G | **合并**改写（**SF-3 补变异句**） | `isolation-gate-rejects-unanchored-repo-paths`（3 Scenario） | `gate: 未锚定的 openspec/changes 相对路径 ⇒ exit 1 且报 file:line` + `gate: 行尾 # isolation-ok 理由 ⇒ 放行` + `gate: 同一行同时有未锚定与已锚定 token ⇒ 仍必须报（token 级，非行级）` |
| **G2** | **补回**（组 C-1） | `isolation-gate-passes-on-this-repository` | `gate: 新 check 单独跑在本仓 ⇒ exit 0（修完之后）` |
| H | 改写 | `isolation-ok-exemptions-are-budgeted-at-two` | `gate: 本仓的 isolation-ok 豁免恰好 2 条，且理由都 ≥10 字` |
| I | 改写 | `isolation-gate-bypass-is-audited` | `gate: bypass 可计量（打印 skipped + 写 bypass 审计）` |
| J | **退役** | — | **无守卫**（11 个用例里没有「cwd == PROJECT_ROOT 时 `tasks.md` 逐字节比对」） |
| K / L / M | **退役** | — | 元断言（既有测试 / 全量门）+ 相对断言（「不改 CI」） |

### `rfc-rddf-project-yaml-config-i10`（14 → 3）

| AC | 处置 | 新 Requirement 名 | 守卫 |
|---|---|---|---|
| 1 | 改写 | `adr-catalog-honours-a-project-configured-pattern`（2 Scenario） | `tests/unit/test_adr_catalog.py::test_scan_adr_catalog_three_digit_pattern` + `::test_scan_adr_catalog_pattern_override_backward_compat` |
| 2 | 改写 | `arch-discovery-reads-the-configured-adr-directory`（2 Scenario） | `tests/integration/test_discover_arch_artifacts_uses_project_yaml.bats` + `test_arch_discovery_contract.bats` |
| **3** | **退役**（组 C-2） | — | batch7b2 已签批删除 + 判据被 v4 反证 + 正确判据已在 `complete-project-yaml-config-gaps` |
| 4 | **退役** | — | **与实现相反**（BLOCKER-1）⇒ 同上，正确判据由 `complete-project-yaml-config-gaps` 持有 |
| 5 | 改写 | `verifier-can-delegate-to-an-external-hook`（2 Scenario） | `tests/integration/test_rdd_verifier_hook_provider.bats`（rc 映射 + 白名单拒绝）+ `tests/unit/test_rdd_verify_cmd.py::test_run_one_change_passed_writes_cache_and_state`（缓存写入，SF-1 补列） |
| 6 | **退役** | — | 相对断言（零回归） |
| 7 / 8 / 9 / 10 | **退役** | — | 元断言（单测通过 / 新增场景全绿） |
| 11 | **退役** | — | 元断言（全量门全绿后才允许 archive） |
| 12 / 13 | **退役** | — | 过程性（新建 ADR / 引用相关 ADR） |
| 14 / 15 / 16 | **退役** | — | 里程碑过程（M1 单独 PR / M2-M4 可并行 / M5 合并） |

## 清单 promote

`tests/unit/spec_form_compliant.json`：`compliant` 4 → **7** 份 · `pending` 8 → **5** 份。

## 验证

| 项 | 改前 | 改后 |
|---|---|---|
| 3 份的 `acceptance-N` Requirement 名 | 34 | **0** |
| 3 份的恒真 WHEN | 34 | **0** |
| 3 份的 Requirement 数 | 34 | **15**（5 + 7 + 3） |
| `openspec validate <3 份>` | 各 1 条 Purpose WARNING | **无 WARNING** |
| `openspec validate --all --json` issue（**准确基线**） | 217 | **214**（新增 0；消失 3 条 Purpose WARNING） |
| `very long` | 62 | **62** |
| `validate --all` ERROR | 11 | **11** |
| 残留扫描器（未豁免 / 含已豁免） | 0/0/0 · 303/159/41 | **不变** |
| `pytest tests/unit/` | 3534 | **3534 passed / 3 skipped** |
| `ruff check skills/_lib/` | 绿 | **绿** |
| 相关 bats（4 个文件，28 例） | — | **全绿** |

**准确基线的重建**：`openspec/` 整树 gitignored ⇒ 无 git diff 可比。3 份 spec 各由**唯一的**归档
change 以 `## ADDED Requirements` delta 创建 ⇒ 改前内容由 delta 精确重建；
⚠️ `rfc-rddf` 还要**再删一条** `acceptance-3`（batch7b2 §D 有意删除）⇒ 归档 delta 是 15 条、
改前 live spec 是 14 条 ⇒ 重建脚本 `/tmp/opencode/rebuild_baseline_b3.py`，
基线树 `/tmp/opencode/specs-baseline-b3/`。

## 回滚凭据

- 基线树：`/tmp/opencode/specs-baseline-b3/`（165 份，改前状态）
- 清单改前：`git show HEAD:tests/unit/spec_form_compliant.json`
- ⚠️ `openspec/` 整树 gitignored ⇒ spec 改动**无 git diff**，上述基线是唯一回滚凭据

## 实施期教训

1. **不能照抄归档 AC 的措辞 —— 它描述的是过去。** 归档 AC 说「`git.openspec_tracked: false`
   时强制轻量模式」，我改写时写成「强制 serial 且**不可覆盖**」⇒ **与实现相反**
   （实现是 CLI flag 优先）⇒ 而且**我自己引的守卫就在反证它**。
   ⇒ 改写必须**实读实现 + 守卫**，而不是润色归档文字。
2. **「spec 里没有」有两种成因，处置相反**：
   - **归档工件缺陷**（AC-G2：14 条 AC ⇒ 13 条 delta）⇒ **补回**（有守卫 + 内容仍有效）；
   - **已签批删除**（`acceptance-3`：batch7b2 §D 有意删除，理由充分）⇒ **不补回**。
   ⇒ 判据要看**归档 delta 与 live spec 的差异记录**，不能只看「有没有守卫」。
3. **退役理由不准确 ≠ 退役结论错**（第 2 批已学），但**这次相反**：退役结论也是错的
   （我补回了一条已被签批删除且被 v4 反证的判据）⇒ **两个方向都要核**。
4. **合并多条 AC 到一条 Requirement 时，要逐个 Scenario 核守卫强度** —— SF-2 就是合并后
   某条正向从句没有守卫（守卫只断言「真仓零 worktree」，脚本提前失败照样绿）。
   ⇒ 收窄到守卫实际断言的内容。

## 进 tail（本批不处置）

1. **剩余 5 份 `acceptance-N` spec**（`env-bootstrap` 44 · `objective-tracking` 33 ·
   `fix-skill-post-install-discoverability` 31 · `fix-bats-per-file-timeout` 22 ·
   `rddf-layout-manifest` 16）⇒ 按基线 ≈3–5 h，可拆 2 批（3 + 2）。
2. **`openspec/` 是否取消 gitignore** —— 用户已定「暂不决定，继续现状」。
3. **`rddf archive` 缺交互确认门**（行为变更，需用户拍板）。
4. **150 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` 占位**。
5. `doc-truth-sync` 的 Requirement 主题划分 · `install.sh:27` 的 `deprecated:` 口径分叉 ·
   `docs/improvement-approved-format.md:3` · 62 条 `very long`（冻结）。
6. batch-2 尾注的待办计数口径不一致（历史 note 噪声）。
