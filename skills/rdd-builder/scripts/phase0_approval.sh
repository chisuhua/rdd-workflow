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
export AUTO_APPROVE DISPATCH_QUICK REQUIRE_CONFIRM REPO_ROOT

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
        CHANGE_DIR="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME"

        REGISTER_CHANGE=0
        if [ -f "$IMPROVEMENT_FILE" ]; then
            # Only a change that actually got created may be registered — an
            # orphan iteration entry for a non-existent change dir is exactly
            # the phantom that store.set_deps_info warns about.
            REGISTER_CHANGE=1
            # Create the change dir only when there is something to write:
            # an unconditional mkdir leaves an empty openspec/changes/<name>/
            # behind whenever the improvement is missing (test pollution).
            mkdir -p "$CHANGE_DIR"

            # ⚠ **delta 先于 proposal 生成**（2026-11-27）：delta 的形态守卫会在**退化形态**时
            # 拒绝生成 ⇒ 若先写 proposal 再写 delta，守卫拒绝时会留下「有 proposal、无 delta」
            # 的半成品态（AC14）。先跑 delta ⇒ 拒绝时两个产物都不落盘。
            #
            # ⚠ **临时文件 + 成功后 mv**（AC14）：`> "$FILE"` 的**重定向先于 python 执行**
            # ⇒ 生成失败时留下**零长度文件** ⇒ 幂等检查 `[ ! -f "$FILE" ]` 为假
            # ⇒ 后续重试**永久静默跳过**该产物的生成。
            #
            # D3 spec-delta 的落点目录：声明了 `**delta**: modified <capability>` ⇒
            # `specs/<capability>/`（design D-3；openspec 的 delta 以 capability 为单位）；
            # 未声明 ⇒ 保持历史形态 `specs/<change-name>/`（**新旧并存**，既有 change 不迁）。
            TARGET_CAP=""
            if [ -f "$IMPROVEMENT_FILE" ]; then
                TARGET_CAP=$(OUTPUT_MODE=target-capability CHANGE_NAME="$CHANGE_NAME" \
                    IMPROVEMENTS_PATH="$IMPROVEMENT_FILE" \
                    python3 "$SCRIPT_DIR/generate_full_proposal.py" 2>/dev/null || true)
            fi
            DELTA_DIR="$CHANGE_DIR/specs/${TARGET_CAP:-$CHANGE_NAME}"
            DELTA_FILE="$DELTA_DIR/spec.md"
            if [ ! -f "$DELTA_FILE" ] && [ -f "$IMPROVEMENT_FILE" ]; then
                mkdir -p "$DELTA_DIR"
                DELTA_TMP="$DELTA_FILE.tmp"
                DELTA_ERR="$(mktemp)"
                DELTA_RC=0
                OUTPUT_MODE=spec-delta CHANGE_NAME="$CHANGE_NAME" \
                    IMPROVEMENTS_PATH="$IMPROVEMENT_FILE" PROJECT_ROOT="$PROJECT_ROOT" \
                    python3 "$SCRIPT_DIR/generate_full_proposal.py" > "$DELTA_TMP" 2>"$DELTA_ERR" || DELTA_RC=$?
                if [ "$DELTA_RC" -eq 3 ]; then
                    # **未声明 delta**（opt-in）⇒ 跳过，不算失败：没有 delta 就没有退化 delta。
                    rm -f "$DELTA_TMP" "$DELTA_ERR"
                    echo "ℹ️  未声明 **delta** ⇒ 不生成 spec delta（如需 delta 请提供 **delta** + **语义要求**）"
                elif [ "$DELTA_RC" -ne 0 ]; then
                    cat "$DELTA_ERR" >&2
                    rm -f "$DELTA_TMP" "$DELTA_ERR"
                    echo "❌ delta 生成失败 ⇒ 已清理临时文件（不留空文件、不留半成品、可重试）" >&2
                    exit 1
                else
                    rm -f "$DELTA_ERR"
                    mv "$DELTA_TMP" "$DELTA_FILE"
                    echo "✅ D3 spec-delta written: $DELTA_FILE"
                fi
            fi

            CHANGE_NAME="$CHANGE_NAME" IMPROVEMENTS_PATH="$IMPROVEMENT_FILE" \
                PROJECT_ROOT="$PROJECT_ROOT" \
                python3 "$SCRIPT_DIR/generate_full_proposal.py" > "$PROPOSAL_FILE.tmp" || {
                rm -f "$PROPOSAL_FILE.tmp"
                echo "❌ proposal 生成失败 ⇒ 已清理临时文件（不留半成品、可重试）" >&2
                exit 1
            }
            mv "$PROPOSAL_FILE.tmp" "$PROPOSAL_FILE"
            echo "✅ proposal.md populated from improvement 5-段 content"
        else
            echo "⚠️  $IMPROVEMENT_FILE not found; leaving proposal.md as skeleton"
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

        # Register the change in iteration.json.
        #
        # The archive-side sync (sync_iteration_after_archive /
        # force_mark_archived) only UPDATES existing entries — nothing ever
        # CREATED them, so a change was invisible to `rddf status` /
        # `rddf feature` / deps until someone hand-edited the JSON.
        # store.set_status creates the entry when it is missing and keeps the
        # other fields of an existing one (idempotent).
        #
        # Non-blocking by design: a missing / unreadable / locked
        # iteration.json must not fail the approval, and a MISSING file must
        # not be created half-baked (the archive-side sync will pick the
        # change up if it ever appears).
        PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$CHANGE_NAME" \
        REGISTER_CHANGE="$REGISTER_CHANGE" python3 - <<'PYEOF'
