#!/usr/bin/env bash
# Wrapper for skills._lib.discover_ship_changes.discover.
#
# Usage:
#   source skills/_lib/discover_ship_changes.sh
#   ship_candidates_json <project_root>     # echoes JSON list to stdout
#   ship_candidate_count <project_root>     # echoes integer count
#   ship_top_candidate  <project_root>      # echoes best candidate name
#
# IMPORTANT: do NOT enable `set -e` / `set -u` here. This file is intended
# to be `source`d by callers (e.g. guide-ship.md bash blocks) and turning
# on shell options from a sourced file leaks into the caller's shell,
# changing failure semantics for code we do not own.

_skill_root=""
if [ -n "${PROJECT_ROOT:-}" ] && [ -f "$PROJECT_ROOT/skills/_lib/discover_ship_changes.py" ]; then
    _skill_root="$PROJECT_ROOT/skills"
elif [ -f "/nonexistent/skills/_lib/discover_ship_changes.py" ] 2>/dev/null; then
    _skill_root="/nonexistent/skills"
fi
# Fallback: locate via skill_root.sh if available.
if [ -z "$_skill_root" ] || [ ! -f "$_skill_root/_lib/discover_ship_changes.py" ]; then
    if [ -f "${HOME}/.agents/skills/_lib/skill_root.sh" ]; then
        _skill_root="$(HOME="$HOME" "${HOME}/.agents/skills/_lib/skill_root.sh" 2>/dev/null \
            | sed -n 's/.*rdd-workflow\/skills.*/&/p' | head -1)"
    fi
fi
# Last-resort: cwd-relative; works when rdd-workflow is the cwd (development mode).
if [ -z "$_skill_root" ] || [ ! -f "$_skill_root/_lib/discover_ship_changes.py" ]; then
    _skill_root="./skills"
fi

_discover_py() {
    PYTHONPATH="$_skill_root:${PYTHONPATH:-}" python3 -c "
import json, sys
from skills._lib.discover_ship_changes import discover
items = discover(sys.argv[1])
print(json.dumps([c.to_dict() for c in items]))
" "$1"
}

_discover_count_py() {
    PYTHONPATH="$_skill_root:${PYTHONPATH:-}" python3 -c "
import sys
from skills._lib.discover_ship_changes import discover
print(len(discover(sys.argv[1])))
" "$1"
}

_discover_top_py() {
    PYTHONPATH="$_skill_root:${PYTHONPATH:-}" python3 -c "
import sys
from skills._lib.discover_ship_changes import discover
items = discover(sys.argv[1])
print(items[0].name if items else '')
" "$1"
}

ship_candidates_json() {
    local project_root="${1:-.}"
    _discover_py "$project_root"
}

ship_candidate_count() {
    local project_root="${1:-.}"
    _discover_count_py "$project_root"
}

ship_top_candidate() {
    local project_root="${1:-.}"
    _discover_top_py "$project_root"
}