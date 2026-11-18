---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up A/B 合并）——openspec_tracked=false 时
  归档不合并 worktree 分支（契约禁止），却也无人合并 ⇒ 提交被搁浅；且 cleanup 失败仍打印成功文案
阶段: phase-2
分类: bugfix
类型: bugfix
状态: implemented (2026-11-17 首轮 → 2026-11-18 architect 复核后补完 5 条 AC，复验通过)

生成时间: 2026-11-17
roadmap_ref:
---

# fix-worktree-archive-branch-merge

**主题**: 阶段步骤化执行

> ⚠ **本项含 spec delta，需 architect 签批**（见「架构依据 · 语义澄清」与 AC「spec delta」一组）。

## 架构依据

### 语义澄清（metis 第 1 轮 P0-1，本项的根因层）

`git.openspec_tracked` 这个开关在 spec 里承担了**两件不相干的事**：

| 事项 | 与「openspec/ 是否被 git 跟踪」的关系 | 现状 |
|---|---|---|
| 跳过 `commit_archive_moves` | **直接相关** —— `openspec/` 未跟踪 ⇒ 归档产物没有东西可 commit | 已实现（`_lib/archive.sh:607-608`、`:876-878`） |
| 跳过 **feature 分支合并**（`git merge <branch> <default_branch>`） | **无关** —— 代码改动是否进主干，与 `openspec/` 目录是否被跟踪毫无关系 | 已实现，但**没人补执行点** |

规范侧的确切措辞：

- `openspec/specs/complete-project-yaml-config-gaps/spec.md:248`：
  > when set to `false`, SHALL skip `git merge` and `commit_archive_moves` operations, **executing only `openspec archive` and `mark_iteration_archived`**.
  （scenario `:253-254` 进一步钉死「SHALL NOT execute `git merge <branch> <default_branch>`」「SHALL NOT execute `commit_archive_moves`」）
- `openspec/specs/archive-openspec-tracked-skip-commit/spec.md:34,40-41`：false 分支 SHALL NOT call `commit_archive_moves`，且执行顺序 SHALL 为 `switch_to_default_branch` → `openspec archive` → `cleanup_worktree_and_branch` → `mark_iteration_archived`。

⇒ **「executing only …」与「顺序 SHALL 为 …」两句，把「归档前插入任何新步骤」都排除在外。**
本项要插入的检查因此**必须走 spec delta**（否则实现即漂移）。这不是绕路，是两份 spec 的原意就与「代码要进主干」冲突。

### 缺陷一：worktree 提交被搁浅，而归档报告成功

`_lib/archive.sh::archive_change` 的 false 分支（`:607-630`）：

```bash
echo "📦 openspec_tracked=false: 跳过 git merge/commit"    # :608
switch_to_default_branch "$main_root" "$default_branch" || return 1   # :609
archive_gate_check "$name" "$main_root" || return 3          # :616
openspec archive "$name" --yes                              # :617
cleanup_worktree_and_branch "$name" "$main_root" "$wt_path" "$branch" || true   # :625
mark_iteration_archived "$name" "$main_root" ""             # :626
return 0                                                     # :628
```

- 合并只在 tracked 路径存在（`merge_feature_branch`，`_lib/archive.sh:239-261`）；false 路径**没有合并执行点**。
- `cleanup_worktree_and_branch`（`:275-297`）在分支有未合入提交时 `git branch -d` 失败 → 打印 `❌ Branch 删除取消。设置 FORCE_BRANCH_DELETE=yes 重试`（`:293`）→ `return 1` —— 但调用点写了 `|| true`，**失败被吞**，归档仍 `return 0`。

**实测（本批 5 项全部命中）**：P3 归档前必须手工 `git merge --no-ff openspec/<name>` 把 worktree 提交并回默认分支，否则该分支的提交永久搁浅，而归档**报告成功**。本批 5 项全部靠手工合并才没丢代码。

**触发范围**：本仓 `git.openspec_tracked: false` 命中；而 `phase2_execute.sh` **不读** `openspec_tracked`（只在 `:7` 的注释里提到它）⇒ 本仓在 false 配置下仍建 worktree ⇒ 命中是必然，不是巧合。
（注：schema 描述里「false ⇒ force lightweight mode (branch only, no worktree)」的**前半句也没有实现** —— 该半句已被 **ADR-0036 的 2026-11-17 修订裁定为退役**（该开关不再强制执行模式），并由 `fix-execution-mode-decision` 落地为「描述只描述归档路径语义」；而「lightweight 这个模式本身不可用」的缺口（不建分支 + 归档路径缺步）归 **`fix-lightweight-branch-and-archive`** 收口。本项因此**不依赖**两者，但需与它们互为参照。）

### 缺陷二：cleanup 失败仍打印「✅ Worktree 已删除」

`:279-283`：

```bash
(cd "$main_root" && git worktree remove "$wt_path" 2>/dev/null) || {
  echo "⚠️  worktree remove 失败: $wt_path"
}
echo "✅ Worktree 已删除: $wt_path"     # ← 在 if/else 之外，无条件打印
```

