# Tasks: auto-wave-scheduler

> **设计依据**: `openspec/changes/auto-wave-scheduler/design.md`
> **架构依据**: ADR-0010 (v2.1 DependencyScheduler 方向), ADR-0022 (manual_deps), ADR-0020 (planned 状态)

## Task 1: 创建 WaveScheduler 模块骨架 (Recommendation + detect_unblocked 骨架)

**Files:**
- Create: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 1.1 Write failing test: `test_recommendation_dataclass_fields` - 验证 Recommendation dataclass 有所有必填字段
- [x] 1.2 Run test, verify fail (ImportError: No module named wave_scheduler)
- [x] 1.3 Implement: `Recommendation` dataclass + `WaveScheduler` 类骨架 (空 detect_unblocked)
- [x] 1.4 Run test, verify pass
- [x] 1.5 Commit: `feat(auto-wave-scheduler): add WaveScheduler module skeleton with Recommendation dataclass`

## Task 2: 实现 detect_unblocked - planned 状态 + iteration.blocker 字段

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 2.1 Write failing tests:
  - `test_detect_unblocked_planned_with_archived_blocker` - planned + blocker archived -> 1 fill 推荐
  - `test_detect_unblocked_planned_with_in_worktree_blocker` - planned + blocker in_worktree -> 0 推荐
  - `test_detect_unblocked_planned_no_blocker` - planned + blocker=None -> 0 推荐 (不重复 list_ready_for_fill)
- [x] 2.2 Run tests, verify fail (NotImplementedError 或返回空)
- [x] 2.3 Implement: `detect_unblocked` 主体,扫描 iteration_data["changes"],对 planned 状态检测 blocker 字段
- [x] 2.4 Run tests, verify pass
- [x] 2.5 Commit: `feat(auto-wave-scheduler): implement detect_unblocked for planned status with iteration.blocker`

## Task 3: 扩展 detect_unblocked - proposed 状态 (wave=ship)

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 3.1 Write failing test: `test_detect_unblocked_proposed_with_archived_blocker` - proposed + blocker archived -> 1 ship 推荐
- [x] 3.2 Run test, verify fail
- [x] 3.3 Implement: 在 detect_unblocked 中添加 proposed 分支,wave="ship"
- [x] 3.4 Run test, verify pass
- [x] 3.5 Commit: `feat(auto-wave-scheduler): extend detect_unblocked for proposed status (wave=ship)`

## Task 4: 扩展 detect_unblocked - manual_deps 多依赖检测

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 4.1 Write failing tests:
  - `test_detect_unblocked_manual_deps_all_archived` - manual_deps=[A,B] 全 archived -> 1 fill 推荐, source=manual_deps
  - `test_detect_unblocked_manual_deps_partial_archived` - manual_deps=[A,B] 部分 archived -> 0 推荐
  - `test_detect_unblocked_manual_deps_takes_priority_over_blocker_none` - blocker=None 但 manual_deps 有 -> 检测 manual_deps
- [x] 4.2 Run tests, verify fail
- [x] 4.3 Implement: 添加 `_resolve_blockers` helper,合并 iteration.blocker 和 manual_deps,所有 manual_deps 需 archived/completed
- [x] 4.4 Run tests, verify pass
- [x] 4.5 Commit: `feat(auto-wave-scheduler): support manual_deps multi-dependency detection`

## Task 5: 实现 check_on_archive (归档钩子)

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 5.1 Write failing tests:
  - `test_check_on_archive_returns_recs_for_dependents` - 归档 X, Y.blocker=X 且 planned -> 返回 [Y]
  - `test_check_on_archive_filters_unrelated` - 归档 X, Z.blocker=Y -> 不返回 Z
  - `test_check_on_archive_missing_iteration_file` - iteration.json 缺失 -> 返回空列表,不抛异常
- [x] 5.2 Run tests, verify fail
- [x] 5.3 Implement: `check_on_archive(project_root, archived_name)`,调 `iteration.load()` + `detect_unblocked`,过滤 `blocked_by == archived_name`
- [x] 5.4 Run tests, verify pass
- [x] 5.5 Commit: `feat(auto-wave-scheduler): implement check_on_archive hook`

## Task 6: 实现 check_on_entry (入口钩子) + format_recommendations

**Files:**
- Modify: `skills/_lib/wave_scheduler.py`
- Test: `tests/unit/test_wave_scheduler.py`

