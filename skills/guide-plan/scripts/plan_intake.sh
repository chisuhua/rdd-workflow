#!/usr/bin/env bash
# _lib/plan_intake.sh - extracted from guide-plan.md Phase 0 intake (L95-L175)
# Exports: run_plan_intake(), check_direct_create_fallback()
#
# Behavior preserved:
# - openspec CLI detection (returns 1 if missing)
# - git workspace state check
# - Current branch display
# - HARD-GATE on .arch-handoff.json existence (returns 1 if missing)
# - Reads ADR_DIR, ROADMAP_PATH, ADR_PATTERN, ARCHITECTURE_DIR via jq from handoff

# ADR-0027 script-plane trigger (see add-post-flow-analysis change)
export RDDF_PHASE="${RDDF_PHASE:-guide-plan}"
source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
trap 'post_flow_on_err' ERR
# - Falls back to defaults if jq missing or handoff fields absent
# - Reads ADR_IDS + CURRENT_PHASE from handoff via python3 (with $ARCH_HANDOFF via env-var)
# - Counts active openspec changes
# - Prints summary

check_direct_create_fallback() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local approved_file="$project_root/proposal-approved.md"

  if [ ! -f "$approved_file" ]; then
    local archived_count
    archived_count=$(ls -d "$project_root"/openspec/changes/archive/*/ 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ "${archived_count:-0}" -gt 0 ]; then
      echo "🆕 未发现 proposal-approved.md - 检测到 $archived_count 个历史归档"
      echo "   后备模式: 跳过提案审批，直接创建新 change"
      echo "   后续可手动追加 proposal-approved.md 作为审计追溯"
      return 0
    fi
  fi
  return 1
}

check_design_handoff() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local handoff_path="$project_root/.rddf/state/.design-handoff.json"

  if [ "${SKIP_DESIGN_HANDOFF:-}" = "yes" ]; then
    echo "⚠️  SKIP_DESIGN_HANDOFF=yes: 跳过 design-done 检查（已知风险）"
    return 0
  fi

  if [ ! -f "$handoff_path" ]; then
    # Fallback: projects with archived changes can bypass design gate
    if check_direct_create_fallback "$project_root" 2>/dev/null; then
      return 0
    fi
    echo "❌ design-done 未完成 (.rddf/state/.design-handoff.json 缺失)"
    echo ""
    echo "   design 阶段必须先完成才能进入 plan 阶段。"
    echo "   -> 请先运行: skill_use(\"guide-design\")"
    echo ""
    echo "   如确定跳过 design 阶段（已知风险），设置环境变量:"
    echo "     export SKIP_DESIGN_HANDOFF=yes"
    return 1
  fi

  # Validate schema v1 or v2 (D3 of move-proposal-creation-to-design)
  # v2 adds 'changes_pre_created'. v1 readers treat it as empty.
  CHANGES_PRE_CREATED=()
  PYTHON_HANDOFF_PATH="$handoff_path" python3 -c "
import json, os, sys
try:
    with open(os.environ['PYTHON_HANDOFF_PATH']) as f:
        d = json.load(f)
    version = d.get('version')
    if version not in (1, 2):
        print(f'❌ design-handoff version must be 1 or 2, got {version}', file=sys.stderr)
        sys.exit(1)
    assert d.get('all_proposals_have_decision') == True, 'all_proposals_have_decision must be true'
    assert isinstance(d.get('proposals_reviewed'), int) and d['proposals_reviewed'] >= 0
    # v2: enforce changes_pre_created array
    if version == 2:
        cpc = d.get('changes_pre_created')
        assert isinstance(cpc, list), 'changes_pre_created must be a list'
        for item in cpc:
            assert isinstance(item, str) and len(item) > 0, 'changes_pre_created items must be non-empty strings'
except (AssertionError, json.JSONDecodeError, KeyError) as e:
    print(f'❌ design-handoff 验证失败: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1 || return 1

  # Read changes_pre_created from v2 payload (v1 = empty)
  if command -v jq >/dev/null 2>&1; then
    mapfile -t CHANGES_PRE_CREATED < <(jq -r '.changes_pre_created // [] | .[]' "$handoff_path" 2>/dev/null)
  else
    while IFS= read -r line; do
      [ -n "$line" ] && CHANGES_PRE_CREATED+=("$line")
    done < <(PYTHON_HANDOFF_PATH="$handoff_path" python3 -c "
import json, os
with open(os.environ['PYTHON_HANDOFF_PATH']) as f:
    d = json.load(f)
for n in d.get('changes_pre_created', []):
    print(n)
")
  fi
  export CHANGES_PRE_CREATED

  if [ "${#CHANGES_PRE_CREATED[@]}" -gt 0 ]; then
    echo "✅ design-done handoff 已验证 (v2 schema, ${#CHANGES_PRE_CREATED[@]} 个预建 changes)"
  else
    echo "✅ design-done handoff 已验证 (v1 schema)"
  fi
  return 0
}

run_plan_intake() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  echo "🔍 Plan 阶段环境检查..."
  echo ""

  # 1. openspec CLI 检测 (共享函数, 缺失返回 1 + 修复指引)
  # source 优先级: 仓库内相对路径 (BASH_SOURCE) → PROJECT_ROOT → skill_root 解析
  local _PI_SELF _PI_DIR
  _PI_SELF="${BASH_SOURCE[0]:-$0}"
  _PI_DIR="$(cd "$(dirname "$_PI_SELF")" && pwd)"
  if [ -f "$_PI_DIR/../../_lib/env_checks.sh" ]; then
    source "$_PI_DIR/../../_lib/env_checks.sh"
  elif [ -f "$PROJECT_ROOT/_lib/env_checks.sh" ]; then
    source "$PROJECT_ROOT/_lib/env_checks.sh"
  else
    source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh" 2>/dev/null
    if command -v resolve_rdd_lib_dir >/dev/null 2>&1 && [ -f "$(resolve_rdd_lib_dir)/env_checks.sh" ]; then
      source "$(resolve_rdd_lib_dir)/env_checks.sh"
    fi
  fi
  _check_openspec || return 1
  echo "✅ openspec CLI: $_OPENSPEC_VER"

  # 2. git 状态 (共享函数)
  _check_git
  if [ "$_GIT_CLEAN" -eq 0 ]; then
      echo "✅ git 工作区干净"
  else
      echo "⚠️  git 工作区有 $_GIT_CLEAN 个未跟踪/修改文件"
  fi

  # 3. 当前分支 (共享函数)
  _check_branch
  echo "📌 当前分支: $_CURRENT_BRANCH"

  # 4. plan 端当前状态
  local ACTIVE_CHANGES
  ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
  echo "📋 当前活跃 changes: $ACTIVE_CHANGES"

  local PENDING_PROPOSALS
  PENDING_PROPOSALS=$(grep -c '| \[' "$PROJECT_ROOT/proposal-approved.md" 2>/dev/null || echo 0)
  if [ "$PENDING_PROPOSALS" -gt 0 ] && [ "$ACTIVE_CHANGES" -eq 0 ]; then
    echo "⚠️  proposal-approved.md 中有 $PENDING_PROPOSALS 个已批准提案但无活跃 change（可能需运行 propose）"
  fi

  # 4.5. Direct-create fallback detection (guide-plan-fallback-direct-create)
  check_direct_create_fallback "$PROJECT_ROOT" || true

  # 5. arch 端交付物检查（plan 端的前置条件 - 硬阻断）
  local ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  if [ "${SKIP_ARCH_HANDOFF:-}" = "yes" ]; then
      echo "⚠️  SKIP_ARCH_HANDOFF=yes: 跳过 arch-handoff + design-handoff 检查（已知风险）"
      return 0
  fi

  if [ ! -f "$ARCH_HANDOFF" ]; then
      echo "❌ 未检测到 arch-done handoff (.rddf/state/.arch-handoff.json)"
      echo ""
      echo "   arch 阶段必须先完成才能进入 plan 阶段。"
      echo "   -> 请先运行: skill_use(\"guide-arch\")"
      echo ""
      echo "   如确定跳过 arch 阶段（已知风险），设置环境变量:"
      echo "     export SKIP_ARCH_HANDOFF=yes"
      
      check_direct_create_fallback "$PROJECT_ROOT"
      return 1
  fi

  # ADR-0016 Layer 3: read discovered paths from handoff with v2.0 fallback defaults.
  local ADR_DIR ROADMAP_PATH ADR_PATTERN ARCHITECTURE_DIR
  ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF" 2>/dev/null || echo "docs/adr")
  ROADMAP_PATH=$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF" 2>/dev/null || echo "roadmap.md")
  ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF" 2>/dev/null || echo "ADR-*.md")
  ARCHITECTURE_DIR=$(jq -r '.architecture_dir // "docs/architecture"' "$ARCH_HANDOFF" 2>/dev/null || echo "docs/architecture")

  # Roadmap existence uses DISCOVERED_ROADMAP_PATH (not hardcoded)
  local ROADMAP_EXISTS
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/$ROADMAP_PATH" ] && echo "yes" || echo "no")

  # Read ADR_IDS + CURRENT_PHASE from handoff via env-var passing (Oracle C1 safe)
  # Instead of bash $ARCH_HANDOFF string interpolation, use env var
  local ADR_IDS CURRENT_PHASE ADR_COUNT parsed
  parsed=$(PYTHON_HANDOFF_PATH="$ARCH_HANDOFF" python3 -c "
import json, os
try:
    with open(os.environ['PYTHON_HANDOFF_PATH']) as f:
        d = json.load(f)
    print(','.join(d.get('completed_adr_ids', [])))
    print(d.get('current_phase', 'default'))
except Exception:
    print('')
    print('default')
" 2>/dev/null || printf '%s\n' '' 'default')
  ADR_IDS=$(echo "$parsed" | sed -n '1p')
  CURRENT_PHASE=$(echo "$parsed" | sed -n '2p')
  if [ -z "$ADR_IDS" ]; then
    ADR_COUNT=0
  else
    ADR_COUNT=$(echo "$ADR_IDS" | tr ',' '\n' | grep -c .)
  fi

  echo "📋 ADR 数量: $ADR_COUNT (from arch-handoff, dir=$ADR_DIR)"
  echo "📋 Roadmap 阶段: $CURRENT_PHASE (path=$ROADMAP_PATH)"
  echo "📋 ADR 编号: $ADR_IDS"
  echo "✅ 检测到 arch-done handoff（arch → plan 硬交接信号）"

  # 5.5. design-done 门控检查 (硬切换, v2.1)
  check_design_handoff "$PROJECT_ROOT" || return 1

  # 6. 提案状态同步: 扫描已归档但未标记的提案，自动标记为已实施
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  local STATE_SH="$(resolve_rdd_lib_dir)/state.sh"
  if [ -f "$STATE_SH" ]; then
    # shellcheck source=/dev/null
    source "$STATE_SH"
    sweep_implemented_proposals "$PROJECT_ROOT"
    sweep_stale_suggestions "$PROJECT_ROOT"
  fi
}