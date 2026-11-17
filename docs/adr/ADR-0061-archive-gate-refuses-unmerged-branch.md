# ADR-0061: 合入门 —— 归档不代劳合并，但未合入不得归档

> **状态**: 已采纳 (2026-11-17)
> **日期**: 2026-11-17
> **决策者**: rdd-workflow maintainer
> **关联 ADR**: ADR-0035（verifier-archive-gate 边界）, ADR-0036（project.yaml 配置源，2026-11-17 修订）, ADR-0024（deps 驱动执行模式）
> **触发来源**: 2026-11-17 第八批 5 项归档过程发现（`git.openspec_tracked=false` 时归档不合并 worktree 分支，却也无人合并 ⇒ 提交被搁浅，而归档报告成功）
> **审稿报告**: `.rddf/reviews/adr-0061-unmerged-branch-2026-11-17.md`（oracle + critic 双审，2026-11-17）

> **术语**：本 ADR 的「**合入门**」= 新增的 `archive_premerge_check`（判定实现分支是否已进默认分支）。
> 仓内既有的「**归档门**」= `archive_gate_check`（AC 验证门）。两者是**不同的门**，文中不混用。

## Context

`git.openspec_tracked=false` 时，归档路径**不合并** worktree 的实现分支 —— 这是两份已采纳 spec 的明文要求：

- `openspec/specs/complete-project-yaml-config-gaps/spec.md`（Requirement `archive-openspec-tracked-skip-git`）：「when set to `false`, SHALL skip `git merge` and `commit_archive_moves` operations, **executing only** `openspec archive` and `mark_iteration_archived`」；
- `openspec/specs/archive-openspec-tracked-skip-commit/spec.md`（Requirement `archive-openspec-tracked-false-branch-cleanup`）：false 分支的执行顺序 SHALL 为 `switch_to_default_branch` → `openspec archive` → `cleanup_worktree_and_branch` → `mark_iteration_archived`。

⇒ 「executing only …」与「顺序 SHALL 为 …」两句把「归档前插入任何新步骤」都排除在外。

**而合并责任无人承担**：

| 事实 | 位置 |
|---|---|
| false 分支里没有合并执行点（合并只存在于 tracked 路径的 `merge_feature_branch`） | `_lib/archive.sh::archive_change` |
| `cleanup_worktree_and_branch` 的失败被 `|| true` 吞掉，归档仍返回 0 | `_lib/archive.sh::archive_change` |
| `git worktree remove` 失败后**仍无条件打印**「✅ Worktree 已删除」 | `_lib/archive.sh::cleanup_worktree_and_branch` |

⇒ **「归档成功」与「代码已进主干」是两件事，而今天前者会在后者为假时成立** —— 对 CI/agent 而言这是最坏的一类静默失败：exit 0 被读作「这批工作已落地」，实际上提交躺在即将被清理的分支上。2026-11-17 本批 5 项全部靠手工 `git merge --no-ff openspec/<name>` 才没丢代码。

**根因是语义混装**：`git.openspec_tracked` 这个开关在 spec 里承担了两件不相干的事：

| 事项 | 与「openspec/ 是否被 git 跟踪」的关系 |
|---|---|
| 跳过 `commit_archive_moves` | **直接相关** —— openspec/ 未跟踪 ⇒ 归档产物没有东西可 commit |
| 跳过 **feature 分支合并** | **无关** —— 代码改动是否进主干，与 openspec/ 目录是否被跟踪毫无关系 |

## Decision

**把两件事解耦，并给「未合入」一个确定的判定点：归档仍然不代劳合并，但未合入时拒绝归档，而不是谎报成功。**

1. **职责解耦**（语义层）：
   - `git.openspec_tracked=false` ⇒ 归档**不执行** `commit_archive_moves`（保持现状，理由仍成立）；
   - 归档**不执行** `git merge`（保持现状）—— 但新增一道**具名判定** `archive_premerge_check`：实现分支未合入默认分支 ⇒ **拒绝归档**，并给出一次到位的指引（可复制的命令 + 显式 opt-in）。
2. **`archive_premerge_check <main_root> <branch> <default_branch> <wt_path>`**，三态返回，**判定顺序与优先级如下**（先跑便宜且确定的判定）：

   | 顺序 | 判定 | 返回 | 说明 |
   |---|---|---|---|
