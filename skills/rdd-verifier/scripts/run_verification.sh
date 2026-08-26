#!/usr/bin/env bash
# run_verification.sh <change_name> — Invoke ac-verifier skill for one change
#
# Usage: bash run_verification.sh <change_name>
# Exit: ac-verifier exit code (0=pass, 1=fail, 2=skip, 3=error)
#
# Per ADR-0034 §4.1: wraps ac-verifier skill invocation for one change.
set -euo pipefail

CHANGE_NAME="${1:-}"
[ -z "$CHANGE_NAME" ] && {
    echo "❌ usage: run_verification.sh <change_name>" >&2
    exit 2
}

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
AC_SCRIPT="$PROJECT_ROOT/skills/ac-verifier/scripts/ac_verifier.sh"

if [ ! -f "$AC_SCRIPT" ]; then
    echo "❌ ac-verifier skill not found at $AC_SCRIPT" >&2
    exit 3
fi

bash "$AC_SCRIPT" "$CHANGE_NAME"