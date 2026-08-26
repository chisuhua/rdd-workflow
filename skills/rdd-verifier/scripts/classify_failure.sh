#!/usr/bin/env bash
# classify_failure.sh <change_name> — Read verdict cache, classify each fail, print labels
#
# Usage: bash classify_failure.sh <change_name>
# Stdout: "AC-N:label" lines (one per failing AC)
# Exit: 0 always (1 if cache missing)
#
# Per ADR-0034 §5.1 + Oracle §E: heuristic classification, no new LLM call.
set -euo pipefail

CHANGE_NAME="${1:-}"
[ -z "$CHANGE_NAME" ] && {
    echo "❌ usage: classify_failure.sh <change_name>" >&2
    exit 2
}

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CACHE="$PROJECT_ROOT/.rddf/state/.ac-verdict-${CHANGE_NAME}.json"

if [ ! -f "$CACHE" ]; then
    echo "❌ verdict cache missing: $CACHE" >&2
    exit 1
fi

python3 - "$CACHE" <<PYEOF
import json
import sys
from pathlib import Path

# Inject _lib into sys.path so _lib.verifier.classify is importable
sys.path.insert(0, str(Path("$PROJECT_ROOT") / "_lib"))
from _lib.verifier.classify import classify_failure

cache = json.loads(open(sys.argv[1], encoding="utf-8").read())
for item in cache.get("verdict", []):
    if item.get("status") == "fail":
        label = classify_failure(item)
        print(f"{item['ac_id']}:{label}")
PYEOF