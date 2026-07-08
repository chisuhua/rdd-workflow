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
#       Sets global RECOMMEND (skill name) and REASON (one-line explanation)
#       based on priority-ordered detection. Returns 0 always (best-effort).
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
#   - .rddf/state/.phase-gate-report.md — pending review
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
#     4. .phase-gate-report.md present              → "status --roadmap"
#     5. detached worktrees (count > 0)             → "guide-ship"
#     6. worktree tasks all completed               → "guide-ship"
#     7.  committed change in HEAD (no worktree)   → "guide-ship"
#     8.  no roadmap.md                            → "guide-arch"
#     9.  no openspec/changes/                     → "guide-plan"
#    10. proposal-suggestions.md has pending entry  → "guide-plan"
#    11. default                                    → "guide-ship"
scan_state() {
  local PROJECT_ROOT="$1"
  if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  fi

  local ARCH_HANDOFF PLAN_HANDOFF
  ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  PLAN_HANDOFF="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"

  # 1. arch-handoff present, plan-handoff absent → guide-plan
  if [ -f "$ARCH_HANDOFF" ] && [ ! -f "$PLAN_HANDOFF" ]; then
    # 1.5: arch-done incomplete — arch-handoff exists but ADR missing
    local ADR_COUNT=0
    if command -v python3 >/dev/null 2>&1 && [ -f "$ARCH_HANDOFF" ]; then
      ADR_COUNT=$(python3 -c "import json; d=json.load(open('$ARCH_HANDOFF')); print(d.get('adr_count',0))" 2>/dev/null || echo 0)
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
      ACTIVE_COUNT=$(python3 -c "import json; d=json.load(open('$PLAN_HANDOFF')); print(d.get('active_changes',0))" 2>/dev/null || echo 0)
    fi
    if [ "$ACTIVE_COUNT" -eq 0 ]; then
      RECOMMEND="guide-ship"
      REASON="plan-handoff 残留 (无活跃 change → 进入 ship 清理/归档)"
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

  # 4. phase-gate-report exists → status --roadmap
  # P1-3: must review before proceeding
  if [ -f "$PROJECT_ROOT/.rddf/state/.phase-gate-report.md" ]; then
    RECOMMEND="status --roadmap"
    REASON="阶段门控报告待 review"
    return 0
  fi

  # 5. detached worktrees (other sessions) → guide-ship
  local DETACHED
  DETACHED=$(git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | wc -l)
  if [ "$DETACHED" -gt 0 ]; then
    RECOMMEND="guide-ship"
    REASON="$DETACHED 个 worktree 在跑（可能在分离终端）"
    return 0
  fi

  # 6. worktree tasks all completed → guide-ship (archive)
  if git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | grep -q .; then
    RECOMMEND="guide-ship"
    REASON="worktree 存在,任务已完成 → 进入 archive"
    return 0
  fi

  # 7. committed change in HEAD (no worktree yet) → guide-ship
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

  # 8. no roadmap → guide-arch
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

  # 9. no openspec/changes/ directory → guide-plan
  if [ ! -d "$PROJECT_ROOT/openspec/changes" ]; then
    RECOMMEND="guide-plan"
    REASON="无 change → 进入变更生成"
    return 0
  fi

  # 10/11. proposal-suggestions.md JSON parse
  # P1-7: json.load not grep (description field may also contain "待创建" text)
  # cwd safety: PY_PROJECT_ROOT env var (archive.sh:mark_iteration_archived pattern)
  local HAS_PENDING
  HAS_PENDING=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, json, sys
try:
    with open(os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-suggestions.md")) as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print("no")
        sys.exit(0)
    pending = any(isinstance(e, dict) and e.get("status") == "待创建" for e in entries)
    print("yes" if pending else "no")
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    print("no")
' 2>/dev/null)
  if [ "$HAS_PENDING" = "yes" ]; then
    RECOMMEND="guide-plan"
    REASON="有 change 待创建 → 继续 propose"
  else
    RECOMMEND="guide-ship"
    REASON="无待创建 change → 准备 ship"
  fi
}