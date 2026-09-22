#!/usr/bin/env bash
# skills/rdd-planner/scripts/planner_objective_revise.sh
# Interactive sprint-review revise entrypoint for objective files.
#
# Owned by rdd-planner (per ADR-0028 + ADR-0054): only rdd-planner writes
# objective files. This script wraps skills/roadmap/scripts/objective_revise.sh
# with a planner-flavored prompt flow:
#   1. List current objectives
#   2. Pick target objective (or pass as $1)
#   3. Pick ledger kind (5-value enum)
#   4. Enter content / decision / reason
#   5. Append §11 row + bump last_revised (via objective_revise.sh)
#
# Non-interactive mode: pass all flags directly (CI / agent use).
#
# Usage:
#   bash planner_objective_revise.sh [<objective-id>]
#       [--kind deferral-rationale|go-decision|sprint-review|scope-change|adr-amendment]
#       [--content "<text>"] [--decision "<text>"] [--reason "<text>"]
#
# Env vars:
#   PROJECT_ROOT   Repo root (default: git toplevel)
#   RDDF_NONINTERACTIVE=1  Skip prompts, require all flags (fails if missing)
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export PROJECT_ROOT

# Resolve helper from THIS file, not PROJECT_ROOT: tests pin PROJECT_ROOT to temp dirs.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REVISE_SH="$SCRIPT_DIR/../roadmap/scripts/objective_revise.sh"
KIND_ENUM_VALUES="deferral-rationale|go-decision|sprint-review|scope-change|adr-amendment"

# Parse args
OBJ_ID="${1:-}"
shift || true
KIND=""
CONTENT=""
DECISION=""
REASON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kind)     KIND="${2:-}"; shift 2 ;;
    --content)  CONTENT="${2:-}"; shift 2 ;;
    --decision) DECISION="${2:-}"; shift 2 ;;
    --reason)   REASON="${2:-}"; shift 2 ;;
    *) echo "❌ unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Interactive mode (TTY) — prompt for missing values
if [[ "${RDDF_NONINTERACTIVE:-}" != "1" && -t 0 ]]; then
  if [[ -z "$OBJ_ID" ]]; then
    echo "现有 objectives（.rddf/roadmap/objectives/）:"
    if [[ -d "$PROJECT_ROOT/.rddf/roadmap/objectives" ]]; then
      ls "$PROJECT_ROOT/.rddf/roadmap/objectives"/*.md 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/.md$//' || true
    fi
    printf "选择 objective id: "
    read -r OBJ_ID
  fi
  if [[ -z "$KIND" ]]; then
    printf "选择台账 kind (%s): " "$KIND_ENUM_VALUES"
    read -r KIND
  fi
  if [[ -z "$CONTENT" ]]; then
    printf "内容: "
    read -r CONTENT
  fi
  if [[ -z "$DECISION" ]]; then
    printf "Decision/调整 (可空): "
    read -r DECISION || DECISION=""
  fi
  if [[ -z "$REASON" ]]; then
    printf "原因 (可空): "
    read -r REASON || REASON=""
  fi
fi

# Validate required
if [[ -z "$OBJ_ID" ]]; then
  echo "❌ objective id 必填" >&2
  exit 2
fi
if [[ -z "$KIND" ]]; then
  echo "❌ --kind 必填 (one of: $KIND_ENUM_VALUES)" >&2
  exit 2
fi
if [[ -z "$CONTENT" ]]; then
  echo "❌ --content 必填" >&2
  exit 2
fi

# Delegate to objective_revise.sh (single writer entrypoint under roadmap scripts)
export LEDGER_KIND="$KIND" LEDGER_CONTENT="$CONTENT" LEDGER_DECISION="$DECISION" LEDGER_REASON="$REASON"
bash "$REVISE_SH" "$OBJ_ID" --kind "$KIND" --content "$CONTENT" --decision "$DECISION" --reason "$REASON"

echo "✅ planner revise complete: $OBJ_ID (kind=$KIND)"
