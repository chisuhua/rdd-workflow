#!/usr/bin/env bash
# skills/_lib/orchestrator_entry.sh
#
# ADR-0027 + spec 2026-08-12: bash wrapper around `rddf orchestrate`.
# Provides orchestrator_run / orchestrator_mark / orchestrator_finalize for
# phase scripts to invoke Python orchestrator without losing failure tolerance.
#
# All Python invocations are wrapped in || true so a broken orchestrator
# never breaks the phase (matches _lib/post_archive_cleanup.sh pattern).

_ORCHESTRATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_PROJECT_ROOT_FROM_ORCH="$(cd "$_ORCHESTRATOR_DIR/../.." && pwd)"

# Bypass skills._lib shim so worktree-local modules are found.
_orchestrator_py() {
    PYTHONPATH="${_PROJECT_ROOT_FROM_ORCH}:${PYTHONPATH}" \
    RDDF_PROJECT_ROOT="${_PROJECT_ROOT_FROM_ORCH}" \
    RDDF_PHASE="${RDDF_PHASE:-unknown}" \
        python3 "${_PROJECT_ROOT_FROM_ORCH}/_lib/cli/orchestrate_cmd.py" "$@"
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