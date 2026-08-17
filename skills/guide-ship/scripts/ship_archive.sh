# _lib/ship_archive.sh
# Phase 3 of guide-ship.md extracted into a reusable helper.
# Was a 179-line inline bash block (lines 927-1107) handling archive mode
# detection, feature integrity check, and worktree/lightweight archive
# orchestration.
#
# Functions exported:
#   - detect_archive_mode <project_root> <change_name>
#       Returns "worktree" if .rddf/wt/<change_name>/ exists AND is registered
#       with `git worktree list`. Returns "lightweight" otherwise. Mirrors the
#       original ARCHIVE_MODE detection block.
#
#   - check_feature_integrity <project_root> <change_name>
#       Best-effort feature completion check using skills._lib.iteration.
#       Honors FEATURE_ARCHIVE_GATE=hard (blocking) vs unset/soft (warning).
#       Returns 0 if non-blocking OR no feature context. Returns 1 only when
#       FEATURE_ARCHIVE_GATE=hard and feature is incomplete.
#
#   - archive_change_for_mode <project_root> <change_name> <mode>
#       Full archive orchestration:
#         - worktree mode: validates branch not detached → calls
#           archive_change from archive.sh → cd back to project_root.
#         - lightweight mode: validates delta targets → fast-forward or
#           no-ff merge → openspec archive → commit_archive_moves →
#           branch cleanup (-d, fallback -D when FORCE_BRANCH_DELETE=yes).
#       Mirrors the original MODE-SPECIFIC archive orchestration.
#
# Helpers required (provided by _lib/worktree.sh, archive.sh):
#   - wt_path_for_branch <name>           (worktree.sh)
#   - find_default_branch                (worktree.sh)
#   - main_repo_root                     (worktree.sh)
#   - archive_change <name>              (archive.sh)
#   - commit_archive_moves <name> <root> (archive.sh)
#   - mark_iteration_archived <name> <root> (archive.sh)

# _LIB_DIR points to _lib/ (shared library location)
# This script is in skills/guide-ship/scripts/, so we need to go up 2 levels
# and then into _lib to find the shared helpers.
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
_LIB_DIR="$(cd "$_SCRIPT_DIR/../../_lib" 2>/dev/null && pwd)"

