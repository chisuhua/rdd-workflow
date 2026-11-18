# 验收报告 —— `fix-worktree-archive-branch-merge`（ADR-0061 的实现）· **第 2 轮**

> 验收者：verifier 角色（opencode build agent 的角色矩阵）
> 已用轮次：**2**（第 1 轮：2026-11-18 02:52，15/16 pass；本轮为 architect 复核后补完 5 条 AC 的复验）
> 本报告**取代**第 1 轮报告（第 1 轮的 16 条 AC 已在本轮重新取证并全部保留结论）。
> 判据来源：① 用户「继续推进」；② `.rddf/improvements/fix-worktree-archive-branch-merge.md` 的 `## Acceptance`（**21 条**：16 条原 AC + 5 条 2026-11-18 architect 复核新增）；③ 已签批 `docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md` 的 `## Verification`（V-1 ~ V-14 + V-1b）
> 结论：**21/21 pass，0 ac-fail。** 1 条 SHOULD_FIX（仓库卫生，非 AC）+ 2 条观察。

## 一、验证顺序（早失败早停）

| 步 | 检查 | 命令 / 结果 |
|---|---|---|
| 1 | 静态 | `bash -n _lib/archive.sh` ✅ / `bash -n skills/rdd-builder/scripts/phase3_archive.sh` ✅ / `ast.parse(_lib/builder_deps.py)` ✅ |
| 2 | 单元测试 | `pytest tests/unit/ -k "archive or builder_deps or execution_mode or iteration"` ⇒ **392 passed, 1 skipped**；`tests/unit/test_adr_index_gate.py` ⇒ **8 passed** |
| 3 | 集成 / 端到端 | `bats tests/integration/test_archive_trunk_gate.bats` ⇒ **19/19 ok**；`bats tests/integration/test_archive_with_openspec_tracked_false.bats` ⇒ **8/8 ok**（合计 27 例） |
| 4 | 边界与错误路径 | 4 个**变异注入**（见 §四）⇒ **4/4 被捕获**；还原后 md5 与原文件一致、`git status` 干净 |
| 5 | 遗留清扫复核 | ✅ 见 §六 |
| — | 全量回归门 | `./test.sh --full --regression --no-color` ⇒ **ALL PASSED / EXIT=0**（新增失败 **0**；已知失败 11；pytest unit 3413 passed / 3 skipped；pytest integration 196 passed） |

> ⚠ **分流判定**：`rdd-verifier` skill 的 canonical preconditions **不满足**（`openspec/changes/fix-worktree-archive-branch-merge/` 不存在 —— 本仓 `openspec/` 被 gitignore，本项以 `.rddf/improvements/` + 已签批 ADR 为权威落点）⇒ 走**本地验收 1–5 步**。
> ⚠ **本地验收的额外门**（`iteration.json` 的 `tasks_done == tasks_total > 0`）**不适用**：本项不是 openspec change，`iteration.json` 的 25 条记录中无本项。

## 二、逐条判定 + 证据（21 条）

### A. 原 16 条 AC

