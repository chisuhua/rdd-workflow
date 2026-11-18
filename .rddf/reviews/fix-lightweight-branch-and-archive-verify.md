# 验收报告 —— `fix-lightweight-branch-and-archive`

> 验收者：verifier 角色（opencode build agent 的角色矩阵）
> 判据来源：① 用户「继续推进」；② `.rddf/improvements/fix-lightweight-branch-and-archive.md` 的
> `## Acceptance`（**16 条**，全部可判定）；③ 已签批 `docs/adr/ADR-0036-…md` 的 V-G（lightweight 可用性的
> 前提：建分支 + 归档路径补齐）
> 已用轮次：**1**
> 结论：**16/16 pass，0 ac-fail。** 2 条观察（不阻断）+ 1 条需 architect 裁定的文档过期项（不阻断）。

## 一、验证顺序（早失败早停）

| 步 | 检查 | 命令 / 结果 |
|---|---|---|
| 1 | 静态 | `bash -n _lib/archive.sh` ✅ / `bash -n skills/rdd-builder/scripts/phase2_execute.sh` ✅ / `bash -n skills/rdd-builder/scripts/phase3_archive.sh` ✅ / `ast.parse(_lib/builder_deps.py)` ✅ |
| 2 | 单元测试 | `pytest tests/unit/test_builder_deps.py test_builder_deps_mode_inputs.py test_execution_mode.py` ⇒ **37 passed**；全量 unit ⇒ **3413 passed / 3 skipped** |
| 3 | 集成 / 端到端 | 本项新文件 **25 ok / 0 not-ok / 0 skip**；既有破坏面三个文件 **12 / 6 / 8 ok**；全量 integration ⇒ **196 passed** |
| 4 | 边界与错误路径 | **变异注入复核**：verifier 侧独立复跑 2 例（去掉提交归属检查 / 能力开关回 `False`）⇒ **2/2 被捕获**；builder 侧记录的 16/16 见 improvement 的实施记录 |
| 5 | 全量回归门 | `./test.sh --full --regression --no-color` ⇒ **ALL PASSED / EXIT=0**（新增失败 **0**；已知失败 11；超时未评估 2） |
| 6 | 遗留清扫复核 | ✅ 见 §四 |

> ⚠ **分流判定**：`rdd-verifier` skill 的三条件**不满足**（本仓 `openspec/` 被 gitignore，本项以
> `.rddf/improvements/` 为权威落点，无 `openspec/changes/<name>/` + `## Acceptance` 段）⇒ 走**本地验收**
> 1–6 步。本地验收的额外门（`iteration.json` 的 `tasks_done == tasks_total > 0`）**不适用**：本项不是
> openspec change，`iteration.json` 中没有该项。

## 二、逐条判定 + 证据（16 条）

