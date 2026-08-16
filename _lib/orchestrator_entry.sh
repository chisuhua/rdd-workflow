#!/usr/bin/env bash
# skills/_lib/orchestrator_entry.sh
#
# ADR-0027 + spec 2026-08-12: bash wrapper around `rddf orchestrate`.
# Provides orchestrator_run / orchestrator_mark / orchestrator_finalize for
# phase scripts to invoke Python orchestrator without losing failure tolerance.
#
# All Python invocations are wrapped in || true so a broken orchestrator
# never breaks the phase (matches _lib/post_archive_cleanup.sh pattern).

# Tool root: derived from the script's own location (wherever _lib/ lives,
# whether source checkout, global install, or project-local copy).
_ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Resolve the orchestrator script path. In a source install, the script lives
# at _lib/cli/orchestrate_cmd.py (at the repo root); in a global install it
# lives at _lib/cli/orchestrate_cmd.py (under the skills/ root). Detect by
# checking whether the cli/ subdirectory exists under _ORCHESTRATOR_DIR.
_orchestrate_script() {
    # Source install: repo root is _ORCHESTRATOR_DIR/../.. (skills/../../ = repo/)
    # Global install: script is directly under _ORCHESTRATOR_DIR/cli/
    if [ -f "${_ORCHESTRATOR_DIR}/cli/orchestrate_cmd.py" ]; then
        echo "${_ORCHESTRATOR_DIR}/cli/orchestrate_cmd.py"
    else
        echo "${_ORCHESTRATOR_DIR}/../../_lib/cli/orchestrate_cmd.py"
    fi
}

# Project root: explicit env wins, then git root of cwd, then cwd.
# This is intentionally independent of _ORCHESTRATOR_DIR so that a globally-
# installed helper can serve a third-party project without misattributing
# the project root to the tool repository.
_resolve_project_root() {
    if [ -n "${RDDF_PROJECT_ROOT:-}" ]; then
        echo "$RDDF_PROJECT_ROOT"
        return
    fi
    local git_root
    git_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" && {
        echo "$git_root"
        return
    }
    echo "$PWD"
}

_orchestrator_py() {
    local _proj_root
    _proj_root="$(_resolve_project_root)"
    local _skills_root
    _skills_root="$(cd "$_ORCHESTRATOR_DIR/.." && pwd)"
    PYTHONPATH="${_ORCHESTRATOR_DIR}:${_skills_root}:${PYTHONPATH}" \
    RDDF_PROJECT_ROOT="$_proj_root" \
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
        python3 "$(_orchestrate_script)" "$@"
}

orchestrator_run() {
    if [ "$#" -eq 0 ]; then
        echo "orchestrator_run: requires at least one argument" >&2
        return 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        "$@"
        return $?
    fi
    _orchestrator_py subprocess "$@" 2>/dev/null || "$@"
}

orchestrator_mark() {
    local name="${1:?orchestrator_mark requires name}"
    local marker="${2:-}"
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    _orchestrator_py mark-checkpoint --name "$name" --state-marker "$marker" 2>/dev/null || true
}

orchestrator_finalize() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    _orchestrator_py finalize 2>/dev/null || true
}

orchestrator_sweep() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    _orchestrator_py sweep-stale-traces 2>/dev/null || true
}

orchestrate_phase() {
    local phase="${1:?orchestrate_phase requires phase name}"
    shift
    if [ "$#" -eq 0 ]; then
        echo "orchestrate_phase: requires command after phase" >&2
        return 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        "$@"
        return $?
    fi
    _orchestrator_py subprocess "$@"
    local rc=$?
    _orchestrator_py finalize 2>/dev/null || true
    return $rc
}