| ⓪ | **前置存在性检查**：分支 ref 是否存在 | 缺失 ⇒ `1`（拒绝） | **必须先于 ①②③**（否则 ②③ 的判定命令在 ref 缺失时「失败」，会被读成 ④ 的放行）。与 `verifier-lifecycle` 的 fail-closed 一致（分支缺失 ⇒ 代码可能已随分支删除而不可恢复）⇒ **默认不放行**；`ARCHIVE_ALLOW_UNMERGED=yes` + reason **仍可覆盖**（语义 = 「我知道分支已不存在，放行」） |
   | ① | worktree 内有**未提交改动** | `1`（拒绝） | 噪声排除：系统自己复制进去的副本（`openspec/changes/<name>/`、`.rddf/plans/<name>.md`）**不算**未提交改动；其余未跟踪文件**算**。**优先级高于「已合入」** —— 改动没提交时谈合入没有意义 |
   | ② | `merge-base --is-ancestor <branch> <default>` 为真 | `0`（放行） | 已合入 |
   | ③ | **内容等价**：`git cherry <default> <branch>` 全部为 `-` | `0`（放行）+ 警告 | patch-id 级判据（squash-merge / rebase 的正确口径）。⚠ **不是** tip-to-tip 的 `git diff --quiet` —— 后者在默认分支有任何无关提交时就会判不等 |
   | ④ | **未合入**（`git cherry` 显示 `+`） | `1`（拒绝） | 实现提交还在分支上，worktree 清理即将把它们删掉 ⇒ 拒绝并给出合入命令 |
   | ⑤ | 其余（**非** git 仓库 / git 异常 / 判定命令失败） | `2`（放行 + 显式警告） | 不因环境异常制造假拒绝。⚠ 与 ⓪ 的区别：⓪ 是「分支确实不存在 ⇒ 拒绝」，⑤ 是「**无法判定** ⇒ 放行 + 警告」 |

   - ③ 的成立条件是**条件句**：仅当默认分支自 fork 起没有其它提交时，tip-to-tip 比较才等价 —— 因此文案必须写「提交非祖先但**内容**已进主干」，不得写成「squash/rebase 项目一律放行」。
   - **opt-in 的覆盖面是统一的**：决策 4 的 `ARCHIVE_ALLOW_UNMERGED=yes` + reason **覆盖本门的全部拒绝态**（含 ⓪ 的 ref 缺失、① 的 worktree dirty、未合入）⇒ 语义统一为「默认拒绝；显式 opt-in + 审计可放行」。
   - ⓪①②③④ 之外的一切异常一律落到 ④（放行 + 警告）。
3. **指引文案按失败原因分叉**（`execute` 阶段默认不 commit ⇒ 「worktree 有未提交改动」是**主路径**而非边角）：
   - 分支**有**提交、未合入、worktree 干净 ⇒ 给合并命令：`git -C <main_root> merge --no-ff openspec/<name>`；
   - 分支**无**新提交、worktree 有未提交改动 ⇒ 给提交命令：`git -C <wt_path> add -A && git -C <wt_path> commit -m "..."`（先落到实现分支，再走合并）；
   - 分支**有**提交**且** worktree 仍有未提交改动 ⇒ 给**两步**命令（先 commit 到实现分支，再合并）—— 只给合并命令会让未提交的部分照样随 worktree 清理丢失 ⇒ **指引本身会重新制造本决策要消灭的丢代码**。
   - **分支 ref 不存在**（⓪）⇒ 说明「实现分支 `openspec/<name>` 已不存在（通常已被上一次归档的 cleanup 删除）」+ 找回路径（`git reflog` / `git branch <name> <sha>`），**不给合并命令**（没有分支可合并）。
4. **opt-in**：`ARCHIVE_ALLOW_UNMERGED=yes` **且** `RDDF_ARCHIVE_UNMERGED_REASON` 非空 ⇒ 跳过拒绝，但**必须**留 bypass 审计记录（`_lib/bypass_audit.sh::audit_bypass_log`）。缺 reason 时不生效。
   - ⚠ **`ARCHIVE_ALLOW_UNMERGED=yes` 与 `FORCE_BRANCH_DELETE=yes` 不得同时生效**：前者放行未合入的分支，后者用 `git branch -D` **永久删除**该分支 ⇒ 组合使用 = 代码不可恢复。实现上直接拒绝该组合并报错。