| # | AC | 判定 | 证据（工具取证） |
|---|---|---|---|
| A1 | **spec delta**（两份 spec 解耦「跳过 commit」与「feature 分支合并」）+ `archive-auto-commit` 正向重指向 | ✅ pass | `openspec/specs/complete-project-yaml-config-gaps/spec.md:241` 含 `archive_premerge_check` + 「the archive never merges on the operator's behalf」；`archive-openspec-tracked-skip-commit/spec.md:40` 的顺序 scenario 已含「`switch_to_default_branch`, the merge-status check (`archive_premerge_check`), `openspec archive`, `cleanup_worktree_and_branch`, `mark_iteration_archived`」；`archive-auto-commit/spec.md:85` 的 Requirement 已重指向 `rdd-builder` P3。⚠ 本仓 `openspec/` 被 gitignore ⇒ 文本不入版本库，**权威落点是已签批的 ADR-0061 + 本报告** |
| A2 | `archive_premerge_check` 为**具名函数**、返回三态（0/1/2） | ✅ pass | `_lib/archive.sh:296` 定义；`:298`（空参 ⇒ 2）、`:308`（非 git ⇒ 2）、`:319`（ref 缺失 ⇒ 1）、`:352`（已合入 ⇒ 0）、`:364`（无法判定 ⇒ 2）、`:367`（内容等价 ⇒ 0）、`:377`（未合入 ⇒ 1）—— 7 个 return 点覆盖三态 |
| A3 | **接口契约：支持「无 worktree」模式**（`wt_path` 为空 ⇒ 跳过 dirty 判据） | ✅ pass | `_lib/archive.sh:323` 的守卫 `[ -n "$wt_path" ] && [ "$wt_path" != "/" ] && [ "$wt_path" != "$main_root" ]`；bats「already merged → allow」（`wt_path=""`）绿 |
| A4 | **内容等价用 patch-id 判据**（`git cherry`），非 tip-to-tip `git diff --quiet` | ✅ pass | `_lib/archive.sh:356-368` 用 `git cherry "$default_branch" "$branch"`，无 `diff --quiet`；bats「content-equivalent (squash-merge) → allow with a warning」绿 |
| A5 | 内容等价分支存在 ⇒ 放行 + 警告（squash-merge 不被永久锁死） | ✅ pass | 同上 `:366-369`（`grep -q '^+'` 为假 ⇒ 放行 + `⚠️ … 内容已进主干（patch-id 等价）`）；bats 用例绿 |
| A6 | worktree 内有未提交改动 ⇒ 拒绝（含噪声排除） | ✅ pass | `_lib/archive.sh:327-328`：`git status --porcelain --untracked-files=all` + `grep -vE "^(\?\? )?(openspec/changes/${change_name}/\|\.rddf/plans/)"`；bats「worktree dirty → refuse」+「the artifacts the system copies in do NOT count as dirty」两例绿 |
| A7 | 未合入 ⇒ `archive_change` 返回 1 → `phase3` 退出 3 → `rddf archive` 退出 1，stderr 含「尚未合入」+ 可复制命令 | ✅ pass | 链路：`_lib/archive.sh:373`（`❌ … 尚未合入`）+ `:427-428`（合并命令）→ `:858-861`（`rc -eq 1 ⇒ return 1`）→ `skills/rdd-builder/scripts/phase3_archive.sh:150-152`（`*) ⇒ exit 3`）→ `_lib/cli/archive_cmd.py:90-96`（非零 ⇒ `return 1`）；bats「not merged → refuse + a copy-pasteable merge command」+ 端到端「UNMERGED branch → refused」绿 |
| A8 | opt-in：`ARCHIVE_ALLOW_UNMERGED=yes` + `RDDF_ARCHIVE_UNMERGED_REASON` ⇒ 放行**且**留 bypass 审计；缺 reason 不生效 | ✅ pass | `_lib/archive.sh:406-425`（缺 reason ⇒ `return 1` 不放行；审计经 `_lib/bypass_audit.sh::audit_bypass_log`，落 `RDDF_PROJECT_ROOT="$main_root"`）；bats「opt-in without a reason does NOT release」+「opt-in with a reason … leaves an audit record」绿 |
| A9 | opt-in 与 `FORCE_BRANCH_DELETE` 互斥 | ✅ pass | `_lib/archive.sh:411-415`（同时出现 ⇒ 报错 + `return 1`，理由「该组合 = 未合入的提交被永久删除」）；bats「opt-in + FORCE_BRANCH_DELETE is refused」绿 |
| A10 | **false 分支内不新增** `git merge` / `commit_archive_moves`；既有 awk 守卫**已加固** | ✅ pass | 守卫测试体（`test_archive_with_openspec_tracked_false.bats` 第 8 例）提取终点 = `mark_iteration_archived`（注释明写旧守卫「stopped at the FIRST standalone `fi`」会退化且仍 PASS），且只匹配**调用**（`^[[:space:]]*(commit_archive_moves[[:space:]]|git[[:space:]]+merge[[:space:]])`，避开 `git merge-base` 与注释里的词）；绿 |
| A11 | `cleanup_worktree_and_branch` 只在真删成功时打印「✅ Worktree 已删除」 | ✅ pass | `_lib/archive.sh:459-460`（成功才 echo）/ `:461-473`（失败 ⇒ 失败原因 + 残留路径 + 修复指引）；bats「prints 'Worktree 已删除' ONLY when the removal really happened」绿 |
| A12 | worktree 的三种失败态分别给不同消息 | ✅ pass | `_lib/archive.sh:467-471`：未注册 ⇒ `孤儿目录 … rm -rf / git worktree prune`；已注册但失败 ⇒ `git worktree remove --force`；分支 ref 缺失不计入（`:476-488` 走分支删除态）。bats「an unregistered residual directory gets its own message」+「never removes the MAIN repo」+「an unmerged branch is kept (return 1) unless FORCE_BRANCH_DELETE=yes」三例绿 |
| A13 | tracked 路径的 `cleanup … \|\| return 1` 不再让「归档已成功」整体失败 | ✅ pass | `_lib/archive.sh:917-919`：`\|\| echo "⚠️ 归档已完成，但 worktree/分支清理未完全成功（见上）"`（false 路径 `:877` 为 `\|\| true`，两侧语义一致） |
| A14 | **修改**既有测试文件：原「未合入 ⇒ status 0」改为「已合入 ⇒ 0」+ 新增「未合入 ⇒ 拒绝」 | ✅ pass | `test_archive_with_openspec_tracked_false.bats` 第 1 例「openspec_tracked=false (YAML bool) skips git merge/commit」（构造含 `git merge --no-ff` ⇒ 已合入 ⇒ 0）+ 第 5 例「UNMERGED branch → refused」 |
| A15 | 旁路清单成文并逐条标注是否受门保护 | ✅ pass | `docs/adr/ADR-0061-…md:140`：三条旁路（`phase3_archive.sh` 的 lightweight inline 分支 / `phase0_approval.sh` 的 rdd-quick 直归档 / 手工 `openspec archive`）均标「**不受门保护**」，并把 lightweight 指向 `fix-lightweight-branch-and-archive` |
| A16 | 文档：`skills/rdd-builder/SKILL.md` P3 段 + `docs/architecture/workflow-phases.md` 写明「archive 不代劳合并」 | ✅ pass | 三处均含 `archive_premerge_check` / 合入门 / never merges：`skills/rdd-builder/SKILL.md`、`docs/architecture/workflow-phases.md`、`docs/architecture/gates-and-quality.md:30-51`（「The archive has TWO gates — do not confuse them」） |