`git worktree remove` 失败（dirty 工作区 / `.nfs*` 占位）时**仍打印成功**，而目录还在。
2026-11-17 实测：`.rddf/wt/register-change-in-iteration/` 因 `.nfs*` 删不掉而残留成孤儿目录（未注册 worktree、0 文件、1.5K），消息与事实相反。

### 三处连带的口径问题（metis 第 1 轮指出，均已核实）

1. **两份 spec 措辞不一致**：一份写「skip `git merge` and `commit_archive_moves`」，另一份只写「SHALL NOT call `commit_archive_moves`」并把顺序钉死 ⇒ 读者无法判断哪条是 normative（本项的 spec delta 必须同时处理两份）。
2. **既有测试会被打红**：`tests/integration/test_archive_with_openspec_tracked_false.bats`（`:124-180`）构造的正是「worktree 分支有未合入 commit `change work`」，并断言 `[ "$status" -eq 0 ]` ⇒ 本项的新行为会让它失败 ⇒ 该文件是**必须修改**，不是「新增 bats」。
3. **既有源文本守卫会自我退化**：同文件 `:246-260` 的 awk 提取器在**第一个独立的 `fi` 行**就 `exit` ⇒ 一旦在 false 分支内插入 `if … fi`，守卫范围会缩到几行，之后即使有人加 `commit_archive_moves` 也检不出来，而测试**仍然 PASS** ⇒ 守卫本身必须加固。

## 范围

- **In Scope**：① 归档前新增**具名**检查函数 `archive_premerge_check`，未合入则拒绝归档（可显式 opt-in 覆盖）；② worktree 内**未提交**改动一并检查；③ cleanup 的返回契约与成功文案（dir/file 之外的第三态：worktree 残留）；④ **spec delta**（两份 spec）；⑤ 修改既有测试文件 + 新增用例；⑥ 归档流程文档写明「archive 不代劳合并」。
- **Out Scope**：**不在 false 分支里新增 `git merge` / `commit_archive_moves`**（守 L248/L253）；不改 `merge_feature_branch`（tracked 路径的合并行为已正确）；不改 `FORCE_BRANCH_DELETE` 的语义（只管分支删除）；**不处理 lightweight 路径**（⚠ lightweight 下 `phase2_execute.sh:117-119` **不建分支** ⇒ 「提交停在分支上」不成立，其真实缺口是 `phase3_archive.sh:135-145` 缺 `post_archive_cleanup` + `mark_iteration_archived` ⇒ 归 **`fix-lightweight-branch-and-archive`** 收口 —— 见该立项的分工：「轻量路径的建分支 + 归档路径补齐 + 提交归属检查」都在那边，本项只负责 **worktree 路径**的合入门）；不删任何已存在的分支；不改 `openspec_tracked` 的**归档**语义。

## Why

「归档成功」与「代码已进主干」是两件事，现在前者会在后者为假时成立。对 rdd-workflow 这是**最坏的一类静默失败**：CI/agent 看到 exit 0 就认为这批工作已落地，实际上提交躺在即将被清理的分支上。

metis 提出的反向意见（采纳并已写进 What Changes）：**现状成本是 1 次手工 merge；改成「拒绝归档」是 1 次失败 + 1 次手工 merge + 1 次重跑 ⇒ 人工成本反而更高**。因此本项的目标不是「更响地拒绝」，而是**把「谁来合并」这件事确定下来**：默认由归档流程负责判定并在未合入时给出**一次到位**的指引（含可直接复制的命令与 opt-in 变量），而不是把问题留给记忆。

对 squash-merge 的项目（内容已进主干但 commit 非祖先）必须能放行，否则新门会把它永久锁死 —— 这条已写进 AC。

## What Changes

1. **具名检查函数 + 三态返回**（`_lib/archive.sh`，与 `merge_feature_branch` 同级风格）：

   > ⚠ **本 ADR 覆盖声明（2026-11-17 architect 签批，ADR-0061）**：本小节写于 ADR 之前，
   > 其**判定细节**已被 ADR-0061 取代 —— 实施方**以 ADR-0061 的决策 2 判定表为准**：
   > ① 本小节 b. 的 **tip-to-tip `git diff --quiet`** ⇒ 改为 **patch-id 判据 `git cherry`**；
   > ② 本小节 c./d. 的顺序（is-ancestor → 内容等价 → 无法判定 → dirty）⇒ 改为 ADR 的
   > **⓪ref 存在性 → ①worktree dirty → ②已合入 → ③内容等价 → ④未合入 → ⑤无法判定**；
   > ③ 本小节写的「`2` = 无法判定（**ref 缺失** / 非 git 仓库）⇒ 放行」⇒ 改为 ADR 的
   > **⓪ ref 缺失 ⇒ 拒绝**（fail-closed，与 `verifier-lifecycle` 一致）；**非 git 仓库 ⇒ ⑤ 放行**；
   > ④ 本小节没有「未合入 ⇒ 拒绝」这一档 ⇒ 由 ADR 的 ④ 补上。
   > 下面保留原文仅作**草案留痕**，不作为实现依据。

   `archive_premerge_check <main_root> <branch> <default_branch> <wt_path>`
   - `0` = 已合入 **或** 内容等价（放行）；
   - `1` = 未合入（可操作拒绝）；
   - `2` = 无法判定（ref 缺失 / 非 git 仓库）⇒ **放行 + 显式警告**（与 `verifier_contract_check` 的 legacy fallback 一致，不因环境异常制造假拒绝）。
   判定顺序：
   a. `git -C "$main_root" merge-base --is-ancestor "$branch" "$default_branch"` ⇒ 0 ⇒ 已合入；
   b. 退出 1 ⇒ 内容等价兜底：`git -C "$main_root" diff --quiet "$default_branch" "$branch"` ⇒ 退出 0 ⇒ **内容已进主干**（squash-merge 情形）⇒ 放行 + 警告「提交非祖先但内容一致」；
   c. 退出 >1（128）⇒ 无法判定 ⇒ 走 `2`；
   d. **worktree 未提交改动**：`git -C "$wt_path" status --porcelain` 非空 ⇒ 拒绝（未提交的改动会随 worktree 清理丢失 —— `check_worktree_commits` 只存在于 tracked 路径，false 路径没有它）。
