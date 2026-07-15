# skills/_lib/status_helpers.sh
# Status skill helpers extracted from status.md Mode B (sync detection
# and repair). These were inline bash heredocs spanning ~75 lines and
# are now promoted to shared helpers following the archive.sh
# precedent (P1-14).
#
# Usage:
#   source skills/_lib/status_helpers.sh
#   detect_sync_issues "$PROJECT_ROOT" "<name>" "$HAS_WORKTREE" "$WT_DIRTY"
#   repair_sync_state "$PROJECT_ROOT" "<name>" "<task_description>"
#
# Functions exported:
#   - detect_sync_issues <project_root> <name> <has_worktree> <wt_dirty>
#       Prints any of three classes of problem found for the given
#       change, then returns 0 if at least one issue was reported, 1 if
#       all clean. The caller is expected to render its own report UI;
#       this helper only emits the raw signals.
#         Class 1: PLAN_DONE > TASKS_DONE — Prometheus finished more
#                  units than tasks.md marks complete.
#         Class 2: has_worktree=1 + wt_dirty>0 — worktree has uncommitted
#                  changes that need review.
#         Class 3: worktree branch is behind the default branch (new
#                  commits landed in default since worktree creation).
#
#   - repair_sync_state <project_root> <name> <task_description>
#       Mutates openspec/changes/<name>/tasks.md in place: replaces
#       `- [ ] <task_description>` with `- [x] <task_description>` for
#       the first matching line. Uses awk index() (literal match, not
#       regex) to avoid metacharacter risk in user-supplied task text.
#       Returns 0 on edit, 1 if no matching line found.
#
# Helpers required (none from worktree.sh — these helpers are
# filesystem-only):
#   (no external dependencies)

# Source worktree.sh for wt_path_for_branch + find_default_branch.
# Use a self-discovery approach so this file is testable from any cwd.
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
# Note: status_helpers.sh does not currently source worktree.sh — these
# helpers only need filesystem + git access, not worktree resolution.
# Kept here for symmetry with archive.sh and future-proofing if a
# helper grows a wt_path_for_branch dependency.

# detect_sync_issues <project_root> <name> <has_worktree> <wt_dirty>
#   Prints any of three classes of problem found for the given
#   change. Returns 0 if at least one issue was reported, 1 if all
#   clean.
#
#   Class 1: PLAN_DONE > TASKS_DONE — Prometheus finished more units
#            than tasks.md marks complete.
#   Class 2: has_worktree=1 + wt_dirty>0 — worktree has uncommitted
#            changes that need review.
#   Class 3: worktree branch is behind the default branch (new
#            commits landed in default since worktree creation).
#
#   Origin: status.md Mode B Step 2 (lines 246-294). Promoted to a
#   shared helper so future tests can exercise each class in isolation.
detect_sync_issues() {
  local project_root="${1:-}" name="${2:-}" has_worktree="${3:-0}" wt_dirty="${4:-0}"
  if [[ -z "$project_root" || -z "$name" ]]; then
    echo "❌ detect_sync_issues 需要 project_root 和 name"
    return 1
  fi

  local plan_file tasks_file plan_done tasks_done
  plan_file="$project_root/.rddf/plans/${name}.md"
  tasks_file="$project_root/openspec/changes/${name}/tasks.md"

  local issue_count=0

  # Class 1: PLAN_DONE vs TASKS_DONE divergence
  plan_done=0
  if [ -f "$plan_file" ]; then
    plan_done=$(grep -c "\- \[x\]" "$plan_file" 2>/dev/null || echo 0)
  fi
  tasks_done=$(grep -c "\- \[x\]" "$tasks_file" 2>/dev/null || echo 0)
  if [ "$plan_done" -gt "$tasks_done" ]; then
    echo "⚠️ 不同步: Prometheus 已完成 $plan_done 个单元，但 tasks.md 只标记了 $tasks_done 个"
    echo "修复: 同步 tasks.md 以匹配实际完成状态"
    issue_count=$((issue_count + 1))
  fi

  # Class 2: worktree has uncommitted changes
  if [ "$has_worktree" = "1" ] && [ "$wt_dirty" -gt 0 ]; then
    echo "⚠️ Worktree 有 $wt_dirty 个未提交文件"
    issue_count=$((issue_count + 1))
  fi

  # Class 3: worktree branch is behind the default branch
  if [ "$has_worktree" = "1" ]; then
    local default_branch merge_base main_tip
    default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || echo "main")
    merge_base=$(git merge-base "openspec/$name" "$default_branch" 2>/dev/null)
    main_tip=$(git rev-parse "$default_branch" 2>/dev/null)
    if [ -n "$merge_base" ] && [ -n "$main_tip" ] && [ "$merge_base" != "$main_tip" ]; then
      echo "⚠️ Worktree 分支落后于 $default_branch（创建后有新 commit 进入默认分支）"
      issue_count=$((issue_count + 1))
    fi
  fi

  if [ "$issue_count" -gt 0 ]; then
    return 0
  fi
  return 1
}

#   repair_sync_state <project_root> <name> <task_description>
#       Mutates openspec/changes/<name>/tasks.md in place: replaces
#       `- [ ] <task_description>` with `- [x] <task_description>` for the
#       first matching line. Uses awk `index()` + `substr()` for literal
#       (non-regex) replacement — `sub()` was avoided because
#       `- [ ] <desc>` would interpret `[ ]` as a regex character class
#       matching a single space, breaking the match.
#
#       Returns 0 on edit, 1 if no matching line found (caller can decide
#       to surface a warning).
#
#       Origin: status.md Mode B Step 3 (lines 300-313). Promoted to a
#       shared helper so the awk-magic can be tested in isolation from the
#       rest of the skill flow.
repair_sync_state() {
  local project_root="${1:-}" name="${2:-}" task_desc="${3:-}"
  if [[ -z "$project_root" || -z "$name" || -z "$task_desc" ]]; then
    echo "❌ repair_sync_state 需要 project_root, name, task_description"
    return 1
  fi

  local tasks_file tmpfile
  tasks_file="$project_root/openspec/changes/${name}/tasks.md"
  if [ ! -f "$tasks_file" ]; then
    echo "❌ tasks.md 不存在: $tasks_file"
    return 1
  fi

  tmpfile=$(mktemp -t status_tasks_XXXXXX.md)
  awk -v desc="- [ ] $task_desc" -v repl="- [x] $task_desc" '
    {
      pos = index($0, desc)
      if (pos > 0) {
        $0 = substr($0, 1, pos-1) repl substr($0, pos + length(desc))
        changed = 1
      }
      print
    }
    END { exit (changed ? 0 : 1) }
  ' "$tasks_file" > "$tmpfile" || {
    local rc=$?
    rm -f "$tmpfile"
    if [ "$rc" -ne 0 ]; then
      echo "⚠️  未找到匹配的任务描述: $task_desc"
    fi
    return 1
  }

  if ! mv "$tmpfile" "$tasks_file"; then
    rm -f "$tmpfile"
    echo "❌ mv $tmpfile -> $tasks_file 失败"
    return 1
  fi

  echo "✅ 已标记完成: $task_desc"
  return 0
}