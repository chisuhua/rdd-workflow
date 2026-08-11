#!/usr/bin/env bash
# skills/guide-design/scripts/run_content_review.sh
#
# Single helper that invokes the existing design_content_review.sh
# wrapper. Used by both single-item approve (approve_proposal.sh) and
# batch approve (design_proposal_review.sh) so both code paths share
# one review-call path per design decision 1 of
# openspec/changes/wire-design-content-review-gate/design.md.
#
# Env vars:
#   IMPROVEMENTS_PATH   absolute path to .rddf/improvements/<name>.md (required)
#   PROJECT_ROOT        absolute path to repo root (required)
#   STRICT_DESIGN_GATE  yes -> review blocks on errors (default: no)
#   SKIP_CONTENT_REVIEW yes -> short-circuit; exit 0 with skipped=true
#
# Output:
#   stdout: review script's natural stdout (success/warning/blocking markers)
#   stderr: review script's natural stderr
#   exit:   review script's exit code (0=pass/warning, 1=blocking, 2=skip)
#
# Side-effect: writes "REVIEW_RESULT=<pass|warn|block|skip>" to FD 3
# (if available) so callers can branch on outcome without parsing stdout.

set -uo pipefail

IMPROVEMENTS_PATH="${IMPROVEMENTS_PATH:-}"
PROJECT_ROOT="${PROJECT_ROOT:-}"
STRICT_DESIGN_GATE="${STRICT_DESIGN_GATE:-no}"
SKIP_CONTENT_REVIEW="${SKIP_CONTENT_REVIEW:-no}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
REVIEW_SH="$SCRIPT_DIR/design_content_review.sh"

if [ ! -x "$REVIEW_SH" ]; then
    echo "❌ review wrapper not found or not executable: $REVIEW_SH" >&2
    exit 2
fi

if [ -z "$IMPROVEMENTS_PATH" ]; then
    echo "❌ IMPROVEMENTS_PATH not set" >&2
    exit 2
fi
if [ ! -f "$IMPROVEMENTS_PATH" ]; then
    echo "❌ .rddf/improvements file not found: $IMPROVEMENTS_PATH" >&2
    exit 2
fi

if [ "$SKIP_CONTENT_REVIEW" = "yes" ]; then
    echo "SKIP_CONTENT_REVIEW=yes: review skipped (escape hatch honored)"
    if { true >&3; } 2>/dev/null; then
        echo "REVIEW_RESULT=skip" >&3
    fi
    exit 0
fi

export PROJECT_ROOT IMPROVEMENTS_PATH STRICT_DESIGN_GATE SKIP_CONTENT_REVIEW

set +e
output=$(bash "$REVIEW_SH" 2>&1)
rc=$?
set -e

echo "$output"

if [ "$rc" -eq 0 ]; then
    if echo "$output" | grep -qiE 'WARNING|warn'; then
        result="warn"
    else
        result="pass"
    fi
else
    result="block"
fi

if { true >&3; } 2>/dev/null; then
    echo "REVIEW_RESULT=$result" >&3
fi

exit "$rc"