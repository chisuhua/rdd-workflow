#!/usr/bin/env bash
# roadmap validate-fragments: gate subcommand (exit 0/1/2/3 aligned with openspec validate).
# Per add-hierarchical-roadmap-structure (additive to skills/roadmap/ skill).
#
# Exit codes:
#   0 = no issues / only warnings
#   1 = CRITICAL errors (or STRICT mode escalates warnings)
#   2 = misconfiguration / bad input
#   3 = internal error
#
# Environment:
#   SKIP_ROADMAP_REFS_GATE=yes   → skip validation, print "gate skipped" warning, exit 0
#   STRICT_ROADMAP_REFS_GATE=yes → escalate WARNING → CRITICAL (blocks plan-done)
#   RDDF_PROJECT_ROOT=<path>     → project root (default: git toplevel or cwd)
#
# Usage:
#   roadmap-validate-fragments
#   STRICT_ROADMAP_REFS_GATE=yes roadmap-validate-fragments
#   SKIP_ROADMAP_REFS_GATE=yes roadmap-validate-fragments

set -uo pipefail

PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_ROOT"

if [ "${SKIP_ROADMAP_REFS_GATE:-no}" = "yes" ]; then
    echo "⚠️  Gate skipped (SKIP_ROADMAP_REFS_GATE=yes)"
    exit 0
fi

# Run Python validation
ERRORS_JSON=$(python3 - <<PYEOF
import json, sys
sys.path.insert(0, '${PROJECT_ROOT}')
from _lib.roadmap_validate import validate_fragment_refs
errs = validate_fragment_refs('${PROJECT_ROOT}')
print(json.dumps([{
    "rule": e.rule,
    "fragment_id": e.fragment_id,
    "message": e.message,
    "severity": e.severity,
} for e in errs]))
PYEOF
) || { echo "❌ validate_fragment_refs failed to run" >&2; exit 3; }

# Parse + render
STRICT="${STRICT_ROADMAP_REFS_GATE:-no}"
python3 - <<PYEOF
import json, os, sys
errs = json.loads('''$ERRORS_JSON''')
strict = os.environ.get('STRICT_ROADMAP_REFS_GATE', 'no') == 'yes'
critical = [e for e in errs if e['severity'] == 'CRITICAL']
warning = [e for e in errs if e['severity'] == 'WARNING']

# STRICT mode: warnings → critical
if strict:
    promoted = [{**e, 'severity': 'CRITICAL'} for e in warning]
    critical.extend(promoted)
    warning = []

for e in errs:
    print(f"[{e['severity']}] {e['rule']} {e['fragment_id']}: {e['message']}")

if critical:
    print(f"\n❌ {len(critical)} CRITICAL errors (strict={strict})")
    sys.exit(1)
elif warning:
    print(f"\n⚠️  {len(warning)} warnings (set STRICT_ROADMAP_REFS_GATE=yes to upgrade)")
    sys.exit(0)
else:
    print("\n✅ All checks passed")
    sys.exit(0)
PYEOF
