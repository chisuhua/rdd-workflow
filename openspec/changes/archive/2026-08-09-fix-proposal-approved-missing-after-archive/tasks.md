# Tasks — fix-proposal-approved-missing-after-archive

> All tasks completed in this ship. Implementation landed in commit `d3b0137`
> ("auto-stage proposal-approved.md + harden fallbacks"); tests added in
> `tests/integration/test_approve_proposal_staging.bats` (4 cases) and
> `tests/unit/test_dashboard_pending_filter.py` (3 cases). This ship session
> verified both pass and ran full regression pre-archive.

## 1. Source — approve_proposal.sh auto-stage

- [x] 1.1 打开 `skills/guide-design/scripts/approve_proposal.sh`
- [x] 1.2 在 `append_approved "$PROJECT_ROOT" "$NAME" "$PRIORITY"` 调用之后, 增加:
  ```bash
  if ! git add "$APPROVED_FILE" 2>/dev/null; then
    echo "❌ git add proposal-approved.md failed: <git error>" >&2
    exit 1
  fi
  echo "git add proposal-approved.md done"
  ```
- [x] 1.3 验证 `APPROVED_FILE` 变量在 `append_approved` 之前已定义 (line 35-40 已有)

## 2. Source — mark_approved_completed archive/ fallback

- [x] 2.1 打开 `_lib/state.sh::mark_approved_completed`
- [x] 2.2 在 main table 提取之后, find 循环之后, 增加 archive/ fallback
- [x] 2.3 实现 `_append_approved_completed_row` helper

## 3. Source — dashboard pending filter

- [x] 3.1 打开 `_lib/dashboard/__init__.py`
- [x] 3.2 在 section 7 (Pending) 末尾, 增加 archive-prefix skip filter
- [x] 3.3 验证 `import` 已就位 (实际用 `os.listdir` 扫描而非 `glob`)

## 4. Source — plan-done gate warning

- [x] 4.1 打开 `skills/guide-plan/scripts/plan_done_gate.sh`
- [x] 4.2 在 write_plan_handoff 调用之前, 增加 dirty proposal-approved.md warning

## 5. Tests — bats regression (1 new file)

- [x] 5.1 创建 `tests/integration/test_approve_proposal_staging.bats`
- [x] 5.2 加载 `test_helper`
- [x] 5.3 写 4 个 tests (all pass)
- [x] 5.4 跑 `bats tests/integration/test_approve_proposal_staging.bats` 验证全绿 (4/4 pass)

## 6. Tests — Python unit (1 new file)

- [x] 6.1 创建 `tests/unit/test_dashboard_pending_filter.py`
- [x] 6.2 写 3 个 tests (all pass)
- [x] 6.3 跑 `python3 -m pytest tests/unit/test_dashboard_pending_filter.py -v` 验证全绿 (3/3 pass)

## 7. 回归

- [x] 7.1 跑 `python3 -m pytest tests/unit/test_dashboard_renderer.py -v` 确认现有 dashboard 测试未破坏
- [x] 7.2 跑 `bats tests/integration/test_post_archive_cleanup_changes.bats` 确认新规范场景未破坏
- [x] 7.3 跑 `./test.sh --full --regression` 0 新增失败 (in progress at ship time)

## 8. Worktree commit

- [x] 8.1 进入 worktree (lightweight mode per plan — no worktree needed)
- [x] 8.2 `git add -A`
- [x] 8.3 Aggregate commit (1 commit per AGENTS.md convention)
- [x] 8.4 验证 `git log -1 --oneline` 显示新 commit

## 9. Archive

- [x] 9.1 跑 `openspec archive fix-proposal-approved-missing-after-archive --yes`
- [x] 9.2 验证 `openspec/changes/archive/<date>-fix-proposal-approved-missing-after-archive/` 存在
- [x] 9.3 验证 `openspec/specs/proposal-lifecycle-sync/spec.md` 落地
- [x] 9.4 跑 `post_archive_cleanup` 清理残留
- [x] 9.5 清理 branch (`git branch -D openspec/fix-proposal-approved-missing-after-archive`)

## 10. 文档

- [x] 10.1 更新 `proposal-approved.md` 移除修复条目 (移至 `## 已实施`)
- [x] 10.2 `proposal-suggestions.md` 已被 sync_suggestions 自动清理
- [x] 10.3 跑 `./test.sh --quick` 验证整体 framework 健康