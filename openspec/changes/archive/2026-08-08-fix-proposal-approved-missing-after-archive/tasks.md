# Tasks — fix-proposal-approved-missing-after-archive

## 1. Source — approve_proposal.sh auto-stage

- [ ] 1.1 打开 `skills/guide-design/scripts/approve_proposal.sh`
- [ ] 1.2 在 `append_approved "$PROJECT_ROOT" "$NAME" "$PRIORITY"` 调用之后, 增加:
  ```bash
  if ! git add "$APPROVED_FILE" 2>/dev/null; then
    echo "❌ git add proposal-approved.md failed: <git error>" >&2
    exit 1
  fi
  echo "git add proposal-approved.md done"
  ```
- [ ] 1.3 验证 `APPROVED_FILE` 变量在 `append_approved` 之前已定义 (line 35-40 已有)

## 2. Source — mark_approved_completed archive/ fallback

- [ ] 2.1 打开 `_lib/state.sh::mark_approved_completed`
- [ ] 2.2 在 main table 提取之后, find 循环之后, 增加:
  ```bash
  if [ "$found" = "0" ]; then
    if compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      _append_approved_completed_row "$project_root" "$name"
    else
      echo "⚠️ mark_approved_completed: $name not found in proposal-approved.md and no archive/ detected" >&2
      return 1
    fi
  fi
  ```
- [ ] 2.3 实现 `_append_approved_completed_row` helper (read existing `## 已实施` section, append row, write back)

## 3. Source — dashboard pending filter

- [ ] 3.1 打开 `_lib/dashboard/__init__.py`
- [ ] 3.2 在 section 7 (Pending) 末尾, `data.pending_suggestions = pending` 之前, 增加:
  ```python
  filtered = []
  for s in data.suggestions:
      archive_pattern = os.path.join(project_root, "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-" + s.name)
      if glob.glob(archive_pattern):
          continue  # archived, skip
      filtered.append(s)
  data.suggestions = filtered
  data.pending_suggestions = len(filtered)
  ```
- [ ] 3.3 验证 `glob` 已 import (若未, 加 `import glob` 到顶部)

## 4. Source — plan-done gate warning

- [ ] 4.1 打开 `skills/guide-plan/scripts/plan_done_gate.sh`
- [ ] 4.2 在 write_plan_handoff 调用之前, 增加:
  ```bash
  if command -v git >/dev/null 2>&1; then
      DIRTY=$(cd "$PROJECT_ROOT" && git status --porcelain proposal-approved.md 2>/dev/null || true)
      if [ -n "$DIRTY" ]; then
          echo "⚠️ proposal-approved.md has uncommitted changes — commit before plan-done" >&2
      fi
  fi
  ```

## 5. Tests — bats regression (1 new file)

- [ ] 5.1 创建 `tests/integration/test_approve_proposal_staging.bats`
- [ ] 5.2 加载 `test_helper`
- [ ] 5.3 写 4 个 tests:
  - `test: approve_proposal stages proposal-approved.md on success`
  - `test: approve_proposal fails on git add error (readonly file)`
  - `test: mark_approved_completed fallback appends to ## 已实施 when archive exists`
  - `test: mark_approved_completed returns 1 when no evidence`
- [ ] 5.4 跑 `bats tests/integration/test_approve_proposal_staging.bats` 验证全绿

## 6. Tests — Python unit (1 new file)

- [ ] 6.1 创建 `tests/unit/test_dashboard_pending_filter.py`
- [ ] 6.2 写 3 个 tests:
  - `test_archived_change_excluded_from_pending`
  - `test_approved_change_excluded_from_pending`
  - `test_orphan_approval_change_in_pending`
- [ ] 6.3 跑 `python3 -m pytest tests/unit/test_dashboard_pending_filter.py -v` 验证全绿

## 7. 回归

- [ ] 7.1 跑 `python3 -m pytest tests/unit/test_dashboard_renderer.py -v` 确认现有 dashboard 测试未破坏
- [ ] 7.2 跑 `bats tests/integration/test_post_archive_cleanup_changes.bats` 确认新规范场景未破坏
- [ ] 7.3 跑 `./test.sh --full --regression` 0 新增失败

## 8. Worktree commit

- [ ] 8.1 进入 worktree `cd .rddf/wt/fix-proposal-approved-missing-after-archive`
- [ ] 8.2 `git add -A`
- [ ] 8.3 `git commit -m "fix(rdd-workflow): auto-stage proposal-approved.md + harden fallbacks

  - approve_proposal.sh: git add proposal-approved.md after write (fail-fast)
  - mark_approved_completed: compgen -G archive/<date>-<name> fallback
  - dashboard: skip archived changes from pending
  - plan-done gate: warn on dirty proposal-approved.md

  Skills: fix-proposal-approved-missing-after-archive (P1, bugfix)"`
- [ ] 8.4 验证 `git log -1 --oneline` 显示新 commit

## 9. Archive

- [ ] 9.1 跑 `openspec archive fix-proposal-approved-missing-after-archive --yes`
- [ ] 9.2 验证 `openspec/changes/archive/<date>-fix-proposal-approved-missing-after-archive/` 存在
- [ ] 9.3 验证 `openspec/specs/proposal-lifecycle-sync/spec.md` 落地
- [ ] 9.4 跑 `post_archive_cleanup` 清理残留
- [ ] 9.5 清理 worktree (`git worktree remove --force` + `git branch -D`)

## 10. 文档

- [ ] 10.1 更新 `proposal-approved.md` 移除修复条目 (移至 `## 已实施`)
- [ ] 10.2 `proposal-suggestions.md` 已被 sync_suggestions 自动清理
- [ ] 10.3 跑 `./test.sh --quick` 验证整体 framework 健康
