#!/usr/bin/env bash
# Wrapper for skills._lib.discover_ship_changes.discover.
#
# Usage:
#   source skills/_lib/discover_ship_changes.sh
#   ship_candidates_json <project_root>     # echoes JSON list to stdout
#   ship_candidate_count <project_root>     # echoes integer count
#   ship_top_candidate  <project_root>      # echoes best candidate name

set -euo pipefail

_discover_py() {
    python3 -c "
import json, sys
sys.path.insert(0, '.')
from skills._lib.discover_ship_changes import discover
items = discover(sys.argv[1])
print(json.dumps([c.to_dict() for c in items]))
" "$1"
}

_discover_count_py() {
    python3 -c "
import sys
sys.path.insert(0, '.')
from skills._lib.discover_ship_changes import discover
print(len(discover(sys.argv[1])))
" "$1"
}

_discover_top_py() {
    python3 -c "
import sys
sys.path.insert(0, '.')
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