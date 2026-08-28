#!/usr/bin/env bash
# skills/add-improve/scripts/from_roadmap.sh
# Bash entry for `add-improve --from-roadmap` mode (Oracle C1 env-var pattern).
#
# Usage:
#   bash from_roadmap.sh --from-roadmap <phase_id>/<category_id> \
#                        --theme <theme_name> \
#                        [--rationale "<draft rationale>"] \
#                        [--name-prefix <prefix>] \
#                        [--name-suffix <suffix>] \
#                        [--auto-name] \
#                        [--multi <count>] \
#                        --project-root <path>
#
# Naming (improve-from-roadmap-naming-flexibility, 2026-08-28):
#   default       from-roadmap-<phase>-<category>        (backward compat)
#   --name-prefix <prefix>-<phase>-<category>
#   --name-suffix <phase>-<category><suffix>
#   --auto-name   <name>-<YYYYMMDDHHMMSS> timestamp-unique
#   --multi <N>   create N sub-proposals <base>-sub-1..N from one theme
#   Conflicts (name already exists) auto-append -2, -3, ... (never overwrite).
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
NAME_PREFIX=""
NAME_SUFFIX=""
AUTO_NAME=""
MULTI=""

usage() {
    cat <<EOF
Usage: $0 --from-roadmap <phase/category> --theme <name> [options] --project-root <path>

Options:
  --from-roadmap    REQUIRED: phase_id/category_id (e.g., phase-1/arch-design)
  --theme           REQUIRED: roadmap theme name (must NOT contain shell metacharacters)
  --rationale       OPTIONAL: AI-drafted rationale (passed to brainstorm scaffold)
  --name-prefix     OPTIONAL: proposal name prefix (e.g., fix-audit-)
  --name-suffix     OPTIONAL: proposal name suffix (e.g., -rfc)
  --auto-name       OPTIONAL: generate timestamp-based unique proposal name
  --multi <count>   OPTIONAL: generate <count> sub-proposals from one theme
  --project-root    REQUIRED: absolute path to project root
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-roadmap) FROM_ROADMAP="$2"; shift 2 ;;
        --theme)        THEME="$2"; shift 2 ;;
        --rationale)    RATIONALE="$2"; shift 2 ;;
        --name-prefix)  NAME_PREFIX="$2"; shift 2 ;;
        --name-suffix)  NAME_SUFFIX="$2"; shift 2 ;;
        --auto-name)    AUTO_NAME="yes"; shift ;;
        --multi)        MULTI="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

if [[ -z "$FROM_ROADMAP" || -z "$THEME" || -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: --from-roadmap, --theme, --project-root are required" >&2
    usage
fi

if [[ -n "$MULTI" && ! "$MULTI" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: --multi must be a positive integer (got '$MULTI')" >&2
    exit 1
fi

export ADD_IMPROVE_FROM_ROADMAP="$FROM_ROADMAP"
export ADD_IMPROVE_THEME="$THEME"
export BRAINSTORM_RATIONALE_DRAFT="$RATIONALE"
export ADD_IMPROVE_NAME_PREFIX="$NAME_PREFIX"
export ADD_IMPROVE_NAME_SUFFIX="$NAME_SUFFIX"
export ADD_IMPROVE_AUTO_NAME="$AUTO_NAME"
export ADD_IMPROVE_MULTI="$MULTI"
export PROJECT_ROOT

cleanup() {
    unset ADD_IMPROVE_FROM_ROADMAP
    unset ADD_IMPROVE_THEME
    unset BRAINSTORM_RATIONALE_DRAFT
    unset ADD_IMPROVE_NAME_PREFIX
    unset ADD_IMPROVE_NAME_SUFFIX
    unset ADD_IMPROVE_AUTO_NAME
    unset ADD_IMPROVE_MULTI
}
trap cleanup EXIT

if ! python3 "$SCRIPT_DIR/from_roadmap.env.py" validate; then
    echo "ERROR: env-var validation failed" >&2
    exit 1
fi

# Brainstorm HARD-GATE (pre-create): when a draft for this proposal already
# exists, refuse to (re)create it until the draft satisfies the brainstorm
# HARD-GATE (5 sections + Why/What Changes + Acceptance checkboxes + 主题).
BRAINSTORM_CHECK="$SCRIPT_DIR/../../rdd-workflow-brainstorm/scripts/pre_create_brainstorm_check.sh"
PROPOSAL_FILE="$PROJECT_ROOT/.rddf/improvements/from-roadmap-${FROM_ROADMAP//\//-}.md"
if [[ -f "$PROPOSAL_FILE" ]] && ! bash "$BRAINSTORM_CHECK" "$PROPOSAL_FILE" --project-root "$PROJECT_ROOT"; then
    echo "ERROR: existing draft fails brainstorm HARD-GATE, run skill_use('rdd-workflow-brainstorm') first" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/from_roadmap.py"
