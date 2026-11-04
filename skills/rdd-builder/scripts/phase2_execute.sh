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

if [ "$EXEC_MODE" = "worktree" ]; then
    WT_PATH=".rddf/wt/$CHANGE_NAME"
    BRANCH="openspec/$CHANGE_NAME"
    if [ ! -d "$WT_PATH" ]; then
        git worktree add "$WT_PATH" -b "$BRANCH" 2>/dev/null || {
            echo "worktree creation failed at $WT_PATH (branch may already exist)" >&2
            WT_PATH="$PROJECT_ROOT"  # fallback to main repo
        }
    fi
    EXEC_DIR="$WT_PATH"
    # Carry the change's artifacts into the new worktree:
    # `git worktree add` builds from HEAD, so files that were never
    # committed are absent there. Without this, P2 fails with
    # "plan file missing" for exactly the changes that are not committed yet.
    #
    # Two edge cases this must handle:
    #   - dst already exists (the change WAS committed → worktree already
    #     has it): copy the CONTENTS, not the directory itself — plain
    #     `cp -R src dst` would create `dst/src` (a nested <name>/<name>/).
    #   - src == dst (worktree creation fell back to the main repo):
    #     `cp -R a a` fails with "cannot copy a directory into itself",
    #     and `set -e` would abort P2.
    for _rel in "openspec/changes/$CHANGE_NAME" ".rddf/plans/$CHANGE_NAME.md"; do
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
else
    EXEC_DIR="$PROJECT_ROOT"
fi

cd "$EXEC_DIR"
if [ -f ".rddf/plans/$CHANGE_NAME.md" ]; then
    echo "Phase 2 worktree setup complete (mode=$EXEC_MODE, dir=$EXEC_DIR)"
else
    echo "plan file missing at .rddf/plans/$CHANGE_NAME.md" >&2
    exit 3
fi

cd "$PROJECT_ROOT"

PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" EXEC_DIR="$EXEC_DIR" python3 <<'PYEOF'
import os, sys
root = os.environ.get('PKG_ROOT') or ''
if root:
    sys.path.insert(0, root)
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root=os.environ['PROJECT_ROOT'],
    change_name=os.environ['CHANGE_NAME'],
    current_phase="phase-2",
    execution_status="completed",
    worktree_path=os.environ['EXEC_DIR'],
    branch="openspec/%s" % os.environ['CHANGE_NAME'],
)
PYEOF

exit 0