2. **插入点**：false 分支内，`switch_to_default_branch`（`:609`）之后、`openspec archive`（`:617`）之前（**必须早于归档**，否则已经归档完了才发现没合入）。⚠ 该插入点与两份 spec 的「executing only …」/「顺序 SHALL 为 …」冲突 ⇒ 由第 4 项的 spec delta 覆盖。
   - 拒绝时：打印「`openspec/<name>` 分支尚未合入 `<default_branch>`」+ 可复制命令（`git -C <main_root> merge --no-ff openspec/<name>`）+ opt-in 提示；`archive_change` 返回 **1**（⇒ `phase3_archive.sh` 映射为 exit **3** ⇒ `rddf archive` 退出 **1**）。
   - opt-in：`ARCHIVE_ALLOW_UNMERGED=yes` **且** `RDDF_ARCHIVE_UNMERGED_REASON` 非空 ⇒ 跳过拒绝但**必须**经 `_lib/bypass_audit.sh::audit_bypass_log` 留审计（复用现成通道）；优先级高于新门，`FORCE_BRANCH_DELETE` 仍只在门通过后的删除阶段生效。
3. **cleanup 返回契约与文案**（`cleanup_worktree_and_branch`，`:275-297`）：
   - 返回值改为三态：`0` = 全清 / `1` = 分支保留（未合入，且未 FORCE）/ `2` = worktree 残留；
   - 「✅ Worktree 已删除」**只在真删成功时打印**；失败时打印失败原因 + 残留路径 + 修复指引（`git worktree remove --force <path>`）；
   - **三种 worktree 失败态分开报错**：① 目录未注册到 git（`git worktree list --porcelain` 不含）⇒ 提示 `git worktree prune` / 手工 `rm -rf`（对应 2026-11-17 实测的孤儿目录）；② 已注册但 remove 失败（dirty / `.nfs*`）⇒ `--force` 指引；③ 分支 ref 缺失 ⇒ **不算**「未合入」；
   - **同时修 tracked 路径的不对称**：`_lib/archive.sh:661` 的 `cleanup_worktree_and_branch … || return 1` 会让「归档已成功」因删除失败而整体失败 —— 与本项自己的论点相反 ⇒ 一并改为「归档成功、清理失败只警告」（返回码语义对齐）。
4. **spec delta**（两份）：
   - `complete-project-yaml-config-gaps`（`:248` / `:253-254`）：把「skip `git merge`」与「skip `commit_archive_moves`」**解耦** —— 后者保留，前者改为「未合入时 SHALL 拒绝归档（可显式 opt-in）」；
   - `archive-openspec-tracked-skip-commit`（`:34` / `:40-41`）：顺序 scenario 增加归档前的合入检查步骤。
   ⚠ 这是**已签批 spec 的语义变更** ⇒ 实施前须由 architect 签批（本项在 P0 阶段需路由 architect，见 AC）。
5. **测试**：
   - **修改** `tests/integration/test_archive_with_openspec_tracked_false.bats`：把现有「未合入 ⇒ status 0」的用例改成「**已合入** ⇒ 0」（该用例的构造是 worktree + branch + 一次 commit，需先合并），另**新增**「未合入 ⇒ 拒绝」用例；
   - 新增用例：内容等价（squash-merge 形态）⇒ 放行 + 警告；`is-ancestor` 返回 128 ⇒ 走「无法判定」分支（放行 + 警告）；worktree dirty ⇒ 拒绝；opt-in 覆盖 ⇒ 放行 + 审计记录；
   - **加固既有源文本守卫**：把 awk 提取终点从「第一个独立 `fi`」改成「`mark_iteration_archived`」（否则插入内层 `if` 后守卫退化且仍 PASS）；新增**行为断言**（stub `archive_premerge_check` ⇒ 断言 `commit_archive_moves` 未被调用、`git merge` 未被执行）—— 纯 `grep "git merge"` 会与 `merge-base` 字面冲突，属预期误报，不可作为守卫。