### B. 2026-11-18 architect 复核新增的 5 条 AC

| # | AC | 判定 | 证据（工具取证） |
|---|---|---|---|
| B1 | **调用点按返回码消费（V-14）**：`0` ⇒ 放行；`1` ⇒ 拒绝；`2` ⇒ **放行 + 警告** | ✅ pass | `_lib/archive.sh:854-861`：`_premerge_rc=0` → `archive_premerge_check … \|\| _premerge_rc=$?` → `if [ "$_premerge_rc" -eq 1 ]; then return 1; fi`（**2 不触发拒绝**）。判据形态 = **调用点级 stub**：`test_archive_with_openspec_tracked_false.bats` 第 6 例 stub `archive_premerge_check() { …; return 2; }` ⇒ 断言 `archive_change` 仍返回 0 且 `openspec archive` 被调用 ⇒ 绿 |
| B2 | **⓪ 的路径不给合并命令（V-5(d)）** | ✅ pass | `_lib/archive.sh:316` 以 `kind="missing"` 调 `_premerge_refuse`；`:427-429` 仅 `kind = "unmerged"` 才打 `merge --no-ff`。判据形态 = **否定断言**：bats「the ref-missing path gives NO merge command」断言 `[[ "$output" != *"merge --no-ff"* ]]` 且含 `reflog` ⇒ 绿 |
| B3 | **非 git 仓库归 ⑤（不落进 ⓪）** | ✅ pass | `_lib/archive.sh:302-309`：`git rev-parse --git-dir` 失败 ⇒ 打印「不是 git 仓库（无法判定是否已合入 → 放行）」+ `return 2`。bats「a non-git directory is 'cannot decide' (2), not 'branch missing' (1)」断言 `status -eq 2` + 含「不是 git 仓库」+ **不含**「不存在」⇒ 绿 |
| B4 | **dirty 路径按「分支有提交 / 无提交」分叉（V-5(c)）** | ✅ pass | `_lib/archive.sh:385-393`（`_branch_has_new_commits`，`rev-list --count "$default..$branch"`，「无法判定」按「无」处理 ⇒ 取更窄的提交建议）→ `:331-343` 分叉：有提交 ⇒ 两步（`commit -m` + `merge --no-ff`）；无提交 ⇒ 只给 `commit -m` + 「该分支目前没有新提交 ⇒ 提交之后才谈得上合入」。两条 bats 用例分别断言命令条数（「WITH commits → two-step guidance」/「with NO commits → commit-only guidance」，后者含否定断言 `!= *"merge --no-ff"*`）⇒ 绿 |
| B5 | **`docs/architecture/gates-and-quality.md` 写明「合入门」与「archive 不代劳合并」（V-12）** | ✅ pass | `docs/architecture/gates-and-quality.md:30-51`：两道门对照表（Trunk gate `archive_premerge_check` vs AC archive gate `archive_gate_check`）+「**The archive never merges for you.**」+ 六步判定顺序 + opt-in 说明 + 三条旁路路径。bats「docs: the gates catalogue names the trunk gate and 'the archive never merges'」⇒ 绿 |

