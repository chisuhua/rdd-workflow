#!/usr/bin/env bash
# skills/guide-design/scripts/design_approve_batch.sh
# Per design-approve-batch-tool proposal.
#
# Usage:
#   bash skills/guide-design/scripts/design_approve_batch.sh --changes <c1,c2,...> [--dry-run]
#   bash skills/guide-design/scripts/design_approve_batch.sh <c1> <c2> ...
#
# Env vars (passed to Python via env-var, per Oracle C1):
#   PROJECT_ROOT, CHANGES (comma-separated), DRY_RUN
#
# Behavior:
#   1. Generate proposal.md drafts for each change (to /tmp/proposal-drafts/<name>.md)
#   2. Print all drafts for review
#   3. Ask user y/N confirmation
#   4. On y: invoke approve_proposal.sh for each change (idempotent — skips already created)
#   5. On n: skip all (don't break any change)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
DRAFT_DIR="${TMPDIR:-/tmp}/proposal-drafts"

# Parse args
DRY_RUN="no"
CHANGES=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --changes)
            # Split comma-separated value into individual changes
            IFS=',' read -ra parts <<< "${2:?need value}"
            for p in "${parts[@]}"; do
                CHANGES+=("$p")
            done
            shift 2
            ;;
        --dry-run) DRY_RUN=yes; shift ;;
        --help|-h)
            echo "Usage: $0 [--changes <c1,c2,...>] [--dry-run]"
            echo "       $0 <change1> [change2 ...]"
            exit 0
            ;;
        -*) echo "unknown option: $1" >&2; exit 1 ;;
        *)  CHANGES+=("$1"); shift ;;
    esac
done

if [ "${#CHANGES[@]}" -eq 0 ]; then
    echo "❌ no changes specified (use --changes or positional args)" >&2
    exit 1
fi

# Filter: skip already-created changes (idempotent)
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
TO_APPROVE=()
SKIPPED=()
for change in "${CHANGES[@]}"; do
    if [ -d "$PROJECT_ROOT/openspec/changes/$change" ]; then
        SKIPPED+=("$change")
    else
        TO_APPROVE+=("$change")
    fi
done

if [ "${#SKIPPED[@]}" -gt 0 ]; then
    echo "�️  skipped (already created): ${SKIPPED[*]}"
fi

if [ "${#TO_APPROVE[@]}" -eq 0 ]; then
    echo "✅ all changes already created, nothing to do"
    exit 0
fi

# Generate drafts
mkdir -p "$DRAFT_DIR"
echo "📝 generating drafts to $DRAFT_DIR/ ..."
for change in "${TO_APPROVE[@]}"; do
    draft="$DRAFT_DIR/$change.md"
    if CHANGE_NAME="$change" \
       IMPROVEMENTS_PATH="$PROJECT_ROOT/.rddf/improvements/$change.md" \
       python3 "$SCRIPT_DIR/generate_full_proposal.py" > "$draft" 2>/dev/null; then
        echo "  ✅ $change → $draft"
    else
        echo "  ❌ $change failed to generate (missing improvement file?)" >&2
        exit 1
    fi
done

if [ "$DRY_RUN" = "yes" ]; then
    echo ""
    echo "[DRY-RUN] would approve ${#TO_APPROVE[@]} changes: ${TO_APPROVE[*]}"
    echo "  drafts available at $DRAFT_DIR/"
    exit 0
fi

# Ask user confirmation
echo ""
echo "━━━ generated drafts for ${#TO_APPROVE[@]} change(s) ━━━"
for change in "${TO_APPROVE[@]}"; do
    echo ""
    echo "### $change (preview, first 30 lines) ###"
    head -30 "$DRAFT_DIR/$change.md"
done
echo ""
echo "accept and approve all? [y/N]: "
read -r user_reply

case "${user_reply:-N}" in
    y|Y|yes|YES)
        echo "✅ approved, invoking approve_proposal.sh ..."
        ;;
    *)
        echo "⏭️  rejected, no changes were modified"
        echo "  drafts preserved at $DRAFT_DIR/ for inspection"
        exit 0
        ;;
esac

# Approve each
failed=0
for change in "${TO_APPROVE[@]}"; do
    echo "→ approving: $change"
    if DESIGN_PROPOSAL_AUTO_ACCEPT=yes \
       bash "$SCRIPT_DIR/approve_proposal.sh" "$change" 2>&1 | tail -3; then
        :
    else
        echo "  ❌ failed to approve $change" >&2
        failed=$((failed + 1))
    fi
done

if [ "$failed" -gt 0 ]; then
    echo ""
    echo "� $failed change(s) failed to approve"
    exit 1
fi

echo ""
echo "✅ all ${#TO_APPROVE[@]} change(s) approved and committed"