#!/usr/bin/env bash
# skills/guide-design/scripts/design_preflight.sh — design Phase 1 证据收集
# 永远 exit 0; 输出 status JSON 到 stdout, 诊断日志到 stderr.
# 调用方根据 .recommendation 字段决定下一步.

set -euo pipefail

PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

emit_status() {
  local arch_handoff="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  local adr_dir="${SPEC_WORKFLOW_ADR_DIR:-$PROJECT_ROOT/docs/adr}"
  local roadmap="${SPEC_WORKFLOW_ROADMAP_PATH:-$PROJECT_ROOT/roadmap.md}"

  local arch_handoff_exists="false"
  [ -f "$arch_handoff" ] && arch_handoff_exists="true"

  local adr_count=0
  if [ -d "$adr_dir" ]; then
    local adr_file
    for adr_file in "$adr_dir"/ADR-*.md; do
      [ -f "$adr_file" ] || continue
      [[ "$(basename "$adr_file")" == *template* ]] && continue
      adr_count=$((adr_count + 1))
    done
  fi

  local roadmap_exists="false"
  [ -f "$roadmap" ] && roadmap_exists="true"

  local session_arch_done="false"
  if [ -f "$PROJECT_ROOT/.rddf/state/sessions.json" ]; then
    session_arch_done=$(jq -r '
      [.sessions[]? | select(.stage=="stage_arch" and .status=="completed")]
      | length > 0
    ' "$PROJECT_ROOT/.rddf/state/sessions.json" 2>/dev/null || echo "false")
  fi

  local recommendation="hard_reject_no_evidence"
  if [ "$arch_handoff_exists" = "true" ]; then
    recommendation="normal"
  elif [ "$adr_count" -gt 0 ] && [ "$roadmap_exists" = "true" ]; then
    recommendation="soft_prompt_reconstruct"
  fi

  if ! command -v jq >/dev/null 2>&1; then
    printf '%s\n' '{"arch_handoff_exists":false,"adr_count":0,"roadmap_exists":false,"session_history_arch_done":false,"recommendation":"hard_reject_no_evidence","degraded":"jq_missing"}'
    return 0 2>/dev/null || exit 0
  fi

  jq -n \
    --argjson arch_handoff_exists "$arch_handoff_exists" \
    --argjson adr_count "$adr_count" \
    --argjson roadmap_exists "$roadmap_exists" \
    --argjson session_history_arch_done "$session_arch_done" \
    --arg recommendation "$recommendation" \
    '{arch_handoff_exists: $arch_handoff_exists,
      adr_count: $adr_count,
      roadmap_exists: $roadmap_exists,
      session_history_arch_done: $session_history_arch_done,
      recommendation: $recommendation}'
}

emit_status
