#!/usr/bin/env bash
# _lib/post_archive_cleanup.sh
#
# post_archive_cleanup <project_root> <change_name>
#
# Idempotent post-archive cleanup. After openspec archive <change_name>
# finishes moving files, this hook:
#   1. Scans `git status --porcelain` for residue
#   2. Classifies into 3 buckets: deleted-tracked (whitelist), modified-critical (whitelist),
#      other (untouched)
#   3. git rm -f deleted-tracked items
#   4. git add modified-critical items (does NOT auto-commit them)
#   5. Auto-commit only the rm bucket (commit subject: chore(post-archive): clean
#      residue from <change_name>); idempotent no-op when buckets empty
#
# Env vars:
#   SKIP_POST_ARCHIVE_CLEANUP=yes        — early-return 0 (escape hatch)
#   DRY_RUN_POST_ARCHIVE_CLEANUP=yes     — echo actions instead of running git
#
# Exit codes:
#   0 — always (idempotent / non-blocking)
#
# Root causes this hook fixes (see improvements/post-archive-cleanup-hook.md):
#   1. ship_archive.sh:256 cleanup_plan_file() uses rm -f instead of git rm
#   2. _lib/archive.sh:515 commit_archive_moves() only stages 3 paths, misses .rddf/
#   3. _lib/state.sh:452 check_dirty_key_files() is a sentinel that only warns

set -uo pipefail

# Whitelist: deleted-tracked paths to git rm
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
)

# Whitelist: modified-critical paths to git add (staged, not committed)
_WHITELIST_MODIFIED_PATTERNS=(
  "proposal-approved.md"
  "proposal-suggestions.md"
  "roadmap.md"
)

# Check if a relative path matches any glob-style prefix in patterns.
_matches_prefix() {
  local path="$1"; shift
  for pat in "$@"; do
    case "$path" in
      ${pat}*) return 0 ;;
    esac
  done
  return 1
}

post_archive_cleanup() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local change_name="${2:-}"
  local dry_run="${DRY_RUN_POST_ARCHIVE_CLEANUP:-no}"
  local skip="${SKIP_POST_ARCHIVE_CLEANUP:-no}"

  if [ "$skip" = "yes" ]; then
    echo "⏭️  post_archive_cleanup: SKIPPED (SKIP_POST_ARCHIVE_CLEANUP=yes)"
    return 0
  fi

  cd "$project_root" || { echo "❌ post_archive_cleanup: cannot cd to $project_root" >&2; return 1; }

  # Build maps of basename → paths matching each bucket
  local modified_to_add=()
  local deleted_to_rm=()

  while IFS= read -r line; do
    # porcelain v1 format: XY <path>
    # X = index status, Y = worktree status
    local x="${line:0:1}" y="${line:1:1}"
    local path="${line:3}"
    [ -z "$path" ] && continue

    # Strip leading "renamed: " / "copied: " etc. prefix if any (defensive)
    case "$x$y" in
      ' D')   # deleted in worktree, not staged
        if _matches_prefix "$path" "${_WHITELIST_DELETED_PATTERNS[@]}"; then
          deleted_to_rm+=("$path")
        fi
        ;;
      'M '|'A '|' M')  # modified/added in index, or modified in worktree
        if _matches_prefix "$path" "${_WHITELIST_MODIFIED_PATTERNS[@]}"; then
          modified_to_add+=("$path")
        fi
        ;;
      'MM'|'AM'|'MD'|'MA')  # also modified in worktree
        if _matches_prefix "$path" "${_WHITELIST_MODIFIED_PATTERNS[@]}"; then
          modified_to_add+=("$path")
        fi
        ;;
    esac
  done < <(git status --porcelain)

  # Apply: git rm deleted bucket
  if [ "${#deleted_to_rm[@]}" -gt 0 ]; then
    if [ "$dry_run" = "yes" ]; then
      printf '   would git rm -f %s\n' "${deleted_to_rm[@]}"
    else
      git rm -f "${deleted_to_rm[@]}" 1>/dev/null
      printf '🧹 cleaned: %s\n' "${deleted_to_rm[@]}"
    fi
  fi

  # Apply: git add modified bucket (only staged, not committed)
  if [ "${#modified_to_add[@]}" -gt 0 ]; then
    if [ "$dry_run" = "yes" ]; then
      printf '   would git add %s\n' "${modified_to_add[@]}"
    else
      git add "${modified_to_add[@]}" 1>/dev/null
      printf '🧹 staged: %s\n' "${modified_to_add[@]}"
    fi
  fi

  # Commit only the rm bucket (not the modified — those stay for user commit)
  if [ "${#deleted_to_rm[@]}" -gt 0 ] && [ "$dry_run" != "yes" ]; then
    git commit -q -m "chore(post-archive): clean residue from ${change_name:-unknown}"
    echo "✅ committed chore(post-archive) for ${change_name:-unknown}"
  fi

  return 0
}
