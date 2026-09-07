#!/usr/bin/env bash
# skills/rdd-arch/scripts/arch_gap_analysis.sh — thin bash wrapper over
# `_lib/arch/protocol.py` (Analyzer Subset §2, per ADR-0046 + the
# cross-stage protocol template).
#
# Oracle C1: bash NEVER interpolates env vars into `python3 -c "..."` strings.
# All values are passed via `os.environ` in `_lib/arch/protocol.py`.
#
# This wrapper preserves the PRE-REFACTOR bash wrapper contract byte-identically
# so the 8 existing bats tests in `tests/integration/test_arch_gap_analysis_extraction.bats`
# stay green (Oracle risk #3).
#
# Exported bash functions:
#   generate_gap_analysis <slug>  — writes <arch_dir>/<slug>-gap-analysis.md
#   list_gap_analyses              — enumerates existing gap analyses
#
# Env vars:
#   PROJECT_ROOT                    optional; auto-detect if unset
#   DISCOVERED_ARCHITECTURE_DIR     optional; default `docs/architecture`
#   RDDF_ARCH_GAP_TODAY            optional; ISO-8601 timestamp (default: now)

set -euo pipefail

# Resolve the Python data layer path. Per AGENTS.md rule 25, new code imports
# `_lib.X` (canonical). The repo-root `_lib/` is on sys.path via `tests/conftest.py`
# or the global-install `.pth` file (see install.sh).
#
# Fallback chain (Oracle C1 compatible — never bash-string-interpolate):
#   1. RDDF_LIB_ROOT env var (caller override)
#   2. Read this file's real path via `readlink -f` and resolve relative to it
#   3. git rev-parse --show-superproject-working-tree (submodule-aware)
#   4. git rev-parse --show-toplevel (main repo)
if [ -z "${RDDF_LIB_ROOT:-}" ]; then
  _WRAPPER_REAL="$(readlink -f "${BASH_SOURCE[0]:-$0}" 2>/dev/null || echo "${BASH_SOURCE[0]:-$0}")"
  _WRAPPER_DIR="$(cd "$(dirname "$_WRAPPER_REAL")/../.." 2>/dev/null && pwd || true)"
  if [ -n "$_WRAPPER_DIR" ] && [ -d "$_WRAPPER_DIR/_lib" ]; then
    RDDF_LIB_ROOT="$_WRAPPER_DIR"
  else
    RDDF_LIB_ROOT="$(git rev-parse --show-superproject-working-tree 2>/dev/null \
      || git rev-parse --show-toplevel 2>/dev/null \
      || pwd)"
  fi
fi
export RDDF_LIB_ROOT
unset _WRAPPER_REAL _WRAPPER_DIR

_validate_arch_gap_env() {
  local slug="${1:-}"
  local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local arch_dir="${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

  if [ -z "$slug" ]; then
    echo "❌ 主题不能为空"
    return 1
  fi

  export RDDF_ARCH_GAP_SLUG="$slug"
  export RDDF_ARCH_GAP_PROJECT_ROOT="$project_root"
  export RDDF_ARCH_GAP_ARCH_DIR="$arch_dir"
  export RDDF_ARCH_GAP_TODAY="${RDDF_ARCH_GAP_TODAY:-$(date -Iseconds)}"
  export RDDF_ARCH_GAP_ACTION="generate"
  return 0
}

generate_gap_analysis() {
  local SLUG="${1:-}"
  if ! _validate_arch_gap_env "$SLUG"; then
    return 1
  fi

  local PROJECT_ROOT_VAL="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local ARCH_DIR="$PROJECT_ROOT_VAL/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"
  local NEW_GAP="$ARCH_DIR/${SLUG}-gap-analysis.md"

  mkdir -p "$ARCH_DIR" || { echo "❌ 无法创建目录: $ARCH_DIR"; return 1; }
  if [ -f "$NEW_GAP" ]; then
    echo "❌ 差距分析已存在: $NEW_GAP"
    return 1
  fi

  # Delegate body generation to `_lib/arch/protocol.py::build_skeleton`
  # (Oracle C1: env vars only — never `python3 -c "$VAR" ...` interpolation).
  local skeleton
  skeleton="$(python3 - <<'PYEOF' 2>&1
import os, sys
sys.path.insert(0, os.environ["RDDF_LIB_ROOT"])
from _lib.arch import build_skeleton
sys.stdout.write(build_skeleton(
    os.environ["RDDF_ARCH_GAP_SLUG"],
    os.environ.get("RDDF_ARCH_GAP_TODAY", ""),
))
PYEOF
)"
  printf '%s\n' "$skeleton" > "$NEW_GAP"

  echo "✅ 已创建: $NEW_GAP"
  echo "   请编辑该文件补全差距分析内容"
}

list_gap_analyses() {
  local PROJECT_ROOT_VAL="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local ARCH_DIR_VAL="$PROJECT_ROOT_VAL/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

  local gap_paths
  gap_paths="$(python3 - <<PYEOF 2>&1
import os, sys
sys.path.insert(0, os.environ["RDDF_LIB_ROOT"])
from pathlib import Path
from _lib.arch import list_analyses
for p in list_analyses(Path(os.environ.get("RDDF_ARCH_GAP_ARCH_DIR", "docs/architecture"))):
    print(p.name)
PYEOF
)"

  if [ -z "$gap_paths" ]; then
    echo "⚠️  暂无差距分析"
    return 1
  fi

  echo "现有差距分析列表:"
  echo "$gap_paths" | nl -w2 -s". " | while IFS= read -r line; do
    echo "  $line"
  done
  return 0
}