if [ -f "$_LIB_DIR/worktree.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/worktree.sh"
fi
if [ -f "$_LIB_DIR/archive.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/archive.sh"
fi

# Bootstrap resolve_rdd_lib_dir for external-project support
# (fix-ship-archive-resolve-lib-path: was hardcoding $project_root/_lib/)
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"

# Source post-archive cleanup hook (post-archive-cleanup-hook)
_HL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_HL_SCRIPT_DIR/../../../_lib/post_archive_cleanup.sh" ]; then
  # shellcheck source=/dev/null
  source "$_HL_SCRIPT_DIR/../../../_lib/post_archive_cleanup.sh"
fi

# detect_archive_mode <project_root> <change_name>
detect_archive_mode() {
  local project_root="$1"
  local change_name="$2"
  local wt_path="$project_root/.rddf/wt/${change_name}"

  if [ -d "$wt_path" ] && git -C "$project_root" worktree list | grep -qF "$wt_path"; then
    echo "worktree"
  else
    echo "lightweight"
  fi
}

# check_feature_integrity <project_root> <change_name>
check_feature_integrity() {
  local project_root="$1"
  local change_name="$2"

  PY_PROJECT_ROOT="$project_root" CHANGE_NAME="$change_name" python3 <<'PYEOF' 2>/dev/null
import os, sys
try:
    from skills._lib import iteration as it
except ImportError:
    sys.exit(0)

project_root = os.environ.get("PY_PROJECT_ROOT", ".")
change_name = os.environ.get("CHANGE_NAME", "")
try:
    d = it.load(project_root)
    feature = it.derive_feature_name(change_name)

    pf = None
    ch = it.get_change(d, change_name)
    if ch:
        pf = ch.get("parent_feature")
    if not change_name.startswith("feature-") and not pf:
        sys.exit(0)

    progress = it.feature_progress(d)
    if feature not in progress:
        sys.exit(0)

    done, total = progress[feature]
    if total <= 1:
        sys.exit(0)

    remaining = total - done
    if remaining > 1 or (remaining == 1 and any(
        c.get("status") != "archived"
        for c in d.get("changes", [])
        if it.derive_feature_name(c.get("name", "")) == feature
        and c.get("name") != change_name
    )):
        print(f"⚠️  Feature '{feature}' 完整性提示: 已归档 {done}/{total}")
        print(f"   还有 {total - done} 个 sub-change 未归档，此 feature 仍未完整")

        gate_mode = os.environ.get("FEATURE_ARCHIVE_GATE", "soft")
        if gate_mode == "hard":
            print(f"   ❌ FEATURE_ARCHIVE_GATE=hard 阻止归档 (请先处理其余 sub-change)")
            sys.exit(1)
        else:
            print(f"   归档不会阻断 (设置 FEATURE_ARCHIVE_GATE=hard 可升级为硬阻断)")
except SystemExit:
    raise
except Exception:
    pass
PYEOF
}

# archive_change_for_mode <project_root> <change_name> <mode>
#   Modes: worktree (uses .rddf/wt/<name>/) or lightweight (branch on main repo).
#   Returns 0 only after archive succeeded in both modes; any failure returns non-zero
#   so callers do not silently mark the change as archived.
archive_change_for_mode() {
  local project_root="$1"
  local change_name="$2"
  local mode="$3"

  # Determine tasks_root up front so the completion gate reads the up-to-date copy
  # (worktree copy in worktree mode, main-repo branch in lightweight mode).
  local tasks_root="$project_root"
  local wt_path=""
  if [ "$mode" = "worktree" ]; then
    wt_path="$project_root/.rddf/wt/${change_name}"
    tasks_root="$wt_path"
  fi

  # Shared completion gate (worktree + lightweight). Set FORCE_ARCHIVE_INCOMPLETE=yes
  # to bypass. archive_gate_check writes its own diagnostic to stderr on failure.
  if ! archive_gate_check "$change_name" "$tasks_root"; then
    return 2
  fi

  check_main_repo_clean "$change_name" "$project_root" || {
    echo "❌ Archive blocked: main repo has dirty files" >&2
    return 1
  }

  if [ "$mode" = "worktree" ]; then
    echo "🔍 验证 worktree 分支状态..."

    local wt_branch
    wt_branch=$(git -C "$project_root" worktree list --porcelain | awk -v path="$wt_path" '
        $1 == "worktree" && $2 == path { found=1; next }
        found && $1 == "branch" { print $2; exit }
        found && $1 == "detached" { print "DETACHED"; exit }
    ')

    if [ "$wt_branch" = "DETACHED" ]; then
      echo "❌ 错误：Worktree 处于 detached HEAD，无法 merge" >&2
      echo "   请先切换到正确分支：" >&2
      echo "   cd $wt_path && git checkout openspec/$change_name" >&2
      return 1
    fi

    if ! archive_change "$change_name"; then
      echo "❌ archive_change failed; skipping cleanup to keep state consistent" >&2
      cd "$project_root" || return 1
      return 1
    fi
    cd "$project_root" || return 1
  else
    # Lightweight mode
    local default_branch
    default_branch=$(find_default_branch)
    local branch="openspec/$change_name"

    local new_commits
    new_commits=$(git -C "$project_root" rev-list --count "$default_branch..$branch" 2>/dev/null || echo 0)

    if [ "$new_commits" -eq 0 ]; then
      echo "❌ 分支 $branch 无新提交，archive 阻断 (设置 FORCELESS_COMMITS_BYPASS 或先聚合 commit)" >&2
      return 1
    fi

    echo "📦 Merge $branch → $default_branch ($new_commits 个新提交)"

    git -C "$project_root" checkout "$default_branch" || {
      echo "❌ 无法切换到 $default_branch" >&2
      return 1
    }

    if git -C "$project_root" merge --ff-only "$branch" 2>/dev/null; then
      echo "✅ Fast-forward merge 到 $default_branch 完成"
    else
      echo "⚠️  Fast-forward 不可用，创建 merge commit"
      git -C "$project_root" merge --no-ff "$branch" -m "merge: $change_name change" || {
        echo "❌ merge 失败" >&2
        return 1
      }
    fi

    # Spec-validation gate (fix-ship-archive-resolve-lib-path: use resolve_rdd_lib_dir)
    RDD_LIB_DIR="$(resolve_rdd_lib_dir)" || {
      echo "❌ Archive pre-flight failed: cannot resolve shared library (resolve_rdd_lib_dir failed)" >&2
      echo "   Hint: ensure rdd-workflow is installed globally (install.sh --global) or _lib is available" >&2
      return 1
    }
    if [ ! -f "$RDD_LIB_DIR/validate_delta_targets.py" ]; then
      echo "❌ Archive pre-flight failed: validate_delta_targets.py not found at $RDD_LIB_DIR" >&2
      return 1
    fi
    if ! python3 "$RDD_LIB_DIR/validate_delta_targets.py" "$change_name" 2>/dev/null; then
      echo "❌ Archive pre-flight failed for $change_name" >&2
      echo "   Delta targets invalid. Run validate_delta_targets.py for details." >&2
      python3 "$RDD_LIB_DIR/validate_delta_targets.py" "$change_name"
      return 1
    fi

    if ! openspec archive "$change_name" --yes; then
      echo "❌ openspec archive 失败" >&2
      return 1
    fi

    # ADR-0027 close hook: auto-close linked GitHub issues (lightweight mode).
    # Mirrors _lib/archive.sh::archive_change worktree-mode integration.
    # Failure-tolerant — archive main flow already succeeded, hook is best-effort.
    close_issues_for_change_hook "$change_name" "$project_root" || true

    # Auto-commit archive file moves (failure-tolerant)
    commit_archive_moves "$change_name" "$project_root" || true

    # Sync iteration.json (archive-iteration-sync fix)
    local archive_commit_sha=""
    archive_commit_sha=$(git -C "$project_root" rev-parse HEAD 2>/dev/null || echo "")
    mark_iteration_archived "$change_name" "$project_root" "$archive_commit_sha"

    # On-disk reconciliation (harden-archive-iteration-sync).
    # If mark_iteration_archived failed silently (e.g., transient import error),
    # force-mark from on-disk archive/ truth. Skipped if FORCE_ITERATION_BACKFILL=no.
    if [ "${FORCE_ITERATION_BACKFILL:-yes}" = "yes" ]; then
      SKILLS_PARENT="${HOME}/.agents/skills" \
      MAIN_ROOT="$project_root" \
      CHANGE_NAME="$change_name" \
      ARCHIVE_COMMIT_SHA="$archive_commit_sha" \
        python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.repair import force_mark_archived
except ImportError as e:
    print(f"⚠️  repair module unavailable: {e}", file=sys.stderr)
    sys.exit(0)
try:
    main_root = os.environ["MAIN_ROOT"]
    change_name = os.environ["CHANGE_NAME"]
    sha = os.environ.get("ARCHIVE_COMMIT_SHA") or None
    modified = force_mark_archived(main_root, change_name, archive_commit_sha=sha)
    if modified:
        print(f"⚠️ iteration.json sync failed — auto-recovered via on-disk scan for {change_name}", file=sys.stderr)
except Exception as e:
    print(f"⚠️ on-disk reconciliation failed: {e}", file=sys.stderr)
' || true
    else
      echo "⚠️ FORCE_ITERATION_BACKFILL=no set — skipping on-disk reconciliation" >&2
    fi

    # Delete branch
    if git -C "$project_root" branch -d "$branch" 2>/dev/null; then
      echo "✅ Branch 已删除: $branch"
    else
      echo "⚠️  Branch $branch 有未合并的提交" >&2
      if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
        git -C "$project_root" branch -D "$branch" 2>/dev/null || true
      fi
    fi

    echo "✅ $change_name 已归档（轻量模式）"
  fi

  # Update proposal-approved.md status (archive-update-proposal-status fix)
  # Moved from archive.sh step 9 to this single funnel for both modes.
  local update_script="$_SCRIPT_DIR/../../propose/scripts/update_proposal_status.py"
  if [ -f "$update_script" ]; then
    python3 "$update_script" "$change_name" "$project_root" 2>/dev/null || true
  fi

  # Cleanup plan-handoff after archive (archive-cleanup-plan-handoff)
  cleanup_plan_handoff "$project_root" "$change_name" || true

  # Cleanup plan file after archive (archive-cleanup-plan-files)
  cleanup_plan_file "$project_root" "$change_name" || true

  # Post-archive cleanup hook (post-archive-cleanup-hook).
  # Non-blocking: clears residual deleted tracked files after archive.
  post_archive_cleanup "$project_root" "$change_name" || true

  return 0
}

# cleanup_plan_file <project_root> <change_name>
#   Delete .rddf/plans/<change_name>.md after archive.
#   Idempotent: returns 0 if file doesn't exist.
cleanup_plan_file() {
  local project_root="$1"
  local change_name="$2"
  local plan_file="$project_root/.rddf/plans/${change_name}.md"

  [ -f "$plan_file" ] || return 0

  rm -f "$plan_file"
  echo "✅ 已清理计划文件: .rddf/plans/${change_name}.md"
}

# cleanup_plan_handoff <project_root> <change_name>
#   Updates .rddf/state/.plan-handoff.json after archiving a change:
#   - Adds archived_at timestamp
#   - Decrements active_changes count
#   - Appends to archived_changes list
cleanup_plan_handoff() {
  local project_root="$1"
  local change_name="$2"
  local handoff_file="$project_root/.rddf/state/.plan-handoff.json"

  [ ! -f "$handoff_file" ] && return 0

  HANDOFF_FILE="$handoff_file" CHANGE_NAME="$change_name" \
  python3 -c '
import json, os
from datetime import datetime, timezone

handoff_file = os.environ["HANDOFF_FILE"]
change_name = os.environ["CHANGE_NAME"]

with open(handoff_file) as f:
    data = json.load(f)

data["archived_at"] = datetime.now(timezone.utc).isoformat()

active = data.get("active_changes", 0)
if isinstance(active, int) and active > 0:
    data["active_changes"] = active - 1

if "archived_changes" not in data:
    data["archived_changes"] = []
data["archived_changes"].append(change_name)

with open(handoff_file, "w") as f:
    json.dump(data, f, indent=2)
' 2>/dev/null || true
}

check_main_repo_clean() {
  local change_name="$1"
  local project_root="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local dirty_files

  dirty_files=$(git -C "$project_root" status --porcelain 2>/dev/null | head -20)
  if [ -z "$dirty_files" ]; then
    return 0
  fi

  local change_scope_dirty=""
  local other_dirty=""
  while IFS= read -r line; do
    local filepath
    filepath=$(echo "$line" | awk '{print $2}')
    case "$filepath" in
      openspec/changes/$change_name/*)
        change_scope_dirty="$change_scope_dirty $filepath" ;;
      .rddf/*) ;;
      *)
        other_dirty="$other_dirty $filepath" ;;
    esac
  done <<< "$dirty_files"

  if [ -n "$change_scope_dirty" ]; then
    echo "❌ Dirty files in change scope ('$change_name'):$change_scope_dirty" >&2
    return 1
  fi

  if [ -n "$other_dirty" ]; then
    echo "⚠️  Unrelated dirty files:$other_dirty (non-blocking)" >&2
  fi

  return 0
}