## 三、判别力（变异注入）—— 4/4 被捕获

| 变异 | 期望 | 实测 |
|---|---|---|
| 调用点改回 `if ! archive_premerge_check …`（三态折叠） | B1 红 | ✅ `not ok 25 … trunk gate state 2 (cannot decide) does NOT fail the archive (ADR-0061 V-14)` |
| `kind` 守卫去掉（⓪ 路径又打合并命令） | B2 / B4 红 | ✅ `not ok 15 … ref-missing path gives NO merge command` + `not ok 18 … commit-only guidance` |
| 去掉 ⓪a（非 git 前置） | B3 红 | ✅ `not ok 16 … a non-git directory is 'cannot decide' (2)` |
| 去掉 dirty 分叉（恒走两步） | B4 红 | ✅ `not ok 18 … dirty worktree with NO commits on the branch → commit-only guidance` |

**还原校验**：`_lib/archive.sh` md5 `2272e25e175164b81a2d4c1b35001abc` 前后一致，`git status --short` 为空 ⇒ 无残留改动。

## 四、失败项与路由建议

**无 ac-fail 项。** 1 条 SHOULD_FIX（**仓库卫生，非 AC 违规**）+ 2 条观察：

### SHOULD_FIX-1（路由：builder）—— bypass 审计日志被测试夹具污染

`.rddf/state/.bypass-audit.jsonl`（gitignored 的运行时审计日志）现存 **32 条**记录，**全部**来自测试夹具
（`SKIP_RDD_VERIFIER` / `TEST_VAR` + reason `matrix fixture` / `test reason` / `hotfix for prod incident #123`
+ change `no-branch-change` / `test-change` / `matrix-change`）—— 来源是 `tests/integration/test_archive_gate_cache_root.bats:178`
的 matrix H 用例（`archive_gate_check` 把审计根解析到**仓库根**而非测试 tmpdir ⇒ 夹具写进了真实审计日志）。

⚠ 该文件语义上是「**确实发生过旁路**」的审计凭据 ⇒ 夹具条目会让真实审计记录失真。
第 1 轮报告曾清理过一次（当时 2 条），本轮又累积到 32 条。
**处置**：清空该文件（或只删夹具条目）。**verifier 不代改**（`.rddf/state/.bypass-audit.jsonl` 不在 verifier 的写集内）⇒ 路由 builder。

### 观察-1（不阻断）：dirty 噪声排除的范围比 AC 原文宽

AC A6 写「`.rddf/plans/<name>.md` 不算未提交改动」，实现（`_lib/archive.sh:328`）排除的是**整个** `.rddf/plans/`
⇒ 其它 change 的 plan 文件若在**本 change 的 worktree 里**是未跟踪的，不会被判 dirty（该仓 `.rddf/plans/` 是**被跟踪**的
目录，见 `.gitignore:9`；已跟踪且被修改的文件仍会被判 dirty ⇒ 只有「未跟踪的其它 plan」被放过）。
不影响任何 AC 的判定口径（AC 的意图「系统复制的 artifacts 不算 dirty」已满足）；建议后续收窄为 `\.rddf/plans/${change_name}\.md`。

