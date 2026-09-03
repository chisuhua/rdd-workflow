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

# Source orchestrator_entry.sh unconditionally (spec 2026-08-13 §2).
# Bootstrap git rev-parse below is unavoidable — orchestrator_run not yet
# defined. T8 grep-rule will exempt this line per spec §6.1.
source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/orchestrator_entry.sh" 2>/dev/null || \
source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true

source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/post_flow_wrap.sh" 2>/dev/null || \
source "$HOME/.agents/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
trap 'post_flow_on_err' ERR

# C4 (spec 2026-08-13 §6): always finalize on exit so sweep can detect
# phases killed without explicit cleanup.
trap 'orchestrator_finalize' EXIT
# - Falls back to defaults if jq missing or handoff fields absent
# - Reads ADR_IDS + CURRENT_PHASE from handoff via python3 (with $ARCH_HANDOFF via env-var)
# - Counts active openspec changes
# - Prints summary

check_direct_create_fallback() {
  local project_root="${1:-$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local approved_file="$project_root/proposal-approved.md"

  if [ ! -f "$approved_file" ]; then
    local archived_count
    archived_count=$(orchestrator_run ls -d "$project_root"/openspec/changes/archive/*/ 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ "${archived_count:-0}" -gt 0 ]; then
      echo "🆕 未发现 proposal-approved.md - 检测到 $archived_count 个历史归档"
      echo "   后备模式: 跳过提案审批，直接创建新 change"
      echo "   后续可手动追加 proposal-approved.md 作为审计追溯"
      return 0
    fi
  fi
  return 1
}

# Gap 1 contract: CHANGES_PRE_CREATED consumers (guide-plan.md Phase 0/2/2.5).
# SKIP_DESIGN_HANDOFF=yes leaves CHANGES_PRE_CREATED=() — helpers safely
# report "not pre-created" because every entry check fails on an empty array.

is_design_pre_created() {
  local name="$1"
  local item
  for item in "${CHANGES_PRE_CREATED[@]:-}"; do
    [ "$item" = "$name" ] && return 0
  done
  return 1
}

get_design_pre_created_label() {
  local name="$1"
  if is_design_pre_created "$name"; then
    echo "🆕 design-pre-created"
  fi
}

# Space-separated artifact IDs for Phase 2.5 fill. Pre-created changes
# MUST NOT include 'proposal' — design approval already wrote a complete
# proposal.md and overwriting would destroy content review artifacts.
get_fill_artifacts_for() {
  local name="$1"
  if is_design_pre_created "$name"; then
    echo "design tasks specs"
  else
    echo "proposal design tasks specs"
  fi
}

# fix-plan-intake-stale-pre-created-changes (P1, 2026-09-01):
# Return 0 only if name is in CHANGES_PRE_CREATED AND not yet created
# (openspec/changes/<name>/ missing) AND not archived
# (openspec/changes/archive/*-<name> missing).
#
# Wrapped in a subshell so the line-23 ERR trap (post_flow_on_err)
# cannot intercept our explicit exit 1 — subshell exits are immune
# to the parent shell's ERR trap.
is_design_pre_created_pending() {
  (
    set +e
    trap - ERR
    local name="$1"
    local pr="${PROJECT_ROOT:-}"
    is_design_pre_created "$name" || exit 1
    [ -z "$pr" ] && exit 1
    [ -d "$pr/openspec/changes/$name" ] && exit 1
    compgen -G "$pr/openspec/changes/archive/*-$name" >/dev/null && exit 1
    exit 0
  )
}

# Run a helper so the line-23 ERR trap cannot zero its explicit `return 1`
# exit code (post_flow_on_err always returns 0). Use this when wrapping a
# helper that uses return codes as API.
with_clean_exit_code() {
  local _rc
  (
    set +e
    trap - ERR
    "$@"
    _rc=$?
  )
  return "$_rc"
}

# fix-plan-intake-stale-pre-created-changes (P1, 2026-09-01):
# Python one-shot classification of CHANGES_PRE_CREATED. Reads the names
# already loaded into the array, classifies each as pending/active/archived
# against openspec/changes/<name> and openspec/changes/archive/*-<name>,
# and exports CHANGES_PENDING_COUNT / CHANGES_ACTIVE_COUNT /
# CHANGES_ARCHIVED_COUNT env vars for downstream consumers (Phase 2
# display layer, guide-plan SKILL.md, fill logic).
#
# Args: $1 = PROJECT_ROOT (default: $PROJECT_ROOT env or git toplevel).
# Sets globals: CHANGES_PENDING_COUNT, CHANGES_ACTIVE_COUNT,
#               CHANGES_ARCHIVED_COUNT.
classify_pre_created_changes() {
  local pr="${1:-${PROJECT_ROOT:-$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  # Bypass orchestrator_run: its subprocess wrapper swallows stdout, which
  # would break the read-from-pipe capture below. Same caveat as
  # check_design_handoff's mapfile block.
  local _result
  _result=$(PROJECT_ROOT="$pr" CHANGES_PRE_CREATED_CSV="${CHANGES_PRE_CREATED[*]:-}" python3 -c '
import os, glob
pr = os.environ["PROJECT_ROOT"]
names = [n for n in os.environ.get("CHANGES_PRE_CREATED_CSV", "").split() if n]
pending = active = archived = 0
for name in names:
    if os.path.isdir(os.path.join(pr, "openspec", "changes", name)):
        active += 1
    elif glob.glob(os.path.join(pr, "openspec", "changes", "archive", f"*-{name}")):
        archived += 1
    else:
        pending += 1
print(f"{pending} {active} {archived}")
' 2>/dev/null)
  read -r CHANGES_PENDING_COUNT CHANGES_ACTIVE_COUNT CHANGES_ARCHIVED_COUNT <<< "$_result"
  export CHANGES_PENDING_COUNT CHANGES_ACTIVE_COUNT CHANGES_ARCHIVED_COUNT
  : "${CHANGES_PENDING_COUNT:=0}" "${CHANGES_ACTIVE_COUNT:=0}" "${CHANGES_ARCHIVED_COUNT:=0}"
}

# fix-plan-intake-stale-pre-created-changes (P1, 2026-09-01):
# Python one-shot count of proposal-approved.md rows that are:
#   - in the ## 已批准 section (before ## 已实施)
#   - NOT yet created (openspec/changes/<name> missing)
#   - NOT yet archived (openspec/changes/archive/*-<name> missing)
# Returns the count via stdout. Used by run_plan_intake to fix the
# misleading "X 个已批准提案但无活跃 change" warning that previously
# counted the entire file (including the implemented archive section).
count_pending_proposals() {
  local pr="${1:-${PROJECT_ROOT:-$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
  # Bypass orchestrator_run: its subprocess wrapper swallows stdout.
  PROJECT_ROOT="$pr" python3 -c '
import os, glob, re, sys
pr = os.environ["PROJECT_ROOT"]
path = os.path.join(pr, "proposal-approved.md")
if not os.path.isfile(path):
    print("0")
    sys.exit(0)
with open(path, encoding="utf-8") as f:
    content = f.read()
section = content.split("## 已实施", 1)[0]
names = re.findall(r"\[\s*([^\]]+)\]\s*\(\s*\.rddf/improvements/([^)]+)\s*\)", section)
count = 0
for disp, fname in names:
    name = fname.replace(".md", "")
    if os.path.isdir(os.path.join(pr, "openspec", "changes", name)):
        continue
    if glob.glob(os.path.join(pr, "openspec", "changes", "archive", f"*-{name}")):
        continue
    count += 1
print(count)
' 2>/dev/null
}

check_design_handoff() {
  local project_root="${1:-$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)}"
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
  PYTHON_HANDOFF_PATH="$handoff_path" orchestrator_run python3 -c "
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

  # Read changes_pre_created from v2 payload (v1 = empty).
  # Bypass orchestrator_run: its subprocess wrapper swallows stdout, which
  # would break mapfile/while-read capture here.
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
    classify_pre_created_changes "$project_root"
    echo "✅ design-done handoff 已验证 (v2 schema, ${#CHANGES_PRE_CREATED[@]} 个预建 changes: ${CHANGES_PENDING_COUNT} 待处理, ${CHANGES_ACTIVE_COUNT} 已创建, ${CHANGES_ARCHIVED_COUNT} 已归档)"
  else
    echo "✅ design-done handoff 已验证 (v1 schema)"
  fi
  return 0
}

run_plan_intake() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(orchestrator_run git rev-parse --show-toplevel 2>/dev/null || pwd)
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
  ACTIVE_CHANGES=$(orchestrator_run ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
  echo "📋 当前活跃 changes: $ACTIVE_CHANGES"

  local PENDING_PROPOSALS
  PENDING_PROPOSALS=$(count_pending_proposals "$PROJECT_ROOT")
  if [ -z "$PENDING_PROPOSALS" ]; then PENDING_PROPOSALS=0; fi
  echo "📋 待创建 proposal: $PENDING_PROPOSALS"
  if [ "$PENDING_PROPOSALS" -gt 0 ] && [ "$ACTIVE_CHANGES" -eq 0 ]; then
    echo "⚠️  proposal-approved.md 中有 $PENDING_PROPOSALS 个真正待创建提案（已排除已创建/已归档）"
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
      echo "   -> 请先运行: skill_use(\"rdd-arch\")"
      echo ""
      echo "   如确定跳过 arch 阶段（已知风险），设置环境变量:"
      echo "     export SKIP_ARCH_HANDOFF=yes"
      
      check_direct_create_fallback "$PROJECT_ROOT"
      return 1
  fi

  # ADR-0016 Layer 3: read discovered paths from handoff with v2.0 fallback defaults.
  # Same orchestrator_run caveat as design-handoff block above.
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
  parsed=$(PYTHON_HANDOFF_PATH="$ARCH_HANDOFF" orchestrator_run python3 -c "
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