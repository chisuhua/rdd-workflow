#!/usr/bin/env bash
# skills/add-improve/scripts/from_issue.sh
# Bash entry for `add-improve --from-issue` mode (Oracle C1 env-var pattern).
#
# Usage:
#   bash from_issue.sh --from-issue <N> [--gh-repo <owner/repo>] \
#                       --title "<title>" \
#                       [--body "<body>"] \
#                       --project-root <path>
#
# Behavior:
#   1. Parses CLI args into env-vars (ADD_IMPROVE_FROM_ISSUE, ...)
#   2. If --gh-repo is unset, calls gh_repo_detect via fallback chain
#   3. Calls from_issue.env.py validate to reject shell metacharacters
#   4. Calls from_issue.py to write proposal scaffold
#   5. Unsets env-vars on exit (cleanup)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ISSUE=""
GH_REPO=""
TITLE=""
BODY=""
PROJECT_ROOT=""

usage() {
    cat <<EOF
Usage: $0 --from-issue <N> --title <title> [--gh-repo <owner/repo>] [--body <body>] --project-root <path>

Options:
  --from-issue    REQUIRED: issue number (positive integer)
  --gh-repo       OPTIONAL: owner/repo (default: detected via gh_repo_detect chain)
  --title         REQUIRED: issue title
  --body          OPTIONAL: issue body (truncated to 4000 chars upstream)
  --project-root  REQUIRED: absolute path to project root
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-issue)   ISSUE="$2"; shift 2 ;;
        --gh-repo)      GH_REPO="$2"; shift 2 ;;
        --title)        TITLE="$2"; shift 2 ;;
        --body)         BODY="$2"; shift 2 ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

if [[ -z "$ISSUE" || -z "$TITLE" || -z "$PROJECT_ROOT" ]]; then
    echo "ERROR: --from-issue, --title, --project-root are required" >&2
    usage
fi

# Default gh_repo via detection chain when --gh-repo omitted
if [[ -z "$GH_REPO" ]]; then
    GH_REPO=$(PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}" python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from _lib.gh_repo_detect import detect_gh_repo
print(detect_gh_repo())
" 2>/dev/null) || {
        echo "ERROR: --gh-repo not provided and gh_repo_detect failed. Try: --gh-repo owner/repo" >&2
        exit 1
    }
fi

export ADD_IMPROVE_FROM_ISSUE="$ISSUE"
export ADD_IMPROVE_GH_REPO="$GH_REPO"
export ADD_IMPROVE_ISSUE_TITLE="$TITLE"
export ADD_IMPROVE_ISSUE_BODY="$BODY"
export PROJECT_ROOT

cleanup() {
    unset ADD_IMPROVE_FROM_ISSUE
    unset ADD_IMPROVE_GH_REPO
    unset ADD_IMPROVE_ISSUE_TITLE
    unset ADD_IMPROVE_ISSUE_BODY
}
trap cleanup EXIT

if ! python3 "$SCRIPT_DIR/from_issue.env.py" validate; then
    echo "ERROR: env-var validation failed" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/from_issue.py"
