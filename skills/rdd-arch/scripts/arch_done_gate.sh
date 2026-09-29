#!/usr/bin/env bash
# _lib/arch_done_gate.sh — extracted from guide-arch.md L522-L559 (Phase 5)
# Exports:
#   check_arch_done_gate()        — single-gate validation
#   check_gap_analyses_advisory()  — optional gap-analysis structural check (advisory, non-blocking)
#
# Single-gate validation for arch-done transition (per ADR-0048, 2026-09-09):
#   Gate 1: ADR count >= 1 (uses DISCOVERED_ADR_DIR + DISCOVERED_ADR_PATTERN)
#   Advisory (non-blocking): gap-analysis structural_ok via _lib/arch/protocol.py::validate_document()
#
# CHANGED per ADR-0048 §Decision 1:
#   - Removed Gate 2 (roadmap.md exists check); roadmap now managed by rdd-planner Phase 0
#   - arch-done no longer references roadmap (role boundary clean per ADR-0028)
#   - Forward handoff: rdd-planner Phase 0 detects missing roadmap and triggers init
#
# CHANGED 2026-09-29 (closes ADR-0046 deferred wiring):
#   - Added check_gap_analyses_advisory() to fulfill the deferred promise from
#     SKILL.md L553 ("arch-done Phase 5 接线 validation 已 defer 至独立 future change").
#   - Per ADR-0046 §5: structural_ok failures are HARD but here advisory (never blocks
#     arch-done; humans curate gap analyses asynchronously).
#
# Returns 0 on success, 1 on gate failure.
# Caller should use '|| exit 1' to translate to script exit.
#
# Honors env vars:
#   DISCOVERED_ADR_DIR, DISCOVERED_ADR_PATTERN
#   (set by discover-arch-artifacts.sh from arch_env_check.sh Phase 1 Step 5)
#   DISCOVERED_ROADMAP_PATH no longer used here (roadmap discovery moved to rdd-planner)
#   DISCOVERED_ARCHITECTURE_DIR (set by discover-arch-artifacts.sh) — for gap-analysis scan

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
          type discover_architecture_dir &>/dev/null && discover_architecture_dir >/dev/null
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

  # Advisory check: gap-analysis structural validation (closes ADR-0046 deferred wiring)
  check_gap_analyses_advisory "$PROJECT_ROOT" "${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

  return 0
}

# check_gap_analyses_advisory <project_root> <arch_dir>
#
# Per ADR-0046 §5 REPURPOSE: validate_document() returns ValidationReport with
#   - structural_ok (HARD, deterministic): all 5 required sections present
#   - completeness (ADVISORY): draft/partial/complete based on placeholder count
#
# This gate is ADVISORY only — never blocks arch-done. Humans curate gap analyses
# asynchronously (per ADR-0046 §5). Surfaces:
#   - structural_ok = False → generator drift (hard warning, should be fixed)
#   - completeness = "draft" → never filled (informational)
#   - completeness = "complete" → fully curated (info)
#   - completeness = "partial" → partially curated (info)
#
# Honors env vars (Oracle C1 — never bash-interpolate into python strings):
#   RDDF_LIB_ROOT          — sys.path root for _lib imports
#   RDDF_GAP_PROJECT_ROOT  — project root passed to python
#   RDDF_GAP_ARCH_DIR      — architecture dir (relative to project_root) passed to python
#
# Returns 0 always (advisory only). Caller should NOT propagate return value.

check_gap_analyses_advisory() {
  local PROJECT_ROOT_VAL="$1"
  local ARCH_DIR_REL="${2:-docs/architecture}"

  if [ -z "$PROJECT_ROOT_VAL" ]; then
      echo "  ℹ️  跳过 gap-analysis advisory（PROJECT_ROOT 未提供）"
      return 0
  fi
  if [ ! -d "$PROJECT_ROOT_VAL/$ARCH_DIR_REL" ]; then
      echo "  ℹ️  跳过 gap-analysis advisory（$ARCH_DIR_REL 目录不存在）"
      return 0
  fi

  # Oracle C1 safe: pass via env vars, not string interpolation
  export RDDF_GAP_PROJECT_ROOT="$PROJECT_ROOT_VAL"
  export RDDF_GAP_ARCH_DIR="$ARCH_DIR_REL"

  echo "门控 1.5 (advisory): gap-analysis structural 验证 (per ADR-0046, 不阻断)"

  python3 - <<'PYEOF' 2>&1
import os, sys
from pathlib import Path

project_root = os.environ["RDDF_GAP_PROJECT_ROOT"]
arch_dir_rel = os.environ["RDDF_GAP_ARCH_DIR"]

# Ensure sys.path includes project_root (where _lib/ lives)
sys.path.insert(0, project_root)

try:
    from _lib.arch import validate_document, list_analyses
except ImportError as e:
    print(f"  ⚠️  无法导入 _lib.arch: {e}")
    print(f"     跳过 advisory 检查")
    sys.exit(0)

arch_dir_abs = Path(arch_dir_rel)
if not arch_dir_abs.is_absolute():
    arch_dir_abs = Path(project_root) / arch_dir_abs

analyses = list_analyses(arch_dir_abs)
if not analyses:
    print("  ℹ️  暂无 gap-analysis 文档（可选，无 ADR 强制要求）")
    sys.exit(0)

print(f"  发现 {len(analyses)} 个 gap-analysis 文档")

structural_ok_count = 0
structural_fail_count = 0
completeness_draft = 0
completeness_partial = 0
completeness_complete = 0

for gap_file in analyses:
    report = validate_document(gap_file)
    if report.structural_ok:
        structural_ok_count += 1
    else:
        structural_fail_count += 1
        print(f"    ❌ {gap_file.name}: 结构不完整")
        for issue in report.issues:
            print(f"        - {issue}")
        continue

    # structural_ok True → 报告 completeness
    if report.completeness == "draft":
        completeness_draft += 1
        print(f"    📝 {gap_file.name}: 草案（待补全）")
    elif report.completeness == "partial":
        completeness_partial += 1
        print(f"    🔵 {gap_file.name}: 部分补全")
    else:  # complete
        completeness_complete += 1
        print(f"    ✅ {gap_file.name}: 完整")

print(f"  摘要: 结构 OK={structural_ok_count}, 结构失败={structural_fail_count}, draft={completeness_draft}, partial={completeness_partial}, complete={completeness_complete}")
print(f"  注: 此项为 advisory，不阻断 arch-done（per ADR-0046 §5）")
PYEOF
  unset RDDF_GAP_PROJECT_ROOT RDDF_GAP_ARCH_DIR
  return 0
}