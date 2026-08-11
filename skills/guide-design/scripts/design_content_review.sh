#!/usr/bin/env bash
# skills/guide-design/scripts/design_content_review.sh
#
# Wrapper for design_content_review.py — .rddf/improvements-layer content review.
# Oracle C1: env-var only passing, no string interpolation into python.
#
# Env vars:
#   IMPROVEMENTS_PATH    path to .rddf/improvements/<name>.md (required)
#   STRICT_DESIGN_GATE   yes -> exit 1 on review errors (default: warning only)
#   SKIP_CONTENT_REVIEW  yes -> bypass review entirely (default: no)
#
# Exit codes:
#   0  pass / warning raised
#   1  strict mode blocked (review errors with STRICT_DESIGN_GATE=yes)
#   2  usage error (missing IMPROVEMENTS_PATH)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
IMPROVEMENTS_PATH="${IMPROVEMENTS_PATH:-}"
STRICT_DESIGN_GATE="${STRICT_DESIGN_GATE:-no}"
SKIP_CONTENT_REVIEW="${SKIP_CONTENT_REVIEW:-no}"

if [ "$SKIP_CONTENT_REVIEW" = "yes" ]; then
    echo "SKIP_CONTENT_REVIEW=yes: skipping review"
    exit 0
fi

if [ -z "$IMPROVEMENTS_PATH" ]; then
    echo "ERROR: IMPROVEMENTS_PATH not set" >&2
    exit 2
fi

if [ ! -f "$IMPROVEMENTS_PATH" ]; then
    echo "ERROR: IMPROVEMENTS_PATH file not found: $IMPROVEMENTS_PATH" >&2
    exit 2
fi

export PROJECT_ROOT IMPROVEMENTS_PATH STRICT_DESIGN_GATE SKIP_CONTENT_REVIEW
python3 "$SCRIPT_DIR/design_content_review.py"
