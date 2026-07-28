#!/usr/bin/env bash
# skills/openspec-gate/scripts/openspec-gate.sh
# Detect staged files that are not linked to any active openspec change.
# Default scope: include/, src/, plugins/, drivers/ with .cpp, .h, .hpp, .c, .py, .ts
# Environment:
#   OPENSPEC_GATE_MODE=warn|block   (default: warn)
#   OPENSPEC_GATE_PATHS             (space-separated path prefixes)
#   OPENSPEC_GATE_EXTENSIONS        (space-separated file extensions)

set -euo pipefail

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

GATE_MODE="${OPENSPEC_GATE_MODE:-warn}"
GATE_PATHS="${OPENSPEC_GATE_PATHS:-include/ src/ plugins/ drivers/}"
GATE_EXTENSIONS="${OPENSPEC_GATE_EXTENSIONS:-.cpp .h .hpp .c .py .ts}"

STAGED_FILES=$(git diff --cached --name-only)

ACTIVE_CHANGES=$(
  ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null \
    | grep -v archive/ \
    | xargs -n1 basename \
    || true
)

UNTRACKED=()
for f in $STAGED_FILES; do
  # Skip files already under the openspec/ change tree
  if echo "$f" | grep -q "^openspec/"; then
    continue
  fi

  # Check path prefix against default gate paths
  IN_PATH=false
  for prefix in $GATE_PATHS; do
    if echo "$f" | grep -q "^${prefix}"; then
      IN_PATH=true
      break
    fi
  done
  [ "$IN_PATH" = true ] || continue

  # Check extension against default gate extensions
  HAS_EXT=false
  for ext in $GATE_EXTENSIONS; do
    if echo "$f" | grep -q "${ext}$"; then
      HAS_EXT=true
      break
    fi
  done
  [ "$HAS_EXT" = true ] || continue

  # Check whether the staged path is linked to an active change by name
  IN_CHANGE=false
  for change in $ACTIVE_CHANGES; do
    if echo "$f" | grep -qi "$change"; then
      IN_CHANGE=true
      break
    fi
  done

  if [ "$IN_CHANGE" = false ]; then
    UNTRACKED+=("$f")
  fi
done

if [ ${#UNTRACKED[@]} -gt 0 ]; then
  echo "⚠️  以下文件未关联到任何 openspec change:"
  printf '  %s\n' "${UNTRACKED[@]}"
  echo "请创建或关联到对应 change。OPENSPEC_GATE_MODE=block 可升级为硬拦截。"
  if [ "$GATE_MODE" = "block" ]; then
    exit 1
  fi
fi
