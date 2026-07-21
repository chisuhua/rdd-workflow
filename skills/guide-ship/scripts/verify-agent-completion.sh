#!/usr/bin/env bash
# verify-agent-completion.sh
# Verify agent completion contract: archive dir, iteration sync, worktree cleanup.
# Usage: verify-agent-completion.sh <change_name> [project_root]

set -euo pipefail

CHANGE_NAME="${1:?change_name required}"
PROJECT_ROOT="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
FAILURES=0

check_contract_archive() {
    if [ -d "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/archive" ]; then
        echo "  ✅ Contract 1: Archive directory exists"
        return 0
    else
        echo "  ❌ Contract 1: Archive directory missing"
        return 1
    fi
}

check_contract_iteration() {
    if python3 -c "
import json, sys
with open('$PROJECT_ROOT/.rddf/state/iteration.json') as f:
    data = json.load(f)
changes = data.get('changes', data.get('changes', []))
if isinstance(changes, dict):
    change = changes.get('$CHANGE_NAME', {})
else:
    change = next((c for c in changes if c.get('name') == '$CHANGE_NAME'), {})
if change.get('archived_at'):
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null; then
        echo "  ✅ Contract 2: iteration.json synced (archived_at present)"
        return 0
    else
        echo "  ❌ Contract 2: iteration.json missing archived_at"
        return 1
    fi
}

check_contract_worktree() {
    if git -C "$PROJECT_ROOT" worktree list 2>/dev/null | grep -q "$CHANGE_NAME"; then
        echo "  ❌ Contract 3: Worktree still exists"
        return 1
    else
        echo "  ✅ Contract 3: Worktree deleted"
        return 0
    fi
}

auto_fix_worktree() {
    echo "  🔧 Auto-fix: Removing worktree..."
    local wt_path
    wt_path=$(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null | grep -B1 "$CHANGE_NAME" | head -1 | awk '{print $2}')
    if [ -n "$wt_path" ] && [ -d "$wt_path" ]; then
        git -C "$PROJECT_ROOT" worktree remove "$wt_path" --force 2>/dev/null || true
        rm -rf "$wt_path" 2>/dev/null || true
        echo "  ✅ Worktree removed"
    fi
}

auto_fix_iteration() {
    echo "  🔧 Auto-fix: Patching iteration.json..."
    python3 -c "
import json, os
path = '$PROJECT_ROOT/.rddf/state/iteration.json'
with open(path) as f:
    data = json.load(f)
changes = data.get('changes', [])
if isinstance(changes, list):
    for c in changes:
        if c.get('name') == '$CHANGE_NAME':
            c['archived_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
            break
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null && echo "  ✅ iteration.json patched"
}

check_contract_archive || { FAILURES=$((FAILURES+1)); }
check_contract_iteration || { FAILURES=$((FAILURES+1)); auto_fix_iteration; }
check_contract_worktree || { FAILURES=$((FAILURES+1)); auto_fix_worktree; }

if [ "$FAILURES" -eq 0 ]; then
    echo "✅ All 3 contracts passed"
    exit 0
else
    echo "⚠️  $FAILURES contract(s) failed - auto-fix attempted"
    exit 1
fi
