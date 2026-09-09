#!/usr/bin/env bash
# Phase 0: 4-option approval gate (HARD pause).
# Reject/defer/revise routes via rddf feedback add (single-writer contract, per ADR-0037).
# Approve triggers D3 spec-delta generation per ADR-0025 (inline Python helper, decoupled from guide-design).
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

AUTO_APPROVE=0
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
    esac
done
export AUTO_APPROVE

if [ -z "$CHANGE_NAME" ]; then
    echo "phase0_approval.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 0: Approval Gate for $CHANGE_NAME ==="

echo "1) approve  2) reject  3) defer  4) revise"
if [ "${AUTO_APPROVE:-0}" = "1" ]; then
    choice="1"
else
    read -r -p "Choose [1-4]: " choice
fi

case "$choice" in
    1)
        echo "approved"
        IMPROVEMENT_FILE="$PROJECT_ROOT/.rddf/improvements/$CHANGE_NAME.md"
        PROPOSAL_FILE="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"

        if [ -f "$IMPROVEMENT_FILE" ]; then
            CHANGE_NAME="$CHANGE_NAME" IMPROVEMENTS_PATH="$IMPROVEMENT_FILE" \
                python3 "$SCRIPT_DIR/generate_full_proposal.py" \
                > "$PROPOSAL_FILE"
            echo "✅ proposal.md populated from improvement 5-段 content"
        else
            echo "⚠️  $IMPROVEMENT_FILE not found; leaving proposal.md as skeleton"
        fi

        SPECS_DIR="$PROJECT_ROOT/openspec/specs/$CHANGE_NAME"
        mkdir -p "$SPECS_DIR"
        SPEC_FILE="$SPECS_DIR/spec.md"
        if [ ! -f "$SPEC_FILE" ]; then
            python3 <<PYEOF
import sys
from pathlib import Path
specs_dir = Path("$SPECS_DIR")
specs_dir.mkdir(parents=True, exist_ok=True)
spec_md = specs_dir / "spec.md"
if not spec_md.exists():
    spec_md.write_text("""## ADDED Requirements

### Requirement: $CHANGE_NAME
Auto-derived from .rddf/improvements/$CHANGE_NAME.md per ADR-0025 D1/D2 + rdd-builder Phase 0 approve.
""")
print(f"D3 spec-delta written: {spec_md}")
PYEOF
        fi
        exit 0
        ;;
    2)
        echo "rejected"
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind rejected --body "Rejected in Phase 0" || echo "(feedback add deferred)"
        exit 0
        ;;
    3)
        echo "deferred"
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind blocked --body "Deferred in Phase 0" || echo "(feedback add deferred)"
        exit 0
        ;;
    4)
        echo "revising"
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind needs-revision --body "Revision requested in Phase 0" || echo "(feedback add deferred)"
        exit 1
        ;;
    *)
        echo "invalid choice" >&2
        exit 2
        ;;
esac