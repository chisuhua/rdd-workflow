# skills/_lib/scan-state.sh
# Project state scanner extracted from skills/guide.md lines 21-110.
# Used by `guide` (skill recommender) to detect: arch handoff, plan handoff,
# worktree state, committed changes, roadmap presence, pending proposals,
# and emit RECOMMEND + REASON for the calling AI agent.
#
# Usage:
#   source skills/_lib/scan-state.sh
#   scan_state
#   echo "$RECOMMEND  $REASON"
#
# Function exported:
#   - scan_state
#       Sets globals RECOMMEND + REASON only (other potential globals
#       such as ROADMAP, ARCH_HANDOFF, etc. are deliberately NOT
#       exported — callers must read the filesystem themselves if
#       they need additional state).
#       See `EXPORTED_VARS: {RECOMMEND REASON}` header for grep-ability.
# EXPORTED_VARS: {RECOMMEND REASON}
#
# Bug fix history (carried verbatim from skills/guide.md, comments preserved
# as regression guards):
#   - $3, not $2: git worktree list puts branch in column 3
#   - [openspec/ prefix: git worktree list output wraps branches in brackets,
#     so the regex must include the opening '[' to avoid matching on path
#     substrings (this P1-3 bracket fix is part of the extraction)
#   - git show HEAD:<path> requires repo-relative path; cd into PROJECT_ROOT
#   - json.load (not grep) on proposal-suggestions.md to avoid matching the
#     literal word "待创建" inside description fields (P1-7)
#   - PY_PROJECT_ROOT env var (not cwd-relative open) to keep python safe
#     regardless of caller's cwd (pattern from archive.sh:mark_iteration_archived)
#
# State files read (gitignored under .rddf/state/):
#   - .rddf/state/.arch-handoff.json   — arch phase done sentinel
#   - .rddf/state/.plan-handoff.json   — plan phase done sentinel
#   - proposal-suggestions.md          — JSON array with status field
#   - roadmap.md                       — arch artifact (committed)

