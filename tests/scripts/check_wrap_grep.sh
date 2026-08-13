#!/usr/bin/env bash
# Spec 2026-08-13 §6 grep regression guard.
# Verifies that all 4 phase entry scripts wrap every direct binary
# invocation via orchestrator_run, and install an EXIT trap for
# orchestrator_finalize. Exits 0 on pass, 1 on violation.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS=(
    "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh"
    "$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh"
    "$REPO_ROOT/skills/guide-ship/scripts/ship_env_check.sh"
    "$REPO_ROOT/skills/execute/scripts/select_worktree.sh"
)

# Positive list of binaries that should be wrapped via orchestrator_run.
# Adding a new binary invocation to any entry script? Add it here too.
WRAPPABLE_BINARIES='git|ls|python3|python|jq|grep|cat|bash|sh|find|awk|sed|cp|mv|rm|mkdir|sleep|head|tail|wc|tr|sort|xargs|env|date|chmod|tar|curl|wget'

violations=0
for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo "MISSING: $script"
        violations=$((violations + 1))
        continue
    fi
    hits=$(grep -nE "^\s*($WRAPPABLE_BINARIES)\s" "$script" \
        | grep -v orchestrator_run \
        | grep -v '^[^:]*:#' \
        || true)
    if [ -n "$hits" ]; then
        echo "UNWRAPPED in $script:"
        echo "$hits" | sed 's/^/  /'
        violations=$((violations + 1))
    fi
    if ! grep -q "trap 'orchestrator_finalize' EXIT" "$script"; then
        echo "MISSING EXIT trap in $script"
        violations=$((violations + 1))
    fi
done

if [ "$violations" -gt 0 ]; then
    echo ""
    echo "$violations violation(s). See spec 2026-08-13 §6."
    exit 1
fi
echo "OK: all 4 entry scripts pass grep rule + EXIT trap check."
