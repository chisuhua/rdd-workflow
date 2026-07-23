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
#   - switch_to_default_branch <main_root> <default_branch>
#       cd to main_root and checkout default_branch. Returns 0 on
#       success, 1 on failure with an error message.
#
#   - merge_feature_branch <main_root> <branch> <default_branch> <name>
#       Merge <branch> into <default_branch> at <main_root>. Uses
#       --ff-only when the feature branch has not diverged from
#       default, --no-ff when it has (creates a merge commit).
#       Returns 0 on success, 1 on any merge failure.
#
#   - cleanup_worktree_and_branch <name> <main_root> <wt_path> <branch>
#       Remove the worktree at <wt_path> and delete the feature
#       <branch>. Honors FORCE_BRANCH_DELETE=yes for `git branch -D`
#       fallback when -d fails (worktree branch not fully merged).
#       Returns 0 on success, 1 when -d fails and FORCE_BRANCH_DELETE
#       is not 'yes'.
#
#   - archive_change <name>
#       Full archive flow: pre-check → merge (ff-only or no-ff) → verify
#       → openspec archive → worktree/branch cleanup → auto-commit of
#       archive file moves (via commit_archive_moves). The openspec CLI
#       call is kept inline (not a helper) because it is CLI, not
#       library code.
#
#   - commit_archive_moves <name> <main_root>
#       Stage + commit the 3 path trio created by `openspec archive
#       <name>`: the deleted active change dir, the new
#       archive/<date>-<name>/ dir, and the new main spec dir.
#       Honors SKIP_ARCHIVE_AUTO_COMMIT=yes (opt-out).
#       Idempotent: when working tree is clean (already committed),
#       exits 0 with no commit.
#       Returns 0 on success or skipped, 1 on commit failure (after
#       git reset HEAD to clean up the index).
#
#   - mark_iteration_archived <name> <main_root>
#       Update .rddf/state/iteration.json to mark <name> as archived.
#       Best-effort: failure does NOT propagate (we don't want a stale
#       iteration file to break an otherwise successful archive).
#       Returns 0 always.
#
# Helpers required (provided by skills/_lib/worktree.sh):
#   - wt_path_for_branch <name>
#   - find_default_branch
#   - main_repo_root

# Source worktree.sh for wt_path_for_branch + find_default_branch.
# Use a self-discovery approach so this file is testable from any cwd.
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_LIB_DIR/worktree.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/worktree.sh"
fi

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

# switch_to_default_branch <main_root> <default_branch>
#   cd to main_root and git checkout default_branch. Returns 0 on
#   success, 1 on failure with an error message echoing the bad
#   branch name. Caller is expected to have validated that
#   <main_root> is an existing directory.
#
#   Origin: archive.sh step 3 — main_repo checkout, originally
#   inline in archive_change. Promoted to a shared helper so the
#   switch step can be exercised in isolation from the full
#   archive flow.
switch_to_default_branch() {
  local main_root="${1:-}" default_branch="${2:-}"
  [[ -z "$main_root" || -z "$default_branch" ]] && return 1

  (cd "$main_root" && git checkout "$default_branch" 2>/dev/null) || {
    echo "❌ 无法切换到默认分支 $default_branch"
    return 1
  }
}

# merge_feature_branch <main_root> <branch> <default_branch> <name>
#   Merge <branch> into <default_branch> at <main_root>. Uses
#   --ff-only when the feature branch has not diverged from default
#   (merge_base == main_tip), --no-ff when it has (creates a merge
#   commit tagged with the change name). Returns 0 on success, 1 on
#   any merge failure.
#
#   Origin: archive.sh step 4 — divergence probe plus ff-only/no-ff
#   branch, originally inline in archive_change. Promoted to a
#   shared helper.
merge_feature_branch() {
  local main_root="${1:-}" branch="${2:-}" default_branch="${3:-}" name="${4:-}"
  [[ -z "$main_root" || -z "$branch" || -z "$default_branch" || -z "$name" ]] && return 1

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
}

