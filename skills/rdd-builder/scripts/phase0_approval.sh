#!/usr/bin/env bash
# Phase 0: 5-option approval gate (auto-pick by default per 用户 UX 需求)
# - 1 approve: continue to Phase 1 plan gen (writes proposal.md + spec-delta per ADR-0025)
# - 2 reject / 3 defer / 4 revise: route via rddf feedback add (single-writer, per ADR-0037)
# - 5 dispatch-quick: NEW per ADR-0048; reads .planner-handoff.json::recommended_route;
#   creates .rddf/state/rdd-quick-context.json and delegates to skill_use("rdd-quick").
#
# 默认 auto-pick (per 用户 UX 需求 2026-09-10): AI 代理基于
# planner advisory + AC count 自动选择 1 或 5, 不需要用户输入.
# 仅在 RDDF_REQUIRE_USER_CONFIRM=yes 或低置信度场景下问用户.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

AUTO_APPROVE=0
DISPATCH_QUICK=0
REQUIRE_CONFIRM="${RDDF_REQUIRE_USER_CONFIRM:-no}"
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
        --dispatch-quick) DISPATCH_QUICK=1 ;;
        --require-confirm) REQUIRE_CONFIRM="yes" ;;
    esac
done
export AUTO_APPROVE DISPATCH_QUICK REQUIRE_CONFIRM

if [ -z "$CHANGE_NAME" ]; then
    echo "phase0_approval.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 0: Approval Gate for $CHANGE_NAME (auto-pick mode) ==="