6. **文档**：在 `skills/rdd-builder/SKILL.md` 的 P3 段（当前 `"merge"` 零命中 ⇒ 真空缺）写明「archive 不代劳合并；`git.openspec_tracked=false` 的 worktree 分支须先并入默认分支」，并同步 `docs/architecture/workflow-phases.md`。

## Acceptance

- [x] **spec delta**：更新 `complete-project-yaml-config-gaps`（`openspec_tracked=false` 段，`:248`/`:253-254`）与 `archive-openspec-tracked-skip-commit`（顺序 scenario，`:34`/`:40-41`）两份 spec，把「跳过 commit_archive_moves」与「feature 分支合并」解耦；并由 architect 签批
- [x] `archive_premerge_check` 为**具名函数**、返回三态（0 已合入/内容等价、1 未合入、2 无法判定）；无法判定时**放行 + 警告**（不制造假拒绝）
- [x] **接口契约：支持「无 worktree」模式**（`wt_path` 为空）—— ①「worktree 内未提交改动」判据在 `wt_path` 为空时**跳过**（lightweight 路径没有 worktree；用主仓的 `git status --porcelain` 会把**别的 change 的脏文件**误判成本 change 的未提交改动 ⇒ 假拒绝，且指引文案会诱导用户把别人的改动 commit 进来）⇒ 轻量路径用「分支提交归属」判据代替（归 `fix-lightweight-branch-and-archive`）；⓪ref 缺失 / ②已合入 / ③内容等价（patch-id）/ **④未合入 ⇒ 拒绝** / ⑤无法判定**五项原样复用**（⚠ 补正前的清单只列四项且把 ④ 当成「无法判定」—— 补正后 ④ = **未合入 ⇒ 拒绝**，⑤ = 无法判定 ⇒ 漏掉 ④ 会让 lightweight 路径**不拒绝未合入分支**）
- [x] **内容等价用 patch-id 判据**（`git cherry <default> <branch>` 全为 `-`），不是 tip-to-tip 的 `git diff --quiet`（后者在默认分支有任何无关提交时就会判不等）—— per ADR-0061 的决策 2 ③（立项 AC 原文的 `git diff --quiet` 口径已被本 ADR 覆盖，须同步）
- [x] 内容等价分支存在：`is-ancestor` 为假但 `git diff --quiet <default> <branch>` 为真 ⇒ 放行 + 警告（squash-merge 项目不被永久锁死）
- [x] worktree 内有未提交改动 ⇒ 拒绝归档（改动不会随 worktree 清理丢失）
- [x] 未合入 ⇒ `archive_change` 返回 1 → `phase3_archive.sh` 退出 3 → `rddf archive` 退出 1，且 stderr 含「尚未合入」与可复制的合并命令
- [x] opt-in：`ARCHIVE_ALLOW_UNMERGED=yes` + `RDDF_ARCHIVE_UNMERGED_REASON` ⇒ 放行**且**留下 bypass 审计记录；缺 reason 时不生效
- [x] **false 分支内不新增** `git merge` / `commit_archive_moves` 调用（既有 awk 守卫**已加固**：提取终点为 `mark_iteration_archived`；并新增行为断言）
- [x] `cleanup_worktree_and_branch` 只在真删成功时打印「✅ Worktree 已删除」；失败时输出含失败原因、残留路径与修复指引
- [x] worktree 的三种失败态分别给出不同消息（未注册残留目录 / 已注册但 remove 失败 / 分支 ref 缺失）
- [x] tracked 路径的 `cleanup … || return 1` 不再让「归档已成功」整体失败（返回码语义与 false 路径一致）
- [x] **修改** `tests/integration/test_archive_with_openspec_tracked_false.bats`：原「未合入 ⇒ status 0」用例改为「已合入 ⇒ 0」，并新增「未合入 ⇒ 拒绝」用例
- [x] 旁路清单成文并逐条标注是否受门保护：`phase3_archive.sh` 的 lightweight inline 分支（**不受**，归 `fix-lightweight-branch-and-archive`）、`phase0_approval.sh` 的 rdd-quick 直归档路径（**不受**）、手工 `openspec archive`（**不受**）
- [x] 文档：`skills/rdd-builder/SKILL.md` P3 段 + `docs/architecture/workflow-phases.md` 写明「archive 不代劳合并」
- [x] `./test.sh --unit` + `bats tests/integration/test_archive*.bats` + `bats tests/integration/test_post_archive*.bats` 全绿

### 2026-11-18 architect 复核新增（ADR-0061 表格补正的涟漪 —— implementation_gap）

> **来源**：ADR-0061 的判定表补正（新增 ④「未合入 ⇒ 拒绝」）后，architect 复核发现**实现的四处
> 不满足已签批契约** + 一处文档缺口。ADR 的「后续待办 → 实施方补」已逐条登记（见
> `docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md`）；本节把它们转成**可执行的 AC**。

