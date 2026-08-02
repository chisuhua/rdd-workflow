#!/usr/bin/env bash
# skills/guide-plan/scripts/artifact_dag.sh
#
# Bash wrapper for artifact_dag.py — openspec artifact DAG driver.
# Oracle C1: env-var only passing, no bash string interpolation into python.
#
# Env vars:
#   PROJECT_ROOT    path to project root (default: git rev-parse --show-toplevel)
#   CHANGE_NAME     openspec change name (required)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CHANGE_NAME="${CHANGE_NAME:-}"

if [ -z "$CHANGE_NAME" ]; then
    echo "ERROR: CHANGE_NAME not set" >&2
    exit 2
fi

export PROJECT_ROOT CHANGE_NAME
python3 "$SCRIPT_DIR/artifact_dag.py"