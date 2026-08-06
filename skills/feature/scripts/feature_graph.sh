#!/usr/bin/env bash
# _lib/feature_graph.sh — extracted from feature.md (subcommand: graph)
# Exports: render_feature_graph()

render_feature_graph() {
  local _SCRIPT_DIR
  _SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]:-$0}")"
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  PYTHONPATH="$_SCRIPT_DIR/../..${PYTHONPATH:+:$PYTHONPATH}" python3 -c "
import os, sys
sys.path.insert(0, os.environ['PROJECT_ROOT'])
from skills.feature.scripts import feature_cli as fc
fc.render_graph(os.environ['PROJECT_ROOT'])
"
}
