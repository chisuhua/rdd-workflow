#!/usr/bin/env bash
# Phase 2: Worktree + Execute (TDD 5 步).
#
# No commit gate here: the former repository-wide `git status --porcelain`
# check rejected Phase 2 whenever ANY unrelated file was dirty (e.g. the
# agent's own .rddf/state/role.json), and it was inert for `openspec/` in
# projects where that directory is gitignored (git.openspec_tracked=false).
# Commit semantics for a change are enforced upstream by
# _lib/archive.sh::check_worktree_commits before archive.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

AUTO_APPROVE=0
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
    esac
done
export AUTO_APPROVE

if [ -z "$CHANGE_NAME" ]; then
    echo "phase2_execute.sh requires <change-name>" >&2
    exit 3
fi

echo "=== Phase 2: Worktree + Execute for $CHANGE_NAME ==="

# Resolve the rdd-workflow package root — the directory that CONTAINS
# `_lib/`. It is NOT the project root: in a user project `_lib/` lives under
# the installed rdd-workflow package (~/.agents/skills/rdd-workflow or
# <project>/.opencode/skills/rdd-workflow).
#
# Order matters: the package that OWNS this script is checked first. In a
# dev checkout (or a symlinked global install) that is the running code,
# whereas a project-local install may shadow it with an older copy.
_resolve_pkg_root() {
  local c here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"  # package root of this script
  if [ -d "$here/_lib" ]; then
    printf '%s' "$here"
    return 0
  fi
  for c in \
    "$PROJECT_ROOT/.opencode/skills/rdd-workflow" \
    "$HOME/.agents/skills/rdd-workflow" \
    "$HOME/.agents/skills"
  do
    if [ -n "$c" ] && [ -d "$c/_lib" ]; then
      printf '%s' "$c"
      return 0
    fi
  done
  return 1
}

PKG_ROOT="$(_resolve_pkg_root || true)"