# cleanup_worktree_and_branch <name> <main_root> <wt_path> <branch>
#   Remove the worktree at <wt_path> and delete the feature
#   <branch> in <main_root>. Honors FORCE_BRANCH_DELETE=yes for the
#   `git branch -D` fallback when -d fails (worktree branch not
#   fully merged). Skips the worktree remove when <wt_path> is
#   empty or "/". Returns 0 on success, 1 when -d fails and
#   FORCE_BRANCH_DELETE is not 'yes'.
#
#   Origin: archive.sh step 7 — worktree remove plus branch -d
#   (with FORCE_BRANCH_DELETE=yes -D fallback), originally inline
#   in archive_change. Promoted to a shared helper.
cleanup_worktree_and_branch() {
  local name="${1:-}" main_root="${2:-}" wt_path="${3:-}" branch="${4:-}"
  [[ -z "$main_root" || -z "$branch" ]] && return 1

  if [ -n "$wt_path" ] && [ "$wt_path" != "/" ]; then
    (cd "$main_root" && git worktree remove "$wt_path" 2>/dev/null) || {
      echo "⚠️  worktree remove 失败: $wt_path"
    }
    echo "✅ Worktree 已删除: $wt_path"
  fi

  if (cd "$main_root" && git branch -d "$branch" 2>/dev/null); then
    echo "✅ Branch 已删除: $branch"
  else
    echo "⚠️  Branch 有未合并的提交: $branch"
    if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
      (cd "$main_root" && git branch -D "$branch" 2>/dev/null) || true
      echo "⚠️  Branch 强制删除(因 FORCE_BRANCH_DELETE=yes)"
    else
      echo "❌ Branch 删除取消。设置 FORCE_BRANCH_DELETE=yes 重试"
      return 1
    fi
  fi
}

# archive_change <name>
#   Full archive flow used by status.md Mode C and guide-ship.md Phase 3.
#   Steps:
#     1. Resolve worktree path, default branch, and main repo root
#     2. Pre-merge commit check (check_worktree_commits)
#     3. Switch to main repo, checkout default branch
#        (switch_to_default_branch)
#     4. Merge worktree branch, --ff-only or --no-ff
#        (merge_feature_branch)
#     5. Post-merge verification (verify_merge_result)
#     6. openspec archive <name> --yes (kept inline — CLI, not lib)
#     7. git worktree remove + git branch -d (or -D via FORCE_BRANCH_DELETE)
#        (cleanup_worktree_and_branch)
#   Returns 0 on success, 1 on any failure.
#
#   Environment:
#     FORCE_BRANCH_DELETE=yes  — fall back to `git branch -D` if `-d`
#                                fails (worktree branch not fully merged)
archive_change() {
  local name="${1:-}" wt_path branch default_branch main_root
  [[ -z "$name" ]] && { echo "❌ 需要 change 名称"; return 1; }

  wt_path=$(wt_path_for_branch "$name" 2>/dev/null || true)
  branch="openspec/$name"
  default_branch=$(find_default_branch)
  main_root=$(main_repo_root)

  if [ -z "$wt_path" ]; then
    echo "❌ 找不到 worktree for $branch"
    return 1
  fi
  if [ -z "$main_root" ] || [ ! -d "$main_root" ]; then
    echo "❌ 无法确定项目根目录（不在 git 仓库内？）"
    return 1
  fi

  # 2. Pre-merge commit check (T20)
  check_worktree_commits "$name" >/dev/null || return 1

  # 3. Switch to default branch in main repo
  switch_to_default_branch "$main_root" "$default_branch" || return 1

  # Capture HEAD before/after merge for post-merge verification
  local before_merge after_merge
  before_merge=$(git rev-parse HEAD)
  merge_feature_branch "$main_root" "$branch" "$default_branch" "$name" || return 1
  after_merge=$(git rev-parse HEAD)

  # 5-6. Verify merge + openspec archive (CLI call kept inline)
  verify_merge_result "$before_merge" "$after_merge" "$name" || return 1
  if ! openspec archive "$name" --yes; then
    echo "❌ openspec archive 失败"
    return 1
  fi

  # 7. Cleanup worktree + branch
  cleanup_worktree_and_branch "$name" "$main_root" "$wt_path" "$branch" || return 1

  # 7.5 Auto-commit archive file moves (added by add-archive-auto-commit).
  # Tolerate failure (file moves remain in working tree for human review).
  commit_archive_moves "$name" "$main_root" || true

  # 8. Update iteration.json (current sprint tracker). Best-effort.
  mark_iteration_archived "$name" "$main_root"

  # 9. Update proposal-approved.md status (archive-update-proposal-status)
  local skills_parent
  skills_parent="$(cd "$_LIB_DIR/../.." 2>/dev/null && pwd)"
  if [ -f "$skills_parent/skills/propose/scripts/update_proposal_status.py" ]; then
    python3 "$skills_parent/skills/propose/scripts/update_proposal_status.py" "$name" "$main_root" 2>/dev/null || true
  fi

  echo "✅ $name 已归档"
  return 0
}