import os, sys
root = os.environ["PROJECT_ROOT"]
name = os.environ["CHANGE_NAME"]
sys.path.insert(0, os.environ["REPO_ROOT"])
if os.environ.get("REGISTER_CHANGE", "0") != "1":
    sys.exit(0)
try:
    from skills._lib.iteration import store
except Exception as exc:
    print(f"⚠️  phase0: iteration store unavailable ({exc}) — change not registered", file=sys.stderr)
    sys.exit(0)

iter_path = os.path.join(root, ".rddf", "state", "iteration.json")
if not os.path.isfile(iter_path):
    print("⚠️  phase0: iteration.json not found — change not registered", file=sys.stderr)
    sys.exit(0)

# Detect corruption BEFORE writing. store.load() does NOT raise on a corrupt
# file: it backs it up and returns an empty document — writing into that would
# overwrite the corrupt file with a single-entry document and silently drop
# every other change from the status views. The read-only verbose reader
# distinguishes missing / invalid JSON / schema-invalid without side effects.
data, err = store._read_unlocked_verbose(iter_path)
if err:
    print(f"⚠️  phase0: iteration.json is invalid ({err}) — change not registered",
          file=sys.stderr)
    sys.exit(0)

existing = next((c for c in data.get("changes", []) if c.get("name") == name), None)
if existing is not None and existing.get("status") not in (None, "", "planned"):
    # Never downgrade an entry that is already under way (in_worktree /
    # review / completed / archived) — a re-approve must not resurrect it.
    print(f"✅ already registered in iteration.json: {name} "
          f"(status={existing.get('status')}) — left untouched")
    sys.exit(0)

try:
    data = store.set_status(data, name, "proposed")
    store.save(root, data)
except Exception as exc:
    print(f"⚠️  phase0: registering the change in iteration.json failed ({exc})", file=sys.stderr)
    sys.exit(0)
print(f"✅ registered in iteration.json: {name}")
PYEOF
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
    'proposal_path': 'openspec/changes/$CHANGE_NAME/proposal.md',  # isolation-ok: 记录的是相对路径描述字段，本脚本不据此做 IO
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
from _lib.builder_handoff import update_builder_handoff
# Merge, not overwrite: the dispatch_quick_review written just above must
# survive (a full write drops it along with every other phase's fields).
update_builder_handoff(
    '$PROJECT_ROOT',
    '$CHANGE_NAME',
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