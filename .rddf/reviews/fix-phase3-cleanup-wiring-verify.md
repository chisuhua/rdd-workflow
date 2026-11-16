# 验收报告：fix-phase3-cleanup-wiring

> 验收者：verifier（角色）｜对象 `openspec/fix-phase3-cleanup-wiring` @ `8f11e25`（已合入 master，基线 94370b7）
> 验收时间：2026-11-17｜**已用轮次：1 / 3**

判定来源：`proposal.md` 的 `## Acceptance`（7 条）。verdict cache：`.rddf/state/verifier/.ac-verdict-fix-phase3-cleanup-wiring.json`。

| AC | 证据 | 判定 |
|---|---|---|
| 1 直接执行非零退出 + 说明「库，需 source」 | `bash _lib/post_archive_cleanup.sh <root> dummy` → **exit 2**，stderr `❌ post_archive_cleanup.sh is a library, not a script.` + 调用指引；bats ok 1 | pass 0.98 |
| 2 缺失 / source 失败 ⇒ stderr WARN（不再吞错） | bats ok 2（库复制到无 state.sh 的目录 ⇒ `state.sh not found` WARN）；源码已无 `2>/dev/null \|\| true` | pass 0.97 |
| 3 cleanup 失败不改变归档结果 | `post_archive_cleanup` 的返回码语义未变（`archive.sh:725` 的 `\|\| true` 未动）；WARN 走 stderr；bats ok 4/5 均 exit 0 | pass 0.96 |
| 4 e2e：正确调用 ⇒ 该提案移入「已实施」 | bats ok 4（`source` 后调用 ⇒ 行变为 `... \| 已实施 \|`） | pass 0.96 |
| 5 幂等：重复调用不产生重复行 | bats ok 5（两次调用后该名仅 1 行） | pass 0.97 |
| 6 `openspec_tracked=false` 形态 e2e 仍真绿 | fixture 的 archive 目录未被 git 跟踪（本仓 openspec/ 即此形态）；bats ok 4/5 在该形态下通过 | pass 0.95 |
| 7 `./test.sh --unit` + `test_post_archive_cleanup*.bats` 全绿 | `test_post_archive*.bats` **32 ok / 0 not ok**；pytest unit 3323 passed / 10 failed（**与基线 worktree 逐条相同**，根解析环境信号，见 D-1）；bats `--regression` 已知 11 / 新增 2（均为既有失败，主仓可复现） | pass 0.94 |

**结论：7/7 pass。**

## 偏差与补充

- **D-1**：AC-7 的「unit 全绿」在本仓不可满足（10 项 worktree 根解析环境失败，基线相同）。
- **D-2（critic SHOULD_FIX 已闭合）**：`state.sh` 的查找锚原本是 `$project_root/_lib/state.sh`，全局安装模式下 `_lib/` 在安装树 ⇒ 每次归档一条噪音 WARN。已改为自发现（项目副本优先 → 库自身目录），并新增「全局安装形态仍能同步」用例（bats ok 3）。

## 遗留清扫

无 TODO/半截实现/被 skip 的测试；清理逻辑（deleted/whitelist 清单）未动；未触及 `phase3` 侧调用点（已由 `fix-worktree-archive-path` 删除）。