# Read planner advisory (per ADR-0048 §Decision 3)
PLANNER_ROUTE="unknown"
if [ -f "$PROJECT_ROOT/.rddf/state/.planner-handoff.json" ]; then
    PLANNER_ROUTE=$(python3 -c "
import json
from pathlib import Path
p = Path('$PROJECT_ROOT/.rddf/state/.planner-handoff.json')
try:
    d = json.loads(p.read_text())
    print(d.get('recommended_route', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")
fi
echo "Planner advisory: recommended_route = $PLANNER_ROUTE"

# Count AC checkboxes in proposal.md (primary) or improvement file (fallback per ADR-0049)
AC_COUNT=0
PROPOSAL_FILE="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"
IMPROVEMENT_FILE="$PROJECT_ROOT/.rddf/improvements/$CHANGE_NAME.md"
if [ -f "$PROPOSAL_FILE" ]; then
    AC_COUNT=$(grep -cE '^- \[[ x]\]' "$PROPOSAL_FILE" 2>/dev/null || echo 0)
    AC_COUNT="${AC_COUNT:-0}"
    echo "AC count: $AC_COUNT (from proposal.md ## 验收标准)"
elif [ -f "$IMPROVEMENT_FILE" ]; then
    AC_COUNT=$(grep -cE '^- \[[ x]\]' "$IMPROVEMENT_FILE" 2>/dev/null || echo 0)
    AC_COUNT="${AC_COUNT:-0}"
    echo "AC count: $AC_COUNT (from .rddf/improvements/<change>.md ## Acceptance, primary per ADR-0049)"
fi

# Show 5-option context (always, for human review)
echo ""
echo "1) approve       2) reject       3) defer       4) revise       5) dispatch-quick"
if [ "$PLANNER_ROUTE" = "simple" ] && [ "$AC_COUNT" -le 2 ]; then
    echo "💡 Planner advisory=simple + AC ≤ 2 → option 5 (dispatch-quick) recommended"
fi
echo ""

# Decision logic (per 用户 UX 需求 + ADR-0049 + ADR-0050):
# - --auto-approve CLI flag → case 1 (existing)
# - --dispatch-quick CLI flag → case 5 (existing, still hard-validates recommended_route=simple)
# - RDDF_LLM_DECISION env var (NEW per ADR-0050 GAP-1 fix): AI 代理 LLM 推理结果
#     approve / dispatch-quick / reject / defer / revise → 强制 case X
#     ask-user → 强制 ASK USER (per SKILL.md 阶段 0.0.5 用户介入门控 5 条件)
#     auto → 用 bash 默认 auto-pick 逻辑
# - RDDF_REQUIRE_USER_CONFIRM=yes → ask user (per 用户 UX 需求)
# - DEFAULT auto-pick: advisory=simple + AC ≤ 2 → case 5; else → case 1
LLM_DECISION="${RDDF_LLM_DECISION:-auto}"
if [ "${AUTO_APPROVE:-0}" = "1" ]; then
    choice="1"
    echo "🤖 Auto-pick (--auto-approve CLI): option 1 (approve)"
elif [ "${DISPATCH_QUICK:-0}" = "1" ]; then
    if [ "$PLANNER_ROUTE" != "simple" ]; then
        echo "ERROR: --dispatch-quick requires recommended_route=simple, got $PLANNER_ROUTE" >&2
        exit 2
    fi
    choice="5"
    echo "🤖 Auto-pick (--dispatch-quick CLI): option 5 (dispatch-quick)"
elif [ "$LLM_DECISION" = "ask-user" ]; then
    # LLM signals low confidence (4 conditions per SKILL.md 阶段 0.0.5):
    # - planner advisory=unknown
    # - LLM assessment=unknown
    # - LLM 与 planner advisory 冲突
    # - LLM 检测到 complex + 与 advisory 不一致
    echo "🤔 LLM signals low confidence (RDDF_LLM_DECISION=ask-user) — asking user"
    echo "   Planner advisory: $PLANNER_ROUTE"
    read -r -p "Choose [1-5]: " choice
elif [ "$LLM_DECISION" = "approve" ]; then
    choice="1"
    echo "🤖 Auto-pick (LLM=approve): option 1 (approve)"
elif [ "$LLM_DECISION" = "dispatch-quick" ]; then
    if [ "$PLANNER_ROUTE" != "simple" ]; then
        echo "ERROR: LLM=dispatch-quick requires recommended_route=simple, got $PLANNER_ROUTE" >&2
        exit 2
    fi
    choice="5"
    echo "🤖 Auto-pick (LLM=dispatch-quick): option 5 (dispatch-quick)"
elif [ "$LLM_DECISION" = "reject" ]; then
    choice="2"
    echo "🤖 Auto-pick (LLM=reject): option 2 (reject)"
elif [ "$LLM_DECISION" = "defer" ]; then
    choice="3"
    echo "🤖 Auto-pick (LLM=defer): option 3 (defer)"
elif [ "$LLM_DECISION" = "revise" ]; then
    choice="4"
    echo "🤖 Auto-pick (LLM=revise): option 4 (revise)"
elif [ "$LLM_DECISION" != "auto" ]; then
    echo "ERROR: RDDF_LLM_DECISION must be approve|dispatch-quick|reject|defer|revise|ask-user|auto, got '$LLM_DECISION'" >&2
    exit 2
elif [ "$REQUIRE_CONFIRM" = "yes" ]; then
    # User explicitly requires confirmation
    echo "🤔 RDDF_REQUIRE_USER_CONFIRM=yes — asking user"
    read -r -p "Choose [1-5]: " choice
else
    # DEFAULT: auto-pick based on planner advisory + AC count (per 用户 UX 需求)
    if [ "$PLANNER_ROUTE" = "simple" ] && [ "$AC_COUNT" -le 2 ]; then
        choice="5"
        echo "🤖 Auto-pick (default): option 5 (dispatch-quick)"
        echo "   理由: advisory=simple + AC ≤ 2 → 走 rdd-quick 路径"
    else
        choice="1"
        echo "🤖 Auto-pick (default): option 1 (approve)"
        echo "   理由: advisory=$PLANNER_ROUTE, AC=$AC_COUNT → 走完整 P1-P3 路径"
    fi
    echo "   (如需用户介入, 设 RDDF_REQUIRE_USER_CONFIRM=yes)"
fi

case "$choice" in
    1)
        echo "approved"
        IMPROVEMENT_FILE="$PROJECT_ROOT/.rddf/improvements/$CHANGE_NAME.md"

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
        # Write builder handoff approval_status=approved
        python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_handoff import write_builder_handoff
from datetime import datetime, timezone
write_builder_handoff(
    project_root='$PROJECT_ROOT',
    change_name='$CHANGE_NAME',
    current_phase='phase-1',
    approval_status='approved',
)
print('builder-handoff v1.1: approval_status=approved written')
" || echo "(builder-handoff write deferred; non-blocking)"
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
    5)
        echo "dispatch-quick (per ADR-0048 §Decision 3)"
        if [ "$PLANNER_ROUTE" != "simple" ]; then
            echo "ERROR: dispatch-quick requires recommended_route=simple, got $PLANNER_ROUTE" >&2
            echo "HINT: User explicitly bypassed recommendation; continuing anyway" >&2
        fi

        NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

        # Read LLM dispatch_quick_review if present (per ADR-0049)
        # Warning-only; does NOT block dispatch (HARD pause = user is final decision)
        LLM_COMPLEXITY="unset"
        LLM_CONCERNS=""
        BUILDER_HANDOFF="$PROJECT_ROOT/.rddf/state/builder/$CHANGE_NAME.json"
        if [ -f "$BUILDER_HANDOFF" ]; then
            LLM_COMPLEXITY=$(python3 -c "
import json
try:
    with open('$BUILDER_HANDOFF') as f:
        d = json.load(f)
    review = d.get('dispatch_quick_review') or {}
    print(review.get('complexity_confirmed', 'unset'))
except Exception:
    print('unset')
" 2>/dev/null || echo "unset")
            if [ "$LLM_COMPLEXITY" = "complex" ]; then
                LLM_CONCERNS=$(python3 -c "
import json
try:
    with open('$BUILDER_HANDOFF') as f:
        d = json.load(f)
    review = d.get('dispatch_quick_review') or {}
    concerns = review.get('concerns', [])
    print('; '.join(concerns) if concerns else '(no concerns listed)')
except Exception:
    print('')
" 2>/dev/null || echo "")
                echo ""
                echo "⚠️  LLM hidden complexity check detected 'complex' (per ADR-0049)"
                echo "    Concerns: $LLM_CONCERNS"
                echo "    User already chose option 5; continuing per HARD pause contract"
                echo ""
            fi
        fi

        # Write rdd-quick-context.json (per ADR-0048 §Decision 3 + ADR-0049 LLM signal)
        python3 -c "
import json
from pathlib import Path
ctx = {
    'change_name': '$CHANGE_NAME',
    'proposal_path': 'openspec/changes/$CHANGE_NAME/proposal.md',
    'from_builder': True,
    'dispatched_at': '$NOW',
    'expected_outcome': 'completed',
    'planner_advisory': {
        'recommended_route': '$PLANNER_ROUTE',
        'rationale': 'planner-handoff.json::recommended_route at dispatch time',
    },
    'llm_advisory': {
        'complexity_confirmed': '$LLM_COMPLEXITY',
        'concerns': '$LLM_CONCERNS',
        'rationale': 'builder-handoff::dispatch_quick_review at dispatch time (per ADR-0049)',
    },
    'ac_count': $AC_COUNT,
}
out_path = Path('$PROJECT_ROOT') / '.rddf' / 'state' / 'rdd-quick-context.json'
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(ctx, indent=2))
print(f'rdd-quick-context.json written: {out_path}')
"

        # Write builder-handoff approval_status=dispatched_to_quick (per ADR-0048)
        python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_handoff import write_builder_handoff
write_builder_handoff(
    project_root='$PROJECT_ROOT',
    change_name='$CHANGE_NAME',
    current_phase='phase-0',
    approval_status='dispatched_to_quick',
    dispatch_quick_at='$NOW',
)
print('builder-handoff v1.1: approval_status=dispatched_to_quick written')
" || echo "(builder-handoff write deferred; non-blocking)"

        # Delegate to rdd-quick with --from-builder flag (per ADR-0048)
        echo ""
        echo "→ 委托 skill_use('rdd-quick') --from-builder"
        echo "  rdd-quick 完成后:"
        echo "    - completed  → 直接 openspec archive <change> --yes (跳过 P1-P3)"
        echo "    - escalated  → 回 P0 重新决策 (用户选 1-4)"
        echo "    - unverified → 回 P0 重新决策 (用户选 1-4)"
        echo ""
        # Emit a marker for the orchestrator to detect; do NOT invoke skill_use directly
        # (must be done by the AI agent in its prose context per skill architecture)
        echo "DISPATCH_TO_QUICK=1 CHANGE_NAME=$CHANGE_NAME"
        exit 0
        ;;
    *)
        echo "invalid choice" >&2
        exit 2
        ;;
esac