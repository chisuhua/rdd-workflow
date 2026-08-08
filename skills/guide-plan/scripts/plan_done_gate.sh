#!/usr/bin/env bash
# _lib/plan_done_gate.sh — extracted from guide-plan.md L518-L677
# Exports:
#   - run_plan_done_gate() — Triple-gate validation (Gate 0/1/2)
#   - write_plan_handoff() — Write .rddf/state/.plan-handoff.json
#
# Triple-gate:
#   Gate 0: Ready-for-ship changes count (delegates to iteration.list_ready_for_ship)
#   Gate 1: Active changes count >= 1
#   Gate 2: All changes' artifacts (proposal.md, design.md, tasks.md) committed
#
# Honors env vars:
#   - SKIP_GATE_0=yes — skip Gate 0 (Deps AI reorganization accepted)
#   - GUIDE_PLAN_DEPS_CHOICE=1 — accept Deps AI suggestions (same as SKIP_GATE_0)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

run_plan_done_gate() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  echo "=== Plan 阶段 - 门控检查 ==="
  echo ""

  # v2.0.1: Deps §5e 重组建议回显 (仅参考, 不阻断)
  # External SKIP_GATE_0 env var takes priority (bash expands RHS before local shadowing)
  local SKIP_GATE_0="${SKIP_GATE_0:-false}"
  local DEPS_OUTPUT="$PROJECT_ROOT/.rddf/state/.deps-output.md"
  [ ! -f "$DEPS_OUTPUT" ] && DEPS_OUTPUT="$PROJECT_ROOT/.rddf/state/deps-output.md"
  if [ -f "$DEPS_OUTPUT" ]; then
      local SUGGESTIONS FALLBACK_MARKER dep_choice
      SUGGESTIONS=$(awk '/^## 🧠 AI 分析建议/,/^## [^🧠]|^---/' "$DEPS_OUTPUT" 2>/dev/null \
                    | grep -E "^- \`.*\`: (split|merge|reorder)" || true)
      FALLBACK_MARKER=$(grep -c "AI 语义分析未启用" "$DEPS_OUTPUT" 2>/dev/null || true)

      if [ -n "$SUGGESTIONS" ] && [ "${FALLBACK_MARKER:-0}" -eq 0 ]; then
          echo ""
          echo "⚠️  Deps AI 重组建议（仅参考不阻断 plan-done）:"
          echo "$SUGGESTIONS" | sed 's/^/  /'
          echo ""
          echo "请选择:"
          echo "  1. 接受建议 → 跳过 plan-done, 回到 propose 阶段手动处理"
          echo "  2. 忽略建议 → 继续 plan-done [默认]"
          dep_choice="${GUIDE_PLAN_DEPS_CHOICE:-2}"
          case "$dep_choice" in
              1) echo "→ 用户选择接受建议, 跳过 plan-done"
                  SKIP_GATE_0=true ;;
              2) echo "→ 用户选择忽略建议, 继续 plan-done" ;;
              *) echo "→ 无效选择 '$dep_choice', 默认忽略" ;;
          esac
      elif [ "${FALLBACK_MARKER:-0}" -gt 0 ]; then
          echo ""
          echo "ℹ️  AI 语义分析未启用 (fallback) - 跳过 §5e 重组建议检查"
      fi
  fi
  echo ""

  # 门控 0: Ready-for-ship changes 数量检查
  echo "门控 0: Ready-for-ship changes 数量检查 (proposed + 无活跃 blocker)"
  if [ "${SKIP_GATE_0:-false}" = "true" ] || [ "${SKIP_GATE_0}" = "true" ]; then
      echo "  ⏭️  跳过（用户接受 deps 重组建议）"
      echo ""
      export PLAN_GATE_0_SKIPPED="true"
      return 0
  fi

  local PROPOSED_COUNT
  # Filesystem scan (matches Gate 1): count active changes directly.
  # Avoids stale data from iteration.json accumulating after archive operations.
  PROPOSED_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]' || echo 0)
  echo "  ready-for-ship (proposed + blocker cleared): $PROPOSED_COUNT"
  if [ "${PROPOSED_COUNT:-0}" -eq 0 ]; then
      echo "  ❌ 失败: 至少需要 1 个 ready-for-ship change 才能交接给 guide-ship"
      echo "     使用 fill 阶段将 planned change 升级，或在 propose 阶段创建完整 change"
      return 1
  fi
  echo "  ✅ 通过"
  echo ""

  # 门控 1: 至少 1 个 active change
  local CHANGE_COUNT
  CHANGE_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')
  echo "门控 1: Active changes 数量检查"
  echo "  当前活跃 changes: $CHANGE_COUNT"
  if [ "$CHANGE_COUNT" -eq 0 ]; then
      echo "  ❌ 失败: 至少需要 1 个 active change"
      echo "     请回到 propose 阶段创建 change"
      return 1
  fi
  echo "  ✅ 通过"
  echo ""

  # 门控 2: 所有 change 的三个 artifacts 已提交
  echo "门控 2: Artifacts 提交性检查"
  # 把循环放在子 shell 里,避免污染调用者的 cwd;再用 $? 拿子 shell 的退出码决定是否拒绝。
  if (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
      [ -d "$d" ] || continue
      case "$d" in */archive/) continue ;; esac
      name=$(basename "$d")
      for artifact in proposal.md design.md tasks.md; do
          if ! git show HEAD:"$d$artifact" > /dev/null 2>&1; then
              echo "  ❌ $name missing committed $artifact — refuse to exit plan-side"
              exit 1   # subshell exit, not function exit
          fi
      done
  done); then
      echo "  ✅ 所有 change 的 artifacts 已提交"
  else
      echo "❌ 失败: 存在未提交 artefacts"
      echo "     请回到 propose 阶段完成 artifacts 创建并提交"
      return 1
  fi
  echo ""

  # ── reflect_engine(plan): post-gate reflection hook ──
  # Non-blocking: failures here never affect the gate decision.
  # Plan phase triggers when the same root cause appears >= 2 times.
  if [ "${SKIP_WORKFLOW_REFLECTION:-}" != "1" ]; then
    PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import os, sys, json
