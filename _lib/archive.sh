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

# Source post-archive cleanup hook (post-archive-cleanup-hook)
if [ -f "$_LIB_DIR/post_archive_cleanup.sh" ]; then
  # shellcheck source=/dev/null
  source "$_LIB_DIR/post_archive_cleanup.sh"
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

# check_tasks_completion <name> <main_root>
#   Reads <main_root>/openspec/changes/<name>/tasks.md and reports the
#   checkbox completion ratio. Honors STRICT_TASKS_GATE (blocks when
#   ratio < 100%) and SKIP_TASKS_GATE (bypass). Default = warning only.
#   Missing tasks.md or 0 tasks = no-op (return 0).
#
#   Origin: enforce-tasks-completion-before-archive proposal. Pairs
#   with check_worktree_commits as the second pre-merge safety net.
check_tasks_completion() {
  local name="${1:-}"
  local main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  if [ "${SKIP_TASKS_GATE:-no}" = "yes" ]; then
      echo "[SKIP] tasks gate skipped (SKIP_TASKS_GATE=yes)" >&2
      return 0
  fi

  local tasks_md="$main_root/openspec/changes/$name/tasks.md"
  if [[ ! -f "$tasks_md" ]]; then
      echo "[INFO] no tasks.md for $name, skipping completion check" >&2
      return 0
  fi

  local done_count open_count total_count pct
  done_count=$(grep -cE '^- \[[xX]\]' "$tasks_md" 2>/dev/null | head -n1)
  done_count=${done_count:-0}
  [[ "$done_count" =~ ^[0-9]+$ ]] || done_count=0
  open_count=$(grep -cE '^- \[ \]' "$tasks_md" 2>/dev/null | head -n1)
  open_count=${open_count:-0}
  [[ "$open_count" =~ ^[0-9]+$ ]] || open_count=0
  total_count=$(( done_count + open_count ))
  if [ "$total_count" -eq 0 ]; then
      echo "[INFO] tasks.md for $name has 0 checkboxes, skipping completion check" >&2
      return 0
  fi
  pct=$(( done_count * 100 / total_count ))

  echo "📋 tasks completion: $done_count/$total_count (${pct}%)"

  if [ "$pct" -lt 100 ]; then
      if [ "${STRICT_TASKS_GATE:-no}" = "yes" ]; then
          echo "❌ STRICT_TASKS_GATE: tasks incomplete $done_count/$total_count (${pct}%)" >&2
          return 1
      fi
      echo "⚠️ tasks incomplete (warning, set STRICT_TASKS_GATE=yes to block): $done_count/$total_count (${pct}%)" >&2
  fi
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

# verifier_contract_check <change_name> [project_root]
#   Returns 0 if change has passing (or audited bypassed) verification record
#   bound to the current openspec/<change> branch tip, with no failed AC in
#   the canonical verdict cache. Returns 1 otherwise.
#   Honors SKIP_RDD_VERIFIER (audited bypass) and FEATURE_ARCHIVE_GATE=hard.
#   Per fix-rdd-verifier-lifecycle-dashboard Tasks 11-14.
#
#   When iteration.json has NO verification metadata for the change,
#   returns 0 with reason="verification-missing" (legacy fallback) so
#   existing changes without verification history are not broken.
#   Set RDDF_REQUIRE_VERIFIER_CONTRACT=yes to enforce strict mode and
#   block on missing verification.
verifier_contract_check() {
  local change_name="${1:-}"
  local project_root="${2:-}"
  [[ -z "$change_name" ]] && return 0

  if [ -z "$project_root" ]; then
    project_root="${RDDF_PROJECT_ROOT:-${PROJECT_ROOT:-$(pwd)}}"
  fi

  local require_strict="${RDDF_REQUIRE_VERIFIER_CONTRACT:-no}"

  export RDDF_PROJECT_ROOT="$project_root"
  local pythonpath="${PROJECT_ROOT:-${REPO_ROOT:-}}"
  if [ -z "$pythonpath" ]; then
    pythonpath="$(git -C "$project_root" rev-parse --show-toplevel 2>/dev/null || echo "$project_root")"
  fi
  local result
  result=$(RDDF_PROJECT_ROOT="$project_root" \
           FEATURE_ARCHIVE_GATE="${FEATURE_ARCHIVE_GATE:-off}" \
           PYTHONPATH="$pythonpath" \
           python3 -m _lib.verifier.archive_gate check "$change_name" 2>&1) || true
  unset RDDF_PROJECT_ROOT

  if [ "$result" = "READY" ]; then
    return 0
  fi

  if [ "$require_strict" != "yes" ] && [[ "$result" == *"verification missing"* ]]; then
    echo "⚠️  verifier contract: $result (legacy fallback, set RDDF_REQUIRE_VERIFIER_CONTRACT=yes to enforce)"
    return 0
  fi

  echo "❌ verifier contract: $result"
  return 1
}

# archive_gate_check <change_name> [tasks_root]
#   Returns 0 if change has at least 1 completed task ([x]), returns 1 if 0.
#   Honors FORCE_ARCHIVE_INCOMPLETE=yes to bypass the gate.
#   tasks_root (optional) is the directory containing openspec/changes/<name>/tasks.md
#   — typically the worktree path in worktree mode or the main repo path in
#   lightweight mode. If omitted, falls back to the current working directory.
archive_gate_check() {
  local change_name="${1:-}"
  local tasks_root="${2:-}"
  [[ -z "$change_name" ]] && return 0

  if [ "${FORCE_ARCHIVE_INCOMPLETE:-no}" = "yes" ]; then
    return 0
  fi

  if [ -z "$tasks_root" ]; then
    tasks_root="."
  fi

  # Verifier contract gate (per fix-rdd-verifier-lifecycle-dashboard)
  # Default: legacy fallback (warning only) when verification data absent.
  # Set RDDF_REQUIRE_VERIFIER_CONTRACT=yes to enforce strict blocking.
  if [ "${SKIP_VERIFIER_CONTRACT:-no}" != "yes" ]; then
    if ! verifier_contract_check "$change_name" "$tasks_root"; then
      return 1
    fi
  fi

  local tasks_file="$tasks_root/openspec/changes/$change_name/tasks.md"
  if [ ! -f "$tasks_file" ]; then
    echo "❌ archive_gate_check: tasks.md 缺失 ($tasks_file)。设置 FORCE_ARCHIVE_INCOMPLETE=yes 跳过"
    return 1
  fi

  local completed
  completed=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null | head -n1)
  [[ "$completed" =~ ^[0-9]+$ ]] || completed=0

  if [ "$completed" -eq 0 ]; then
    echo "❌ 未实现 (0 个完成任务)。设置 FORCE_ARCHIVE_INCOMPLETE=yes 跳过"
    return 1
  fi

  # AC verification step (ac-verifier skill, Task 10) + SHA cache check (ADR-0034 §7.2)
  if [ "${SKIP_AC_VERIFICATION:-no}" != "yes" ]; then
    local proposal_file="$tasks_root/openspec/changes/$change_name/proposal.md"
    if [ -f "$proposal_file" ]; then
      local ac_script
      ac_script="$(git rev-parse --show-toplevel 2>/dev/null)/skills/ac-verifier/scripts/ac_verifier.sh"
      if [ -x "$ac_script" ]; then
        # SHA-fingerprint verdict cache check (Per ADR-0034 §7.2 + Oracle §C)
        # Avoids redundant LLM call when rdd-verifier already ran at same commit.
        local verdict_cache="$tasks_root/.rddf/state/.ac-verdict-${change_name}.json"
        local current_sha
        current_sha=$(git -C "$tasks_root" rev-parse HEAD 2>/dev/null || echo "unknown")

        local cache_hit="no"
        if [ -f "$verdict_cache" ]; then
          local cached_sha
          cached_sha=$(python3 -c "import json,sys; print(json.load(open('$verdict_cache')).get('codebase_commit',''))" 2>/dev/null || echo "")
          if [ -n "$cached_sha" ] && [ "$cached_sha" = "$current_sha" ]; then
            cache_hit="yes"
            echo "♻️  Reusing ac-verifier verdict cache (commit $cached_sha)"
          else
            echo "⚠️  ac-verifier verdict cache stale (cached: ${cached_sha:-none}, current: $current_sha)"
          fi
        fi

        if [ "$cache_hit" = "yes" ]; then
          # Evaluate cached verdict for STRICT_AC_GATE
          if [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
            local cached_has_fail
            cached_has_fail=$(python3 -c "
import json,sys
try:
    d = json.load(open('$verdict_cache'))
    fails = [v for v in d.get('verdict', []) if v.get('status') == 'fail']
    sys.exit(1 if fails else 0)
except Exception:
    sys.exit(0)
" 2>/dev/null)
            if [ "$?" -ne 0 ] || [ "$cached_has_fail" = "1" ]; then
              echo "❌ archive_gate_check: AC verification failed under STRICT_AC_GATE (cached)"
              python3 -c "
import json
try:
    d = json.load(open('$verdict_cache'))
    for v in d.get('verdict', []):
        if v.get('status') == 'fail':
            print(f'  {v.get(\"ac_id\", \"?\")}: {v.get(\"reasoning\", \"no reasoning\")}')
except Exception:
    pass
" 2>/dev/null
              return 1
            fi
          fi
          # Non-strict + cache hit = pass; skip LLM
        else
          # Original ac-verifier invocation (cache miss or stale)
          local ac_output ac_exit
          ac_output=$(PROJECT_ROOT="$tasks_root" bash "$ac_script" "$change_name" 2>&1)
          ac_exit=$?
          case $ac_exit in
            0) ;;  # all pass — continue
            1)
              if [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
                echo "❌ archive_gate_check: AC verification failed under STRICT_AC_GATE"
                echo "$ac_output" | tail -30
                return 1
              else
                echo "⚠️  archive_gate_check: AC verification warning (set STRICT_AC_GATE=yes to block)"
                echo "$ac_output" | tail -30
              fi
              ;;
            2) ;;  # skipped — continue silently
            3)
              echo "⚠️  AC verification errored; treating as warning (set SKIP_AC_VERIFICATION=yes to suppress)"
              echo "$ac_output" | tail -10
              ;;
          esac
        fi
      fi
    fi
  fi
  return 0
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
#     6. openspec archive <name> --yes (kept inline - CLI, not lib)
#     7. git worktree remove + git branch -d (or -D via FORCE_BRANCH_DELETE)
#        (cleanup_worktree_and_branch)
#   Returns 0 on success, 1 on any failure.
#
#   Environment:
#     FORCE_BRANCH_DELETE=yes  - fall back to `git branch -D` if `-d`
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

  # 2.5. Shared completion gate (also called by ship_archive.sh lightweight path).
  # Pass wt_path so the gate reads the up-to-date tasks.md from the worktree,
  # not the stale copy on the default branch.
  archive_gate_check "$name" "$wt_path" >/dev/null || return 3

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

  # 6.5 Close linked GitHub issues (ADR-0027 change-b). Failure-tolerant.
  close_issues_for_change_hook "$name" "$main_root" || true

  # 7. Cleanup worktree + branch
  cleanup_worktree_and_branch "$name" "$main_root" "$wt_path" "$branch" || return 1

  # 7.5 Auto-commit archive file moves (added by add-archive-auto-commit).
  # Tolerate failure (file moves remain in working tree for human review).
  commit_archive_moves "$name" "$main_root" || true

  # 8. Update iteration.json (current sprint tracker). Best-effort.
  local archive_commit_sha=""
  archive_commit_sha=$(git -C "$main_root" rev-parse HEAD 2>/dev/null || echo "")
  mark_iteration_archived "$name" "$main_root" "$archive_commit_sha"

  # 8.7 Tasks completion gate (enforce-tasks-completion-before-archive):
  # warn when tasks.md is < 100% complete; STRICT_TASKS_GATE=yes blocks;
  # SKIP_TASKS_GATE=yes bypasses. Default = warning only.
  check_tasks_completion "$name" "$main_root" || true

  # 8.6 Collect L2 violation count (collect-l2-violation-count-on-archive)
  collect_l2_count_wrapper "$name" "$main_root"

  # 8.5 Tasks.md sidecar (fix-tasks-md-archive-residue): snapshot the
  # original tasks.md to .archived-snapshot and replace tasks.md with
  # an archived-skeleton header. Must run AFTER step 8 (mark_iteration_archived)
  # so the [x] count is taken from the original file. Idempotent: skips
  # if sidecar already exists.
  PYTHONPATH="$_LIB_DIR/../.." "$_LIB_DIR/../_lib_iteration_sidecar.py" \
      "$main_root" "$name" \
      2>/dev/null || true
  python3 -c "