# scan_state
#   Mutates caller-namespace globals RECOMMEND and REASON.
#   Priority order (highest first):
#     1.  arch-handoff present, plan-handoff absent → "guide-plan"
#     1.5 arch-handoff present, ADR < 1           → "guide-arch (recover)"
#     2.  plan-handoff present                     → "guide-ship"
#     2.5 plan-handoff present, active_changes = 0  → "guide-ship (cleanup)"
#     3.  worktree with incomplete tasks           → "guide-ship"
#     4.  detached worktrees (count > 0)             → "guide-ship"
#     5.  worktree tasks all completed               → "guide-ship"
#     6.  committed change in HEAD (no worktree)   → "guide-ship"
#     7.  no roadmap.md                            → "guide-arch"
#     8.  no openspec/changes/                     → "guide-plan"
#     9.  proposal-suggestions.md has pending entry  → "guide-plan"
#    10. default                                    → "guide-ship"
scan_state() {
  local PROJECT_ROOT="$1"
  if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  fi

  local ARCH_HANDOFF PLAN_HANDOFF
  ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  PLAN_HANDOFF="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"

  type -t check_dirty_key_files &>/dev/null || source "$PROJECT_ROOT/skills/_lib/state.sh"
  check_dirty_key_files "$PROJECT_ROOT"

  # 1. arch-handoff present, plan-handoff absent → guide-plan
  if [ -f "$ARCH_HANDOFF" ] && [ ! -f "$PLAN_HANDOFF" ]; then
    # 1.5: arch-done incomplete — arch-handoff exists but ADR missing
    local ADR_COUNT=0
    if command -v python3 >/dev/null 2>&1 && [ -f "$ARCH_HANDOFF" ]; then
      ADR_COUNT=$(python3 -c "import json; d=json.load(open('$ARCH_HANDOFF')); v=d.get('adr_count',0); print(v if isinstance(v,int) else len(v))" 2>/dev/null || echo 0)
    fi
    if [ "$ADR_COUNT" -lt 1 ]; then
      RECOMMEND="guide-arch"
      REASON="arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)"
      return 0
    fi
    RECOMMEND="guide-plan"
    REASON="架构定义已完成 → 进入变更生成"
    return 0
  fi

  # 2. plan-handoff present → guide-ship
  if [ -f "$PLAN_HANDOFF" ]; then
    # 2.5: ghost plan-handoff — file exists but no active changes
    local ACTIVE_COUNT=0
    if command -v python3 >/dev/null 2>&1 && [ -f "$PLAN_HANDOFF" ]; then
      ACTIVE_COUNT=$(python3 -c "import json; d=json.load(open('$PLAN_HANDOFF')); v=d.get('active_changes',0); print(v if isinstance(v,int) else len(v))" 2>/dev/null || echo 0)
    fi
    if [ "$ACTIVE_COUNT" -eq 0 ]; then
      RECOMMEND="guide-ship"
      REASON="plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)"
      return 0
    fi
    # Cross-validate: count non-archived change dirs in filesystem
    local FS_ACTIVE_COUNT
    FS_ACTIVE_COUNT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)
    if [ "$FS_ACTIVE_COUNT" -eq 0 ]; then
      RECOMMEND="guide-arch"
      REASON="plan-handoff stale (says $ACTIVE_COUNT active, but 0 in filesystem -> all archived)"
      return 0
    fi
    RECOMMEND="guide-ship"
    REASON="变更生成已完成 → 进入变更执行"
    return 0
  fi

  # 3. worktree with incomplete tasks → guide-ship
  # $3, not $2: git worktree list branch field is column 3 (was P0-2)
  # [openspec/ prefix: brackets are part of the output format (P1-3 fix)
  local WORKTREE_IN_PROGRESS=""
  for wt in $(git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1 {print $1}'); do
    for tf in "$wt"/openspec/changes/*/tasks.md; do
      [ -f "$tf" ] || continue
      if grep -q '^- \[ \]' "$tf" 2>/dev/null; then
        WORKTREE_IN_PROGRESS="yes"
        break 2
      fi
    done
  done
  if [ -n "$WORKTREE_IN_PROGRESS" ]; then
    RECOMMEND="guide-ship"
    REASON="worktree 存在,任务未完成 → 继续执行"
    return 0
  fi

  # 4. detached worktrees (other sessions) → guide-ship
  local DETACHED
  DETACHED=$(git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | wc -l)
  if [ "$DETACHED" -gt 0 ]; then
    RECOMMEND="guide-ship"
    REASON="$DETACHED 个 worktree 在跑（可能在分离终端）"
    return 0
  fi

  # 5. worktree tasks all completed → guide-ship (archive)
  if git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | grep -q .; then
    RECOMMEND="guide-ship"
    REASON="worktree 存在,任务已完成 → 进入 archive"
    return 0
  fi

  # 6. committed change in HEAD (no worktree yet) → guide-ship
  # git show HEAD:<path> requires repo-relative path; cd into PROJECT_ROOT first
  if (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    if git show HEAD:"$d.openspec.yaml" > /dev/null 2>&1; then
      exit 0
    fi
  done; exit 1); then
    RECOMMEND="guide-ship"
    REASON="有已 commit 的 change 待建 worktree"
    return 0
  fi

  # 7. no roadmap → guide-arch
  # ADR-0016 Layer 3: read roadmap_path from handoff with fallback
  ARCH_HANDOFF="${PROJECT_ROOT}/.rddf/state/.arch-handoff.json"
  if [ -f "$ARCH_HANDOFF" ] && command -v jq >/dev/null 2>&1; then
    _ROADMAP_FILE="${PROJECT_ROOT}/$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")"
    _ROADMAP_NAME=$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")
  else
    _ROADMAP_FILE="${PROJECT_ROOT}/roadmap.md"
    _ROADMAP_NAME="roadmap.md"
  fi
  if [ ! -f "$_ROADMAP_FILE" ]; then
    RECOMMEND="guide-arch"
    REASON="无 ${_ROADMAP_NAME} → 进入架构定义"
    return 0
  fi

  # 8. no openspec/changes/ directory → guide-plan
  if [ ! -d "$PROJECT_ROOT/openspec/changes" ]; then
    RECOMMEND="guide-plan"
    REASON="无 change → 进入变更生成"
    return 0
  fi

  # 9/10. Dual-index scan: proposal-suggestions.md + proposal-approved.md
  # Check approved proposals first (ready for plan)
  # cwd safety: PY_PROJECT_ROOT env var
  local HAS_APPROVED
  HAS_APPROVED=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, re
try:
    approved_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-approved.md")
    if not os.path.exists(approved_path):
        print("no")
        raise SystemExit(0)
    with open(approved_path) as f:
        content = f.read()
    # Check if there are rows in the approved table (not in completed section)
    section = re.split(r"## 已实施", content)
    approved_section = section[0] if section else content
    has_entries = bool(re.search(r"\|\s*\[[^\]]+\]\(improvements/[^)]+\)\s*\|", approved_section))
    print("yes" if has_entries else "no")
except Exception:
    print("no")
' 2>/dev/null)
  
  if [ "$HAS_APPROVED" = "yes" ]; then
    RECOMMEND="guide-plan"
    REASON="有已批准 change 待创建 -> 进入 plan"
    return 0
  fi

  # Check pending suggestions (needs arch discussion)
  local HAS_PENDING
  HAS_PENDING=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os
try:
    imp_dir = os.path.join(os.environ["PY_PROJECT_ROOT"], "improvements")
    suggestions_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-suggestions.md")
    if not os.path.isdir(imp_dir) or not os.path.exists(suggestions_path):
        print("no")
        raise SystemExit(0)
    # Check if suggestions.md references any improvement that is NOT in approved.md
    approved_names = set()
    approved_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-approved.md")
    if os.path.exists(approved_path):
        import re
        with open(approved_path) as f:
            approved_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(improvements/", f.read()))
    with open(suggestions_path) as f:
        suggestions_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(improvements/", f.read()))
    pending = suggestions_names - approved_names
    print("yes" if pending else "no")
except Exception:
    print("no")
' 2>/dev/null)
  
  if [ "$HAS_PENDING" = "yes" ]; then
    RECOMMEND="guide-arch"
    REASON="有待讨论提案 -> 进入 arch 审查"
  else
    # filter-guide-ship: skip guide-ship when no active changes in filesystem
    local FS_ACTIVE_COUNT_DEFAULT
    FS_ACTIVE_COUNT_DEFAULT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)
    if [ "$FS_ACTIVE_COUNT_DEFAULT" -eq 0 ]; then
      RECOMMEND="guide-plan"
      REASON="无活跃 change -> 进入变更生成 (跳过 guide-ship)"
    else
      RECOMMEND="guide-ship"
      REASON="无待讨论提案 -> 准备 ship"
    fi
  fi

  check_stale_workflow_state "$PROJECT_ROOT"
  check_working_tree_cleanliness "$PROJECT_ROOT"
  check_arch_handoff_stale "$PROJECT_ROOT"
}

# check_arch_handoff_stale [PROJECT_ROOT]
#   Cross-validates arch-handoff.json's adr_count against the filesystem.
#   When handoff says 0 ADRs but the filesystem has ADR files, emits a
#   warning that the handoff may be stale.
check_arch_handoff_stale() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local arch_handoff="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  
  [ ! -f "$arch_handoff" ] && return 0
  
  PY_HANDOFF="$arch_handoff" PY_ROOT="$PROJECT_ROOT" python3 -c '
import os, json, glob
try:
    with open(os.environ["PY_HANDOFF"]) as f:
        d = json.load(f)
    adr_count = d.get("adr_count", 0)
    if isinstance(adr_count, list):
        adr_count = len(adr_count)
    if adr_count == 0:
        root = os.environ["PY_ROOT"]
        adr_dir = d.get("adr_dir", "docs/adr")
        adr_path = os.path.join(root, adr_dir)
        fs_files = glob.glob(os.path.join(adr_path, "ADR-*.md"))
        fs_count = len([f for f in fs_files if os.path.isfile(f)])
        if fs_count > 0:
            print(f"⚠️  arch-handoff 记录 0 ADRs 但文件系统发现 {fs_count} 个 - handoff 可能过期")
except Exception:
    pass
' 2>/dev/null
  return 0
}

# scan_session_binding [PROJECT_ROOT]
#   Scans .rddf/state/sessions.json for the current OpenCode session's
#   binding status. Populates global array BINDING_LINES with 1-2 lines:
#     - Line 1: "📍 Current: <rds_id> (kind=<K>, started=<T>)" if bound
#               "📍 No current binding" otherwise
#     - Line 2: "💡 Recommended: <rds_id> ... → skill_use(...)" only when
#               unbound AND an orphaned session exists.
#   Silent on missing/invalid file (returns 0, BINDING_LINES stays empty).
#   Read-only: does NOT modify sessions.json.
BINDING_LINES=()

# check_stale_workflow_state [PROJECT_ROOT]
#   Emits a one-line warning if a pre-refactor workflow-state.md exists.
#   Read-only: never deletes the file (respects user data per AGENTS.md).
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi
  return 0
}

# check_working_tree_cleanliness [PROJECT_ROOT]
#   Scans git status for common dirty-tree issues:
#     - Deleted tracked files (file moved but git rm not committed)
#     - Modified tracked files (unstaged changes)
#     - Staged changes (git add but not committed)
#     - Large untracked directories (potential build artifacts)
#   Prints a structured summary. Sets global WT_ISSUES_COUNT.
#   Read-only: never modifies files.
WT_ISSUES_COUNT=0
check_working_tree_cleanliness() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  WT_ISSUES_COUNT=0

  # Quick skip: if tree is clean, return early
  if git -C "$PROJECT_ROOT" diff-index --quiet HEAD -- 2>/dev/null && \
     [ -z "$(git -C "$PROJECT_ROOT" ls-files --others --exclude-standard 2>/dev/null | head -1)" ]; then
    return 0
  fi

  echo ""
  echo "🧹 Working Tree Check:"

  # 1. Deleted tracked files ( D)
  local DELETED
  DELETED=$(git -C "$PROJECT_ROOT" status --short 2>/dev/null | grep '^ D' | sed 's/^ D //' | head -20)
  local DELETED_COUNT
  DELETED_COUNT=$(printf '%s' "$DELETED" | grep -c . 2>/dev/null || true)
  DELETED_COUNT=${DELETED_COUNT##*$'\n'}
  if [ "${DELETED_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    echo "   🗑️  Deleted tracked files ($DELETED_COUNT):"
    echo "$DELETED" | while read -r f; do
      [ -z "$f" ] && continue
      # Check if moved to archive/
      local archive_path="openspec/changes/archive/$(basename "$(dirname "$f")")"
      if echo "$f" | grep -q '^openspec/changes/' && [ -d "$PROJECT_ROOT/$archive_path" ]; then
        echo "      $f  (已归档 → git rm \"$f\")"
      else
        echo "      $f  (已删除但未提交 → git rm \"$f\")"
      fi
    done
    WT_ISSUES_COUNT=$((WT_ISSUES_COUNT + DELETED_COUNT))
  fi

  # 2. Modified tracked files ( M)
  local MODIFIED
  MODIFIED=$(git -C "$PROJECT_ROOT" status --short 2>/dev/null | grep '^ M' | sed 's/^ M //' | head -10)
  local MOD_COUNT
  MOD_COUNT=$(printf '%s' "$MODIFIED" | grep -c . 2>/dev/null || true)
  MOD_COUNT=${MOD_COUNT##*$'\n'}
  if [ "${MOD_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    echo "   ✏️  Modified tracked files ($MOD_COUNT):"
    echo "$MODIFIED" | while read -r f; do
      [ -z "$f" ] && continue
      echo "      $f"
    done
    WT_ISSUES_COUNT=$((WT_ISSUES_COUNT + MOD_COUNT))
  fi

  # 3. Staged changes (M / A in index)
  local STAGED
  STAGED=$(git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null | head -10)
  local STAGED_COUNT
  STAGED_COUNT=$(printf '%s' "$STAGED" | grep -c . 2>/dev/null || true)
  STAGED_COUNT=${STAGED_COUNT##*$'\n'}
  if [ "${STAGED_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    echo "   📦 Staged changes ($STAGED_COUNT):"
    echo "$STAGED" | while read -r f; do
      [ -z "$f" ] && continue
      echo "      $f"
    done
    WT_ISSUES_COUNT=$((WT_ISSUES_COUNT + STAGED_COUNT))
  fi

  # 4. Large untracked directories (potential build artifacts)
  local UNTRACKED_DIRS
  UNTRACKED_DIRS=$(git -C "$PROJECT_ROOT" ls-files --others --exclude-standard --directory 2>/dev/null | grep '/$' | grep -v '^.git' | head -10)
  local UT_COUNT
  UT_COUNT=$(printf '%s' "$UNTRACKED_DIRS" | grep -c . 2>/dev/null || true)
  UT_COUNT=${UT_COUNT##*$'\n'}
  if [ "${UT_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    # Check if directories are large (>10MB)
    local LARGE_DIRS=""
    while IFS= read -r d; do
      [ -z "$d" ] && continue
      local size
      size=$(du -sm "$PROJECT_ROOT/$d" 2>/dev/null | cut -f1 || echo 0)
      if [ "${size:-0}" -gt 10 ] 2>/dev/null; then
        LARGE_DIRS="$LARGE_DIRS$d (${size}MB)"$'\n'
      fi
    done <<< "$UNTRACKED_DIRS"
    if [ -n "$LARGE_DIRS" ] && [ "$(echo "$LARGE_DIRS" | grep -c . 2>/dev/null || true)" -gt 0 ] 2>/dev/null; then
      echo "   📁 Large untracked directories:"
      echo "$LARGE_DIRS" | while read -r d; do
        [ -z "$d" ] && continue
        echo "      $d → 建议加到 .gitignore 或清理"
      done
      WT_ISSUES_COUNT=$((WT_ISSUES_COUNT + 1))
    fi
  fi

  if [ "$WT_ISSUES_COUNT" -eq 0 ]; then
    echo "   ✅ No issues detected"
  fi
}

# check_heartbeat_timeouts [PROJECT_ROOT]
#   Scans .rddf/state/sessions.json and marks timed-out active sessions as
#   orphaned. This is a state-mutating helper; it should run before any
#   read-only binding lookup so callers see an up-to-date sessions view.
#   Safe to call when sessions.json is missing (returns 0).
check_heartbeat_timeouts() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
  [ -f "$SESSIONS_FILE" ] || return 0
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)" || SCRIPT_DIR=""
  # script lives at skills/guide/scripts/scan-state.sh → repo root is 3 levels up
  local PYTHON_PATH="${SCRIPT_DIR:+$(cd "$SCRIPT_DIR/../../.." && pwd)}"
  PY_PROJECT_ROOT="$PROJECT_ROOT" \
  python3 - "$SESSIONS_FILE" "${PYTHON_PATH:-$PROJECT_ROOT}" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else ".")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=sys.argv[1])
coord.check_heartbeat_timeouts()
PYEOF
}

scan_session_binding() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
  # Derive Python import path from this script's location (skills/guide/scripts/ → repo root)
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)" || SCRIPT_DIR=""
  # script lives at skills/guide/scripts/scan-state.sh → repo root is 3 levels up
  local PYTHON_PATH="${SCRIPT_DIR:+$(cd "$SCRIPT_DIR/../../.." && pwd)}"
  BINDING_LINES=()
  [ -f "$SESSIONS_FILE" ] || return 0
  local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$PPID}"
  # check_stale_workflow_state() is called automatically at the end of scan_state()
  check_heartbeat_timeouts "$PROJECT_ROOT"
  while IFS= read -r line; do
    BINDING_LINES+=("$line")
  done < <(PY_PROJECT_ROOT="$PROJECT_ROOT" \
    python3 - "$SESSIONS_FILE" "$owner" "${PYTHON_PATH:-$PROJECT_ROOT}" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=sys.argv[1])
owner = sys.argv[2]
current = coord.find_current_binding(owner)
if current:
    print(f"📍 Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("📍 No current binding")
    nxt = coord.find_next_recommendation(owner)
    if nxt:
        print(f"💡 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   → skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
    )
}