- [x] **调用点按返回码消费（V-14）**：`archive_change` 的 false 分支**不得**把三态折叠成两态 —— `0` ⇒ 放行；`1` ⇒ 拒绝（返回 1）；`2` ⇒ **放行 + 警告**。⇒ 判据形态（**调用点级 stub**）：stub `archive_premerge_check` 返回 `2` ⇒ 断言 `archive_change` **仍返回 0**。（⚠ 用 stub 而不是构造真实 ⑤：真实 `archive_change` 流程里 ⑤ 几乎不可达 —— 非 git 仓库 ⇒ `wt_path_for_branch` 先失败；默认分支不可解析 ⇒ `switch_to_default_branch` 先失败；`git cherry` 空输出 ⇒ 已被 `merge-base --is-ancestor` 抢先捕获。）
- [x] **⓪ 的路径不给合并命令（V-5(d)）**：分支 ref 缺失 ⇒ 输出**含** `git reflog` 找回路径、**不含** `merge --no-ff`（没有分支可合并）。⇒ 判据形态：一条**否定断言**（`[[ "$output" != *"merge --no-ff"* ]]`）。
- [x] **非 git 仓库归 ⑤（不落进 ⓪）**：`<main_root>` 不是 git 仓库 ⇒ 判定落在 ⑤（**放行 + 显式警告**），**不得**报「分支不存在（可能已被上一次归档的 cleanup 删除）」的误导文案。⇒ 判据形态：一条「非 git 目录 ⇒ 返回码 2 + 警告文案」的用例。
- [x] **dirty 路径按「分支有提交 / 无提交」分叉（V-5(c)）**：worktree dirty 时 —— 分支**有**提交 ⇒ 给**两步**命令（先 commit 到实现分支，再合并）；分支**无**提交 ⇒ 只给提交命令。⇒ 判据形态：两条用例分别断言命令条数。
- [x] **`docs/architecture/gates-and-quality.md` 写明「合入门」与「archive 不代劳合并」（V-12）**：该文件是 `docs/architecture/` 的**门清单**（现有条目：`gate.py` 的 plan-done / archive-done / ship-lightweight-mode 三个 gate、`arch_quality_gate.py`、tribunal）⇒ 须新增一条「**合入门**（`archive_premerge_check`）：实现分支未合入默认分支 ⇒ 拒绝归档（可显式 opt-in）；归档**不代劳合并**」并与「AC 归档门」区分。

## Capabilities

- 「归档成功」不再掩盖「代码未进主干」（**受门保护的路径上**；旁路路径已在 AC 中列明，不做过度承诺）
- 「谁来合并」被确定下来：归档流程负责**判定**并给出一次到位的指引，而不是靠操作者记忆
- squash-merge / rebase 类项目不被新门锁死
- cleanup 的消息与事实一致：残留看得见，且带可复制的修复命令
- 两份 spec 的措辞与实现一致（不再是「executing only」与实际步骤不符）

## Impact

- **影响面**：`_lib/archive.sh`（新增具名函数 + false 分支插入点 + `cleanup_worktree_and_branch` 返回契约 + tracked 路径 `:661` 对称修正 + 函数头注释）、`openspec/specs/complete-project-yaml-config-gaps/spec.md`、`openspec/specs/archive-openspec-tracked-skip-commit/spec.md`、`tests/integration/test_archive_with_openspec_tracked_false.bats`（修改 + 新增）、`skills/rdd-builder/SKILL.md`、`docs/architecture/workflow-phases.md`。
- **风险**：
  - 新增的「未合入 ⇒ 拒绝」会改变当前能跑通的手工流程（先归档、后合并）⇒ **预期行为变更**，须在变更说明与文档里写明；
  - **`FORCE_BRANCH_DELETE=yes` 的优先级**：它只在 cleanup 阶段生效（`:289-291`），位于新门**之后** ⇒ 门拒绝时该变量永远到不了 ⇒ 不得声称「FORCE_BRANCH_DELETE 的旁路不受影响」（本项 AC 已按此重写）；
  - spec delta 触及已签批 spec ⇒ 需 architect 签批，实施前不得先行改代码。
- **兼容性**：`archive_change` 的返回码集合不变（新增拒绝走既有的 1 ⇒ phase3 exit 3 的映射）；已归档 change 的目录结构不变；本仓（false）路径的**既有成功场景**行为不变（已合入 ⇒ 仍 0）。
- **依赖**：
  - 本批第 2 项（`fix-worktree-archive-path`，已归档）已把 phase3 改为委托 `archive_change` ⇒ 本项的检查点落在它改过的那段代码上，两者不冲突；
  - `fix-execution-mode-decision`（同批，**已实施 2026-11-17**）负责「`openspec_tracked` 只属归档路径 + 波次维度」的 schema / README / spec 退役对齐 —— 该开关**不再**强制执行模式 ⇒ 本项的触发面不受它影响；
  - **`fix-lightweight-branch-and-archive`**（同批，draft）负责 **lightweight 路径**的建分支 + 归档路径补齐（含提交归属检查 + 合入判定复用）—— **lightweight 路径的同类缺口归它收口**，本项只负责 worktree 路径。

## 审稿记录

metis 1 轮（2026-11-17，planner 阶段 gap 分析）。逐条处置：

