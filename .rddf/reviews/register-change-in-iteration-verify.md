# 验收报告：register-change-in-iteration

> 验收者：verifier（角色）｜对象 `openspec/register-change-in-iteration` @ `d91d0e4`（已合入 master，基线 `8f11e25`）
> 验收时间：2026-11-17｜**已用轮次：1 / 3**
> 判定来源：`proposal.md` 的 `## Acceptance`（9 条）。verdict cache：`.rddf/state/verifier/.ac-verdict-register-change-in-iteration.json`

| AC | 证据 | 判定 |
|---|---|---|
| 1 P0 approve 后 `rdcf status <name>` 能列出该条目 | 临时项目根实跑：`phase0_approval.sh demo --auto-approve` → `✅ registered in iteration.json: demo`；`RDDF_PROJECT_ROOT=<root> rddf status demo` → `Change: demo / Status: 📋 proposed / Builder phase: phase-1`（此前为 `❌ change 'demo' not found`） | pass 0.97 |
| 2 归档侧 sync 不再返回 missing warning | `sync_iteration_after_archive(root, 'demo')` → **None**（不是 `"change 'demo' missing from iteration.json"`）；bats ok 1 | pass 0.96 |
| 3 重复 approve 幂等（不重置 tasks_done/archived_at/added_at） | bats ok 2（`tasks_done=3/tasks_total=5/added_at` 保留）+ ok 7（`in_worktree` 不被降级） | pass 0.96 |
| 4 缺失/损坏/锁失败 ⇒ 只 WARN，P0 仍 exit 0 | 实跑：缺失 ⇒ `⚠️ phase0: iteration.json not found — change not registered`，exit 0；bats ok 3/5/6（损坏 JSON 与 schema-invalid 均 WARN + exit 0 + **文件内容逐字节不变** + 无 `.corrupt` 备份） | pass 0.96 |
| 5 缺失时不创建半成品文件 | 实跑后 `[ -f iteration.json ]` 为假 ⇒ 未创建 | pass 0.97 |
| 6 `choice=5`（dispatch-quick）不写 iteration.json | bats ok 4 | pass 0.96 |
| 7 跑完 `test_rdd_builder_phases.bats` 后仓库本体 iteration.json 不变 | 该文件新增断言「repo's iteration.json untouched」ok；既有用例已改为临时项目根 | pass 0.95 |
| 8 sync / force_mark_archived 不回归 | `pytest -k "iteration or store or archive"` → 332 passed；bats `--regression` 的新增项逐条在主仓复现（10 项既有），本 change 零回归 | pass 0.94 |
| 9 doctor `roadmap-feature` / `state` 无新增 finding | 两个 category 均 `✅ All 1 categories OK` | pass 0.95 |

**结论：9/9 pass。**

## 偏差与背景

- **D-1**：AC-8 字面「`./test.sh --unit` 全绿」在本仓不可满足（pytest unit 有 10 项 worktree 根解析环境失败，基线相同）。
- **D-2（critic 抓到的实现缺陷，已修）**：`store.load()` 对损坏文件不抛异常（备份 `.corrupt.<ts>` 后返回空文档）⇒ 原实现会把原文件**覆写成单条目**并打印成功。已改为写入前用只读的 `store._read_unlocked_verbose()` 判别三态。
- **D-3**：实施中确认 `from _lib.iteration import store` 会触发**循环 import**（`_lib.iteration.store` → `skills._lib.iteration.schema` → … → `_lib.iteration.store`）；仓库规范入口是 `skills._lib.iteration`（见 `_lib/iteration/post_archive.py:141`）。
- **D-4（既有缺陷，本 change 顺手暴露）**：`tests/KNOWN_FAILURES.txt` 会被 `test_known_failures_baseline.bats` 清空（该测试直接写真实仓库文件，teardown 还原失效即留残值）⇒ 回归统计失真（本次出现「已知 0 / 新增 10」）。已从 git 恢复；**建议单独立项**。

## 遗留清扫

无 TODO/半截实现/被 skip 的测试；既有 `phase0: approve writes spec.md` 用例已从「仓库本体 + 旧路径断言」改为「临时项目根 + D3 delta 路径」，覆盖的是现行契约。
