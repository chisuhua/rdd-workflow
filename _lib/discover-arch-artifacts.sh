# skills/_lib/discover-arch-artifacts.sh
#
# Sourced library for arch-side artifact discovery (ADR-0016 Layer 1).
# Follows the same sourced-only pattern as worktree.sh / archive.sh.
#
# Globals (after source + function call):
#   DISCOVERED_<KIND>_PATH    — relative path to the artifact
#   DISCOVERED_<KIND>_FOUND   — "true" | "false"
#   DISCOVERED_<KIND>_TRIED   — integer, number of candidates attempted
#   DISCOVERED_ADR_PATTERN    — glob pattern for ADR filenames
#
# Environment overrides (TRULY highest priority — applied BEFORE existence check
# AND before default candidates; env var pointing to non-existent path is honored,
# found=false is recorded but the path is still used):
#   SPEC_WORKFLOW_ADR_DIR
#   SPEC_WORKFLOW_ROADMAP_PATH
#   SPEC_WORKFLOW_ARCHITECTURE_DIR
#   SPEC_WORKFLOW_ADR_PATTERN
#
# Conventions (fallback when no candidate found AND no env var):
#   adr_dir          = docs/adr
#   roadmap_path     = roadmap.md
#   architecture_dir = docs/architecture
#   adr_pattern      = ADR-*.md

# Guard against direct execution (sourced-only)
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "discover-arch-artifacts.sh: must be sourced, not executed" >&2
  exit 1
fi

: "${PROJECT_ROOT:=$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Default candidate lists (used only when env var is unset/empty)
_ADR_DIR_CANDIDATES_DEFAULT=(
  "docs/adr"
  "doc/adr"
  "documentation/adrs"
  "adrs"
)

_ROADMAP_CANDIDATES_DEFAULT=(
  "roadmap.md"
  "docs/roadmap.md"
  "planning/roadmap.md"
  "ROADMAP.md"
)

_ARCHITECTURE_DIR_CANDIDATES_DEFAULT=(
  "docs/architecture"
  "docs/arch"
  "documentation/architecture"
)

# Internal helper: ENV VAR SHORT-CIRCUITS — when present, the env value wins
# unconditionally (even if the path does not exist). When env is unset/empty,
# fall back to scanning default candidates.
#
# IMPORTANT: This function is called DIRECTLY, not via command substitution.
# All exports happen in the caller's shell — this avoids the bash subshell
# propagation gotcha where exports inside $(...) are lost to the parent.
#
# Args: <kind> <check_type> <default_value> <env_var_name>
#   kind         — ADR_DIR | ROADMAP | ARCHITECTURE_DIR
#   check_type   — "dir" | "file"
#   default_value — convention fallback path
#   env_var_name — name of env var to check (NOT its value)
#
# Sets globals (does NOT echo; caller echoes if needed):
#   DISCOVERED_<KIND>_PATH
#   DISCOVERED_<KIND>_FOUND
#   DISCOVERED_<KIND>_TRIED
_discover_with_override() {
  local _kind="$1"
  local _check_type="$2"
  local _default="$3"
  local _env_name="$4"
  local _result _found _tried

  # Path 1: env var short-circuits (high priority — even if path missing).
  if [ -n "${!_env_name:-}" ]; then
    _result="${!_env_name}"
    _tried=1
    if [ "$_check_type" = "dir" ] && [ -d "${PROJECT_ROOT}/${_result}" ]; then
      _found="true"
    elif [ "$_check_type" = "file" ] && [ -f "${PROJECT_ROOT}/${_result}" ]; then
      _found="true"
    else
      _found="false"
    fi
    export "DISCOVERED_${_kind}_PATH=${_result}"
    export "DISCOVERED_${_kind}_FOUND=${_found}"
    export "DISCOVERED_${_kind}_TRIED=${_tried}"
    return 0
  fi

  # Path 2: scan default candidates (first existing match wins)
  local _default_candidates=()
  case "$_kind" in
    ADR_DIR)          _default_candidates=("${_ADR_DIR_CANDIDATES_DEFAULT[@]}") ;;
    ROADMAP)          _default_candidates=("${_ROADMAP_CANDIDATES_DEFAULT[@]}") ;;
    ARCHITECTURE_DIR) _default_candidates=("${_ARCHITECTURE_DIR_CANDIDATES_DEFAULT[@]}") ;;
  esac

  _result="${_default}"
  _found="false"
  _tried=0
  for candidate in "${_default_candidates[@]}"; do
    _tried=$((_tried + 1))
    if [ "$_check_type" = "dir" ] && [ -d "${PROJECT_ROOT}/${candidate}" ]; then
      _result="${candidate}"; _found="true"; break
    elif [ "$_check_type" = "file" ] && [ -f "${PROJECT_ROOT}/${candidate}" ]; then
      _result="${candidate}"; _found="true"; break
    fi
  done

  export "DISCOVERED_${_kind}_PATH=${_result}"
  export "DISCOVERED_${_kind}_FOUND=${_found}"
  export "DISCOVERED_${_kind}_TRIED=${_tried}"
  return 0
}