- **采纳 P0-1（根因在语义层）**：原草案把「契约禁止合并」当成不可动的硬约束，直接在 false 分支加检查 —— 但 `complete-project-yaml-config-gaps:248` 的「executing **only** `openspec archive` and `mark_iteration_archived`」意味着**插入任何新步骤都是 spec 违规**。已重写「架构依据 · 语义澄清」，把「跳过 commit_archive_moves（与 openspec 是否 tracked 相关）」与「跳过 feature 分支合并（与代码是否 tracked 无关）」解耦，并新增 spec delta AC + architect 签批要求。
- **采纳 P0-2（三态 + 具名函数）**：原草案只处理「未合入 / 已合入」两态，且检查内联在分支里 ⇒ 无法单测、无法 stub。已改为具名 `archive_premerge_check` + 0/1/2 三态（无法判定 ⇒ 放行 + 警告）。
- **采纳 P0-3（内容等价）**：原草案会让 squash-merge 项目永久卡死。已加 `git diff --quiet` 兜底分支 + AC。
- **采纳 P0-4（cleanup 契约二选一）**：原草案「捕获返回码 ⇒ 打印 worktree 仍残留」是**空转条款**（worktree remove 失败路径从不返回非 0）。已改为三态返回契约 + 同时修 tracked 路径 `:661` 的不对称（归档已成功却整体失败）。
- **采纳 P0-5（AC 重写为可判定）**：退出码表（archive_change 1 → phase3 3 → rddf archive 1）、断言对象改为「change 目录仍在 + stub 未被调用」（「无 archive 目录」不可判定）、既有测试文件列入**必须修改**、spec delta AC、旁路清单 AC。
- **采纳 P1-1（worktree 未提交改动）**：原草案只看 commit 图 ⇒ agent 改了没 commit 时门会通过、随后 remove 失败、归档返回 0（用户问题只修一半）。已加 `status --porcelain` 检查 + AC。
- **采纳 P1-2（opt-in 定义）**：原草案提到「显式 opt-in」却没定义变量名；且原 Impact 里「FORCE_BRANCH_DELETE 不受影响」是**假的**（它在门之后）。已定义 `ARCHIVE_ALLOW_UNMERGED=yes` + `RDDF_ARCHIVE_UNMERGED_REASON` + bypass 审计，并删除那句假声明。
- **采纳 P1-3（lightweight 冲突）**：原草案 Out Scope 说「不处理 lightweight」，而同批另一条说「必要时覆盖到 lightweight」⇒ 互相打脸。已在本项 Out Scope 明确「lightweight 归 **`fix-lightweight-branch-and-archive`** 收口」并互相引用。
- **采纳 P1-4（三种 worktree 失败态）**：原草案把「孤儿目录」「remove 失败」「分支缺失」混为一谈。已拆成三条消息。
- **采纳 P2-1（守卫改行为断言）**：既有 awk 守卫在插入内层 `if` 后会**退化且仍 PASS** ⇒ 已加「守卫必须加固」AC，并要求行为断言（stub 具名函数）；纯 `grep "git merge"` 会与 `merge-base` 字面冲突，明确不可用作守卫。
- **采纳 P2-2（文档落点）**：已指定 `skills/rdd-builder/SKILL.md` P3 段（当前 `"merge"` 零命中）与 `docs/architecture/workflow-phases.md`。
- **采纳（人工成本的反向意见）**：原草案只把问题「喊得更响」。已写入 Why：目标是**确定合并责任**并给一次到位的指引，而不是增加往返；且拒绝必须是「默认判定 + 明确 opt-in」，不是强制人工步骤。
- **记录未采纳（metis 的「门应更早」建议）**：metis 建议把门提前到 P3 入口以降低拒绝代价。本项未采纳：P3 入口拿不到 `wt_path` 与分支的权威来源（`wt_path_for_branch` 是注册表口径），提前会引入第二套判定源；门留在 `archive_change` 内、与 `wt_path`/分支同源。代价（gate 与 openspec CLI 会先跑）记入 Impact。

## 立项核查（2026-11-17，planner）

| 断言 | 核实结果 |
|---|---|
| `openspec_tracked=false` 时跳过 `git merge` / `commit_archive_moves` | ✅ `archive.sh:607-608`（merge）+ `:877-878`（commit_archive_moves 的 defense-in-depth） |
| spec `archive-openspec-tracked-skip-git` 要求 skip merge + commit | ✅ 存在，Requirement + Scenario 齐全 |
| spec `archive-openspec-tracked-false-branch-cleanup:32-42` 要求顺序 `switch→archive→cleanup→mark` | ✅ 行号准确 |
| `cleanup_worktree_and_branch` 失败仍打印成功 | ✅ `archive.sh:281-284`：`git worktree remove ... \|\| { echo 失败 }` **之后无条件** `echo "✅ Worktree 已删除"` |
| 调用方吞返回码 | ✅ `archive.sh:625` `cleanup_worktree_and_branch ... \|\| true` |
| `archive_premerge_check` 尚不存在 | ✅ 无匹配（本项要新建的具名函数） |

⇒ 立项诊断准确。**本项需 spec delta ⇒ 实施前需 architect 签批**（已写在立项告示里）。

---

## 实施记录（2026-11-17，builder）

### 实现了什么

