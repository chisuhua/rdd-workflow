# _lib/scan-state.sh
# Project state scanner extracted from skills/guide.md lines 21-110.
# Used by `guide` (skill recommender) to detect: arch handoff, plan handoff,
# worktree state, committed changes, roadmap presence, pending proposals,
# and emit RECOMMEND + REASON for the calling AI agent.
#
# Usage:
#   source _lib/scan-state.sh
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
#   - json.load (not grep) on improvement-suggestions.md to avoid matching the
#     literal word "待创建" inside description fields (P1-7)
#   - PY_PROJECT_ROOT env var (not cwd-relative open) to keep python safe
#     regardless of caller's cwd (pattern from archive.sh:mark_iteration_archived)
#
# State files read (gitignored under .rddf/state/):
#   - .rddf/state/.arch-handoff.json      — arch phase done sentinel
#   - .rddf/state/.planner-handoff.json   — planner phase done sentinel (v4)
#   - .rddf/state/.plan-handoff.json      — legacy v3 fallback only
#   - .rddf/state/.design-handoff.json    — legacy v3 fallback only
#   - improvement-suggestions.md          — JSON array with status field
#   - roadmap.md                       — arch artifact (committed)

# scan_binding_lines <sessions_file> <owner_id>
#
# Emits BINDING_LINES env var or prints to stdout the active session binding
# for the given owner. Called by scan_state when sessions.json has active sessions.
scan_binding_lines() {
  local sessions_file="$1"
  local owner_id="$2"
  local binding_line

  if [ ! -f "$sessions_file" ]; then
    return 0
  fi

  binding_line=$(python3 - "$sessions_file" "$owner_id" <<'PYEOF'
import json, sys, os
from datetime import datetime, timezone

sessions_file = sys.argv[1]
owner_id = sys.argv[2]

try:
    with open(sessions_file) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

active = [s for s in data.get("sessions", []) if s.get("state") == "active"
          and s.get("owner_opencode_session_id") == owner_id]
if not active:
    sys.exit(0)

# Take the most recent active session
s = max(active, key=lambda x: x.get("started_at", ""))
started = s.get("started_at", "")
try:
    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    age_min = int((datetime.now(timezone.utc) - started_dt).total_seconds() // 60)
except Exception:
    age_min = -1

changes = s.get("attached_changes", [])
changes_str = ", ".join(changes) if changes else "(none)"
line = f"📍 Current: {s['session_id']} (kind={s.get('kind', '?')}, parent={s.get('parent_session_id')}, age={age_min}min, changes={changes_str})"
print(line)
PYEOF
)

  if [ -n "$binding_line" ]; then
    BINDING_LINES="$binding_line"
    printf '%s\n' "$binding_line"
  fi
}

# handoff_valid <file>
#   True when the file exists and contains parsable JSON.
#   A corrupt handoff must NEVER be treated as "stage completed" — a
#   half-written file would otherwise silently advance the pipeline.
#   Without python3 we cannot judge; keep historical behavior (file exists = ok).
_HANDOFF_VALIDATION_DEGRADED=0
_handoff_valid() {
  local f="$1"
  [ -f "$f" ] || return 1
  if ! command -v python3 >/dev/null 2>&1; then
    # Without python3 the JSON cannot be parsed, so validity is UNVERIFIED.
    # The file is accepted (so the pipeline still works), but the result is
    # marked non-authoritative — a corrupt handoff must never be silently
    # treated as complete.
    _HANDOFF_VALIDATION_DEGRADED=1
    return 0
  fi
  # The handoff must be a JSON OBJECT, not just any JSON value — the
  # Python consumers require a dict (state_reader.read_*_handoff).
  python3 -c "import json,sys; d=json.load(open(sys.argv[1], encoding='utf-8')); sys.exit(0 if isinstance(d, dict) else 1)" "$f" >/dev/null 2>&1
}

# count_active_changes <project_root>
#   Number of non-archived change directories on disk.
#   This replaces the v3 `active_changes` field, which planner-handoff-v1
#   does not define (hence always resolved to 0).
#   The archive directory is excluded EXACTLY (a change literally named
#   "xxx-archive" is still an active change) — the Python consumers use
#   `name != "archive"`, so a substring match here would make the two
#   implementations disagree on the same project.
_count_active_changes() {
  local root="$1"
  # `|| true` on the listing (not on the whole pipeline): if `openspec/changes/`
  # does not exist, `ls` fails and — under `set -o pipefail` — the pipeline
  # would fail, making a trailing `|| echo 0` append a SECOND "0" to the
  # already-printed "0" ("00"). The value must be a single bare integer.
  ( cd "$root" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null || true ) \
    | sed 's#/$##' | awk -F/ '$NF != "archive"' | wc -l | tr -d '[:space:]'
}

# scan_state
#   Mutates caller-namespace globals RECOMMEND and REASON.
#   Priority order (highest first):
#     0.  Effective planner marker: the v4 `.planner-handoff.json` wins;
#         the v3 `.plan-handoff.json` / `.design-handoff.json` are a
#         read-only legacy fallback (with a `legacy` warning). A corrupt
#         file is NOT a marker — a half-written handoff must not advance
#         the pipeline.
#     1.  arch-handoff present, no effective marker:
#     1c.  corrupt `.planner-handoff.json`            → "rdd-planner" (视为未完成)
#     1a.  ADR < 1                                    → "rdd-arch" (recover)
#     1b.  arch done, planner 未跑                     → "rdd-planner"
#     2.  effective marker present:
#     2.   marker = v4 planner / v3 design / v3 plan   → "rdd-builder" (按 kind 分流)
#     2.5  marker 有效但 0 活跃 change                 → "rdd-builder" (变更生成 / 残留清理)
#     3.  worktree with incomplete tasks              → "rdd-builder (继续执行)"
#     4.  detached worktrees (count > 0)              → "rdd-builder (运行中)"
#     5.  worktree tasks all completed                → "rdd-builder (archive)"
#     6.  committed change in HEAD (no worktree)      → "rdd-builder (建 worktree)"
#     7.  no roadmap.md                               → "rdd-arch"
#     8.  no openspec/changes/                        → "rdd-builder (变更生成)"
#     9.  improvement-suggestions.md has pending entry → "rdd-builder (设计审查)"
#    10.  default: no active change                  → "rdd-builder (变更生成)"
#         default: active change present             → "rdd-builder (ship)"
_scan_state_impl() {
  local PROJECT_ROOT="$1"
  if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  fi

  local ARCH_HANDOFF PLANNER_HANDOFF V3_PLAN_HANDOFF V3_DESIGN_HANDOFF
  ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  PLANNER_HANDOFF="$PROJECT_ROOT/.rddf/state/.planner-handoff.json"
  # v3 legacy handoffs — read ONLY as fallback, never written by v4 stages
  V3_PLAN_HANDOFF="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"
  V3_DESIGN_HANDOFF="$PROJECT_ROOT/.rddf/state/.design-handoff.json"

  if ! type -t check_dirty_key_files &>/dev/null; then
    local _state_helper
    for _state_helper in "$PROJECT_ROOT/_lib/state.sh" "$PROJECT_ROOT/skills/_lib/state.sh" "${HOME}/.agents/_lib/state.sh" "${HOME}/.agents/skills/_lib/state.sh"; do
      if [ -f "$_state_helper" ]; then
        source "$_state_helper"
        break
      fi
    done
    if ! type -t check_dirty_key_files &>/dev/null; then
      echo "⚠️ rdd-workflow not installed: tried $PROJECT_ROOT/_lib/state.sh and $HOME/.agents/_lib/state.sh, both missing. Run INSTALL.md" >&2
    fi
  fi
  if type -t check_dirty_key_files &>/dev/null; then
    check_dirty_key_files "$PROJECT_ROOT"
  fi

  local _binding_owner="${OPENCODE_SESSION_ID:-}"
  if [ -n "$_binding_owner" ]; then
    scan_binding_lines "$PROJECT_ROOT/.rddf/state/sessions.json" "$_binding_owner" || true
  fi

  # 0. Effective planner marker.
  #    The v4 handoff wins; the v3 files are a read-only legacy fallback
  #    (never written by v4 stages). A corrupt file does NOT count as a
  #    marker — a half-written handoff must not advance the pipeline.
  #    NOTE: this must NOT return early: v3 projects keep their original
  #    downstream behaviour (worktree / roadmap / proposal checks).
  #
  #    The marker KIND matters: a v3 DESIGN handoff means "design done,
  #    change generation next"; a v3 PLAN handoff means "changes exist,
  #    execution/cleanup next". They are different stages and must not
  #    share one code path.
  local PLANNER_EFFECTIVE="" PLANNER_KIND=""
  if _handoff_valid "$PLANNER_HANDOFF"; then
    PLANNER_EFFECTIVE="$PLANNER_HANDOFF"
    PLANNER_KIND="v4"
  elif _handoff_valid "$V3_PLAN_HANDOFF"; then
    PLANNER_EFFECTIVE="$V3_PLAN_HANDOFF"
    PLANNER_KIND="v3-plan"
  elif _handoff_valid "$V3_DESIGN_HANDOFF"; then
    PLANNER_EFFECTIVE="$V3_DESIGN_HANDOFF"
    PLANNER_KIND="v3-design"
  fi
  if [ -n "$PLANNER_KIND" ] && [ "$PLANNER_KIND" != "v4" ]; then
    echo "⚠️  legacy v3 handoff detected (.plan-handoff.json / .design-handoff.json); migrate to .planner-handoff.json" >&2
  fi

  # 1c. planner-handoff present but unparsable → treat as planner NOT done.
  #     MUST precede branch 1: branch 1 matches on "arch present + no
  #     effective marker", and a corrupt file yields no marker — so branch 1
  #     would always win and this diagnostic would be unreachable.
  if [ -f "$PLANNER_HANDOFF" ] && ! _handoff_valid "$PLANNER_HANDOFF" && [ -f "$ARCH_HANDOFF" ]; then
    RECOMMEND="rdd-planner"
    REASON="planner-handoff 损坏（JSON 无法解析）→ 视为 planner 未完成，回到 planner 阶段"
    return 0
  fi

  # 1. arch-handoff present, no planner marker → planner stage
  if [ -f "$ARCH_HANDOFF" ] && [ -z "$PLANNER_EFFECTIVE" ]; then
    # 1.5: arch-done incomplete — arch-handoff exists but ADR missing
    local ADR_COUNT=0
    if command -v python3 >/dev/null 2>&1 && [ -f "$ARCH_HANDOFF" ]; then
      ADR_COUNT=$(PY_HANDOFF="$ARCH_HANDOFF" python3 -c "import json,os; d=json.load(open(os.environ['PY_HANDOFF'])); v=d.get('adr_count',0); print(v if isinstance(v,int) else len(v))" 2>/dev/null || echo 0)
    fi
    if [ "$ADR_COUNT" -lt 1 ]; then
      RECOMMEND="rdd-arch"
      REASON="arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)"
      return 0
    fi
    # 1b: arch done, planner not yet run → planner stage (v4 四阶段)
    RECOMMEND="rdd-planner"
    REASON="arch-done 已完成 → 进入 planner 阶段（.planner-handoff.json 尚未生成）"
    return 0
  fi

  # 2. planner marker present → builder
  if [ -n "$PLANNER_EFFECTIVE" ]; then
    local ACTIVE_COUNT=0
    if [ "$PLANNER_KIND" = "v3-design" ]; then
      # v3 design semantics (pre-existing behaviour): design reviewed,
      # changes not generated yet → next is change generation.
      RECOMMEND="rdd-builder"
      REASON="design-done 已完成 → 进入变更生成"
      return 0
    elif [ "$PLANNER_KIND" = "v3-plan" ]; then
      # v3 plan semantics: the handoff carries an `active_changes` count
      ACTIVE_COUNT=$(python3 -c "import json; d=json.load(open('$PLANNER_EFFECTIVE')); v=d.get('active_changes',0); print(v if isinstance(v,int) else len(v))" 2>/dev/null || echo 0)
      if [ "$ACTIVE_COUNT" -eq 0 ]; then
        RECOMMEND="rdd-builder"
        REASON="plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)"
        return 0
      fi
    else
      # v4 semantics: planner-handoff-v1 defines no `active_changes` field,
      # so the filesystem is the only reliable source.
      ACTIVE_COUNT=$(_count_active_changes "$PROJECT_ROOT")
      if [ "$ACTIVE_COUNT" -eq 0 ]; then
        RECOMMEND="rdd-builder"
        REASON="planner-handoff 已完成 → 进入变更生成"
        return 0
      fi
    fi
    # Cross-validate: count non-archived change dirs in filesystem
    local FS_ACTIVE_COUNT
    FS_ACTIVE_COUNT=$(_count_active_changes "$PROJECT_ROOT")
    if [ "$FS_ACTIVE_COUNT" -eq 0 ]; then
      RECOMMEND="rdd-arch"
      if [ "$PLANNER_KIND" = "v3-plan" ]; then
        REASON="plan-handoff stale (says $ACTIVE_COUNT active, but 0 in filesystem -> all archived)"
      else
        REASON="planner-handoff stale (says $ACTIVE_COUNT active, but 0 in filesystem -> all archived)"
      fi
      return 0
    fi
    RECOMMEND="rdd-builder"
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
    RECOMMEND="rdd-builder"
    REASON="worktree 存在,任务未完成 → 继续执行"
    return 0
  fi

  # 4. detached worktrees (other sessions) → guide-ship
  local DETACHED
  DETACHED=$(git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | wc -l | tr -d '[:space:]')
  if [ "$DETACHED" -gt 0 ]; then
    RECOMMEND="rdd-builder"
    REASON="$DETACHED 个 worktree 在跑（可能在分离终端）"
    return 0
  fi

  # 5. worktree tasks all completed → guide-ship (archive)
  if git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | grep -q .; then
    RECOMMEND="rdd-builder"
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
    RECOMMEND="rdd-builder"
    REASON="有已 commit 的 change 待建 worktree"
    return 0
  fi

  # 7. no roadmap → rdd-arch
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
    RECOMMEND="rdd-arch"
    REASON="无 ${_ROADMAP_NAME} → 进入架构定义"
    return 0
  fi

  # 8. no openspec/changes/ directory → guide-plan
  if [ ! -d "$PROJECT_ROOT/openspec/changes" ]; then
    RECOMMEND="rdd-builder"
    REASON="无 change → 进入变更生成"
    return 0
  fi

  # 9/10. Dual-index scan: improvement-suggestions.md + improvement-approved.md
  # Check approved proposals first (ready for plan)
  # cwd safety: PY_PROJECT_ROOT env var
  local HAS_APPROVED
  HAS_APPROVED=$(PY_PROJECT_ROOT="$PROJECT_ROOT" PY_RDD_LIB_HELPER="" python3 -c '
import os, sys, glob
def _find_helper():
    candidates = [
        os.path.join(os.environ["PY_PROJECT_ROOT"], "_lib"),
        os.path.expanduser("~/.agents/skills/_lib"),
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "parse_approved.py")):
            return d
    return ""
helper_dir = _find_helper()
if not helper_dir:
    print("no")
    sys.exit(0)
sys.path.insert(0, helper_dir)
try:
    from parse_approved import parse_approved_proposals
except Exception:
    print("no")
    sys.exit(0)
approved_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "improvement-approved.md")
try:
    names = parse_approved_proposals(approved_path)
except Exception:
    names = []
print("yes" if names else "no")
' 2>/dev/null)
  
  if [ "$HAS_APPROVED" = "yes" ]; then
    RECOMMEND="rdd-builder"
    REASON="有已批准 change 待创建 -> 进入 plan"
    return 0
  fi

  # Check pending suggestions (needs arch discussion)
  local HAS_PENDING
  HAS_PENDING=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os
try:
    imp_dir = os.path.join(os.environ["PY_PROJECT_ROOT"], ".rddf/improvements")
    suggestions_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "improvement-suggestions.md")
    if not os.path.isdir(imp_dir) or not os.path.exists(suggestions_path):
        print("no")
        raise SystemExit(0)
    # Check if suggestions.md references any improvement that is NOT in approved.md
    approved_names = set()
    approved_path = os.path.join(os.environ["PY_PROJECT_ROOT"], "improvement-approved.md")
    if os.path.exists(approved_path):
        import re
        with open(approved_path) as f:
            approved_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(.rddf/improvements/", f.read()))
    with open(suggestions_path) as f:
        suggestions_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(.rddf/improvements/", f.read()))
    pending = suggestions_names - approved_names
    print("yes" if pending else "no")
except Exception:
    print("no")
' 2>/dev/null)
  
  if [ "$HAS_PENDING" = "yes" ]; then
    RECOMMEND="rdd-builder"
    REASON="有待讨论提案 -> 进入设计阶段审查"
  else
    # filter-guide-ship: skip guide-ship when no active changes in filesystem
    local FS_ACTIVE_COUNT_DEFAULT
    FS_ACTIVE_COUNT_DEFAULT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)
    if [ "$FS_ACTIVE_COUNT_DEFAULT" -eq 0 ]; then
      RECOMMEND="rdd-builder"
      REASON="无活跃 change -> 进入变更生成 (跳过 guide-ship)"
    else
      RECOMMEND="rdd-builder"
      REASON="无待讨论提案 -> 准备 ship"
    fi
  fi

  check_stale_workflow_state "$PROJECT_ROOT"
  check_working_tree_cleanliness "$PROJECT_ROOT"
  check_arch_handoff_stale "$PROJECT_ROOT"
  check_orphan_plan_files "$PROJECT_ROOT" 2>/dev/null || true

  local binding_owner="${OPENCODE_SESSION_ID:-}"
  if [ -n "$binding_owner" ]; then
    scan_binding_lines "$PROJECT_ROOT/.rddf/state/sessions.json" "$binding_owner" || true
  fi
}