_EXEC_ERR=$(mktemp)
EXEC_MODE=$(PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 -c "
import os, sys
root = os.environ.get('PKG_ROOT') or ''
if root:
    sys.path.insert(0, root)
from _lib.builder_handoff import read_builder_handoff
print(read_builder_handoff(
    os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME']
).get('execution_mode_decision', {}).get('mode', 'worktree'))
" 2>"$_EXEC_ERR") || EXEC_MODE=""
if [ -z "$EXEC_MODE" ]; then
    # Do not swallow the reason: a missing/corrupt builder state must not
    # silently downgrade the execution mode.
    echo "⚠️  could not read execution_mode_decision for '$CHANGE_NAME' — falling back to worktree mode" >&2
    [ -s "$_EXEC_ERR" ] && sed 's/^/    /' "$_EXEC_ERR" >&2
    EXEC_MODE="worktree"
fi
rm -f "$_EXEC_ERR"

# Set by the lightweight branch preparation below; they carry the fail-closed
# downgrade out into the handoff.
EXEC_MODE_REASON=""
BRANCH_BASE_SHA=""
BRANCH="openspec/$CHANGE_NAME"

# Carry the change's artifacts into the execution directory:
# `git worktree add` builds from HEAD, so files that were never committed are
# absent there. Without this, P2 fails with "plan file missing" for exactly the
# changes that are not committed yet.
#
# Two edge cases this must handle:
#   - dst already exists (the change WAS committed → worktree already has it):
#     copy the CONTENTS, not the directory itself — plain `cp -R src dst` would
#     create `dst/src` (a nested <name>/<name>/).
#   - src == dst (lightweight mode, or a worktree creation that fell back to the
#     main repo): `cp -R a a` fails with "cannot copy a directory into itself",
#     and `set -e` would abort P2.
_carry_artifacts() {
    local _rel _src _dst
    for _rel in "openspec/changes/$CHANGE_NAME" ".rddf/plans/$CHANGE_NAME.md"; do  # isolation-ok: 相对片段，稍后分别与 $PROJECT_ROOT / $EXEC_DIR 拼接
        _src="$PROJECT_ROOT/$_rel"
        _dst="$EXEC_DIR/$_rel"
        [ -e "$_src" ] || continue
        if [ "$_src" = "$_dst" ] || { [ -e "$_dst" ] && [ "$_src" -ef "$_dst" ]; }; then
            continue  # same location — nothing to carry over
        fi
        mkdir -p "$(dirname "$_dst")"
        if [ -d "$_src" ]; then
            mkdir -p "$_dst"
            cp -R "$_src/." "$_dst/"
        else
            cp -R "$_src" "$_dst"
        fi
    done
}


# --- P2 前置检查（只读）----------------------------------------------------
# `git worktree add` builds the worktree from HEAD ⇒ whatever the MAIN repo
# gained after the recorded baseline — or never committed — is invisible inside
# it. Measured 2026-11-26: an authorization ledger entry committed in the main
# repo after P2 had to be merged into the worktree by hand.
#
# This check only REPORTS (commit sha + file list). It never commits and never
# merges — automating that is out of scope (and risky).
_p2_prereq_check() {
    local dirty base ahead
    dirty="$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=no 2>/dev/null || true)"
    if [ -n "$dirty" ]; then
        echo "⚠️  P2 前置检查：主仓有未提交的 tracked 改动 ⇒ worktree 从 HEAD 建，看不到它们" >&2
        printf '%s\n' "$dirty" | head -10 | sed 's/^/     /' >&2
        echo "   ⇒ 先把授权类产物（如台账 Entry）commit，再建 worktree" >&2
    fi
    base="$(PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 -c "
import os, sys
sys.path.insert(0, os.environ.get('PKG_ROOT') or '')
from _lib.builder_handoff import read_builder_handoff
handoff = read_builder_handoff(os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME'])
print((handoff.get('execution_mode_decision') or {}).get('branch_base_sha') or '')
" 2>/dev/null || true)"
    if [ -n "$base" ]; then
        ahead="$(git -C "$PROJECT_ROOT" rev-list --count "$base"..HEAD 2>/dev/null || echo 0)"
        if [ "$ahead" != "0" ]; then
            echo "⚠️  P2 前置检查：主仓 HEAD 领先上次 P2 基线 $base（$ahead 个 commit）" >&2
            echo "   这些产物在 worktree 里不可见（worktree 从该基线建）：" >&2
            git -C "$PROJECT_ROOT" diff --name-only "$base"..HEAD 2>/dev/null \
                | head -20 | sed 's/^/     /' >&2
        fi
    fi
}

if [ "$EXEC_MODE" = "worktree" ]; then
    # The worktree lives INSIDE the project, not inside whatever directory the
    # caller happened to be in. Without this, a caller whose cwd differs from
    # $PROJECT_ROOT (the phase-2 test does exactly that: it drives the script
    # against a throwaway repo while the cwd is the real repo) creates the
    # worktree — and the branch — in the WRONG repository: the real one got a
    # stray `openspec/<change>` branch and a full-tree checkout it never
    # asked for, and the fake repo got nothing.
    cd "$PROJECT_ROOT" || { echo "❌ cannot cd to project root: $PROJECT_ROOT" >&2; exit 3; }
    WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
    if [ ! -d "$WT_PATH" ]; then
        _p2_prereq_check
        git worktree add "$WT_PATH" -b "$BRANCH" 2>/dev/null || {
            echo "worktree creation failed at $WT_PATH (branch may already exist)" >&2
            WT_PATH="$PROJECT_ROOT"  # fallback to main repo
        }
    fi
    EXEC_DIR="$WT_PATH"
    _carry_artifacts
else
    # ── lightweight mode: the implementation branch must EXIST ──────────────
    # Until now this mode declared `branch="openspec/<name>"` in the handoff
    # without creating anything: a ghost branch. The verifier anchors on the
    # branch tip, so a change without a real ref could never be archived
    # (it only passed via an audited bypass).
    #
    # Policy (deliberately explicit — an ambiguous policy here is what
    # produced the ghost branch):
    #   ref missing                     → create it from the default tip
    #   ref exists, tip == default tip  → reuse it
    #   ref exists, tip != default tip  → fail closed → worktree mode
    # A failure to prepare the branch downgrades the mode to `worktree`;
    # the downgrade is written into the handoff's reason so the mode and the
    # reason never contradict the reality.
    BRANCH="openspec/$CHANGE_NAME"
    DEFAULT_BRANCH=""
    if [ -f "$PKG_ROOT/_lib/archive.sh" ]; then
        # shellcheck source=/dev/null
        source "$PKG_ROOT/_lib/archive.sh" 2>/dev/null || true
    fi
    if declare -f lightweight_branch_prepare >/dev/null 2>&1; then
        DEFAULT_BRANCH=$(cd "$PROJECT_ROOT" && find_default_branch 2>/dev/null || echo "")
        _prep_rc=0
        _prep_out=$(lightweight_branch_prepare "$PROJECT_ROOT" "$BRANCH" "$DEFAULT_BRANCH" 2>&1) || _prep_rc=$?
        _prep_reason=""
        while IFS= read -r _line; do
            case "$_line" in
                "base "*)
                    BRANCH_BASE_SHA="${_line#base }"
                    ;;
                "")
                    ;;
                *)
                    if [ -z "$_prep_reason" ]; then
                        _prep_reason="$_line"
                    fi
                    echo "  $_line"
                    ;;
            esac
        done <<< "$_prep_out"
        if [ "$_prep_rc" -ne 0 ]; then
            # Fail closed: the mode must match what actually happens. Record
            # the downgrade NOW — the worktree attempt below may fail, and an
            # aborted P2 must not leave a handoff claiming "lightweight".
            EXEC_MODE="worktree"
            EXEC_MODE_REASON="lightweight 不可用：$_prep_reason"
            PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" \
            EXEC_MODE_REASON="$EXEC_MODE_REASON" python3 - <<'PYEOF' || true