import os, sys
sys.path.insert(0, '$main_root')
from skills._lib.iteration.archive_sidecar import write_tasks_md_sidecar as w
import glob
archived = glob.glob(os.path.join('$main_root', 'openspec', 'changes', 'archive', '*-' + '$name'))
if archived:
    w(archived[0])
" 2>/dev/null || true

  # 9. (Moved to ship_archive.sh::archive_change_for_mode — single funnel for both modes)

  echo "✅ $name 已归档"

  # ── reflect_engine(ship): post-archive reflection hook ──
  # Non-blocking: failures here never affect the archive result.
  # Ship phase triggers on any unrecovered failure or execute error.
  if [ "${SKIP_WORKFLOW_REFLECTION:-}" != "1" ]; then
    local reflect_root
    reflect_root="${main_root:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    REFLECT_ROOT="$reflect_root" python3 -c "
import os, sys, json
root = os.environ.get('REFLECT_ROOT', '.')
sys.path.insert(0, root)
try:
    from skills._lib.reflect_engine import ReflectEngine
    failures = []
    event_log_path = os.path.join(root, '.rddf', 'state', 'event_log.json')
    if os.path.isfile(event_log_path):
        with open(event_log_path) as f:
            events = json.load(f)
        for ev in events[-20:]:
            if ev.get('type') in ('unrecovered_failure', 'execute_error'):
                failures.append(ev)
    engine = ReflectEngine(phase='ship', project_root=root, timeout=10)
    result = engine.analyze(failures=failures)
    if result.action == 'propose_issue':
        print(f'🔍 Reflect: Ship phase detected failures.')
        print(f'   Fingerprint: {result.fingerprint}')
