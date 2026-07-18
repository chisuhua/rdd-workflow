#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_cleanup.sh
# Phase 4 of guide-ship.md extracted into a reusable helper.
# Was a ~27-line inline bash block (L571-L597) handling batch cleanup of
# openspec/* worktrees and branches after archive completes.
#
# Functions exported:
#   - cleanup_worktrees_and_branches <project_root>
#       Removes every openspec/* worktree (via 'git worktree list --porcelain'
#       + 'git worktree remove') and every openspec/* branch.
#       Branch deletion strategy (P2-9): default -d (safe); shows last commit
#       for review; on failure, falls back to -D only when FORCE_BRANCH_DELETE=yes.
#       Idempotent: missing worktrees/branches are silently skipped.
#
# Behavior preserved 1:1 from the original inline block:
#   - Uses 'git worktree list --porcelain' with awk to extract worktree paths
#     whose branch is refs/heads/openspec/* (same filter as ship_monitor.sh).
#   - 'git worktree remove' failures are swallowed (|| true).
#   - Branches iterated via 'git branch | grep "openspec/"'.
#   - LAST_COMMIT shown for human review before deletion.
#   - Honors FORCE_BRANCH_DELETE=yes for force delete; otherwise skips.
#   - Final success echo printed regardless of partial failures.

# cleanup_worktrees_and_branches <project_root>
cleanup_worktrees_and_branches() {
  local PROJECT_ROOT="$1"

  # 清理所有 worktree
  local -a wt_list=()
  if command -v mapfile >/dev/null 2>&1; then
    mapfile -t wt_list < <(git -C "$PROJECT_ROOT" worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
  else
    # bash < 4.0 fallback (preserves original behavior on older shells)
    while IFS= read -r line; do
      [ -n "$line" ] && wt_list+=("$line")
    done < <(git -C "$PROJECT_ROOT" worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
  fi

  local wt
  for wt in "${wt_list[@]}"; do
    git -C "$PROJECT_ROOT" worktree remove "$wt" 2>/dev/null || true
  done

  # 清理所有 openspec/* branches
  # 策略 (P2-9): 默认 -d 安全删除；显示最后提交供人审查；未合并时需显式 FORCE_BRANCH_DELETE=yes 才允许 -D
  local branch LAST_COMMIT
  git -C "$PROJECT_ROOT" branch | grep "openspec/" | while read -r branch; do
    LAST_COMMIT=$(git -C "$PROJECT_ROOT" log -1 --format="%h %s" "$branch" 2>/dev/null)
    if git -C "$PROJECT_ROOT" branch -d "$branch" 2>/dev/null; then
      echo "✅ $branch deleted (last: $LAST_COMMIT)"
    else
      echo "⚠️  $branch 有未合并的提交"
      echo "   最后提交: $LAST_COMMIT"
      if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
        git -C "$PROJECT_ROOT" branch -D "$branch" 2>/dev/null || true
        echo "   强制删除(因 FORCE_BRANCH_DELETE=yes)"
      else
        echo "   跳过(设置 FORCE_BRANCH_DELETE=yes 强制删除)"
      fi
    fi
  done

  echo "✅ 所有 worktree 和 openspec/* branches 已清理"
}