import os, sys
if os.environ.get('PKG_ROOT'):
    sys.path.insert(0, os.environ['PKG_ROOT'])
from _lib.builder_handoff import read_builder_handoff, update_builder_handoff
existing = read_builder_handoff(os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME'])
decision = dict(existing.get('execution_mode_decision') or {})
decision['mode'] = 'worktree'
decision['reason'] = os.environ['EXEC_MODE_REASON']
update_builder_handoff(
    os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME'],
    execution_mode_decision=decision,
)
PYEOF
        fi
    else
        EXEC_MODE="worktree"
        EXEC_MODE_REASON="lightweight 不可用：找不到 _lib/archive.sh（无法建分支）"
    fi
    if [ "$EXEC_MODE" = "lightweight" ]; then
        EXEC_DIR="$PROJECT_ROOT"
    else
        # Fall back to the worktree path — but STRICTLY: a worktree that
        # cannot be created must not silently degrade into "run in the main
        # repo", because the handoff would then claim a mode that the
        # execution does not use.
        WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
        if [ ! -d "$WT_PATH" ]; then
            # `git worktree add` registers the worktree in the repository of the
            # CURRENT directory. Anchoring the path is not enough: without this
            # cd, the worktree would be created inside $PROJECT_ROOT but
            # registered in the CALLER's repository (observed: a stray
            # `openspec/<name>` branch + a prunable worktree entry left in the
            # real repo by the phase-2 test).
            cd "$PROJECT_ROOT" || { echo "❌ cannot cd to project root: $PROJECT_ROOT" >&2; exit 3; }
            git worktree add "$WT_PATH" -b "$BRANCH" 2>/dev/null || {
                echo "❌ lightweight 退回 worktree 模式失败：无法在 '$WT_PATH' 创建 worktree（分支 '$BRANCH' 可能已被占用或指向其它提交）" >&2
                echo "   $EXEC_MODE_REASON" >&2
                echo "   请先删除或改名残留分支 '$BRANCH'，然后重跑 P2。" >&2
                exit 3
            }
        fi
        EXEC_DIR="$WT_PATH"
        _carry_artifacts
    fi
fi

# ── abort semantics ───────────────────────────────────────────────────────
# In lightweight mode the MAIN repo's HEAD is parked on `openspec/<name>`.
# If P2 then fails, the user's repo must not be left on that branch: the
# next change would start from the wrong base. The branch itself may stay
# (a leftover is reusable as long as its tip is the default tip — see
# lightweight_branch_prepare's three-tier policy).
_restore_head_on_abort() {
    local rc="${1:-0}"
    [ "$rc" -eq 0 ] && return 0
    if [ "${EXEC_MODE:-}" = "lightweight" ] && [ -n "${DEFAULT_BRANCH:-}" ]; then
        (cd "$PROJECT_ROOT" && git checkout "$DEFAULT_BRANCH" >/dev/null 2>&1) || true
        echo "⚠️  P2 失败（exit $rc）→ 主仓 HEAD 已回到 '$DEFAULT_BRANCH'" >&2
    fi
    return 0
}
trap '_abort_rc=$?; _restore_head_on_abort "$_abort_rc"' EXIT

cd "$EXEC_DIR"
if [ -f "$EXEC_DIR/.rddf/plans/$CHANGE_NAME.md" ]; then
    echo "Phase 2 worktree setup complete (mode=$EXEC_MODE, dir=$EXEC_DIR)"
else
    echo "plan file missing at $EXEC_DIR/.rddf/plans/$CHANGE_NAME.md" >&2
    exit 3
fi

cd "$PROJECT_ROOT"

PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" EXEC_DIR="$EXEC_DIR" \
EXEC_MODE="$EXEC_MODE" EXEC_MODE_REASON="$EXEC_MODE_REASON" BRANCH_BASE_SHA="$BRANCH_BASE_SHA" \
python3 <<'PYEOF'
import os, sys
root = os.environ.get('PKG_ROOT') or ''
if root:
    sys.path.insert(0, root)
from _lib.builder_handoff import read_builder_handoff, update_builder_handoff
# Merge, not overwrite: a full write resets approval_status to its "pending"
# default (dropping P0's "approved") and any field written by another phase.
#
# execution_mode_decision must describe the mode that ACTUALLY ran. When the
# lightweight branch preparation failed closed, the mode was rewritten to
# "worktree" — leaving the old "lightweight" in the handoff would be a
# declaration that contradicts the execution (the ghost branch all over
# again, one level up).
existing = read_builder_handoff(
    os.environ['PROJECT_ROOT'], os.environ['CHANGE_NAME']
)
decision = dict(existing.get('execution_mode_decision') or {})
decision['mode'] = os.environ['EXEC_MODE']
reason = os.environ.get('EXEC_MODE_REASON') or ''
if reason:
    decision['reason'] = reason
base_sha = os.environ.get('BRANCH_BASE_SHA') or ''
if base_sha:
    decision['branch_base_sha'] = base_sha
update_builder_handoff(
    os.environ['PROJECT_ROOT'],
    os.environ['CHANGE_NAME'],
    current_phase="phase-2",
    # The setup step only PREPARES the worktree — the implementation has not
    # started. Writing "completed" here made every reader (a resumed session,
    # a board, any consumer of the handoff) believe the implementation was
    # done (measured 2026-11-26: 5 files changed, 0 tasks checked, handoff
    # said "completed"). "running" is the truth at this point; "completed" is
    # written by Phase 3, when the tasks are actually checked and the change
    # is archived.
    execution_status="running",
    execution_mode_decision=decision,
    worktree_path=os.environ['EXEC_DIR'],
    branch="openspec/%s" % os.environ['CHANGE_NAME'],
)
PYEOF

# Record execution progress (fix-iteration-tasks-total): this is the only write
# that makes a change verifier-eligible (`done == total > 0`). It is also the
# last chance to record it — the archive sync only fills in what is missing.
# Bookkeeping failure must not abort the phase.
PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" python3 - <<'PYEOF' || true
import os, sys
root = os.environ.get("PKG_ROOT") or ""
if root:
    sys.path.insert(0, root)
# NOTE: import via the skills._lib shim. `_lib/iteration/store.py` imports
# `skills._lib.iteration.schema`, so a direct `import _lib.iteration.X`
# re-enters the package initialisation and raises a circular-import
# ImportError (pre-existing; see the implementation record).
from skills._lib.iteration.writer import record_tasks_snapshot
msg = record_tasks_snapshot(
    os.environ["PROJECT_ROOT"], os.environ["CHANGE_NAME"], phase="execute"
)
if msg:
    print("  ⚠️  " + msg, file=sys.stderr)
PYEOF

exit 0