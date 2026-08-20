#!/usr/bin/env bash
# skills/_lib/discover_roadmap_fragments.sh
#
# Sourceable helper for ADR-0016 v2: discover roadmap fragments directory.
# Project-level override that coexists with the global discover-arch-artifacts.sh.
# Does NOT modify the global ~/.agents/skills/_lib/discover-arch-artifacts.sh
# (which is a user-level install shared across all projects).
#
# Globals (after source + function call):
#   DISCOVERED_ROADMAP_FRAGMENTS_DIR     — relative path to fragments dir
#   DISCOVERED_ROADMAP_FRAGMENTS_FOUND   — "true" | "false"
#   DISCOVERED_ROADMAP_FRAGMENTS_TRIED   — integer
#
# Environment overrides (highest priority):
#   SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR
#
# Conventions (fallback when no candidate found AND no env var):
#   roadmap_fragments_dir = .rddf/roadmap
#
# Design notes (per add-hierarchical-roadmap-structure proposal):
#   - Priority order: env var > existing .rddf/roadmap > .rddf/roadmap.md-derived > default
#   - This file is project-local; the user-level discover-arch-artifacts.sh is untouched
#     (preserves "do not pollute global install" invariant from AGENTS.md Round A safety fixes).

# Guard against direct execution (sourced-only)
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "discover_roadmap_fragments.sh: must be sourced, not executed" >&2
  exit 1
fi

: "${PROJECT_ROOT:=$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

_ROADMAP_FRAGMENTS_CANDIDATES_DEFAULT=(
  ".rddf/roadmap"
)

# discover_roadmap_fragments_dir: discover fragments dir with env-var override.
# Mirrors the pattern from ~/.agents/skills/_lib/discover-arch-artifacts.sh::discover_roadmap.
discover_roadmap_fragments_dir() {
  local _result _found _tried _check_path

  # Path 1: env var short-circuits
  if [ -n "${SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR:-}" ]; then
    _result="${SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR}"
    _tried=1
    # For existence check, use absolute path directly (don't prefix PROJECT_ROOT if absolute)
    if [[ "${_result}" = /* ]]; then
      _check_path="${_result}"
    else
      _check_path="${PROJECT_ROOT}/${_result}"
    fi
    if [ -d "${_check_path}" ]; then
      _found="true"
    else
      _found="false"
    fi
    export DISCOVERED_ROADMAP_FRAGMENTS_DIR="${_result}"
    export DISCOVERED_ROADMAP_FRAGMENTS_FOUND="${_found}"
    export DISCOVERED_ROADMAP_FRAGMENTS_TRIED="${_tried}"
    echo "${_result}"
    return 0
  fi

  # Path 2: scan default candidates
  _result=".rddf/roadmap"
  _found="false"
  _tried=0
  for candidate in "${_ROADMAP_FRAGMENTS_CANDIDATES_DEFAULT[@]}"; do
    _tried=$((_tried + 1))
    if [ -d "${PROJECT_ROOT}/${candidate}" ]; then
      _result="${candidate}"
      _found="true"
      break
    fi
  done

  export DISCOVERED_ROADMAP_FRAGMENTS_DIR="${_result}"
  export DISCOVERED_ROADMAP_FRAGMENTS_FOUND="${_found}"
  export DISCOVERED_ROADMAP_FRAGMENTS_TRIED="${_tried}"
  echo "${_result}"
  return 0
}

# Export for subshells (best-effort; bash 4+)
export -f discover_roadmap_fragments_dir 2>/dev/null || true
