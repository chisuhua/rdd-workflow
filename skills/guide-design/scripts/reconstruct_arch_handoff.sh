#!/usr/bin/env bash
# skills/guide-design/scripts/reconstruct_arch_handoff.sh
# 从文件系统证据合成 .arch-handoff.json (ADR-0016 schema v1).
# 当 .arch-handoff.json 缺失但 arch 工作已完成时使用.
# 幂等: 已存在合法 handoff 时, 默认拒绝覆盖 (--force 覆盖).

set -euo pipefail

PROJECT_ROOT=""
OUTPUT_PATH=""
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    --output)        OUTPUT_PATH="$2"; shift 2 ;;
    --force)         FORCE="true"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
OUTPUT_PATH="${OUTPUT_PATH:-$PROJECT_ROOT/.rddf/state/.arch-handoff.json}"

# Idempotency: don't overwrite without --force
if [ -f "$OUTPUT_PATH" ] && [ "$FORCE" != "true" ]; then
  echo "❌ handoff already exists at $OUTPUT_PATH (use --force to overwrite)" >&2
  exit 1
fi

ADR_DIR_REL="docs/adr"
ADR_DIR_ABS="$PROJECT_ROOT/$ADR_DIR_REL"
ROADMAP_REL="roadmap.md"
ARCHITECTURE_DIR_REL="docs/architecture"

if [ ! -d "$ADR_DIR_ABS" ]; then
  echo "❌ adr_dir not found: $ADR_DIR_ABS" >&2
  echo "   Cannot reconstruct handoff without ADR directory" >&2
  exit 1
fi

# Derive adr_pattern from first existing ADR filename
ADR_PATTERN=$(find "$ADR_DIR_ABS" -maxdepth 1 -name 'ADR-*.md' -type f \
  ! -name '*-template*' 2>/dev/null | head -1 | xargs -I{} basename {} | \
  sed -E 's/[0-9]+.*//')

# Detect roadmap path
if [ ! -f "$PROJECT_ROOT/$ROADMAP_REL" ]; then
  FOUND_ROADMAP=$(find "$PROJECT_ROOT" -maxdepth 2 -name 'roadmap*.md' -type f 2>/dev/null | head -1)
  if [ -n "$FOUND_ROADMAP" ]; then
    ROADMAP_REL=$(realpath --relative-to="$PROJECT_ROOT" "$FOUND_ROADMAP")
  fi
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"

jq -n \
  --arg version "1" \
  --arg adr_dir "$ADR_DIR_REL" \
  --arg adr_pattern "${ADR_PATTERN:-ADR-}" \
  --arg roadmap_path "$ROADMAP_REL" \
  --arg architecture_dir "$ARCHITECTURE_DIR_REL" \
  --arg discovered "true" \
  --arg reconstructed_at "$(date -Iseconds)" \
  --arg reconstructed_from "filesystem-evidence" \
  '{version: ($version | tonumber),
    adr_dir: $adr_dir,
    adr_pattern: $adr_pattern,
    roadmap_path: $roadmap_path,
    architecture_dir: $architecture_dir,
    discovered: ($discovered == "true"),
    reconstructed_at: $reconstructed_at,
    reconstructed_from: $reconstructed_from}' \
  > "$OUTPUT_PATH"

# Log reconstruction event
LOG_FILE="$PROJECT_ROOT/.rddf/state/.reconstruction.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date -Iseconds)] reconstructed .arch-handoff.json from filesystem evidence" >> "$LOG_FILE"

echo "✅ reconstructed: $OUTPUT_PATH" >&2
