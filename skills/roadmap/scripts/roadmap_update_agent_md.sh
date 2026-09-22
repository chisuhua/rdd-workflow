#!/usr/bin/env bash
# skills/roadmap/scripts/roadmap_update_agent_md.sh
# Env-var only pattern (Oracle C1) — no inline python3 -c "...$VAR..." interpolation.
#
# Usage:
#   rddf roadmap --update-agent-md
#   rddf roadmap update-agent-md
#
# Options:
#   --agents-md <path>          Override default AGENTS.md (in repo root).
#   --fragments-dir <path>      Override default .rddf/roadmap.
#   -h | --help                 Show this help.
#
# Exit codes:
#   0  success (rewrote or inserted AGENTS.md AUTO block)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" 2>/dev/null && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

AGENTS_MD_PATH_OVERRIDE=""
FRAGMENTS_DIR_OVERRIDE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --agents-md) AGENTS_MD_PATH_OVERRIDE="$2"; shift 2 ;;
        --fragments-dir) FRAGMENTS_DIR_OVERRIDE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: rddf roadmap --update-agent-md [--agents-md <path>] [--fragments-dir <path>]"
            echo ""
            echo "Rewrites the AGENTS.md AUTO feature-fragments sentinel block."
            echo "Per improve-roadmap-feature-discovery proposal AC-2."
            exit 0
            ;;
        *) echo "❌ unexpected arg: $1" >&2; exit 2 ;;
    esac
done

EXTRA_ENV=""
[ -n "$AGENTS_MD_PATH_OVERRIDE" ] && EXTRA_ENV="$EXTRA_ENV AGENTS_MD_PATH=$AGENTS_MD_PATH_OVERRIDE"
[ -n "$FRAGMENTS_DIR_OVERRIDE" ] && EXTRA_ENV="$EXTRA_ENV FRAGMENTS_DIR=$FRAGMENTS_DIR_OVERRIDE"

PROJECT_ROOT="$PROJECT_ROOT" \
MODE="update-agent-md" \
$EXTRA_ENV \
python3 "$SCRIPT_DIR/../../../_lib/roadmap_state_wrapper.py"