# mark_iteration_archived <name> <main_root>
#   Best-effort update of .rddf/state/iteration.json: mark the change
#   as archived with a timestamp. Never returns non-zero (callers should
#   not treat iteration tracking failure as archive failure).
#
#   Implementation: invokes the Python `skills._lib.iteration` module
#   via a here-string. If the module is missing (older rdd-workflow
#   version) or the file is unreadable, logs a warning and returns 0.
#
#   Path resolution: `skills/_lib/iteration.py` is a sibling of this
#   script, so the parent of $_LIB_DIR is the directory that contains
#   the `skills/` package. We insert that parent on sys.path.
mark_iteration_archived() {
  local name="${1:-}" main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  local iter_file="$main_root/.rddf/state/iteration.json"
  if [ ! -f "$iter_file" ]; then
    # No iteration state yet — nothing to update. This is normal for
    # projects that predate v2.0 or never ran propose with roadmap.
    return 0
  fi

  # _LIB_DIR is set at source time to skills/_lib/. For
  # `from skills._lib import iteration` to work, sys.path needs the
  # PARENT of the `skills/` package, which is two levels up from
  # _LIB_DIR (skills/_lib/ → skills/ → .).
  local skills_parent
  skills_parent="$(cd "$_LIB_DIR/../.." 2>/dev/null && pwd)"

  # v2.0.2 安全修复: bash 变量通过环境变量传递 (os.environ),
  # 不用 '$VAR' 直接拼到 Python 源码. 避免单引号路径/注入风险.
  if ! SKILLS_PARENT="$skills_parent" \
        MAIN_ROOT="$main_root" \
        CHANGE_NAME="$name" \
        python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib import iteration as it_mod
except ImportError as e:
    print(f"⚠️  iteration module unavailable: {e}", file=sys.stderr)
    sys.exit(0)
try:
    main_root = os.environ["MAIN_ROOT"]
    change_name = os.environ["CHANGE_NAME"]
    data = it_mod.load(main_root)
    data = it_mod.mark_archived(data, change_name)
    it_mod.save(main_root, data)
    print(f"✅ iteration.json: marked {change_name} as archived")
except Exception as e:
    print(f"⚠️  iteration.json update failed (archive still succeeded): {e}", file=sys.stderr)
    sys.exit(0)
'; then
    # python3 itself failed (not installed) — silently skip
    :
  fi
  return 0
}

# commit_archive_moves <name> <main_root>
#   Stage + commit the 3 path trio created by `openspec archive <name>`:
#     - openspec/changes/<name>/            (deleted active change dir)
#     - openspec/changes/archive/           (new archive dir + contents)
#     - openspec/specs/                     (new main spec dir)
#   The path scope is intentionally strict (NOT `openspec/` whole) so we
#   never accidentally stage unrelated dirty files. Writes exactly 1
#   commit with subject `archive(<name>): archive completed`, matching
#   the convention established by 0d6ba45.
#
#   Honors opt-out via SKIP_ARCHIVE_AUTO_COMMIT=yes (callers can choose
#   to commit manually instead). Idempotent: clean working tree → exit
#   0 with no commit. On commit failure, runs `git reset HEAD` to roll
#   back the index pollution.
#
#   Returns 0 on success or skipped, 1 if `git add` or `git commit` fails.
#   Callers (archive_change + guide-ship.md lightweight path) typically
#   tolerate failure via `|| true` — the archive itself succeeded, only
#   the auto-commit failed, leaving moves for the human to handle.
commit_archive_moves() {
  local name="${1:-}" main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && {
    echo "❌ commit_archive_moves 需要 name 和 main_root"; return 1;
  }

  if [ "${SKIP_ARCHIVE_AUTO_COMMIT:-no}" = "yes" ]; then
    echo "ℹ️  commit_archive_moves: SKIPPED (SKIP_ARCHIVE_AUTO_COMMIT=yes)"
    return 0
  fi

  if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
    return 0
  fi

  cd "$main_root" || { echo "❌ commit_archive_moves: cannot cd to $main_root"; return 1; }

  if ! git add \
        "openspec/changes/${name}/" \
        "openspec/changes/archive/" \
        "openspec/specs/" 2>/dev/null; then
    git reset HEAD >/dev/null 2>&1 || true
    echo "❌ commit_archive_moves: git add failed"
    return 1
  fi

  if ! git commit -m "archive(${name}): archive completed"; then
    git reset HEAD >/dev/null 2>&1 || true
    echo "❌ commit_archive_moves: git commit failed"
    return 1
  fi

  echo "✅ commit_archive_moves: archive(${name}) committed"
  return 0
}
