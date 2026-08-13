#!/usr/bin/env bash
# skills/add-improve/scripts/from_roadmap.sh
# Bash entry for `add-improve --from-roadmap` mode (Oracle C1 env-var pattern).
#
# Usage:
#   bash from_roadmap.sh --from-roadmap <phase_id>/<category_id> \
#                        --theme <theme_name> \
#                        [--rationale "<draft rationale>"] \
#                        --project-root <path>
#
# Behavior:
#   1. Parses CLI args into env-vars (ADD_IMPROVE_FROM_ROADMAP, ADD_IMPROVE_THEME, etc.)
#   2. Calls from_roadmap.env.py validate to reject shell metacharacters
#   3. Calls from_roadmap.py to invoke brainstorm in constraint mode and write proposal
#   4. Unsets env-vars on exit (cleanup)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FROM_ROADMAP=""
THEME=""
RATIONALE=""
PROJECT_ROOT=""

usage() {
    cat <<EOF
Usage: $0 --from-roadmap <phase/category> --theme <name> [--rationale <text>] --project-root <path>

Options:
  --from-roadmap    REQUIRED: phase_id/category_id (e.g., phase-1/arch-design)
  --theme           REQUIRED: roadmap theme name (must NOT contain shell metacharacters)
  --rationale       OPTIONAL: AI-drafted rationale (passed to brainstorm scaffold)
  --project-root    REQUIRED: absolute path to project root
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-roadmap) FROM_ROADMAP="$2"; shift 2 ;;
        --theme)        THEME="$2"; shift 2 ;;
        --rationale)    RATIONALE="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

if [[ -z "$FROM_ROADMAP" || -z "$THEME" || -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: --from-roadmap, --theme, --project-root are required" >&2
    usage
fi

export ADD_IMPROVE_FROM_ROADMAP="$FROM_ROADMAP"
export ADD_IMPROVE_THEME="$THEME"
export BRAINSTORM_RATIONALE_DRAFT="$RATIONALE"
export PROJECT_ROOT

cleanup() {
    unset ADD_IMPROVE_FROM_ROADMAP
    unset ADD_IMPROVE_THEME
    unset BRAINSTORM_RATIONALE_DRAFT
}
trap cleanup EXIT

if ! python3 "$SCRIPT_DIR/from_roadmap.env.py" validate; then
    echo "ERROR: env-var validation failed" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/from_roadmap.py"