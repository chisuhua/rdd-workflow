# skills/_lib/archive.sh
# Archive helpers extracted from status.md Mode C and guide-ship.md Phase 3
# These were duplicated across 2 files (DRY violation, P1-14).
#
# Usage:
#   source skills/_lib/archive.sh
#   archive_change "test-change"
#
# Functions exported:
#   - check_worktree_commits <name>
#       Pre-merge check (T20): exit 0 if worktree branch has new commits vs
#       default branch, exit 1 if zero new commits.
#
#   - verify_merge_result <before_sha> <after_sha>
#       Post-merge check: if HEAD did not change but branch is not an
#       ancestor of HEAD, raise an error (silent no-op merge bug).
#
#   - archive_change <name>
#       Full archive flow: pre-check → merge (ff-only or no-ff) → verify
#       → openspec archive → worktree/branch cleanup. The openspec CLI
#       call is kept inline (not a helper) because it is CLI, not
#       library code.
#
# Helpers required (provided by skills/_lib/worktree.sh):
#   - wt_path_for_branch <name>
#   - find_default_branch

# Source worktree.sh for wt_path_for_branch + find_default_branch.
# Use a self-discovery approach so this file is testable from any cwd.
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_LIB_DIR/worktree.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/worktree.sh"
fi
unset _LIB_DIR

# check_worktree_commits <name>
#   Returns 0 if the worktree branch has new commits vs the default branch.
#   Returns 1 if the worktree branch is missing OR has zero new commits.
#   Prints a warning to stdout when returning 1 (so callers can use it
#   either as a guard with `if` or as a plain check).
#
#   Origin: T20 pre-merge commit check, originally embedded in
#   guide-ship.md:447-459. Promoted to a shared helper so status.md
#   Mode C and guide-ship.md Phase 3 can both call it.
check_worktree_commits() {
  local name="${1:-}"
  [[ -z "$name" ]] && { echo "❌ 需要 change 名称"; return 1; }

  local default_branch branch new_commits
  default_branch=$(find_default_branch)
  branch="openspec/$name"

  # If the branch itself does not exist, treat as "no new commits".
  if ! git rev-parse --verify "$branch" >/dev/null 2>&1; then
    echo "❌ 分支 $branch 不存在"
    return 1
  fi

  new_commits=$(git rev-list --count "$default_branch..$branch" 2>/dev/null || echo 0)
  if [ "$new_commits" -eq 0 ]; then
    echo "❌ worktree 分支无新提交,无需 merge"
    echo "   可能 execute 未运行或无代码变更"
    return 1
  fi

  # Echo count so callers can also see how many commits will be merged.
  echo "$new_commits"
  return 0
}

# verify_merge_result <before_sha> <after_sha>
#   Returns 0 if HEAD changed (merge produced new commits), OR if the
#   worktree branch is already an ancestor of HEAD (legitimate no-op).
#   Returns 1 if HEAD did not change AND the worktree branch is NOT an
#   ancestor of HEAD (silent merge failure).
#
#   <before_sha>/<after_sha> are HEAD revisions captured before and after
#   the merge call. <name> is the change name used for the ancestor check.
#
#   Origin: P0 FIX post-merge verification, originally in
#   guide-ship.md:480-509. Promoted to a shared helper.
verify_merge_result() {
  local before_sha="${1:-}" after_sha="${2:-}" name="${3:-}"
  [[ -z "$before_sha" || -z "$after_sha" || -z "$name" ]] && {
    echo "❌ verify_merge_result 需要 before/after sha + name"
    return 1
  }

  if [ "$before_sha" != "$after_sha" ]; then
    # HEAD changed — merge produced new commits. Success.
    return 0
  fi

  # HEAD did not change. If the worktree branch is already an ancestor
  # of HEAD, the merge was a legitimate no-op (nothing to do).
  if git merge-base --is-ancestor "openspec/$name" HEAD 2>/dev/null; then
    echo "⚠️  merge 完成但无新 commit（change 分支已是 HEAD 的祖先）"
    return 0
  fi

  # HEAD did not change AND the branch is not an ancestor. Real failure.
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "❌ Merge 验证失败！"
  echo ""
  echo "  可能原因："
  echo "  1. worktree 分支没有新提交"
  echo "  2. 新提交没有在预期文件中"
  echo ""
  echo "  请检查："
  echo "  - worktree 分支历史："
  echo "    git log openspec/$name --oneline -5"
  echo "  - 诊断："
  echo "    git log openspec/$name --stat --name-only | head -30"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  return 1
}

