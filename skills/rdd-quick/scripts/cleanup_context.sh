#!/usr/bin/env bash
# skills/rdd-quick/scripts/cleanup_context.sh
# Remove .rddf/state/rdd-quick-context.json if exists + append audit log entry.
# Called from P4 completion + escalation paths in rdd-quick/SKILL.md.
#
# Per rdd-workflow v2.1 fix (2026-09-28): closes stale advisory on next mode a call.
#
# Usage:
#   cleanup_context.sh --reason completed|escalated
#
# Environment:
#   RDDF_QUICK_STATE_DIR     default ".rddf/state"
#   RDDF_QUICK_HISTORY_FILE  default ".rddf/state/.quick-history.jsonl"
#
# Exit codes:
#   0  success (deleted or no-op)
#   2  invalid args
set -euo pipefail

REASON=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reason)
            REASON="${2:-}"
            shift 2
            ;;
        -h|--help)
            echo "Usage: cleanup_context.sh --reason completed|escalated"
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$REASON" ]]; then
    echo "ERROR: --reason required (completed|escalated)" >&2
    exit 2
fi

if [[ "$REASON" != "completed" && "$REASON" != "escalated" ]]; then
    echo "ERROR: --reason must be 'completed' or 'escalated' (got: $REASON)" >&2
    exit 2
fi

STATE_DIR="${RDDF_QUICK_STATE_DIR:-.rddf/state}"
CONTEXT_FILE="$STATE_DIR/rdd-quick-context.json"
HISTORY_FILE="${RDDF_QUICK_HISTORY_FILE:-$STATE_DIR/.quick-history.jsonl}"

# No-op if context file absent (avoid empty audit log noise)
if [[ ! -f "$CONTEXT_FILE" ]]; then
    exit 0
fi

# Delete context file
rm -f "$CONTEXT_FILE"

# Append audit log entry (newline-terminated for jsonl append consistency)
mkdir -p "$(dirname "$HISTORY_FILE")"
DELETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '{"event": "context_cleanup", "reason": "%s", "deleted_at": "%s"}\n' \
    "$REASON" "$DELETED_AT" >> "$HISTORY_FILE"