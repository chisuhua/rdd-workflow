#!/usr/bin/env bash
# skills/guide-design/scripts/check_theme_coverage_gate.sh
# Standalone theme coverage gate check for design-done phase.
#
# Usage:
#   bash check_theme_coverage_gate.sh <project_root>
#
# Exit codes:
#   0 — coverage gate passed (or skipped)
#   1 — coverage gate failed (uncovered themes with STRICT_PROPOSAL_COVERAGE=yes)
#   2 — missing dependencies / invalid args
#
# Environment:
#   STRICT_PROPOSAL_COVERAGE=yes  → upgrade to blocking
#   SKIP_PROPOSAL_COVERAGE=yes    → skip entire gate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $0 <project_root>" >&2
    exit 2
}

[[ $# -ge 1 ]] || usage

PROJECT_ROOT="$1"

[[ -d "$PROJECT_ROOT" ]] || {
    echo "ERROR: project_root not found: $PROJECT_ROOT" >&2
    exit 2
}

ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
[[ -f "$ROADMAP_FILE" ]] || ROADMAP_FILE="$PROJECT_ROOT/docs/roadmap.md"
[[ -f "$ROADMAP_FILE" ]] || {
    echo "ERROR: roadmap.md not found in $PROJECT_ROOT" >&2
    exit 2
}

IMPROVEMENTS_DIR="$PROJECT_ROOT/.rddf/improvements"
[[ -d "$IMPROVEMENTS_DIR" ]] || {
    echo "⚠️  No .rddf/improvements directory — no proposals to check"
    exit 0
}

COVERAGE_JSON=$(PROJECT_ROOT="$PROJECT_ROOT" \
    python3 "$SCRIPT_DIR/design_preflight.py" \
    "$PROJECT_ROOT" "$ROADMAP_FILE" "$IMPROVEMENTS_DIR" 2>/dev/null) || {
    echo "ERROR: design_preflight.py failed" >&2
    exit 2
}

TOTAL=$(echo "$COVERAGE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total_themes', 0))")
COVERED=$(echo "$COVERAGE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('covered', 0))")
UNCOVERED_LIST=$(echo "$COVERAGE_JSON" | python3 -c "import sys,json;print('\n'.join(json.load(sys.stdin).get('uncovered', [])))")
SKIPPED=$(echo "$COVERAGE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('skipped_count', 0))")
LEGACY=$(echo "$COVERAGE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('unmapped_legacy_count', 0))")

echo "📊 Roadmap 主题覆盖率:"
echo "   总主题: $TOTAL"
echo "   已覆盖: $COVERED"
echo "   已跳过 (~skipped~): $SKIPPED"
echo "   未标注主题 (legacy): $LEGACY"

if [[ "$TOTAL" -eq 0 ]]; then
    echo "✅ 无 roadmap 主题约束，跳过 coverage gate"
    exit 0
fi

if [[ -n "$UNCOVERED_LIST" ]]; then
    echo ""
    echo "📌 未覆盖主题:"
    echo "$UNCOVERED_LIST" | sed 's/^/   - /'
fi

if [[ "${SKIP_PROPOSAL_COVERAGE:-}" == "yes" ]]; then
    echo ""
    echo "⚠️  SKIP_PROPOSAL_COVERAGE=yes, coverage gate skipped"
    exit 0
fi

if [[ "${STRICT_PROPOSAL_COVERAGE:-}" == "yes" ]] && [[ -n "$UNCOVERED_LIST" ]]; then
    echo ""
    echo "❌ STRICT_PROPOSAL_COVERAGE=yes 但有未覆盖主题"
    echo "   选项:"
    echo "   1. 为未覆盖主题创建 proposal"
    echo "   2. 在 roadmap cell 末尾追加 '~skipped~' 显式跳过"
    echo "   3. 设置 SKIP_PROPOSAL_COVERAGE=yes 临时绕过"
    exit 1
fi

if [[ -n "$UNCOVERED_LIST" ]]; then
    echo ""
    echo "⚠️  coverage gate is warning only (set STRICT_PROPOSAL_COVERAGE=yes to enforce)"
fi

exit 0