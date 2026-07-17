#!/usr/bin/env bash
# skills/_lib/feature_status.sh — extracted from feature.md (subcommand: status)
# Exports: render_feature_status() — accepts target feature name as $1

render_feature_status() {
  local _SCRIPT_DIR
  _SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]:-$0}")"
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT
  export FEATURE_TARGET_NAME="$1"
  PYTHONPATH="$_SCRIPT_DIR/../..${PYTHONPATH:+:$PYTHONPATH}" python3 -c "
import os, sys
sys.path.insert(0, os.environ['PROJECT_ROOT'])
from skills.feature.scripts import feature_cli as fc
fc.render_status(os.environ['PROJECT_ROOT'], os.environ.get('FEATURE_TARGET_NAME', ''))
"
}
