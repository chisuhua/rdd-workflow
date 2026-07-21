# skills/propose/scripts/propose_quality_hook.sh
# Bash wrapper for propose_quality_hook.py (Phase 4 quality check).
# Env-var only passing (Oracle C1 safe). No bash string interpolation.

invoke_propose_quality_hook() {
    local CHANGE_NAME="$1"
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
    PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

    CHANGE_NAME="$CHANGE_NAME" PROJECT_ROOT="$PROJECT_ROOT" \
        python3 "$SCRIPT_DIR/propose_quality_hook.py"
}
