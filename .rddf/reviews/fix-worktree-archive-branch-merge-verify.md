# 验收报告 —— `fix-worktree-archive-branch-merge`（ADR-0061 的实现）

> 验收者：verifier 角色（opencode build agent 的角色矩阵）
> 判据来源：① 用户「继续推进直到完成剩余任务」；② `.rddf/improvements/fix-worktree-archive-branch-merge.md` 的 `## Acceptance`（16 条）；③ `docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md` 的 `## Verification`（V-1~V-13）
> 已用轮次：1
> 结论：**15/16 pass，1 项 SHOULD_FIX（不阻断）**

## 一、验证顺序（早失败早停）

| 步 | 检查 | 结果 |
|---|---|---|
| 1 | 静态：`bash -n _lib/archive.sh` / `ship_execution_mode.sh` / `phase1_5_deps.sh` + `ast.parse(builder_deps.py)` | ✅ 全绿 |
| 2 | 单测：`test_archive_gate_verifier` / `test_verifier_gate_cache_root` / `test_builder_deps*` | ✅ 52 passed |
| 3 | 集成：8 个关键 bats（含新增的 trunk gate） | ✅ 82 ok / 0 fail |
| 4 | 全量门：`./test.sh --full --regression` | ✅ ALL PASSED（新增失败 0；pytest unit 3413 passed） |
| 5 | 遗留清扫复核 | ✅ 见 §四 |

## 二、逐条判定 + 证据

| AC | 判定 | 证据 |
|---|---|---|
| spec delta（两份 + `archive-auto-commit` 重指向） | ✅ pass | `grep` 三份 spec：`complete-project-yaml-config-gaps` 3 处、`archive-openspec-tracked-skip-commit` 2 处、`archive-auto-commit` 1 处均含新语义。⚠ 注：本仓 `openspec/` 被 gitignore ⇒ 规范文本不入版本库，**delta 的权威落点是已签批的 ADR-0061**（+ 本报告） |
| `archive_premerge_check` 具名 + 三态 | ✅ pass | `_lib/archive.sh:287`；`test_archive_trunk_gate.bats` 14 例 |
| 内容等价用 **patch-id** | ✅ pass | `archive.sh:330` 用 `git cherry`；squash-merge 用例绿 |
| worktree 未提交改动 ⇒ 拒绝（含噪声排除） | ✅ pass | `archive.sh` 的 ① + `--untracked-files=all`；「artifacts … do NOT count as dirty」用例绿 |
| 未合入 ⇒ 拒绝 + 分叉指引 | ✅ pass | 「not merged → refuse + copy-pasteable merge command」；四支指引（合并 / 先提交 / 先提交后合并 / ref 不存在） |
| opt-in + 审计 + 与 FORCE 互斥 | ✅ pass | 6 处 `ARCHIVE_ALLOW_UNMERGED`；3 个用例（缺 reason 不放行 / 放行+审计 / 与 FORCE 互斥） |
| false 分支不新增 merge / commit 调用 | ✅ pass | awk 守卫**已加固**（提取终点 = `mark_iteration_archived`）且改为只匹配**调用**（注释里合法地提到这两个词） |
| cleanup 三态 + 「只在真删成功时打印」 | ✅ pass | `archive.sh` 的三态返回；3 个 cleanup 用例绿 |
| tracked 路径 cleanup 不再让归档失败 | ✅ pass | `archive.sh:860` 的 `|| echo "⚠️ 归档已完成，但 worktree/分支清理未完全成功"` |
| 退出码链（1 → phase3 3 → `rddf archive` 1） | ✅ pass | `phase3_archive.sh:151-152` 的 `case`（非 3 ⇒ exit 3）+ `archive_cmd.py` 的非零 ⇒ 1 |
| 既有测试已修改 | ✅ pass | `test_archive_with_openspec_tracked_false.bats`：「已合入 ⇒ 0」+「UNMERGED ⇒ refused」 |
| 三种 worktree 失败态 | ✅ pass | 孤儿目录 / 已注册但 remove 失败 / ref 缺失 三条消息分别有用例 |
| 旁路清单成文 | ✅ pass | ADR-0061 的 Consequences（轻量 inline / rdd-quick / 手工 archive 三条不受保护） |
| 文档（两道门 + 不代劳合并） | ✅ pass | `skills/rdd-builder/SKILL.md` 的「P3 归档门」段 + `docs/architecture/workflow-phases.md` 的 Hard gates |
| 全量门 | ✅ pass | ALL PASSED |

## 三、失败项与路由建议

**无 ac-fail 项。** 一条观察（不计入 AC）：

- **ADR-0061 的判定表原本缺「未合入 ⇒ 拒绝」这一档**（按表的字面读法，未合入会落到「无法判定 ⇒
  放行」⇒ 这道门永远不会拒绝）。实现按**决策正文**（未合入 ⇒ 拒绝）落地，并在 ADR 里补了
  「修订 2026-11-18（表格补正）」说明。**建议 architect 复核该补正**（决策未变，仅表格补正）。

## 四、遗留清扫复核

| 项 | 结果 |
|---|---|
| 新增 TODO / FIXME / 注释掉的代码 | ✅ 无 |
| 新增被 skip 的测试 | ✅ 无（`pytest` 的 3 个 skip 是既有） |
| 临时调试日志 / 未替换的 mock | ✅ 无（`setup_openspec_stub` 是测试固件，非生产代码） |
| 本次范围内已删除 / 替代的代码 | `cleanup_worktree_and_branch` 的无条件成功文案已删除 ✓ |
| 测试污染 | `.rddf/state/.bypass-audit.jsonl` 的两条测试条目已清理 ✓ |
| 失败/超时未评估的 bats 文件 | ⚠ **观察（非本 change 引入）**：`tests/scripts/collect_bats_failures.sh` 的 30s per-file 超时对 5 个天生较慢的测试（`test_env_bootstrap` / `test_execute_regression_gate` / `test_install_with_docs` / `test_known_failures_baseline` / `test_no_spec_workflow_residue`）过紧 ⇒ 负载高时会从「慢」翻成「未评估」。已用 `git stash` 对照证实**与本 change 无关**（撤掉改动后同样 27~49s）。建议独立立项（提高超时或给这几个文件标记）。 |

## 五、结论

**B 项 15/16 AC pass，无 ac-fail。** 唯一 note 是 ADR 表格补正（建议 architect 复核）与一条
与本次无关的超时观察。**归档就绪**（在 ADR 表格补正被 architect 确认的前提下）。
