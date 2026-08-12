#!/usr/bin/env bash
# _lib/arch_env_check.sh — extracted from guide-arch.md Phase 1 Steps 1-5 (L92-L189)
# Exports: run_arch_env_check()
#
# Behavior preserved from inline block:
# - openspec CLI detection (returns 1 if missing)
# - git workspace state check
# - Current branch display
# - Build directory detection by project type (Rust/Node/Python/C++/Unknown)
# - ADR/roadmap/gap-analysis/active-change counts
# - Delegates to discover-arch-artifacts.sh (ADR-0016 Layer 1)

# ADR-0027 script-plane trigger (see add-post-flow-analysis change)
export RDDF_PHASE="${RDDF_PHASE:-guide-arch}"
source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
trap 'post_flow_on_err' ERR

run_arch_env_check() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  # source 共享环境检查库 (DRY 单一来源, extract-rdd-env-check-from-guide-arch)
  # 优先相对路径 (仓库内), 再回退 skill_root.sh 解析 (安装模式)
  if [ -f "$PROJECT_ROOT/_lib/env_checks.sh" ]; then
    source "$PROJECT_ROOT/_lib/env_checks.sh"
  else
    source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh" 2>/dev/null
    if command -v resolve_rdd_lib_dir >/dev/null 2>&1 && [ -f "$(resolve_rdd_lib_dir)/env_checks.sh" ]; then
      source "$(resolve_rdd_lib_dir)/env_checks.sh"
    fi
  fi

  echo "🔍 环境检查..."
  echo ""

  # 1. openspec CLI 检测 (共享函数, 缺失返回 1 + 修复指引)
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

  # 4. 构建目录（按项目类型检测, 共享函数）
  _check_build_dir
  if [ -d "$_BUILD_DIR" ]; then
      echo "✅ 构建目录存在 ($_BUILD_DIR/, $_PROJECT_TYPE)"
  else
      echo "⚠️  构建目录不存在 ($_BUILD_DIR/, $_PROJECT_TYPE)"
  fi

  # 5. arch 阶段专用检查 — 先发现路径，再用于计数 (ADR-0016)
  #    工件发现绝不缓存, 每次 phase 进入重新运行
  local DISCOVERED_ADR_DIR DISCOVERED_ADR_PATTERN DISCOVERED_ROADMAP_PATH DISCOVERED_ARCHITECTURE_DIR
  local DISCOVERED_ADR_DIR_FOUND DISCOVERED_ROADMAP_FOUND DISCOVERED_ARCH_FOUND

  # === Phase 1 Step 5: 工件发现 (ADR-0016 Layer 1) ===
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  if [ -f "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh" ]; then
      source "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh"
      discover_adr_dir          >/dev/null
      discover_roadmap          >/dev/null
      discover_architecture_dir >/dev/null
      discover_adr_pattern      >/dev/null
  else
      DISCOVERED_ADR_DIR="docs/adr"
      DISCOVERED_ROADMAP_PATH="roadmap.md"
      DISCOVERED_ARCHITECTURE_DIR="docs/architecture"
      DISCOVERED_ADR_PATTERN="ADR-*.md"
      DISCOVERED_ADR_DIR_FOUND="false"
      DISCOVERED_ROADMAP_FOUND="false"
      DISCOVERED_ARCH_FOUND="false"
  fi

  local ADR_COUNT ROADMAP_EXISTS GAP_COUNT ACTIVE_CHANGES
  ADR_COUNT=$(ls -d "$PROJECT_ROOT/$DISCOVERED_ADR_DIR/"$DISCOVERED_ADR_PATTERN 2>/dev/null | wc -l | tr -d '[:space:]')
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/$DISCOVERED_ROADMAP_PATH" ] && echo "yes" || echo "no")
  GAP_COUNT=$(ls "$PROJECT_ROOT/$DISCOVERED_ARCHITECTURE_DIR/"*-gap-analysis.md 2>/dev/null | wc -l | tr -d '[:space:]')
  ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')

  echo "📋 现有 ADR: $ADR_COUNT"
  echo "📋 Roadmap: $ROADMAP_EXISTS"
  echo "📋 架构差距分析: $GAP_COUNT"
  echo "📋 活动 changes: $ACTIVE_CHANGES"

  echo ""
  echo "🔍 工件发现 (ADR-0016):"
  echo "   ADR 目录:      $DISCOVERED_ADR_DIR ($DISCOVERED_ADR_DIR_FOUND)"
  echo "   ADR 模式:      $DISCOVERED_ADR_PATTERN"
  echo "   Roadmap:       $DISCOVERED_ROADMAP_PATH ($DISCOVERED_ROADMAP_FOUND)"
  echo "   Architecture:  $DISCOVERED_ARCHITECTURE_DIR ($DISCOVERED_ARCH_FOUND)"
}

# Hard gate: check project setup. Returns 1 if any error-severity issue.
run_arch_env_setup_gate() {
  local project_root="${1:-$(pwd)}"
  local _lib_paths=(
    "${project_root}/_lib/check_project_setup.sh"
    "${PROJECT_ROOT:-/nonexistent}/_lib/check_project_setup.sh"
    "${REPO_ROOT:-/nonexistent}/_lib/check_project_setup.sh"
  )
  local _p
  for _p in "${_lib_paths[@]}"; do
    if [ -f "$_p" ]; then
      source "$_p"
      break
    fi
  done
  if ! declare -F check_project_setup >/dev/null; then
    return 0
  fi
  local issues
  issues=$(check_project_setup "$project_root" 2>/dev/null) || return 0
  local fatal
  fatal=$(echo "$issues" | jq -r '.[] | select(.severity=="error" and .status=="fail") | "\(.name)|\(.detail)|\(.fix_command)"')
  if [ -n "$fatal" ]; then
    echo "❌ 项目设置检查未通过 (project-setup-check):"
    while IFS='|' read -r name detail fix; do
      echo "  - $name"
      echo "    $detail"
      echo "    fix: $fix"
    done <<< "$fatal"
    return 1
  fi
  return 0
}