| # | AC | 判定 | 证据（工具取证） |
|---|---|---|---|
| 1 | lightweight 建 `openspec/<change>` 分支、**起点 = 默认分支 tip**，且 P2 在该分支上执行 | ✅ pass | `_lib/archive.sh:452` `git checkout -b "$branch" "$default_tip"`（**显式起点**，非裸 `checkout -b`）；bats「creates … at the default branch tip」断言 `git rev-parse openspec/demo == tip_before` + `git branch --show-current == openspec/demo`；「the first implementation commit sits on the default tip」断言 `openspec/demo^ == 默认 tip` |
| 2 | 分支已存在三档政策可判定；`checkout` 失败且 worktree 也建不起来 ⇒ **exit 3 + 明确文案** | ✅ pass | `_lib/archive.sh::lightweight_branch_prepare` 返回 0/1/2（三档）；`phase2_execute.sh` 的降级分支在 worktree 创建失败时 `exit 3` 并打印原因 + 「请先删除或改名残留分支」；bats「an existing branch at the default tip is reused」+「pointing elsewhere fails closed to worktree」（断言 `status == 3`）+ helper 级三态用例（`create=0` / `reuse=0` / `failclosed=1`） |
| 3 | **提交归属检查生效**：零提交 ⇒ 拒绝 + stderr 含提交命令 | ✅ pass | `_lib/archive.sh:504` `lightweight_commit_ownership_check`；`phase3_archive.sh:218` 调用点 `… \|\| exit 3`；bats「a branch with NO commit of its own is refused」（断言 `status == 3` + 输出含 `commit -m` + change 目录仍在）+「an empty-shell branch created by P2 is refused (base sha path)」 |
| 4 | handoff 的 `mode` / `reason` 与**真实模式**一致（fail-closed 时 mode 改写 + reason 非空） | ✅ pass | `phase2_execute.sh` 在降级**当场**写 handoff（不是等成功路径），并把 `branch_base_sha` 一并写入；bats「fails closed to worktree」断言 `execution_mode_decision.mode == worktree` 且 `reason` 非空；「the base sha is recorded in the handoff」 |
| 5 | lightweight 归档路径在 `openspec archive` **之前**跑合入门；未合入 ⇒ 拒绝 + 合并命令；**拒绝路径 HEAD 仍为默认分支** | ✅ pass | `phase3_archive.sh` 的步骤序 (a)AC 门 → (b)`switch_to_default_branch` → (c)归属 → (d)合入判定 → (e)`openspec archive`；bats「the refusal path leaves HEAD on the default branch」（**夹具让 HEAD 先停在实现分支**，拒绝后断言 HEAD == master —— 去掉 (b) 该用例变红） |
| 6 | **dirty 语义分叉**：主仓无关脏文件 ⇒ 只警告不拒绝；实现未提交 ⇒ 由归属检查拒绝 | ✅ pass | `phase3_archive.sh` 的显式警告「⚠️ lightweight: 主仓存在未提交改动（不据此拒绝 …）」+ 合入门以 `wt_path=""` 调用（其 dirty 判据天然不适用）；bats「unrelated dirty files … do NOT refuse」（断言 `status == 0` 且输出含该警告）+「tracked=false」用例（脏文件存在时仍走到合入门） |
| 7 | **2×2 矩阵**：lightweight×true ⇒ `commit_archive_moves` **被调用**；lightweight×false ⇒ **不被调用**；worktree 两格行为不变 | ✅ pass | `phase3_archive.sh` 的条件调用 `if [ "$OPENSPEC_TRACKED" != "false" ] …`；bats「tracked=true: the archive-moves commit IS created」（`git log` 含 `archive(demo): archive completed`）+「tracked=false」（**调用级**断言：输出中不出现 `commit_archive_moves`，且无该提交）；worktree 两格由 `test_archive_with_openspec_tracked_false.bats`（8 ok）与 `test_archive_trunk_gate.bats`（19 ok）覆盖 |
| 8 | 归档后：分支**已合入**、**已删除**、`iteration.json` 进入 `archived` 且 `archive_commit_sha == 默认分支 tip`（非空） | ✅ pass | `phase3_archive.sh:272-273`（`_archive_sha=$(git -C … rev-parse HEAD)` → `mark_iteration_archived`）；bats「merges the branch, deletes it, syncs iteration.json」三断言（`merge-base --is-ancestor` / `rev-parse --verify refs/heads/…` 非零 / `iteration.json` 的 status 与 sha == `git rev-parse master`） |
| 9 | 归档路径调用 `post_archive_cleanup`；分支清理失败 ⇒ **只警告、归档仍成功** | ✅ pass | `phase3_archive.sh` 步骤 (f) `cleanup_worktree_and_branch … \|\| echo "⚠️ 归档已完成，但分支清理未完全成功"`、(i) `post_archive_cleanup`；bats「runs post_archive_cleanup（residue plan file is removed）」+「a failed branch cleanup only warns（`rc=1` + 主仓完好）」 |
| 10 | `wt_path_for_branch == main_root` 时**不执行** `git worktree remove` | ✅ pass | `_lib/archive.sh:332/604` 的三重守卫 `[ -n "$wt_path" ] && [ "$wt_path" != "/" ] && [ "$wt_path" != "$main_root" ]`；lightweight 传**空** `wt_path`；bats「the main repo is never treated as a worktree」（并已用「去掉该守卫」的变异验证用例会红） |
| 11 | **abort 语义**：P2 失败/放弃后主仓 HEAD 回到默认分支；残留分支可复用但复用前校验 tip | ✅ pass | `phase2_execute.sh` 的 `trap … EXIT` → `_restore_head_on_abort`（仅在 lightweight 且已知默认分支时动作）；复用校验 = `lightweight_branch_prepare` 的 tier-2（tip != 默认 tip ⇒ fail-closed）；bats「P2 abort: a failing P2 returns the main repo HEAD to the default branch」 |
| 12 | **e2e**：注入 lightweight handoff → P2 → 写 verdict cache → 真跑 `rddf rdd-verify`（`state=passed` / `archive_ready=true`）→ P3 → `archived` | ✅ pass | bats「e2e lightweight: handoff → P2 → rdd-verify → P3 → archived」：真跑 `python3 -m _lib.cli.rdd_verify_cmd`（断言退出 0 + 输出含 `passed`）→ P3（断言 change 目录消失、archive 目录出现、`iteration.json` 的 status == `archived`）。夹具按 AC 要求**注入**了 handoff（不依赖 P1.5 自然产出） |
| 13 | 两份已采纳 spec 的 delta 已写 | ✅ pass | `openspec/specs/archive-openspec-tracked-skip-commit/spec.md`：新增「lightweight branch sequence」+「lightweight commit ownership」两个 scenario（`grep -c` = 2）；`openspec/specs/archive-auto-commit/spec.md:97-110`：lightweight MUST 的条件式调用 + 2×2 两格；`openspec validate --all` ⇒ **152 passed / 13 failed（与基线一致，无新增失败）** |
| 14 | **既有测试的预期破坏面已处理** | ✅ pass | `test_rdd_builder_phase3_archive.bats` 夹具补一次分支提交 ⇒ **12 ok**；`test_phase3_archive_delegation.bats` 的 `post_archive_cleanup` 守卫改为 awk 限定 worktree 分支 + 新增「枚举序列完整性」用例 ⇒ **6 ok**；`test_phase2_commit_gate.bats` **8 ok**；`test_rdd_quick_isolation.bats` 的 sha256 锁第七次重取（4 ok） |
| 15 | **反向守卫（归 D 项，本项只登记不证伪）**：登记在审稿记录里 | ✅ pass | improvement 的「依赖登记」段：`acceptance-8` 推翻登记（`grep -c acceptance-8` = 5）+「本项不声称能证明 D 项的 V-G」+ `LIGHTWEIGHT_EXECUTION_READY` 翻正与回滚方式 |
| 16 | `./test.sh --unit` + 全量回归门 + 两个 bats 文件全绿 | ✅ pass | 全量回归门 **ALL PASSED / EXIT=0**（新增失败 0）；unit 3413 passed；`bats test_rdd_builder_phase3_archive.bats`（12）+ `bats test_lightweight_branch_and_archive.bats`（25） |