root = os.environ.get('PROJECT_ROOT', '.')
sys.path.insert(0, root)
try:
    from skills._lib.reflect_engine import ReflectEngine
    failures = []
    event_log_path = os.path.join(root, '.rddf', 'state', 'event_log.json')
    if os.path.isfile(event_log_path):
        with open(event_log_path) as f:
            events = json.load(f)
        for ev in events[-20:]:
            if ev.get('type') == 'gate_fail' and ev.get('gate') == 'plan-done':
                failures.append(ev)
    engine = ReflectEngine(phase='plan', project_root=root, timeout=10)
    result = engine.analyze(failures=failures)
    if result.action == 'propose_issue':
        print(f'🔍 Reflect: Detected {len(failures)} plan-done failures.')
        print(f'   Fingerprint: {result.fingerprint}')
except Exception:
    pass  # non-blocking
" 2>/dev/null || true
  fi
}

write_plan_handoff() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  # Warn if proposal-approved.md has uncommitted changes (soft, no block).
  # Catches plan-phase commits that dropped the design-phase write.
  if command -v git >/dev/null 2>&1; then
    local DIRTY
    DIRTY=$(cd "$PROJECT_ROOT" && git status --porcelain proposal-approved.md 2>/dev/null || true)
    if [ -n "$DIRTY" ]; then
      echo "⚠️ proposal-approved.md has uncommitted changes — commit before plan-done" >&2
    fi
  fi

  # Spec-validation gate: validate every active change's baseline + delta targets
  # before writing the handoff file. Catches v1 (false baseline) and v2
  # (MODIFIED-on-empty-spec) class incidents at plan-done time, NOT archive time.
  local VALIDATION_FAILED=0
  for d in "$PROJECT_ROOT"/openspec/changes/*/; do
      [ -d "$d" ] || continue
      case "$d" in */archive/) continue ;; esac
      local name
      name=$(basename "$d")
      source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
      local PROPOSE_DIR
      PROPOSE_DIR="$(resolve_rdd_skill_dir propose)"
      local RDD_LIB_DIR
      RDD_LIB_DIR="$(resolve_rdd_lib_dir)"
      if [ -f "$PROPOSE_DIR/scripts/validate_baseline.py" ]; then
          if ! python3 "$PROPOSE_DIR/scripts/validate_baseline.py" "$name" >/dev/null 2>&1; then
              echo "❌ plan-done gate: $name failed baseline validation"
              python3 "$PROPOSE_DIR/scripts/validate_baseline.py" "$name" || true
              VALIDATION_FAILED=1
          fi
      fi
      if [ -f "$RDD_LIB_DIR/validate_delta_targets.py" ]; then
          if ! python3 "$RDD_LIB_DIR/validate_delta_targets.py" "$name" >/dev/null 2>&1; then
              echo "❌ plan-done gate: $name failed delta target validation"
              python3 "$RDD_LIB_DIR/validate_delta_targets.py" "$name" || true
              VALIDATION_FAILED=1
          fi
      fi

      # isComplete check: `openspec status --change <name> --json` must report isComplete=true
      if command -v openspec >/dev/null 2>&1; then
          local ISCOMPLETE
          ISCOMPLETE=$(openspec status --change "$name" --json 2>/dev/null | \
              python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('isComplete', True))" 2>/dev/null || echo "true")
          if [ "$ISCOMPLETE" = "False" ]; then
              echo "⚠️  plan-done gate: $name reports isComplete=false (open artifacts remain)"
              # Warning level — do not increment VALIDATION_FAILED
          fi
      fi
  done
  if [ "$VALIDATION_FAILED" -ne 0 ]; then
      echo "❌ plan-done gate blocked: fix validation errors above"
      return 1
  fi

  # Delegate to Python helper via env-var passing only (Oracle C1: no bash string interp)
  PROJECT_ROOT="$PROJECT_ROOT" \
  ACTIVE_CHANGES_COUNT="${ACTIVE_CHANGES_COUNT:-}" \
  CURRENT_CHANGE="${CURRENT_CHANGE:-}" \
  python3 "$SCRIPT_DIR/plan_done_gate_env.py"
}