| AC | 落点 | 证据 |
|---|---|---|
| 具名函数 + 三态 | `_lib/archive.sh::archive_premerge_check`（新增） | 判定顺序 ⓪ref 存在 → ①worktree dirty → ②已合入 → ③内容等价（patch-id）→ ④未合入 → ⑤无法判定 |
| 内容等价（patch-id） | 同上，`git cherry <default> <branch>` 全为 `-` ⇒ 放行 + 警告 | `test_archive_trunk_gate.bats` 的 squash-merge 用例 |
| worktree 未提交改动 ⇒ 拒绝 | 同上，①；**噪声排除**用 `--untracked-files=all`（git 默认把未跟踪目录折叠成 `?? openspec/`，无法精确排除） | 「artifacts the system copies in do NOT count as dirty」 |
| 未合入 ⇒ 拒绝 + 指引 | ④；文案按失败原因分叉（合并命令 / 先提交 / 分支已不存在→reflog） | 「not merged → refuse + a copy-pasteable merge command」 |
| opt-in + 审计 | `ARCHIVE_ALLOW_UNMERGED=yes` + `RDDF_ARCHIVE_UNMERGED_REASON`（缺 reason 不生效）；审计落 `main_root`（与其它 bypass 同一落点） | 「opt-in with a reason … leaves an audit record」 |
| opt-in ≠ FORCE_BRANCH_DELETE | 两者同时出现 ⇒ 报错拒绝（组合 = 代码永久删除） | 「opt-in + FORCE_BRANCH_DELETE is refused」 |
| false 分支不新增 merge / commit | 合入门只做**判定**；既有 awk 守卫**已加固**（提取终点 = `mark_iteration_archived`，且只匹配**调用**而非字面 —— 注释里合法地提到这两个词） | `test_archive_with_openspec_tracked_false.bats` 的守卫用例 |
| cleanup 三态 + 文案 | `cleanup_worktree_and_branch` 返回 0/1/2；「✅ Worktree 已删除」**只在真删成功时打印**；三种失败态分别给消息（未注册孤儿目录 / 已注册但 remove 失败 / 分支 ref 缺失） | `test_archive_trunk_gate.bats` 的 3 个 cleanup 用例 |
| tracked 路径 cleanup 不再让归档失败 | `cleanup … || echo "⚠️ 归档已完成，但 worktree/分支清理未完全成功"` | 同上 |
| 既有测试修改 | 「未合入 ⇒ status 0」改为「已合入 ⇒ 0」+ 新增「未合入 ⇒ 拒绝」 | `test_archive_with_openspec_tracked_false.bats` |
| spec delta | 三份已采纳 spec 就地改写（见下） | ⚠ **本仓 `openspec/` 被 gitignore**（`git.openspec_tracked: false`）⇒ 规范文本**不入版本库** ⇒ delta 的**权威落点是已签批的 ADR-0061**（决策 2/7 + V-11）与本记录 |
| 文档 | `skills/rdd-builder/SKILL.md` 新增「P3 归档门」段（两道门的区分 + 不代劳合并 + opt-in）；`docs/architecture/workflow-phases.md` 的 Hard gates 同步 | grep 可查 |
| 旁路清单 | ADR-0061 的 Consequences 段 | 轻量 inline 分支 / rdd-quick 直归档 / 手工 `openspec archive` 三条**不受**本门保护 |

### 实现中发现的一处 ADR 缺陷（已补正，决策未变）

ADR-0061 决策 2 的**判定表缺了「未合入」这一档** ⇒ 按表的字面读法，「未合入且内容不等价」会落到
「无法判定 ⇒ 放行」⇒ **这道门永远不会拒绝**（与 ADR 的目的、与决策 4 的 opt-in 覆盖面条款、
与 V-4 全部矛盾）。⇒ 已按 ADR 的**决策正文**（未合入 ⇒ 拒绝）实现，并在 ADR 的决策节补上
「### 修订 2026-11-18（表格补正）」说明（**表格补正，决策未变**）。

### 变异验证（判别力）

| 变异 | 结果 |
|---|---|
| 「未合入 ⇒ 拒绝」改回放行 | **5 个用例变红** |
| 去掉 dirty 检查 | 2 个变红 |
| 去掉 opt-in | 2 个变红 |

### 新增/修改的测试

- 新增 `tests/integration/test_archive_trunk_gate.bats`（14 例）：判定矩阵 + opt-in + FORCE 冲突 +
  cleanup 三态 + 主仓守卫。
- 修改 `tests/integration/test_archive_with_openspec_tracked_false.bats`（7 例）：「已合入 ⇒ 0」、
  新增「未合入 ⇒ 拒绝」、awk 守卫加固（提取终点 + 只匹配调用）。

### 遗留（不在本项范围）

- lightweight 路径的同类缺口 ⇒ `fix-lightweight-branch-and-archive`（新立项）。
- false 路径既有的步骤省略（issue 关闭 / tasks 完成度门 / L2 / sidecar / `archive_commit_sha` 为空）
  ⇒ ADR-0061 的 Consequences 已如实记录，本项不修。