5. **判定点位置**：`archive_premerge_check` 在 false 分支内、**先于** AC 归档门执行（便宜且确定 ⇒ 先给出可操作的错误，避免用户先撞 AC 门再撞合入门的两轮往返）。
6. **cleanup 的返回契约与文案**：`cleanup_worktree_and_branch` 改为三态返回（`0` 全清 / `1` 分支保留 / `2` worktree 残留）；「✅ Worktree 已删除」**只在真删成功时打印**；三种 worktree 失败态（未注册残留目录 / 已注册但 remove 失败 / 分支 ref 缺失）分别给不同消息与修复指引；tracked 路径的 `cleanup … || return 1` 同步改为「归档成功、清理失败只警告」（否则「归档已成功」会因删除失败而整体失败 —— 与本决策的论点相反）。
7. **spec delta（两份）**：把「跳过 `commit_archive_moves`」与「feature 分支合并」解耦 —— 前者保留；后者改为「未合入时 SHALL 拒绝归档（可显式 opt-in）」；顺序 scenario 增加归档前的合入**判定**步骤（判定不是合并；归档仍不执行 `git merge`）。
   - 附带：`archive-auto-commit/spec.md` 的 lightweight MUST **不得**改成负向断言 —— 它今天仍然红（`phase3_archive.sh` 的 lightweight inline 分支确实没调 `commit_archive_moves`）⇒ 应**正向重指向**为「`rdd-builder` P3 lightweight 路径 MUST 调用 `commit_archive_moves`」。**该 delta 由本 ADR 主责**（ADR-0036 的 2026-11-17 修订只在 R4 行登记处置方向，不重复写 delta）。
8. **文档**：`skills/rdd-builder/SKILL.md` 的 P3 段与 `docs/architecture/workflow-phases.md` 写明「archive 不代劳合并；`git.openspec_tracked=false` 的实现分支须先并入默认分支」，并显式区分「AC 归档门」与「合入门」。

### 修订 2026-11-18（表格补正：补上「未合入」这一档）

**触发**：实现阶段按本决策写 `archive_premerge_check` 时发现 —— 上表的 ④ 只写了「其余（无法判定）⇒
放行」，**没有「未合入 ⇒ 拒绝」这一档** ⇒ 按表的字面读法，「未合入且内容不等价」会落到 ④ 的
「无法判定 ⇒ 放行」⇒ **这道门永远不会拒绝**。

⇒ 与本 ADR 的**决策正文**矛盾：决策 4 的 opt-in 覆盖面条款明写「覆盖本门的**全部拒绝态**（含 ⓪ 的
ref 缺失、① 的 worktree dirty、**未合入**）」，且整份 ADR 的目的就是「未合入不得归档」⇒ 缺的只是
**表格里的一行**，不是决策。

**改动**：上表补上 ④「未合入（`git cherry` 显示 `+`）⇒ `1`（拒绝）」，原 ④ 顺延为 ⑤「无法判定 ⇒
`2`（放行 + 警告）」；判定顺序相应为 ⓪ → ① → ② → ③ → ④ → ⑤。**决策未变**（未合入 ⇒ 拒绝），仅
表格补正 —— 与决策 2 的 prose、决策 4 的覆盖面条款、V-4 一致。

### 影响范围

- **In Scope**：`_lib/archive.sh`（新增 `archive_premerge_check` + false 分支插入点 + `cleanup_worktree_and_branch` 返回契约 + tracked 路径对称修正）、两份 spec（delta）+ `archive-auto-commit/spec.md`（正向重指向）、`tests/integration/test_archive_with_openspec_tracked_false.bats`（修改 + 新增）、`skills/rdd-builder/SKILL.md`、`docs/architecture/workflow-phases.md`、`docs/architecture/gates-and-quality.md`（门清单同步）、`docs/adr/README.md`（索引同步）。
- **Out Scope**：不在 false 分支新增 `git merge` / `commit_archive_moves`；不改 tracked 路径的合并行为；不改 `FORCE_BRANCH_DELETE` 的语义（它只在门通过后的删除阶段生效）；不处理 lightweight 路径（其缺口归 `fix-execution-mode-decision` 收口）；**不修复** false 路径既有的步骤省略（issue 关闭 / tasks 完成度门 / L2 采集 / tasks sidecar / `archive_commit_sha` 为空）—— 那是既有缺口，本 ADR 只在 Consequences 里如实记录，不在本决策里 normative 化。