# Public discover_adr_dir: calls helper DIRECTLY (no command substitution),
# promotes helper globals to canonical short names, then echoes result.
discover_adr_dir() {
  _discover_with_override ADR_DIR dir "docs/adr" SPEC_WORKFLOW_ADR_DIR
  # Promote helper globals (DISCOVERED_ADR_DIR_PATH etc.) to canonical short
  # names so existing consumers don't break.
  DISCOVERED_ADR_DIR="${DISCOVERED_ADR_DIR_PATH}"
  DISCOVERED_ADR_DIR_FOUND="${DISCOVERED_ADR_DIR_FOUND}"
  DISCOVERED_ADR_DIR_TRIED="${DISCOVERED_ADR_DIR_TRIED}"
  export DISCOVERED_ADR_DIR DISCOVERED_ADR_DIR_FOUND DISCOVERED_ADR_DIR_TRIED
  echo "${DISCOVERED_ADR_DIR}"
}

discover_roadmap() {
  _discover_with_override ROADMAP file "roadmap.md" SPEC_WORKFLOW_ROADMAP_PATH
  DISCOVERED_ROADMAP_PATH="${DISCOVERED_ROADMAP_PATH}"
  DISCOVERED_ROADMAP_FOUND="${DISCOVERED_ROADMAP_FOUND}"
  DISCOVERED_ROADMAP_TRIED="${DISCOVERED_ROADMAP_TRIED}"
  export DISCOVERED_ROADMAP_PATH DISCOVERED_ROADMAP_FOUND DISCOVERED_ROADMAP_TRIED
  echo "${DISCOVERED_ROADMAP_PATH}"
}

discover_architecture_dir() {
  _discover_with_override ARCHITECTURE_DIR dir "docs/architecture" SPEC_WORKFLOW_ARCHITECTURE_DIR
  DISCOVERED_ARCHITECTURE_DIR="${DISCOVERED_ARCHITECTURE_DIR_PATH}"
  DISCOVERED_ARCH_FOUND="${DISCOVERED_ARCHITECTURE_DIR_FOUND}"
  DISCOVERED_ARCH_TRIED="${DISCOVERED_ARCHITECTURE_DIR_TRIED}"
  export DISCOVERED_ARCHITECTURE_DIR DISCOVERED_ARCH_FOUND DISCOVERED_ARCH_TRIED
  echo "${DISCOVERED_ARCHITECTURE_DIR}"
}

# adr_pattern has no existence check — it's a glob pattern, not a path.
#
# Behavior (priority order):
#   1. SPEC_WORKFLOW_ADR_PATTERN env var → always wins (backward compat).
#   2. Auto-detect: probe <ADR_DIR>/<PATTERN> with case variants in order
#      (uppercase first, then lowercase) and pick the first one with >= 1 match.
#      This allows projects that use lowercase (e.g. "adr-*.md") to work
#      alongside the default uppercase ("ADR-*.md") without configuration.
#   3. Fallback: "ADR-*.md" (rdd-workflow convention).
discover_adr_pattern() {
  if [ -n "${SPEC_WORKFLOW_ADR_PATTERN:-}" ]; then
    DISCOVERED_ADR_PATTERN="${SPEC_WORKFLOW_ADR_PATTERN}"
    export DISCOVERED_ADR_PATTERN
    echo "${DISCOVERED_ADR_PATTERN}"
    return 0
  fi

  # Path 1.5: read .rddf/project.yaml (overrides defaults, below env var).
  if [ -f "${PROJECT_ROOT:-.}/.rddf/project.yaml" ]; then
    local _helper="${PROJECT_ROOT:-.}/_lib/project_config.sh"
    if [ -f "$_helper" ]; then
      # shellcheck disable=SC1090
      source "$_helper"
      local _yaml_pattern
      _yaml_pattern=$(project_yaml_get "adr.pattern" "")
      if [ -n "$_yaml_pattern" ]; then
        DISCOVERED_ADR_PATTERN="$_yaml_pattern"
        export DISCOVERED_ADR_PATTERN
        echo "${DISCOVERED_ADR_PATTERN}"
        return 0
      fi
    fi
  fi

  local _probe_dir="${DISCOVERED_ADR_DIR:-docs/adr}"
  local _candidates=("ADR-*.md" "adr-*.md")
  for _candidate in "${_candidates[@]}"; do
    # Use find -name (standard glob library, not affected by shell quoting
    # suppression of glob expansion that breaks plain `ls "path/*.md"`).
    local _hits
    _hits=$(find "${_probe_dir}" -maxdepth 1 -name "${_candidate}" 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ "${_hits:-0}" -gt 0 ]; then
      DISCOVERED_ADR_PATTERN="${_candidate}"
      export DISCOVERED_ADR_PATTERN
      echo "${DISCOVERED_ADR_PATTERN}"
      return 0
    fi
  done

  DISCOVERED_ADR_PATTERN="ADR-*.md"
  export DISCOVERED_ADR_PATTERN
  echo "${DISCOVERED_ADR_PATTERN}"
}

# Convenience: discover everything at once (sets all globals + suppresses echo).
discover_all() {
  discover_adr_dir          >/dev/null
  discover_roadmap          >/dev/null
  discover_architecture_dir >/dev/null
  discover_adr_pattern      >/dev/null
}
