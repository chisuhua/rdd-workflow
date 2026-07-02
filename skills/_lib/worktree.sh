# skills/_lib/worktree.sh
# Git worktree helpers extracted from guide.md, guide-ship.md, status.md, execute.md
# These were duplicated across 5+ files (DRY violation, also P1-14 prerequisite).
#
# Usage:
#   source skills/_lib/worktree.sh
#   path=$(wt_path_for_branch "test-change")
#   default=$(find_default_branch)
#   main=$(main_repo_root)

# wt_path_for_branch <branch>
#   Returns absolute path of worktree for given branch, or empty string if not found
#   Example: wt_path_for_branch "test-change" -> "/abs/path/.rddf/wt/test-change"
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

# find_default_branch
#   Returns the default branch name (main, master, develop, etc.)
#   Reads from refs/remotes/origin/HEAD if available, falls back to probing
#   well-known default branch names in the MAIN repo (not the worktree).
#   Never returns the worktree's own openspec/<name> branch.
#   Used by archive/cleanup helpers that need a base ref.
#   P0-fix (general-harden-doc-consistency): previous fallback `git rev-parse
#   --abbrev-ref HEAD` returned the worktree branch when called from inside
#   a worktree, causing archive_change to self-merge.
find_default_branch() {
  local branch
  branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@')
  if [[ -n "$branch" ]]; then
    echo "$branch"
    return
  fi

  # Fallback: probe well-known default branch names in the MAIN repo.
  # `main_repo_root` is defined later in this file; bash resolves at call time.
  local main_root
  main_root=$(main_repo_root)
  for candidate in main master develop trunk; do
    if git -C "$main_root" rev-parse --verify --quiet "refs/heads/$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done

  # Last resort: init.defaultBranch config, or current branch in main repo.
  branch=$(git config --get init.defaultBranch 2>/dev/null || git -C "$main_root" rev-parse --abbrev-ref HEAD 2>/dev/null)
  echo "$branch"
}

# main_repo_root
#   Returns absolute path of the MAIN repository root (NOT the worktree root).
#   When called from main repo: returns the main repo path.
#   When called from a worktree: returns the main repo path.
#   Falls back to pwd if git is not available.
#   Uses `git rev-parse --git-common-dir` (shared .git dir across worktrees),
#   which is the canonical worktree-safe replacement for `--show-toplevel`.
#   P0-8: ensures STATE_FILE writes to main repo's .rddf/state/, not worktree's.
main_repo_root() {
  local common_dir
  common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || { pwd; return; }
  case "$common_dir" in
    /*) ;;
    *) common_dir="$(pwd)/$common_dir" ;;
  esac
  case "$common_dir" in
    */.git) dirname "$common_dir" ;;
    */.git/worktrees/*) dirname "$(dirname "$common_dir")" ;;
    *) dirname "$common_dir" ;;
  esac
}