### 备选方案

| 备选 | 结论 | 理由 |
|---|---|---|
| A. 在 false 分支里直接执行 `git merge` | **拒绝** | ① **维度错配**：让「openspec/ 是否入库」这个开关授权「代码进主干」，把两件不相干的事绑在一起 —— 与 ADR-0036 的 2026-11-17 修订（该开关只属归档路径 + 波次维度）**直接冲突**；② **授权主体错位**：归档是「记录 + 清理」动作，让它顺带改默认分支 = 把「谁批准合并」交给一个配置开关（对 openspec/ 不入库的项目，主干另有发布流程，工具不该越权写）。（与两份 spec 的冲突是**成本**，不是不可为的理由 —— 本决策通过 delta 解决） |
| B. 维持现状，只把警告文案写响 | **拒绝** | 用户真正的痛点不是「没看到警告」，而是「归档说成功、代码没进主干」；更响的文案不改变 exit 0 的语义，CI 仍然误判。**B 与本决策的差别在于判定点是否存在，不在文案强度** |
| C. 归档前加一道合入判定，未合入则拒绝（可显式 opt-in + 审计） | **接受** | 把「谁来合并」确定下来：归档负责**判定**并给一次到位的指引，合并动作仍在人手里（与两份 spec 的「不代劳合并」不冲突）；squash-merge 项目由 patch-id 判据放行，无法判定时放行不制造假拒绝 |
| D. false 分支改走 tracked 路径（归档时自动合并） | **拒绝** | 与 A 同源同理由，且**更差**一处：它顺带打开 `commit_archive_moves` —— 而 `openspec/` 未跟踪时**没有东西可 commit**，等于制造一个必然失败的 commit 步骤 |
| E. 只加判定、不改 cleanup 文案 | **拒绝** | 留下的是**第二个谎报点**（「✅ Worktree 已删除」在失败时照打），与本决策同类 |

### AC 映射

| 本 ADR 的 Verification 判据 | 对应 `fix-worktree-archive-branch-merge` 的 AC |
|---|---|
| V-1 ~ V-3 | AC「`archive_premerge_check` 具名函数 + 三态」「内容等价分支存在」「worktree 未提交改动 ⇒ 拒绝」。⚠ **本 ADR 覆盖其中「内容等价」的判据口径**：立项原文写的是 `git diff --quiet <default> <branch>`（tip-to-tip），本 ADR 改为 **patch-id 判据**（`git cherry`）—— 实施方以本 ADR 为准（立项的该条 AC 需由 planner 同步修订） |
| V-4 ~ V-6 | AC「未合入 ⇒ `archive_change` 返回 1 → phase3 退出 3 → `rddf archive` 退出 1」「opt-in ⇒ 放行且留审计；缺 reason 不生效」「opt-in 与 `FORCE_BRANCH_DELETE` 不得同时生效」 |
| V-7 ~ V-9 | AC「false 分支内不新增 `git merge` / `commit_archive_moves`」「cleanup 只在真删成功时打印成功」「三种 worktree 失败态分别给不同消息」 |
| V-10 | AC「tracked 路径的 `cleanup … || return 1` 不再让『归档已成功』整体失败」 |
| V-11 ~ V-12 | AC「spec delta（两份）」「文档写明『archive 不代劳合并』并区分两道门」 |

## Consequences

### 正面

- 「归档成功」不再掩盖「代码未进主干」—— 在**受门保护的路径**上（旁路路径见下方）。
- 「谁来合并」被确定下来：归档流程负责**判定**并给出一次到位的指引，而不是靠操作者记忆。
- squash-merge / rebase 类项目不被新门锁死（patch-id 判据）。
- cleanup 的消息与事实一致：残留看得见，且带可复制的修复命令。
- 两份 spec 的措辞与实现一致（不再是「executing only」与实际步骤不符）。

### 负面 / 风险