- `openspec/specs/**` 的全局退役 stage 残余（204 处 / 47 份 spec）⇒ ADR-0036 修订的 backlog。

---

## 实施记录 · 第二轮（2026-11-18，architect 复核后的补完）

### 背景

2026-11-17 的实施把 ADR-0061 落地，但 **ADR 的判定表漏了一行**（缺「未合入 ⇒ 拒绝」这一档）⇒
architect 复核时补正了表格，并顺带发现**实现的四处不满足已签批契约**（决策未变，是实现与契约的落差）：

| 差距 | 违反的契约 | 本轮修法 |
|---|---|---|
| 调用点 `if ! archive_premerge_check …` ⇒ 返回码 `2`（⑤ 无法判定 ⇒ 放行）被折叠成**拒绝** | 表 ⑤ / Consequences / 备选 C / 立项 AC（**四处**都写「放行」）+ V-14 | 调用点改为按返回码**分别**消费：`0` ⇒ 放行 / `1` ⇒ 拒绝（return 1）/ `2` ⇒ **放行 + 警告**（警告由函数打印） |
| ⓪（分支 ref 缺失）的路径仍打合并命令 | 决策 3 第四支 + V-5(d)（「没有分支可合并」） | `_premerge_refuse` 增加 `kind` 参数：`missing` / `dirty` **不打**合并命令；只有 `unmerged` 打 |
| 非 git 仓库落进 ⓪ ⇒ 报「分支不存在（可能已被上一次归档的 cleanup 删除）」 | ⑤ 行的「非 git 仓库 ⇒ 放行 + 警告」+ ⓪ 的前置约定 | 新增 **⓪a 前置检查**：`git rev-parse --git-dir` 失败 ⇒ 归 ⑤（放行 + 警告），**不进** ⓪ |
| dirty 路径恒给「先提交 + 合入命令」，未按「分支有提交 / 无提交」分叉 | 决策 3 第二支 + V-5(c) | 新增 `_branch_has_new_commits`：分支**有**提交 ⇒ 给**两步**（先 commit 再 merge）；**无**提交 ⇒ 只给 commit 命令（「该分支目前没有新提交 ⇒ 提交之后才谈得上合入」） |
| `docs/architecture/gates-and-quality.md` 未写「合入门」 | V-12（点名三处；决策 8 原先只列两处） | 新增「The archive has TWO gates — do not confuse them」段（两道门的判什么 / 在哪 + 「The archive never merges for you」+ 判定顺序 + opt-in + **三条旁路路径不受保护**） |

### 变更落点

| 文件 | 改动 |
|---|---|
| `_lib/archive.sh` | `archive_premerge_check`（⓪a 前置 + 三态消费注释）、`_branch_has_new_commits`（新 helper）、`_premerge_refuse`（`kind` 参数 + 指引分叉）、`archive_change` 的 false 分支（按返回码消费） |
| `tests/integration/test_archive_trunk_gate.bats` | +5 例（ref-missing 不打合并命令 / 非 git 仓库归 ⑤ / dirty 分叉 ×2 / 文档契约）⇒ **19 例** |
| `tests/integration/test_archive_with_openspec_tracked_false.bats` | +1 例（**调用点级**：stub `archive_premerge_check` 返回 `2` ⇒ 断言 `archive_change` 仍返回 0）⇒ **8 例** |
| `docs/architecture/gates-and-quality.md` | 新增「两道门」段 |
| `tests/integration/test_rdd_quick_isolation.bats` | sha256 锁**第六次**重取（`_lib/archive.sh` 又变） |

### 变异验证（判别力）

| 变异 | 结果 |
|---|---|
| 调用点改回 `if ! …`（三态折叠） | **1 例红**（V-14 的调用点级用例） |
| ⓪ 路径又打合并命令 | **2 例红**（ref-missing + dirty 无提交） |
| 去掉 ⓪a 前置（非 git 落进 ⓪） | **1 例红** |
| 去掉 dirty 分叉 | **1 例红** |

⇒ 4 个变异全部被捕获；还原后 **27 例全绿**。

### 连带同步（planner 侧，本轮之前已做）

- `fix-lightweight-branch-and-archive.md` 与本文件的「复用清单」从「四项」改为**五项**
  （⓪/②/③/**④未合入 ⇒ 拒绝**/⑤无法判定）—— 漏掉 ④ 会让 lightweight 路径**不拒绝未合入分支**；
- 两份文件的立项名漂移（4 处）⇒ `fix-execution-mode-decision` → `fix-lightweight-branch-and-archive`；
- 本文件 What Changes §1 加「**本 ADR 覆盖声明**」（草案的 tip-to-tip `git diff --quiet`、旧判定顺序、
  「ref 缺失 ⇒ 放行」均已被 ADR-0061 取代）。

### 仍未落地（不在本项范围）

- **lightweight 路径的同类缺口** ⇒ `fix-lightweight-branch-and-archive`（draft）。
- **spec 全局残余（204 处 / 47 份 spec）** ⇒ `fix-spec-residue-guard`（draft，守卫 + 台账）。
- **回归门「超时未评估」的覆盖率流失** ⇒ `fix-bats-per-file-timeout`（draft）。
