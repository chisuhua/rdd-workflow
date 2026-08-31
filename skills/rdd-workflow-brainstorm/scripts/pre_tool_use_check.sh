#!/usr/bin/env bash
# pre_tool_use_check.sh <tool> [target] [offset]
# Warn-only guard (always exit 0). Emits stderr hints for 3 stale patterns.
# Env override for testability:
#   RDDF_GUARD_FILE_STATE=stale|fresh   — simulated edit target freshness
#   RDDF_GUARD_TARGET_EXISTS=1|0        — simulated write target existence
# Oracle C1: no bash string interpolation into python.

set -uo pipefail

TOOL="${1:-}"
TARGET="${2:-}"
OFFSET="${3:-}"

case "$TOOL" in
  edit)
    state="${RDDF_GUARD_FILE_STATE:-fresh}"
    if [ "$state" = "stale" ]; then
      echo "[pre-tool-check] STALE-LIKELY: edit '$TARGET' after long idle — Read full file first" >&2
    fi
    ;;
  write)
    exists="${RDDF_GUARD_TARGET_EXISTS:-0}"
    if [ "$exists" = "1" ]; then
      echo "[pre-tool-check] EXISTS: write '$TARGET' onto existing file — use edit instead" >&2
    fi
    ;;
  read)
    if [ -n "$OFFSET" ]; then
      echo "[pre-tool-check] OFFSET: read '$TARGET' with hardcoded offset $OFFSET — confirm actual line count first" >&2
    fi
    ;;
esac

exit 0
