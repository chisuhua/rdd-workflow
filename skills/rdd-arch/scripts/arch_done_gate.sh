#!/usr/bin/env bash
# _lib/arch_done_gate.sh — extracted from guide-arch.md L522-L559 (Phase 5)
# Exports: check_arch_done_gate()
#
# Single-gate validation for arch-done transition (per ADR-0048, 2026-09-09):
#   Gate 1: ADR count >= 1 (uses DISCOVERED_ADR_DIR + DISCOVERED_ADR_PATTERN)
#
# CHANGED per ADR-0048 §Decision 1:
#   - Removed Gate 2 (roadmap.md exists check); roadmap now managed by rdd-planner Phase 0
#   - arch-done no longer references roadmap (role boundary clean per ADR-0028)
#   - Forward handoff: rdd-planner Phase 0 detects missing roadmap and triggers init
#
# Returns 0 on success, 1 on either gate failure.
# Caller should use '|| exit 1' to translate to script exit.
#
# Honors env vars:
#   DISCOVERED_ADR_DIR, DISCOVERED_ADR_PATTERN
#   (set by discover-arch-artifacts.sh from arch_env_check.sh Phase 1 Step 5)
#   DISCOVERED_ROADMAP_PATH no longer used here (roadmap discovery moved to rdd-planner)

check_arch_done_gate() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  # ADR-0016: ensure discovery is run before gates check actual paths
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  if [ -f "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh" ]; then
      source "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh"
      if type discover_all &>/dev/null; then
          discover_all >/dev/null
      else
          # Fallback: call individual discoverers (ADR-0048: no longer call discover_roadmap)
          type discover_adr_dir &>/dev/null && discover_adr_dir >/dev/null
          type discover_adr_pattern &>/dev/null && discover_adr_pattern >/dev/null
      fi
  fi

  echo "=== Arch 阶段 - 门控检查 (per ADR-0048: 单门控) ==="
  echo ""

  # 门控 1: ADR 数量 ≥ 1
  local ADR_DIR="${DISCOVERED_ADR_DIR:-docs/adr}"
  local ADR_PATTERN="${DISCOVERED_ADR_PATTERN:-ADR-*.md}"
  local _GLOB="${PROJECT_ROOT}/${ADR_DIR}/${ADR_PATTERN}"
  local ADR_COUNT
  ADR_COUNT=$(ls $_GLOB 2>/dev/null | grep -v -- '-0000-template\.md$' | wc -l | tr -d ' ')
  echo "门控 1: ADR 数量检查 (per ADR-0048, 单门控)"
  echo "  当前 ADR 数量: $ADR_COUNT (path: $ADR_DIR, pattern: $ADR_PATTERN)"
  if [ "$ADR_COUNT" -lt 1 ]; then
      echo "  ❌ 失败: 至少需要 1 个 ADR"
      echo "     请回到 adr-create 阶段创建 ADR"
      return 1
  fi
  echo "  ✅ 通过"
  echo ""
  echo "注: roadmap 检查已从 arch-done 移除 (per ADR-0048 §Decision 1)."
  echo "    roadmap 由 rdd-planner Phase 0 roadmap-bootstrap 接管."
  echo "    arch-done 现在是单门控 (ADR ≥ 1), 与 rdd-planner 完全解耦."
  echo ""
  return 0
}