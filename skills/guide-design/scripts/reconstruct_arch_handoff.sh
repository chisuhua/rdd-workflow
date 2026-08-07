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

# Idempotency
if [ -f "$OUTPUT_PATH" ] && [ "$FORCE" != "true" ]; then
  echo "❌ handoff already exists at $OUTPUT_PATH (use --force to overwrite)" >&2
  exit 1
fi

ADR_DIR_REL="${SPEC_WORKFLOW_ADR_DIR:-docs/adr}"
ADR_DIR_ABS="$PROJECT_ROOT/$ADR_DIR_REL"
ROADMAP_REL="${SPEC_WORKFLOW_ROADMAP_PATH:-roadmap.md}"
ARCHITECTURE_DIR_REL="${SPEC_WORKFLOW_ARCHITECTURE_DIR:-docs/architecture}"

if [ ! -d "$ADR_DIR_ABS" ]; then
  echo "❌ adr_dir not found: $ADR_DIR_ABS" >&2
  echo "   Cannot reconstruct handoff without ADR directory" >&2
  exit 1
fi

# Count ADRs (exclude templates) — required by schema
ADR_COUNT=0
for adr_file in "$ADR_DIR_ABS"/ADR-*.md; do
  [ -f "$adr_file" ] || continue
  [[ "$(basename "$adr_file")" == *template* ]] && continue
  ADR_COUNT=$((ADR_COUNT + 1))
done

# Extract completed_adr_ids (4-digit zero-padded)
COMPLETED_IDS=()
for adr_file in "$ADR_DIR_ABS"/ADR-*.md; do
  [ -f "$adr_file" ] || continue
  [[ "$(basename "$adr_file")" == *template* ]] && continue
  if [[ "$(basename "$adr_file")" =~ ^ADR-([0-9]{4}) ]]; then
    COMPLETED_IDS+=("${BASH_REMATCH[1]}")
  fi
done

# Detect roadmap
ROADMAP_EXISTS="false"
if [ ! -f "$PROJECT_ROOT/$ROADMAP_REL" ]; then
  FOUND_ROADMAP=$(find "$PROJECT_ROOT" -maxdepth 2 -name 'roadmap*.md' -type f 2>/dev/null | head -1)
  if [ -n "$FOUND_ROADMAP" ]; then
    if command -v realpath >/dev/null 2>&1 && realpath --help 2>&1 | grep -q -- '--relative-to'; then
      ROADMAP_REL=$(realpath --relative-to="$PROJECT_ROOT" "$FOUND_ROADMAP")
    else
      ROADMAP_REL="${FOUND_ROADMAP#$PROJECT_ROOT/}"
    fi
  fi
fi
[ -f "$PROJECT_ROOT/$ROADMAP_REL" ] && ROADMAP_EXISTS="true"

# Determine current_phase from roadmap.md first heading if extractable, else "default"
CURRENT_PHASE="default"
if [ -f "$PROJECT_ROOT/$ROADMAP_REL" ]; then
  EXTRACTED=$(head -50 "$PROJECT_ROOT/$ROADMAP_REL" 2>/dev/null | \
    grep -E '^#[[:space:]]*Phase[[:space:]]*[0-9]+' | head -1 | \
    sed -E 's/^#[[:space:]]*Phase[[:space:]]*([0-9]+).*/phase-\1/' || true)
  [ -n "$EXTRACTED" ] && CURRENT_PHASE="$EXTRACTED"
fi

NOW_ISO="$(date -Iseconds)"

mkdir -p "$(dirname "$OUTPUT_PATH")"

# Atomic write: build JSON in tmp, validate, then mv
TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

COMPLETED_IDS_JQ="[]"
if ((${#COMPLETED_IDS[@]} > 0)); then
  COMPLETED_IDS_JQ=$(printf '"%s",' "${COMPLETED_IDS[@]}")
  COMPLETED_IDS_JQ="[${COMPLETED_IDS_JQ%,}]"
fi

jq -n \
  --arg version "1" \
  --arg adr_dir "$ADR_DIR_REL" \
  --arg adr_pattern "ADR-*.md" \
  --arg roadmap_path "$ROADMAP_REL" \
  --arg architecture_dir "$ARCHITECTURE_DIR_REL" \
  --argjson discovered_adr_dir_found "$([ -d "$ADR_DIR_ABS" ] && echo true || echo false)" \
  --argjson discovered_adr_dir_created "false" \
  --argjson discovered_adr_dir_candidates 1 \
  --argjson discovered_roadmap_found "$ROADMAP_EXISTS" \
  --argjson discovered_roadmap_created "false" \
  --argjson discovered_roadmap_candidates 1 \
  --argjson discovered_arch_dir_found "$([ -d "$PROJECT_ROOT/$ARCHITECTURE_DIR_REL" ] && echo true || echo false)" \
  --argjson discovered_arch_dir_created "false" \
  --argjson discovered_arch_dir_candidates 1 \
  --arg arch_complete_at "$NOW_ISO" \
  --argjson adr_count "$ADR_COUNT" \
  --argjson completed_adr_ids "$COMPLETED_IDS_JQ" \
  --argjson roadmap_exists "$ROADMAP_EXISTS" \
  --arg current_phase "$CURRENT_PHASE" \
  --arg plan_started_at "$NOW_ISO" \
  --arg reconstructed_at "$NOW_ISO" \
  --arg reconstructed_from "filesystem-evidence" \
  '{version: ($version | tonumber),
    arch_complete_at: $arch_complete_at,
    adr_count: $adr_count,
    completed_adr_ids: $completed_adr_ids,
    roadmap_exists: $roadmap_exists,
    current_phase: $current_phase,
    plan_started_at: $plan_started_at,
    adr_dir: $adr_dir,
    roadmap_path: $roadmap_path,
    architecture_dir: $architecture_dir,
    adr_pattern: $adr_pattern,
    discovered: {
      adr_dir: {found: $discovered_adr_dir_found, created: $discovered_adr_dir_created, candidates_tried: $discovered_adr_dir_candidates},
      roadmap_path: {found: $discovered_roadmap_found, created: $discovered_roadmap_created, candidates_tried: $discovered_roadmap_candidates},
      architecture_dir: {found: $discovered_arch_dir_found, created: $discovered_arch_dir_created, candidates_tried: $discovered_arch_dir_candidates}
    },
    reconstructed_at: $reconstructed_at,
    reconstructed_from: $reconstructed_from}' \
  > "$TMP_JSON"

jq -e . "$TMP_JSON" >/dev/null
mv "$TMP_JSON" "$OUTPUT_PATH"
trap - EXIT

# Log reconstruction event
LOG_FILE="$PROJECT_ROOT/.rddf/state/.reconstruction.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$NOW_ISO] reconstructed .arch-handoff.json from filesystem evidence" >> "$LOG_FILE"

echo "✅ reconstructed: $OUTPUT_PATH" >&2
