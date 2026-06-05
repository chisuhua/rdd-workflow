# skills/_lib/worktree.sh
# Git worktree helpers extracted from guide.md, guide-ship.md, status.md, execute.md
# These were duplicated across 5+ files (DRY violation, also P1-14 prerequisite).
#
# Usage:
#   source skills/_lib/worktree.sh
#   path=$(wt_path_for_branch "test-change")
#   if is_change_committed "my-change"; then ...; fi
#   default=$(find_default_branch)

# wt_path_for_branch <branch>
#   Returns absolute path of worktree for given branch, or empty string if not found
#   Example: wt_path_for_branch "test-change" -> "/abs/path/.zcf/test-change-wt"
#   Uses `git worktree list --porcelain` (one record per worktree, key/value pairs)
#   to avoid fragile whitespace parsing of the human-readable default format.
wt_path_for_branch() {
  local branch="${1:-}"
  [[ -z "$branch" ]] && return 1
  git worktree list --porcelain 2>/dev/null | \
    awk -v br="refs/heads/openspec/$branch" '
      /^worktree[[:space:]]/ { path = $2 }
      /^branch[[:space:]]/ && $2 == br { print path; exit }
    '
}

# is_change_committed <name>
#   Returns 0 if openspec/changes/<name>/.openspec.yaml is reachable via HEAD, 1 otherwise
#   Uses subshell + git show (handles non-HEAD cases correctly).
#   Resolves PROJECT_ROOT from env, then falls back to git toplevel, then pwd.
#   Exit code is normalized to 0/1 (git show returns 128 on missing path).
is_change_committed() {
  local name="${1:-}"
  [[ -z "$name" ]] && return 1
  (cd "${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" 2>/dev/null && \
    git show "HEAD:openspec/changes/$name/.openspec.yaml" >/dev/null 2>&1) && return 0
  return 1
}

# find_default_branch
#   Returns the default branch name (main, master, develop, etc.)
#   Reads from refs/remotes/origin/HEAD if available, falls back to current branch.
#   Used by archive/cleanup helpers that need a base ref.
find_default_branch() {
  local branch
  branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@')
  if [[ -n "$branch" ]]; then
    echo "$branch"
  else
    git rev-parse --abbrev-ref HEAD 2>/dev/null
  fi
}