- **新增的「未合入 ⇒ 拒绝」会改变当前能跑通的手工流程**（先归档、后合并）⇒ 预期行为变更，须在变更说明与文档里写明。
- **人工成本**：现状是「1 次手工 merge」；新门是「1 次失败 + 1 次手工 merge + 1 次重跑」。这是本决策**主动接受**的代价 —— 换来的是「失败发生在丢代码之前」。
- **旁路路径不受门保护**（本决策不承诺覆盖）：`phase3_archive.sh` 的 lightweight inline 分支（归 `fix-execution-mode-decision` 收口 —— **它必须自带同款合入判定，否则被合法化的模式上没有任何合入判定**）、`phase0_approval.sh` 的 rdd-quick 直归档路径、手工 `openspec archive`。
- **`FORCE_BRANCH_DELETE=yes` 的优先级**：它只在 cleanup 阶段生效，位于本门**之后** ⇒ 门拒绝时该变量永远到不了 ⇒ **不得**声称「`FORCE_BRANCH_DELETE` 的旁路不受影响」；且它与 opt-in 组合 = 代码永久删除（见决策 4）。
- **opt-in 可能变成常规**：若 `ARCHIVE_ALLOW_UNMERGED` 的使用频率上升，它会退化为「默认放行」⇒ 须纳入 bypass 审计的月度阈值统计（建议 `ARCHIVE_ALLOW_UNMERGED: 3`，比默认阈值更紧）。
- **既有缺口（本 ADR 不修，如实记录）**：false 路径比 tracked 路径少四步 —— issue 关闭（`close_issues_for_change_hook`）、tasks 完成度门（`check_tasks_completion`）、L2 采集（`collect_l2_count_wrapper`）、tasks sidecar；且 `mark_iteration_archived "$name" "$main_root" ""` 传空 sha ⇒ false 路径的 `iteration.json` 永远没有 `archive_commit_sha`。
- **判定依赖 git 语义**：`merge-base --is-ancestor` / `git cherry` 的行为随 git 版本略有差异；异常一律落到「放行 + 警告」。
- **与既有重归档逃生阀的交互（行为变更，须写明）**：`_lib/archive.sh` 的 re-archive guard 今天是默认 **WARN 放行**（`RDDF_REQUIRE_ARCHIVE_UNIQUE=yes` 才 BLOCK）。新门落地后，**重归档**（分支已在上次归档被 cleanup 删除 ⇒ ref 缺失 ⇒ 判定 **⓪** 拒绝）会从「warn 放行」变成**hard refuse**，而原有的逃生阀在该态失效（分支已不存在，`RDDF_REQUIRE_ARCHIVE_UNIQUE` 管的是重复归档记录、不是分支 ref）。⇒ 该态由 `ARCHIVE_ALLOW_UNMERGED=yes` + reason 覆盖（opt-in 语义 = 「我知道分支没了，放行」）。
- **回滚路径**：本决策若被推翻，回滚 = 移除 false 分支的合入门插入点 + 回退两份 spec 的 delta + 删除 `archive_premerge_check`（门是**新增**步骤，回滚不触碰既有合并路径 ⇒ 无数据迁移、无状态格式变化）。

### 后续待办

- [ ] **实现**：`archive_premerge_check` + false 分支插入点（先于 AC 门）+ cleanup 三态 + spec delta + 测试改造（见 Verification）。
- [ ] **立项同步（责任方：planner）**：`.rddf/improvements/fix-worktree-archive-branch-merge.md` 的 AC「内容等价分支存在」写的是 `git diff --quiet <default> <branch>`（tip-to-tip），与本 ADR 的 patch-id 判据（`git cherry`）**不一致** ⇒ 实施方若只读立项会实现被否定的口径 ⇒ 该 AC 须由 planner 同步修订（本 ADR 已在 AC 映射表标注覆盖关系）。
- [ ] **不在本决策范围**：lightweight 路径的同类缺口（归 `fix-execution-mode-decision` 收口 —— 其执行模式语义由 ADR-0036 的 2026-11-17 修订一并钉死）。
- [ ] **不在本决策范围**：`v4_residue_check` 的扫描面不含 `openspec/specs/` ⇒ 「已删除路径出现在 normative 文本中」无法被机器发现（随 ADR-0036 修订项一并提出）。
- [ ] **不在本决策范围**：false 路径的步骤省略与空 `archive_commit_sha`（见 Consequences）。

## Verification

