#!/usr/bin/env bash
# ac_verifier.sh — bash wrapper for skills/ac-verifier/scripts/ac_verifier.py
#
# Usage: ac_verifier.sh <change-name> [--dry-run] [--strict] [--skip]
#
# Exit codes:
#   0  All ACs pass (or no AC section found)
#   1  At least one AC fail (warning by default; error under STRICT_AC_GATE)
#   2  Skipped (--skip, no proposal.md, or no AC section)
#   3  Error (LLM call failed after retries, missing API key)
#
# Environment:
#   STRICT_AC_GATE=yes          Promote AC fail → archive blocker
#   SKIP_AC_VERIFICATION=yes    Skip verification entirely (exit 2)
#   AC_LLM_MOCK=yes             Use mock LLM (testing only)
#   AC_LLM_PROVIDER             openai | anthropic | local-ollama (default: auto-detect)
#   AC_LLM_MODEL                Model name
#   AC_LLM_TIMEOUT              Seconds per LLM call (default: 60)
set -euo pipefail

# Resolve script directory and python module path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Argument parsing
CHANGE_NAME=""
DRY_RUN=""
STRICT=""
SKIP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN="--dry-run"; shift ;;
    --strict) STRICT="--strict"; shift ;;
    --skip) SKIP="--skip"; shift ;;
    -h|--help)
      cat <<EOF
Usage: $(basename "$0") <change-name> [--dry-run] [--strict] [--skip]

Verify OpenSpec change acceptance criteria against committed code.

Exit codes: 0=pass, 1=fail, 2=skip, 3=error
EOF
      exit 0
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      exit 3
      ;;
    *)
      CHANGE_NAME="$1"
      shift
      ;;
  esac
done

[[ -z "$CHANGE_NAME" ]] && { echo "Usage: $(basename "$0") <change-name> [--dry-run] [--strict] [--skip]" >&2; exit 3; }

# Honor SKIP_AC_VERIFICATION env var (matches SKIP_* pattern)
if [ "${SKIP_AC_VERIFICATION:-no}" = "yes" ] || [ -n "$SKIP" ]; then
  echo "⏭️  AC verification skipped via SKIP_AC_VERIFICATION" >&2
  exit 2
fi

# Honor STRICT_AC_GATE env var (matches STRICT_*_GATE pattern)
if [ -z "$STRICT" ] && [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
  STRICT="--strict"
fi

# Locate proposal.md
PROPOSAL_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"
if [ ! -f "$PROPOSAL_PATH" ]; then
  echo "⚠️  proposal.md not found at $PROPOSAL_PATH; skipping" >&2
  exit 2
fi

# Invoke Python orchestrator via direct path (dash-bridge not available outside pytest)
PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$PROJECT_ROOT" \
  exec python3 "$SCRIPT_DIR/ac_verifier.py" "$CHANGE_NAME" \
    --proposal "$PROPOSAL_PATH" \
    --project-root "$PROJECT_ROOT" \
    $DRY_RUN $STRICT