- [x] 6.1 Write failing tests:
  - `test_check_on_entry_returns_all_unblocked` - 入口扫描所有可推进的 changes
  - `test_format_recommendations_fill_wave` - 验证 fill wave 输出格式
  - `test_format_recommendations_ship_wave` - 验证 ship wave 输出格式
  - `test_format_recommendations_empty` - 空列表 -> 空字符串
- [x] 6.2 Run tests, verify fail
- [x] 6.3 Implement: `check_on_entry(project_root, skill_name)` + `format_recommendations(recs)` (返回多行字符串)
- [x] 6.4 Run tests, verify pass
- [x] 6.5 Commit: `feat(auto-wave-scheduler): implement check_on_entry hook and format_recommendations`

## Task 7: bash wrapper - wave_scheduler_hooks.sh

**Files:**
- Create: `skills/_lib/wave_scheduler_hooks.sh`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [x] 7.1 Write failing bats tests:
  - `test_wave_scheduler_post_archive_prints_suggestion` - 模拟归档场景,验证输出包含 "Wave suggestion"
  - `test_wave_scheduler_entry_check_guide_plan` - 模拟入口场景,验证输出
  - `test_wave_scheduler_post_archive_no_iteration_file` - iteration.json 缺失时不报错
  - `test_wave_scheduler_post_archive_no_recs` - 无推荐时不打印 (或打印空)
- [x] 7.2 Run tests, verify fail (脚本不存在)
- [x] 7.3 Implement: bash wrapper,通过 env-var 传递参数 (Oracle C1 safe),调 Python 模块
- [x] 7.4 Run tests, verify pass
- [x] 7.5 Commit: `feat(auto-wave-scheduler): add bash wrapper wave_scheduler_hooks.sh`

## Task 8: Hook 集成 - guide-ship Phase 3 post-archive

**Files:**
- Modify: `skills/guide-ship/SKILL.md` (Phase 3 post-archive hook 调用)
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [x] 8.1 Write failing bats test: `test_guide_ship_uses_wave_scheduler_post_archive` - 验证 SKILL.md 引用 `wave_scheduler_hooks.sh` 而非 `post_archive_fill.sh`
- [x] 8.2 Run test, verify fail
- [x] 8.3 Modify: guide-ship SKILL.md Phase 3 post-archive 部分,source wave_scheduler_hooks.sh 并调用 `wave_scheduler_post_archive "$CHANGE_NAME"`
- [x] 8.4 Run test, verify pass
- [x] 8.5 Commit: `feat(auto-wave-scheduler): integrate wave_scheduler into guide-ship Phase 3`

## Task 9: Hook 集成 - guide-plan 和 guide-ship 入口

**Files:**
- Modify: `skills/guide-plan/SKILL.md` (Phase 0 入口)
- Modify: `skills/guide-ship/SKILL.md` (Phase 1 入口)
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [x] 9.1 Write failing bats tests:
  - `test_guide_plan_has_entry_check` - 验证 guide-plan SKILL.md 引用 `wave_scheduler_entry_check`
  - `test_guide_ship_has_entry_check` - 验证 guide-ship SKILL.md 引用 `wave_scheduler_entry_check`
- [x] 9.2 Run tests, verify fail
- [x] 9.3 Modify: guide-plan SKILL.md Phase 0 末尾添加 `wave_scheduler_entry_check guide-plan`; guide-ship SKILL.md Phase 1 末尾添加 `wave_scheduler_entry_check guide-ship`
- [x] 9.4 Run tests, verify pass
- [x] 9.5 Commit: `feat(auto-wave-scheduler): integrate wave_scheduler entry check into guide-plan and guide-ship`

## Task 10: 全量验证 + smoke test 更新

**Files:**
- Test: `tests/unit/test_wave_scheduler.py`
- Test: `tests/integration/test_wave_scheduler_hook.bats`

- [x] 10.1 Run: `python3 -m pytest tests/unit/test_wave_scheduler.py -v` - 全部通过
- [x] 10.2 Run: `bats tests/integration/test_wave_scheduler_hook.bats` - 全部通过
- [x] 10.3 Run: `python3 -m pytest tests/unit/test_iteration.py tests/unit/test_dependency_scheduler.py -v` - 现有测试不破坏
- [x] 10.4 Run: `bats tests/integration/test_guide_ship_skill.bats tests/integration/test_guide_plan_skill.bats` - 现有 skill 测试不破坏
- [x] 10.5 lsp_diagnostics on `skills/_lib/wave_scheduler.py` - 无 error
- [x] 10.6 Commit (if any fixups): `test(auto-wave-scheduler): final verification pass`
