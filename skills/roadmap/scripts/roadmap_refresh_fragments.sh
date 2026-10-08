#!/usr/bin/env bash
# skills/roadmap/scripts/roadmap_refresh_fragments.sh
# Env-var only pattern (Oracle C1) — no inline python3 -c "...$VAR..." interpolation.
#
# Usage:
#   rddf roadmap --refresh-fragments
#   rddf roadmap refresh-fragments
#
# Options:
#   --main-doc <path>          Override default .rddf/roadmap.md.
#   --agents-md <path>         Override default AGENTS.md.
#   --fragments-dir <path>     Override default .rddf/roadmap.
#   -h | --help                 Show this help.
#
# Exit codes:
#   0  success (rewrote both .rddf/roadmap.md AUTO-INDEX + AGENTS.md AUTO block)
#   1  internal error (delegated from _lib.roadmap_state_wrapper)
#
# Per add-refresh-fragments-cli (2026-10-08): bundles `render_fragment_index`
# + `update_agent_md` into a single command to avoid manual sync drift surfaced
# by `rdd-doctor roadmap-feature` check (drift signals whenever a new
# `feat-*.md` is added without manual AUTO-INDEX sync).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" 2>/dev/null && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

MAIN_DOC_OVERRIDE=""
AGENTS_MD_OVERRIDE=""
FRAGMENTS_DIR_OVERRIDE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --main-doc) MAIN_DOC_OVERRIDE="$2"; shift 2 ;;
        --agents-md) AGENTS_MD_OVERRIDE="$2"; shift 2 ;;
        --fragments-dir) FRAGMENTS_DIR_OVERRIDE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: rddf roadmap --refresh-fragments [options]"
            echo ""
            echo "Refreshes both .rddf/roadmap.md AUTO-INDEX Features/Phases"
            echo "segments AND AGENTS.md AUTO feature-fragments sentinel block"
            echo "in one atomic operation."
            echo ""
            echo "Options:"
            echo "  --main-doc <path>      Override default .rddf/roadmap.md"
            echo "  --agents-md <path>     Override default AGENTS.md"
            echo "  --fragments-dir <path> Override default .rddf/roadmap"
            exit 0
            ;;
        *) echo "❌ unexpected arg: $1" >&2; exit 2 ;;
    esac
done

EXTRA_ENV=""
[ -n "$MAIN_DOC_OVERRIDE" ] && EXTRA_ENV="$EXTRA_ENV MAIN_DOC_PATH=$MAIN_DOC_OVERRIDE"
[ -n "$AGENTS_MD_OVERRIDE" ] && EXTRA_ENV="$EXTRA_ENV AGENTS_MD_PATH=$AGENTS_MD_OVERRIDE"
[ -n "$FRAGMENTS_DIR_OVERRIDE" ] && EXTRA_ENV="$EXTRA_ENV FRAGMENTS_DIR=$FRAGMENTS_DIR_OVERRIDE"

PROJECT_ROOT="$PROJECT_ROOT" \
MODE="refresh-fragments" \
$EXTRA_ENV \
python3 "$SCRIPT_DIR/../../../_lib/roadmap_state_wrapper.py"