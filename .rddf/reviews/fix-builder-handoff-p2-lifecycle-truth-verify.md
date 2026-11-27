# verify: fix-builder-handoff-p2-lifecycle-truth

> **验收对象**：本 change 的**实现**（worktree 分支 `openspec/fix-builder-handoff-p2-lifecycle-truth`，1 个提交 `1cff170d`）
> **验收时间**：2026-11-27
> **执行角色**：builder（角色内建 verifier 契约 · **本地验收路径**）
> **判据来源**：`proposal.md` 的 `## Acceptance`（AC1–AC7）

## 分流判定（为什么走本地验收，而不是 `rdd-verifier` skill）

| 条件 | 实测 | 判定 |
|---|---|---|
| ① change 存在 + 有 AC 段 | `openspec/changes/fix-builder-handoff-p2-lifecycle-truth/proposal.md` 含 `## Acceptance`（7 条） | ✅ |
| ② P3 archive gate 触发 | 主仓 `iteration.json` 该 change `tasks_done=0`（P0 快照）；批量分流扫主仓、实现落在 worktree | ❌ |
| ③ `rdd-verifier` skill 可加载 | installed | ✅ |

⇒ 条件② 不满足 ⇒ **本地验收**。

## 逐条判定（AC1–AC7）

| AC | 判据 | 证据 | 判定 |
|:--:|---|---|:--:|
| AC1 | P2 准备完成后 `execution_status` ≠ `completed` | `tests/unit/test_builder_handoff_lifecycle.py::test_phase2_setup_does_not_write_completed`（源码级断言：`phase2_execute.sh` 内**不出现** `execution_status="completed"`，且出现 `"running"`）；`test_phase3_archive_writes_completed`（归档侧写 `completed`） | ✅ |
| AC2 | 旧 handoff（`completed`）读取不炸且按 setup 语义解释 | 同文件 `test_legacy_handoff_is_readable_and_interpreted_as_setup`（tasks 1/3 + 旧 `completed` ⇒ `actually_complete=False`、`inconsistent=True` ⇒ **不被采信为完成**）、`test_setup_only_handoff_does_not_claim_completion`、`test_missing_files_do_not_crash`、`test_zero_total_tasks_is_not_complete` | ✅ |
| AC3 | `in-progress` 落盘后 schema 校验通过（枚举收敛） | 同文件 `test_execution_status_enum_has_no_wild_values`（schema enum == pending\|running\|failed\|completed）+ `test_no_wild_in_progress_value_is_written_anywhere`（全仓无 `"in-progress"` 写入点）；**连带修改**：`tests/unit/test_builder_handoff.py:30/47` 同批归一为 `running`（该文件 11 例仍绿） | ✅ |
| AC4 | 存在**至少一个**门控点按新语义判定（**消费方**） | 消费方裁决 = **P2.5 review**（design D-1；archive gate / status / dashboard 均已另有真源，不重复）。证据：同文件 `test_phase25_review_uses_the_shared_state_helper` + `test_phase25_review_reports_inconsistency`；端到端 `tests/integration/test_phase25_shows_implementation_state.bats` **3/3**（真实输出：`实现状态：tasks 0/2（未完成）   handoff execution_status=completed` + `⚠️ 不一致：… ⇒ 以 tasks 为准`） | ✅ |
| AC5 | P2 前检查报出「主仓领先基线」的 commit sha + 文件清单 | `tests/integration/test_phase2_prereq_check.bats` **4/4**：① 报 sha + 文件名；② 报未提交 tracked 改动；③ 干净且在基线上时**保持沉默**；④ 检查**不自动** commit/merge（脏文件仍脏） | ✅ |
| AC6 | 变异：写回 `execution_status="completed"` ⇒ AC1 红 | 实测（临时改 `phase2_execute.sh` ⇒ `test_phase2_setup_does_not_write_completed` 红），回滚后全绿；`grep -c MUTATION` == 0 | ✅ |
| AC7 | `./test.sh --gates` + `./test.sh --unit` 全绿 | gates ⇒ **ALL PASSED**（`openspec validate --all` 165/165）；unit ⇒ **3769 passed / 2 skipped / 6 failed**（6 = 既有 worktree 环境性失败） | ✅ |

## 消费方判定的说明（AC4 的取舍）

候选与裁决见 design D-1。关键点：`execution_status` 此前**只有写入方** ⇒ 拆分字段属「纯化妆」。
本 change 不新增字段、只让既有字段**说真话**，并把**唯一天然消费方**（P2.5 合并决策点）接上：

- P2.5 review 现在**必看**真实进度（disk 的 tasks 计数）⇒ 谎报当场暴露；
- 真相源是 disk，不是 handoff ⇒ **真源不增**（与 U3 的 disk 化同向）。

## 验证步骤（verifier 契约 1–5 步）

1. **静态检查**：`./test.sh --gates` ⇒ **ALL PASSED**（隔离门 / ruff / mypy strict / doctor 10 类 / markdown drift / ADR 形态增量 / openspec validate 165/165）；改动文件 ruff 单跑 ⇒ All checks passed；`bash -n` 三个脚本 ⇒ syntax ok。
2. **单元测试**：`pytest tests/unit` ⇒ **3769 passed / 2 skipped / 6 failed**。
3. **集成**：新增 bats 7 例（4 + 3）全绿；`openspec validate <change> --strict` ⇒ valid。
4. **边界与错误路径**：handoff 文件缺失 / tasks.md 缺失 / tasks 总数为 0 / 一致 / 不一致 / 旧值 —— 各有用例；前置检查的「干净时沉默」与「不自动 commit」各有用例。
5. **遗留清扫**：改动文件 `TODO|FIXME|MUTATION|pytest.skip` 扫描 ⇒ 零残留。

### 环境性失败（**非本次引入**）

`tests/unit/test_resolve_project_root_contract_python.py`（5）+ `test_skills_lib_python_resolve_project_root.py`（1）：
worktree 下实现经 `--git-common-dir` 解析到主仓，测试期望 worktree 根；主仓跑同组全绿 ⇒ 既有不一致，另案。

## 已知遗留（登记，不静默）

| # | 遗留 | 归属 |
|---|---|---|
| 1 | `iteration.json` 的 `tasks_done` 仍不刷新（本次同样影响它，但**不影响**新的真相源：真相在 tasks.md） | U5 同类；本 change 已把「真相」移出 iteration |
| 2 | 存量 `.rddf/state/builder/*.json` 的 `completed` **不迁移**（只报不一致） | 设计裁决（运行态文件、gitignored；迁移风险 > 收益） |
| 3 | worktree 模式下 6 个 project-root 测试失败 | 另案 |
| 4 | 前置检查**只报不自动做**（不 commit / 不 merge 主仓内容） | 设计裁决（自动化同步风险高） |

## 已用轮次

**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）。失败项：**0**。