# archive_change <name>
#   Full archive flow used by status.md Mode C and guide-ship.md Phase 3.
#   Steps:
#     1. Resolve worktree path + default branch
#     2. Pre-merge commit check (check_worktree_commits)
#     3. Switch to main repo, checkout default branch
#     4. Merge worktree branch (--ff-only or --no-ff)
#     5. Post-merge verification (verify_merge_result)
#     6. openspec archive <name> --yes
#     7. git worktree remove + git branch -d (or -D via FORCE_BRANCH_DELETE)
#   Returns 0 on success, 1 on any failure.
#
#   Environment:
#     FORCE_BRANCH_DELETE=yes  — fall back to `git branch -D` if `-d`
#                                fails (worktree branch not fully merged)
#     PROJECT_ROOT             — main repo path; defaults to
#                                `git rev-parse --show-toplevel`
archive_change() {
  local name="${1:-}"
  [[ -z "$name" ]] && { echo "❌ 需要 change 名称"; return 1; }

  local wt_path branch default_branch
  wt_path=$(wt_path_for_branch "$name" 2>/dev/null || true)
  branch="openspec/$name"
  default_branch=$(find_default_branch)

  if [ -z "$wt_path" ]; then
    echo "❌ 找不到 worktree for $branch"
    return 1
  fi

  # 2. Pre-merge commit check (T20)
  if ! check_worktree_commits "$name" >/dev/null; then
    # check_worktree_commits already printed a clear error
    return 1
  fi

  # 3. Switch to main repo and checkout default branch
  local main_root
  main_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -z "$main_root" ] || [ ! -d "$main_root" ]; then
    echo "❌ 无法确定项目根目录（不在 git 仓库内？）"
    return 1
  fi
  (cd "$main_root" && git checkout "$default_branch" 2>/dev/null) || {
    echo "❌ 无法切换到默认分支 $default_branch"
    return 1
  }

  # Capture HEAD before merge for post-merge verification
  local before_merge after_merge
  before_merge=$(git rev-parse HEAD)

  # 4. Merge (--ff-only if no divergence, --no-ff if diverged)
  (cd "$main_root" && {
    local merge_base main_tip
    merge_base=$(git merge-base "$branch" "$default_branch" 2>/dev/null)
    main_tip=$(git rev-parse "$default_branch" 2>/dev/null)
    if [ "$merge_base" = "$main_tip" ]; then
      git merge --ff-only "$branch" || {
        echo "❌ merge 失败 (--ff-only)"
        return 1
      }
      echo "✅ Fast-forward merge 到 $default_branch 完成"
    else
      echo "⚠️ Worktree 分支已落后于 $default_branch，创建 merge commit"
      git merge --no-ff "$branch" -m "merge: $name change" || {
        echo "❌ merge 失败 (--no-ff)"
        return 1
      }
    fi
  }) || return 1

  after_merge=$(git rev-parse HEAD)

  # 5. Post-merge verification
  if ! verify_merge_result "$before_merge" "$after_merge" "$name"; then
    return 1
  fi

  # 6. openspec archive (CLI, not a helper)
  if ! openspec archive "$name" --yes; then
    echo "❌ openspec archive 失败"
    return 1
  fi

  # 7. Cleanup: worktree + branch
  if [ -n "$wt_path" ] && [ "$wt_path" != "/" ]; then
    (cd "$main_root" && git worktree remove "$wt_path" 2>/dev/null) || {
      echo "⚠️  worktree remove 失败: $wt_path"
    }
    echo "✅ Worktree 已删除: $wt_path"
  fi

  if (cd "$main_root" && git branch -d "$branch" 2>/dev/null); then
    echo "✅ Branch 已删除: $branch"
  else
    if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
      (cd "$main_root" && git branch -D "$branch" 2>/dev/null) || true
      echo "⚠️  Branch 强制删除"
    else
      echo "⚠️  Branch 删除失败,需要 FORCE_BRANCH_DELETE=yes"
    fi
  fi

  echo "✅ $name 已归档"
  return 0
}
