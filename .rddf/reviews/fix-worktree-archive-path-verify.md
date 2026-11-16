# 验收报告：fix-worktree-archive-path

> 验收者：verifier（角色）｜对象：`openspec/fix-worktree-archive-path` @ `25cee92`（已合入 master，基线 `0bcff93`）
> 验收时间：2026-11-16｜**已用轮次：1 / 3**

## 判定来源

`proposal.md` 的 `## Acceptance`（10 条，优先级 2）。verdict cache：`.rddf/state/verifier/.ac-verdict-fix-worktree-archive-path.json`（`codebase_commit = 25cee92`，10 条全 pass，`failed_acs: []`）；归档门完整性：`{"complete": true, "problems": [], "schema_version": 2}`；audit log 追加 1 行。

## 逐条判定（10/10 pass）

| AC | 证据 | 判定 |
|---|---|---|
| AC-1 worktree 分支不再 `cd wt && openspec archive` | `grep`：只剩 `:128 archive_change "$CHANGE_NAME" \|\| rc=$?`；`cd .rddf/wt/*` 消失；`openspec archive` 仅剩 lightweight 分支 `:141`。bats `test_phase3_archive_delegation` ok 2 | pass 0.97 |
| AC-2 不再调 `post_archive_cleanup` | `grep -c` = 0；bats ok 3 | pass 0.98 |
| AC-3 worktree×false 归档落主仓 | `test_phase3_archives_in_main_repo` ok 1：openspec 桩记录 `CWD=<main>` 且不等于 wt 路径 | pass 0.97 |
| AC-4 spec delta 合流 | 归档由主仓 CLI 执行（同上），本 change 的 P3 实跑后主仓 `openspec/specs/fix-worktree-archive-path/spec.md` 生成 | pass 0.94 |
| AC-5 worktree 与分支清理 | `test_phase3_archives_in_main_repo` ok 2 + `test_phase3_return_code_mapping` ok 3 | pass 0.97 |
| AC-6 tracked=true 行为不变 | `test_phase3_return_code_mapping` ok 3（main log 含 `feature work`、wt 清理）+ `test_archive_with_openspec_tracked_false` 6/6 | pass 0.97 |
| AC-7 返回码映射 + 透传 gate 文案 | 行为级：门拒绝⇒7 且输出含 `no valid verdict cache`；无新提交⇒3；成功⇒0。**变异验证**：去掉 `\|\| rc=$?` ⇒ 3 例全红 | pass 0.96 |
| AC-8 lightweight 行为不变 + 缺口注释 | 源码有 `# lightweight mode: inline archive` 与 `# KNOWN GAP ... neither the archive_change cleanup nor its iteration sync`；`test_rdd_builder_phase3_archive` 12/12 | pass 0.96 |
| AC-9 iteration 字段仍由 archive_change 写 | `_lib/archive.sh:625` 的 `mark_iteration_archived` 仍在 false 分支；phase3 不再写 iteration；handoff 记 archived（ok 3） | pass 0.93 |
| AC-10 回归命令全绿 | pytest unit 3323 passed / 10 failed（**与基线 worktree 逐条相同**，根解析环境信号）/ 2 skipped；`test_rdd_builder_phases.bats` 全绿；bats `--regression` 已知 11 + 新增 3（2 项既有 —— 主仓可复现；1 项是我改 `_lib/archive.sh` 触发的哈希 pin，**已重捕获**） | pass 0.95 |

**结论：10/10 pass，cache 被归档门接受。**

## 判据偏差 / 已知缺口（不改变判定）

- **D-1**：AC-10 字面「全绿」在本仓不可满足（pytest unit 有 10 项 worktree 根解析环境失败，基线同样失败）。
- **D-2（重要，跨 change）**：本仓是 `openspec_tracked=false` ⇒ `archive_change` 的 false 分支按**已签批契约**（complete-project-yaml-config-gaps L254「false 分支 SHALL NOT execute git merge」）不合并分支 ⇒ **worktree 模式的代码提交在 P3 后没有执行点合回主干**。本 change 的归档因此先手工把分支合入 master 再走 P3。该缺口是契约的后果、非本 change 引入，**建议单独立项**（给流程补「合并分支」执行点），优先级偏高。
- **D-3**：`verifier_contract_check` 内部按 `_main_repo_root` 解析 cache，与 bash 侧 `$tasks_root` 不同源 ⇒ worktree 模式下恒报 `verification missing` 并降级为 WARNING（legacy fallback）。与上一项 change 报告的 F-B 同源。

## 遗留清扫

无 TODO/半截实现/被 skip 的测试；`skills/rdd-verifier/`、`openspec/specs/` 未动；唯一「越界」是修正上一项验收报告里的一处字面 workspace 路径（触发 `test_no_hardcoded_workspace_paths` 不变式），已在 `dcd93fb` 单独提交并说明。