# scan_state (public wrapper)
#   Calls _scan_state_impl and then marks the result as NON-AUTHORITATIVE
#   when the handoff JSON could not be validated (python3 unavailable).
#   A corrupt handoff must never be silently treated as complete, so the
#   degradation has to be visible in the REASON the agent reads.
scan_state() {
  _scan_state_impl "$@"
  if [ "${_HANDOFF_VALIDATION_DEGRADED:-0}" -eq 1 ]; then
    REASON="${REASON:-未知} (非权威：python3 不可用，handoff JSON 有效性未校验)"
  fi
  return 0
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

  # Pre-menu setup analysis (non-blocking)
  local _lib_dir
  _lib_dir=$(cd "$REPO_ROOT/skills/_lib" 2>/dev/null && pwd || echo "$REPO_ROOT/skills/_lib")
  if [ -f "$_lib_dir/check_project_setup.sh" ]; then
    source "$_lib_dir/check_project_setup.sh"
    local _setup_issues
    _setup_issues=$(check_project_setup "${PROJECT_ROOT:-$REPO_ROOT}" 2>/dev/null || echo '[]')
    echo ""
    echo "🔧 项目设置检查 (safe_auto_fix, 不阻塞):"
    echo "$_setup_issues" | jq -r '.[] | "  - \(.name): \(.status) — \(.detail)\n    fix: \(.fix_command)"' 2>/dev/null || true
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
  # v3 (feat-guide-orchestrator-session-event-bus): REMOVE check_heartbeat_timeouts call.
  # scan-state.sh is a read-only scanner per guide/SKILL.md:30 ("纯只读扫描器").
  # Heartbeat GC is now handled by hooks.sh entry/close (and rddf-session gc subcommand),
  # using check_heartbeat_timeouts(readonly=False) which preserves the mutating semantics.
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
        print("   No orphaned rddf-sessions found. Run rdd-arch or guide-plan to start.")
PYEOF
     )
}

# check_orphan_plan_files <project_root>
#   Scan .rddf/plans/ for plan files whose corresponding change is no longer
#   active (not in openspec/changes/ and not in openspec/changes/archive/).
#   Outputs a non-blocking warning with file names and count.
check_orphan_plan_files() {
  local project_root="$1"
  local plans_dir="$project_root/.rddf/plans"

  [ -d "$plans_dir" ] || return 0

  local orphan_count=0
  local orphan_list=""

  for plan_file in "$plans_dir"/*.md; do
    [ -f "$plan_file" ] || continue
    local basename
    basename=$(basename "$plan_file" .md)
    local change_dir="$project_root/openspec/changes/$basename"

    if [ -d "$change_dir" ]; then
      continue
    fi

    if ls "$project_root/openspec/changes/archive/"*-"$basename" >/dev/null 2>&1; then
      continue
    fi

    orphan_count=$((orphan_count + 1))
    orphan_list="$orphan_list  - $basename"$'\n'
  done

  if [ "$orphan_count" -gt 0 ]; then
    echo "⚠️  发现 $orphan_count 个孤立计划文件 (.rddf/plans/):"
    echo "$orphan_list"
    echo "   (对应 change 已归档或不存在，可手动删除)"
  fi
}