### 观察-2（不阻断）：回归门「超时未评估」2 个文件（**既有、非本 change 引入**）

全量回归门报「⚠️ 超时未评估: 2 个 bats 文件」。本轮**逐个复现并定位**（`timeout 30 bats <file>` ⇒ 退出码 124）：

| 文件 | rc | 是否本 change 触及 |
|---|---|---|
| `tests/integration/test_arch_env_check_extraction.bats` | 124 | ❌ 不在本 change 的 diff 内 |
| `tests/integration/test_cross_repo_impact_detection.bats` | 124 | ❌ 不在本 change 的 diff 内 |

其余 4 个候选（`test_install_with_docs` / `test_known_failures_baseline` / `test_no_spec_workflow_residue` / `test_rdd_doctor`）单独跑 **rc=0** ⇒ 只是被前序文件的负载拖累，未超时。
`tests/KNOWN_FAILURES.txt` 的注释已把 `test_arch_env_check_extraction.bats`（两次 `cp -r "$REPO_ROOT"`）登记为「30s per-file 超时过紧」的既有项。
⇒ 已立项 **`fix-bats-per-file-timeout`**（draft）跟踪，本项不修。

## 五、回归门与既有基线的对照

| 指标 | 值 |
|---|---|
| `./test.sh --full --regression` | **ALL PASSED**（EXIT=0） |
| bats 新增失败 | **0**（已知失败 11 —— 全部在 `tests/KNOWN_FAILURES.txt` 基线内；`actual` 的 3 个失败名逐条命中基线） |
| bats 超时未评估 | 2（既有，见观察-2） |
| pytest unit | 3413 passed / 3 skipped |
| pytest integration | 196 passed |

## 六、遗留清扫复核

| 项 | 结果 |
|---|---|
| 新增 TODO / FIXME / XXX / HACK | ✅ 无。`git diff 26fcd24~1..HEAD` 的匹配项**全部**落在 `.md` 散文里（描述审计结论），代码中零命中 |
| 注释掉的代码 | ✅ 无（`git diff` 中新增行以 `#` 开头且含命令的匹配：0） |
| 临时调试日志（`set -x` / `DEBUG` / `print(`） | ✅ 无（新增行匹配：0） |
| 新增被 skip 的测试 | ✅ 无（本项改动的 3 个测试文件中 `skip` 增量 = 0） |
| 未替换的 mock / 临时 fallback | ✅ 无（`setup_openspec_stub` 是测试固件，非生产代码） |
| 临时文件 / 半截实现 | ✅ 无（本轮验证用的备份与变异脚本在 `/tmp/opencode/`，仓库内无残留） |
| 变异注入后的还原 | ✅ md5 一致 + `git status` 干净 |
| **本范围外的仓库残留**（记录，不在本项清理） | ⚠① `.rddf/state/.bypass-audit.jsonl` 32 条夹具条目（→ SHOULD_FIX-1，路由 builder）；⚠② 遗留分支 `openspec/test-change`（**2026-11-17 12:39** 由更早会话的测试创建，已完全合入 `master`，`git cherry` 为空 ⇒ 无内容风险，仅为残留 ref） |
| `.rddf/state/trace/*.jsonl` | ⚠ 本轮测试产生的 trace 文件（gitignored，`guide-arch` / `execute` 轨迹）—— **既有测试行为**，非本 change 引入；不影响版本库 |

## 七、结论

**21/21 AC pass，0 ac-fail。** 5 条 architect 复核新增 AC（B1–B5）全部落地且**判别力经变异注入验证**
（4/4 变异被捕获）；16 条原 AC 逐条重新取证，结论与第 1 轮一致。ADR-0061 的判定表补正已由 architect 签批
（oracle REJECT → 逐条处置 → critic APPROVE_WITH_CONDITIONS，0 BLOCKER），本项**无残留 ac-fail**。

**唯一待办**：SHOULD_FIX-1（bypass 审计日志夹具污染）—— 仓库卫生问题，路由 builder 清理，不影响本项的归档就绪判定。
**B 项归档就绪**（该清理可与下一项 `fix-lightweight-branch-and-archive` 的实施一并处理）。
