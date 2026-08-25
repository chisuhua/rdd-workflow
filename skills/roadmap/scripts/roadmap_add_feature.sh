#!/usr/bin/env bash
# skills/roadmap/scripts/roadmap_add_feature.sh
# Env-var only pattern (Oracle C1) — no inline python3 -c "...$VAR..." interpolation.
#
# Usage:
#   rddf roadmap add-feature <name> [options]
#
# Options:
#   --phase-refs <p1,p2,...>    Required. Comma-separated phase IDs.
#   --theme "<text>"            Required. Single-line 主题.
#   --status <a|d|x>            Optional. Default: a (active).
#   --force                     Optional. Overwrite existing feat-<name>.md.
#
# Exit codes:
#   0  success
#   1  validation error (phase_refs invalid / duplicate without --force)
#   2  usage error (missing arg / malformed flag)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" 2>/dev/null && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

NAME=""
PHASE_REFS=""
THEME=""
STATUS="active"
FORCE="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --phase-refs) PHASE_REFS="$2"; shift 2 ;;
        --theme) THEME="$2"; shift 2 ;;
        --status)
            case "$2" in
                a|active) STATUS="active" ;;
                d|done) STATUS="done" ;;
                x|archived) STATUS="archived" ;;
                *) echo "❌ invalid --status: $2 (expected a|d|x)" >&2; exit 2 ;;
            esac
            shift 2
            ;;
        --force) FORCE="true"; shift ;;
        -h|--help)
            echo "Usage: rddf roadmap add-feature <name> --phase-refs <...> --theme <text> [--status a|d|x] [--force]"
            exit 0
            ;;
        *)
            if [ -z "$NAME" ]; then NAME="$1"; shift; else
                echo "❌ unexpected positional arg: $1" >&2; exit 2
            fi
            ;;
    esac
done

if [ -z "$NAME" ]; then
    echo "❌ name required (positional)" >&2
    exit 2
fi
if [ -z "$PHASE_REFS" ]; then
    echo "❌ --phase-refs required" >&2
    exit 2
fi
if [ -z "$THEME" ]; then
    echo "❌ --theme required" >&2
    exit 2
fi

PROJECT_ROOT="$PROJECT_ROOT" \
CHANGE_NAME="$NAME" \
PHASE_REFS="$PHASE_REFS" \
THEME="$THEME" \
STATUS="$STATUS" \
FORCE="$FORCE" \
python3 "$SCRIPT_DIR/../../../_lib/roadmap_state_wrapper.py"