## 三、失败项与路由建议

**无 ac-fail 项。** 2 条观察 + 1 条需 architect 裁定（均不阻断）：

### 观察-1（不阻断）：spec delta 的守卫在 CI 里会 skip

`test_lightweight_branch_and_archive.bats` 的两条 spec-delta 用例以 `[ -f <spec> ] || skip …` 起头 ——
本仓 `openspec/` 是 **untracked**（`git.openspec_tracked: false`）⇒ 干净 clone / CI 里这两个文件不存在，
用例会 skip（本机存在 ⇒ 实跑并通过）。这是**既有约束**（同类守卫在整个测试集里都是这个形态），
且 delta 的权威落点是已签批 ADR + improvement 的实施记录 ⇒ 不构成假保证，但**覆盖率在 CI 里确实为零**。
如需在 CI 里也生效，得让 `openspec/specs/**` 进版本库（属 `fix-spec-residue-guard` 的范围，
`openspec/specs/**` 的 204 处 stage 残余也在那边）。

### 观察-2（不阻断）：回归门「超时未评估」2 个文件（既有、非本 change 引入）

`./test.sh --full --regression` 报「⚠️ 超时未评估: 2 个 bats 文件」。上一轮已逐个复现定位
（`timeout 30 bats <file>` ⇒ rc=124）：`test_arch_env_check_extraction.bats` 与
`test_cross_repo_impact_detection.bats` —— **两者都不在本 change 的 diff 内**（本 change 触及的 bats 文件是
`test_lightweight_branch_and_archive` / `test_rdd_builder_phase3_archive` / `test_phase3_archive_delegation` /
`test_phase2_commit_gate` / `test_rdd_quick_isolation`），且 `tests/KNOWN_FAILURES.txt` 已把前者登记为
「30s per-file 超时过紧」的既有项。已立项 `fix-bats-per-file-timeout`（draft）跟踪。