except Exception:
    pass  # non-blocking
" 2>/dev/null || true
  fi

  # 9. Post-archive cleanup hook (post-archive-cleanup-hook).
  # Non-blocking: fixes residual deleted tracked files (e.g. .rddf/plans/<name>.md)
  # left by the dispersed cleanup chain. Run after all archive git mutations.
  post_archive_cleanup "$main_root" "$name" || true

  return 0
}

# mark_iteration_archived <name> <main_root> [archive_commit_sha]
#   Best-effort update of .rddf/state/iteration.json: mark the change
#   as archived with a timestamp. Never returns non-zero (callers should
#   not treat iteration tracking failure as archive failure).
#
#   Implementation: invokes the Python `skills._lib.iteration.post_archive`
#   module via a here-string. If the module is missing or the file is
#   unreadable, logs a warning and returns 0.
#
#   Path resolution: `skills/_lib/iteration.py` is a sibling of this
#   script, so the parent of $_LIB_DIR is the directory that contains
#   the `skills/` package. We insert that parent on sys.path.
mark_iteration_archived() {
  local name="${1:-}" main_root="${2:-}" archive_commit_sha="${3:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  local iter_file="$main_root/.rddf/state/iteration.json"
  if [ ! -f "$iter_file" ]; then
    # No iteration state yet — nothing to update. This is normal for
    # projects that predate v2.0 or never ran propose with roadmap.
    return 0
  fi

  local skills_parent
  skills_parent="$(cd "$_LIB_DIR/../.." 2>/dev/null && pwd)"

  # v2.0.2 安全修复: bash 变量通过环境变量传递 (os.environ),
  # 不用 '$VAR' 直接拼到 Python 源码. 避免单引号路径/注入风险.
  if ! SKILLS_PARENT="$skills_parent" \
        MAIN_ROOT="$main_root" \
        CHANGE_NAME="$name" \
        ARCHIVE_COMMIT_SHA="$archive_commit_sha" \
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
    sha = os.environ.get("ARCHIVE_COMMIT_SHA") or None
    warning = it_mod.post_archive.sync_iteration_after_archive(
        main_root, change_name, archive_commit_sha=sha)
    if warning:
        print(f"⚠️  iteration.json update partial: {warning}", file=sys.stderr)
    else:
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

# collect_l2_count_wrapper <name> <main_root>
#   Best-effort L2 count collection. Never propagates failure.
collect_l2_count_wrapper() {
  local name="${1:-}" main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  local skills_parent
  skills_parent="$(cd "$main_root/skills/../" 2>/dev/null && pwd)"
  [[ -z "$skills_parent" ]] && return 0

  SKILLS_PARENT="$skills_parent" \
    MAIN_ROOT="$main_root" \
    CHANGE_NAME="$name" \
    python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.l2 import collect_l2_count
    warning = collect_l2_count(os.environ["MAIN_ROOT"], os.environ["CHANGE_NAME"])
    if warning:
        print(f"⚠️  {warning}", file=sys.stderr)
except Exception as e:
    print(f"⚠️  collect_l2_count failed (archive continues): {e}", file=sys.stderr)
' 2>/dev/null || true
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

  # Stage the 3 path trio: deleted active change dir, new archive dir, new spec dir.
  # git add on the deleted path stages the deletions; git rm -r is NOT needed
  # (and would cause git add to fail since the path no longer exists in the
  # working tree after rm). The `|| true` handles the case where the path
  # doesn't exist (e.g. already cleaned up by openspec archive).
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

# close_issues_for_change_hook <name> <main_root>
#   ADR-0027 change-b: invoke the close hook after openspec archive succeeds.
#   Failure-tolerant by contract (the archive main flow already passed; the
#   hook only reports + auto-closes linked GitHub issues, never blocks it).
#   Returns 0 always so the `|| true` call site stays sound.
close_issues_for_change_hook() {
  local name="${1:-}" main_root="${2:-}"
  [[ -z "$name" || -z "$main_root" ]] && return 0

  if [ "${RDDF_REPORT_CLOSE_ON_ARCHIVE:-yes}" = "no" ]; then
    return 0
  fi

  local py_dir
  py_dir="$(cd "$main_root" && pwd)"
  if ! RDDF_CLOSE_CHANGE_NAME="$name" \
       RDDF_CLOSE_PROJECT_ROOT="$py_dir" \
       RDDF_NEW_VERSION="${RDDF_NEW_VERSION:-next}" \
       python3 -c "
import os, sys
sys.path.insert(0, os.environ['RDDF_CLOSE_PROJECT_ROOT'] + '/_lib')
from close_issues import close_issues_for_change
result = close_issues_for_change(
    os.environ['RDDF_CLOSE_CHANGE_NAME'],
    os.environ['RDDF_CLOSE_PROJECT_ROOT']
)
if result.closed:
    print(f'✅ closed {len(result.closed)} issue(s): {result.closed}')
if result.skipped:
    print(f'⏭  skipped (already closed): {result.skipped}')
if result.manual_links:
    for ref, url in result.manual_links:
        print(f'ℹ️  no push permission — close manually: {url}')
if result.errors:
    for err in result.errors:
        print(f'⚠️  {err}', file=sys.stderr)
" 2>/dev/null; then
    echo "⚠️  close_issues_for_change_hook: python invocation failed (non-blocking)"
  fi
  return 0
}

# reconcile [project_root]
#   Manual on-disk backfill: scan archive/ for entries missing iteration.json
#   archived_at, force-set them. Idempotent — safe to run multiple times.
reconcile() {
  local project_root="${1:-$PWD}"
  local archive_dir="$project_root/openspec/changes/archive"
  [ -d "$archive_dir" ] || { echo "❌ No archive dir at $archive_dir"; return 1; }

  echo "🔍 Scanning $archive_dir for stale iteration.json entries..."

  local skills_parent
  skills_parent="$(cd "$_LIB_DIR/../.." 2>/dev/null && pwd)"

  local fixed=0 skipped=0
  for d in "$archive_dir"/*/; do
    [ -d "$d" ] || continue
    local dir_name
    dir_name=$(basename "$d")
    # Strip the full date prefix `<YYYY>-<MM>-<DD>-` (11 chars). The
    # previous expansion `${dir_name#*-}` only stripped the FIRST `-`,
    # producing names like `08-16-foo` from `2026-08-16-foo`, which
    # then fed wrong names to force_mark_archived. Use Python here to
    # keep the parsing deterministic — bash parameter expansion for
    # multi-segment prefixes is fragile.
    local change_name
    change_name=$(SKILLS_PARENT="$skills_parent" \
                  DIR_NAME="$dir_name" \
                  python3 -c '
import os, re
dir_name = os.environ["DIR_NAME"]
m = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", dir_name)
if m:
    print(m.group(1))
else:
    print(dir_name)  # legacy no-date-prefix form: pass through as-is
')
    [ -z "$change_name" ] && continue

    local result
    result=$(SKILLS_PARENT="$skills_parent" \
             MAIN_ROOT="$project_root" \
             CHANGE_NAME="$change_name" \
             python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.repair import force_mark_archived
except ImportError:
    print("error:module")
    sys.exit(0)
modified = force_mark_archived(os.environ["MAIN_ROOT"], os.environ["CHANGE_NAME"])
print("fixed" if modified else "skipped")
' 2>/dev/null)
    case "$result" in
      fixed)   echo "  ✅ $change_name: fixed"; fixed=$((fixed+1)) ;;
      skipped) echo "  ⏭️  $change_name: already synced"; skipped=$((skipped+1)) ;;
      *)       echo "  ⚠️  $change_name: $result" ;;
    esac
  done

  echo ""
  echo "Summary: $fixed fixed, $skipped skipped"
}
