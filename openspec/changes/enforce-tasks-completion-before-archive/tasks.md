# enforce-tasks-completion-before-archive — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 在 `_lib/archive.sh::archive_change` 末尾添加 `check_tasks_completion` 函数
  - 函数签名: `check_tasks_completion <name> <wt_path>`
  - 算法: 读取 `$wt_path/openspec/changes/<name>/tasks.md`,统计 `done = count("- [x]" + "- [X]")`,`total = count("- [")`,`pct = (done/total)*100 if total > 0 else 100`
  - 输出格式: `📋 tasks completion: <done>/<total> (<pct>%)`
  - 缺失 tasks.md 时输出 `[INFO] no tasks.md for <name>, skipping completion check`,return 0
  - 函数定义位置: `_lib/archive.sh` line ~85(与 `check_worktree_commits` 同一区域)
- [ ] 1.2 在 `archive_change` 函数 step 8.5 之前(line 397)插入 hook 调用
  - 调用位置: `mark_iteration_archived "$name" "$main_root" "$archive_commit_sha"` 之后
  - 调用形式: `check_tasks_completion "$name" "$wt_path"`(失败时 `|| true` 包裹,默认 warning 不阻断)
- [ ] 1.3 实现 `STRICT_TASKS_GATE=yes` escalation
  - 在 `check_tasks_completion` 函数体内部分支处理:
    - 默认模式: tasks < 100% 时输出 stderr warning,return 0(archive 继续)
    - STRICT 模式: tasks < 100% 时输出 stderr error,return 1(archive 阻断)
  - env var 检测: `if [ "${STRICT_TASKS_GATE:-no}" = "yes" ]`
  - 参考实现模式: `STRICT_CHANGE_GATE` (skills/guide-plan/scripts/plan_done_gate.sh line 146)
- [ ] 1.4 实现 `SKIP_TASKS_GATE=yes` opt-out
  - 在 `check_tasks_completion` 函数开头检测:
    - `if [ "${SKIP_TASKS_GATE:-no}" = "yes" ]; then echo "[SKIP] tasks gate skipped (SKIP_TASKS_GATE=yes)"; return 0; fi`
  - 与 SKIP_TASKS_GATE 配合:既可用于紧急 hotfix,也可与 STRICT 组合(`STRICT=yes && SKIP=yes` 时 SKIP 优先)
- [ ] 1.5 给 `rdd-doctor` 实现 `--category tasks-checkbox` 检查
  - 在 `skills/rdd-doctor/scripts/doctor_main.py` 中注册 `tasks_checkbox_checker` 函数(参照现有 `state_checker` / `plan_tdd_checker` / `roadmap_meta_checker` / `proposal_table_checker`)
  - 扫描范围: `openspec/changes/*/tasks.md` + `openspec/changes/archive/*/tasks.md`
  - 报告规则: 完成度 < 100% 的 change 报 WARNING(完成度=0 时升级 INFO);0 task 的 change 跳过不报
  - 输出格式: `[WARNING] <change-name>: tasks <done>/<total> (<pct>%) — location: openspec/changes/<path>/tasks.md`
  - 跨 8 个存量归档 change 都会触发 WARNING(预期行为,追溯历史)
- [ ] 1.6 新增 `tests/integration/test_archive_tasks_gate.bats`(≥5 用例)
  - Case 1: 默认 warning — mock tasks 8/10 → archive 继续 + stderr 含 "📋 tasks completion: 8/10 (80%)"
  - Case 2: STRICT 阻断 — `STRICT_TASKS_GATE=yes` + tasks 8/10 → 退出码 1 + stderr 含 "❌ STRICT_TASKS_GATE"
  - Case 3: SKIP 跳过 — `SKIP_TASKS_GATE=yes` + tasks 0/55 → 退出码 0,无 warning
  - Case 4: 0 tasks edge case — change 无 tasks.md → 退出码 0 + stderr 含 "[INFO] no tasks.md"
  - Case 5: 完成度统计准确性 — mock 9 种 `[x]`/`[ ]`/`[X]` 分布,断言百分比计算正确(`- [x] + - [X]` 都算 done,`- [ ]` + `- [~]` + `- [WIP]` 都算未完成)
- [ ] 1.7 验证现有 archive 相关测试保持 pass(无 regression)
  - `tests/integration/test_archive_iteration_sync_resilience.bats` 5 个用例保持 pass
  - `tests/integration/test_archive_state_recovery.bats` 等其他 archive 测试保持 pass
  - `tests/integration/test_ship_archive_extraction.bats` 锁定 `archive_change_for_mode` 行为不变
- [ ] 1.8 手工验证
  - 默认模式: 对 `migrate-improvements-to-rddf-namespace` (0/55) archive replay → 输出 warning 但 exit 0
  - STRICT 模式: 同样 change + `STRICT_TASKS_GATE=yes` → exit 1 + 阻断消息
  - doctor 模式: `rdd-doctor --category tasks-checkbox` → 列出 8 个存量 WARNING + 任何 active change
  - SKIP 模式: `SKIP_TASKS_GATE=yes rddf archive <change>` → exit 0,无任何输出