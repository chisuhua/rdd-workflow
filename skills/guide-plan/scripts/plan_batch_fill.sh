#!/usr/bin/env bash
# Batch-fill design-pre-created OpenSpec changes.
# Usage: plan_batch_fill.sh --changes c1,c2,...
set -euo pipefail

_PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export PROJECT_ROOT="$_PROJECT_ROOT"

# Pass the argument vector through Python's environment rather than interpolating
# user-controlled change names into source code (Oracle C1).
export PLAN_BATCH_FILL_ARGS_JSON
PLAN_BATCH_FILL_ARGS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@")"
exec python3 -c '
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.guide_plan.scripts.plan_batch_fill import main
args = json.loads(os.environ["PLAN_BATCH_FILL_ARGS_JSON"])
raise SystemExit(main(args))
'
