#!/usr/bin/env bash
# skills/roadmap/scripts/roadmap_list_features.sh
# Env-var only pattern (Oracle C1) — no inline python3 -c "...$VAR..." interpolation.
#
# Usage:
#   rddf roadmap list-features [options]
#
# Options:
#   --format <table|json|yaml>   Output format. Default: table.
#   --no-archived                Exclude archived feature fragments.
#   --fragments-dir <path>       Override default .rddf/roadmap.
#   -h | --help                  Show this help.
#
# Exit codes:
#   0  success
#   2  usage error (invalid format, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" 2>/dev/null && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

FMT="table"
INCLUDE_ARCHIVED="true"
FRAGMENTS_DIR_OVERRIDE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --format)
            case "$2" in
                table|json|yaml) FMT="$2" ;;
                *) echo "❌ invalid --format: $2 (expected table|json|yaml)" >&2; exit 2 ;;
            esac
            shift 2
            ;;
        --no-archived) INCLUDE_ARCHIVED="false"; shift ;;
        --fragments-dir) FRAGMENTS_DIR_OVERRIDE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: rddf roadmap list-features [--format table|json|yaml] [--no-archived]"
            echo ""
            echo "Lists all .rddf/roadmap/features/*.md fragments."
            echo ""
            echo "Per improve-roadmap-feature-discovery proposal AC-1."
            exit 0
            ;;
        *) echo "❌ unexpected arg: $1" >&2; exit 2 ;;
    esac
done

EXTRA_ENV=""
if [ -n "$FRAGMENTS_DIR_OVERRIDE" ]; then
    EXTRA_ENV="FRAGMENTS_DIR=$FRAGMENTS_DIR_OVERRIDE"
fi

PROJECT_ROOT="$PROJECT_ROOT" \
MODE="list-features" \
FMT="$FMT" \
$EXTRA_ENV \
python3 "$SCRIPT_DIR/../../../_lib/roadmap_state_wrapper.py"