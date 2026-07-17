#!/usr/bin/env bash
# skills/_lib/feature_summary.sh — extracted from feature.md (subcommand: summary)
# Exports: render_feature_summary()

render_feature_summary() {
  local _SCRIPT_DIR
  _SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]:-$0}")"
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  PYTHONPATH="$_SCRIPT_DIR/../..${PYTHONPATH:+:$PYTHONPATH}" python3 -c "
import os, sys
sys.path.insert(0, os.environ['PROJECT_ROOT'])
from skills.feature.scripts import feature_cli as fc
fc.render_summary(os.environ['PROJECT_ROOT'])
"
}
