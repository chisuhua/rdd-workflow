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

set +e
AC_OUTPUT=$(PROJECT_ROOT="$PROJECT_ROOT" bash "$AC_SCRIPT" "$CHANGE_NAME" 2>&1)
AC_EXIT=$?
set -e

printf '%s\n' "$AC_OUTPUT"

if [ "$AC_EXIT" -eq 0 ] || [ "$AC_EXIT" -eq 1 ]; then
    PROJECT_ROOT="$PROJECT_ROOT" VERIFIER_CHANGE_NAME="$CHANGE_NAME" \
        VERIFIER_EXIT_CODE="$AC_EXIT" VERIFIER_OUTPUT="$AC_OUTPUT" \
        python3 - <<'PY'
import json
import os
from pathlib import Path

from _lib.verifier.branch import resolve_implementation_commit
from _lib.verifier.cache import verdict_cache

root = Path(os.environ["PROJECT_ROOT"])
change = os.environ["VERIFIER_CHANGE_NAME"]
exit_code = int(os.environ["VERIFIER_EXIT_CODE"])
output = os.environ.get("VERIFIER_OUTPUT", "")
try:
    payload = json.loads(output)
except json.JSONDecodeError:
    payload = {}
verdict = payload.get("verdict", []) if isinstance(payload, dict) else []
failed = [item.get("ac_id", "?") for item in verdict if item.get("status") == "fail"]
commit = resolve_implementation_commit(root, change) or "unknown"
verdict_cache(
    root,
    change,
    payload.get("codebase_commit", commit) if isinstance(payload, dict) else commit,
    verdict,
    ran_by="rdd-verifier",
    verification_state="passed" if exit_code == 0 else "failed",
    failed_acs=failed,
    implementation_ref=f"openspec/{change}",
)
PY
fi

exit "$AC_EXIT"