- [ ] **V-1** `archive_premerge_check` 为具名函数，返回三态且判定顺序为 **⓪ref 存在性 → ①未提交改动 → ②已合入 → ③内容等价 → ④无法判定**（⓪ 必须先于 ②③，否则「ref 缺失」会被读成 ④ 的放行）。
- [ ] **V-2** 内容等价用 **patch-id** 判据（`git cherry <default> <branch>` 全为 `-`）⇒ 放行 + 警告；默认分支有无关提交时仍能正确判「内容已进主干」。
- [ ] **V-3** worktree 内未提交改动 ⇒ 拒绝；**噪声排除**生效（系统复制的 `openspec/changes/<name>/` 与 `.rddf/plans/<name>.md` 不算未提交改动）；且「已合入 + 仍有未提交改动」时**以 dirty 为准**（拒绝）。
- [ ] **V-4** 分支 ref 缺失 ⇒ **拒绝**（与 `verifier-lifecycle` 的 fail-closed 一致），不是放行；且该判定是 ⓪ 的**前置存在性检查**（不依赖 ②③ 的命令结果）。
- [ ] **V-5** 拒绝 ⇒ `archive_change` 返回 1 ⇒ `phase3_archive.sh` 退出 3 ⇒ `rddf archive` 退出 1，且 stderr 含**按失败原因分叉**的可复制命令：① 有提交未合入 ⇒ 合并命令；② 无提交但 worktree dirty ⇒ 先提交命令；③ 有提交**且** dirty ⇒ 先提交后合并两步命令；④ **分支 ref 不存在** ⇒ 说明分支已不存在 + 找回路径（不给合并命令）。
- [ ] **V-6** `ARCHIVE_ALLOW_UNMERGED=yes` + `RDDF_ARCHIVE_UNMERGED_REASON` ⇒ 放行**且**留下 bypass 审计记录；缺 reason 时不生效；**与 `FORCE_BRANCH_DELETE=yes` 同时出现时报错拒绝**。
- [ ] **V-7** 合入门**先于** AC 归档门执行（用户先拿到可操作的合并指引，不先撞 AC 门）。
- [ ] **V-8** false 分支内不新增 `git merge` / `commit_archive_moves` 调用；既有 awk 守卫**已加固**（提取终点为 `mark_iteration_archived`）且**今天就已退化**（原守卫在第一个独立 `fi` 就 exit，插入的 `commit_archive_moves` 若在其后根本检不出）⇒ 守卫与行为断言都要补。
- [ ] **V-9** `cleanup_worktree_and_branch` 只在真删成功时打印「✅ Worktree 已删除」；失败时输出含失败原因、残留路径与修复指引；三种 worktree 失败态给出不同消息。
- [ ] **V-10** tracked 路径的 `cleanup … || return 1` 不再让「归档已成功」整体失败（返回码语义与 false 路径一致）。
- [ ] **V-11** 两份 spec 已更新：`complete-project-yaml-config-gaps` 的 `openspec_tracked=false` 段与 `archive-openspec-tracked-skip-commit` 的顺序 scenario；`archive-auto-commit` 的 lightweight MUST 已**正向重指向** `rdd-builder` P3（不是改成负向断言）。
- [ ] **V-12** `skills/rdd-builder/SKILL.md` 的 P3 段、`docs/architecture/workflow-phases.md` 与 `docs/architecture/gates-and-quality.md` 写明「archive 不代劳合并」，并区分「AC 归档门」与「合入门」。
- [ ] **V-13** `docs/adr/README.md` 已用 `_lib/adr_index_generator.py --write` 重建，`tests/unit/test_adr_index_gate.py` 通过。

## References

- `openspec/specs/complete-project-yaml-config-gaps/spec.md` —— Requirement `archive-openspec-tracked-skip-git`（本决策修改其语义）
- `openspec/specs/archive-openspec-tracked-skip-commit/spec.md` —— Requirement `archive-openspec-tracked-false-branch-cleanup`（本决策修改其顺序 scenario）
- `openspec/specs/verifier-lifecycle/spec.md` —— Requirement「Implementation commit SHALL be the openspec branch tip」（分支缺失 ⇒ fail closed ⇒ V-4 的依据）
- `openspec/specs/archive-auto-commit/spec.md` —— Requirement「lightweight 模式 MUST 也调用 helper」（本决策将其正向重指向 `rdd-builder` P3）
- ADR-0035 —— verifier-archive-gate 边界（门与验证器的职责划分）
- ADR-0036 —— `.rddf/project.yaml` 配置源（2026-11-17 修订：`git.openspec_tracked` 的维度归属）
- `.rddf/improvements/fix-worktree-archive-branch-merge.md` —— 本决策的立项（14 条 AC 与本 ADR 的 Verification 一一映射）