### 需 architect 裁定（不阻断）：ADR-0036 的一处事实陈述已过期

`docs/adr/ADR-0036-rddf-project-yaml-config.md` 备选方案表 A 行仍写「`phase3_archive.sh` 的 lightweight
inline 分支**无 cleanup、无 iteration 同步**（文件自认 KNOWN GAP）⇒ lightweight 产出的 change 今天过不了
归档门」。本项落地后该**事实陈述**不再成立（V-G 的前提同时满足）。
⇒ 属**已签批 ADR 的正文**，verifier 与 builder 都不改；已在 improvement 的「仍未落地」段登记，路由 architect
决定是否追注。

## 四、遗留清扫复核

| 项 | 结果 |
|---|---|
| 新增 TODO / FIXME / XXX / HACK（代码文件） | ✅ 无（`git diff -- '*.sh' '*.py'` 匹配 0） |
| 注释掉的代码 | ✅ 无（新增行以 `#` 开头且含命令的匹配 0） |
| 临时调试日志（`set -x` / `DEBUG` / `console.log`） | ✅ 无 |
| 新增被 skip 的测试 | ✅ 无（`git diff -- tests/` 的 `skip` 增量为 0；本机跑 25 例 0 skip） |
| 未替换的 mock / 临时 fallback | ✅ 无（`openspec` 桩是测试固件；`declare -f` 守卫是**永久**防御，不是临时代码） |
| 临时代码 / 半截实现 | ✅ 无（`lightweight_branch_prepare` / `lightweight_commit_ownership_check` 均有调用点与用例） |
| 变异文件的还原 | ✅ 两次复核后逐字节还原（每次比对 `open(p).read() == open(bak).read()` 为 True） |
| 孤儿 worktree / 残留分支（本项产生） | ✅ 无（`git worktree list` 只有主仓；测试全部在 `mktemp -d` 内） |
| **本范围外的既有残留**（记录，不在本项清理） | ⚠ 分支 `openspec/test-change`（2026-11-17 由更早会话的测试创建，已完全合入 `master`，`git cherry` 为空 ⇒ 无内容风险） |
| 上一轮验收的 SHOULD_FIX（bypass 审计日志夹具污染） | ✅ 已由 builder 清理（32 条夹具条目，备份在 `/tmp/opencode/bypass-audit-backup.jsonl`） |

## 五、结论

**16/16 AC pass，0 ac-fail。** 关键行为（建分支 / 提交归属 / 合入判定 / 分支清理 / iteration 同步 /
post-archive cleanup / 2×2 矩阵）均有**工具证据**，且判别力经**变异注入**验证（builder 16/16 +
verifier 独立复核 2/2）。全量回归门 **ALL PASSED**（新增失败 0）。

**本项归档就绪。** 唯一需要外部角色动作的是 ADR-0036 的过期陈述（architect 裁定），不影响本项。
