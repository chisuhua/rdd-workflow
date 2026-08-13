#!/usr/bin/env bash
# skills/_lib/post_flow_wrap.sh
#
# ADR-0027 §1.2 script-plane trigger: bash trap wrapper that classifies
# real subprocess failures via the python3 post_flow_analysis module.
#
# Usage:
#   # Source this file in a phase entry script and set RDDF_PHASE:
#       source skills/_lib/post_flow_wrap.sh
#       export RDDF_PHASE="guide-plan"
#       export RDDF_ERR_LOG="$(mktemp)"
#       trap 'post_flow_on_err $RDDF_PHASE' ERR
#
#   # Or wrap an explicit command:
#       source skills/_lib/post_flow_wrap.sh
#       run_with_analysis "execute" my_helper_script arg1 arg2
#
# Failure-tolerant: the trap and the python classifier invocation are
# both wrapped in || true, so a broken post-flow-analysis never breaks
# the phase it observes (mirrors _lib/post_archive_cleanup.sh pattern).

# Resolve _lib/ path relative to this script's own location so callers
# can source the file from any cwd. This file lives at
# skills/_lib/post_flow_wrap.sh, so _lib/ is at ../../_lib/ relative
# to this file's directory. For global install (copied to ~/.agents/skills/_lib/),
# fall back to ~/.agents/skills/_lib/ directly.
_POST_FLOW_WRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -d "$_POST_FLOW_WRAP_DIR/../../_lib" ]; then
    _POST_FLOW_LIB_DIR="$(cd "$_POST_FLOW_WRAP_DIR/../../_lib" && pwd)"
else
    # Global install fallback: _lib is at the parent of _POST_FLOW_WRAP_DIR
    _POST_FLOW_LIB_DIR="$(cd "$_POST_FLOW_WRAP_DIR/.." && pwd)"
fi

# post_flow_on_err <phase>
#   Trap ERR handler. Captures exit code, calls python3 classifier with
#   the current stderr log (RDDF_ERR_LOG). The python call itself is
#   wrapped in || true so a broken classifier never breaks the phase.
post_flow_on_err() {
    local phase="${1:-${RDDF_PHASE:-unknown}}"
    local code=$?
    # Skip no-op and user-cancellation exits
    [ "$code" -eq 0 ] && return 0
    [ "$code" -eq 130 ] && return 0  # SIGINT
    [ "$code" -eq 143 ] && return 0  # SIGTERM

    # Single-writer rule (spec 2026-08-12 §7): defer to orchestrator.
    # Default ON since spec 2026-08-13 §2; override with RDDF_USE_ORCHESTRATOR=no.
    if [ "${RDDF_USE_ORCHESTRATOR:-yes}" = "yes" ]; then
        return 0
    fi

    # Best-effort: find a stderr log. Prefer the env var; fall back to /dev/null.
    local err_log="${RDDF_ERR_LOG:-/dev/null}"
    [ -f "$err_log" ] || err_log="/dev/null"

    # Find project root (explicit env > PWD fallback; PWD is correct when
    # sourced from a phase script running in the third-party project).
    local project_root="${RDDF_PROJECT_ROOT:-$PWD}"

    RDDF_PHASE="$phase" \
    RDDF_EXIT_CODE="$code" \
    RDDF_STDERR_FILE="$err_log" \
    RDDF_PROJECT_ROOT="$project_root" \
    PYTHONPATH="$_POST_FLOW_LIB_DIR" \
    python3 -c "
import os, sys
from post_flow_analysis import analyze_and_report
cls = analyze_and_report(
    phase=os.environ['RDDF_PHASE'],
    exit_code=int(os.environ['RDDF_EXIT_CODE']),
    stderr_file=os.environ['RDDF_STDERR_FILE'],
    project_root=os.environ['RDDF_PROJECT_ROOT'],
)
if cls.user_hint:
    print(f'[{cls.root_cause}] {cls.user_hint}')
" 2>/dev/null || true

    return 0
}

# run_with_analysis <phase> <cmd...>
#   Explicit wrapper: run cmd, capture exit code, invoke classifier.
#   Mirrors post_flow_on_err but for one-off invocations where the
#   caller doesn't want a trap on every line.
run_with_analysis() {
    local phase="${1:?run_with_analysis requires phase name}"
    shift
    local err_log
    err_log="$(mktemp)"
    "$@" 2>"$err_log"
    local code=$?
    if [ "$code" -ne 0 ] && [ "$code" -ne 130 ] && [ "$code" -ne 143 ]; then
        local project_root="${RDDF_PROJECT_ROOT:-$PWD}"
        RDDF_PHASE="$phase" \
        RDDF_EXIT_CODE="$code" \
        RDDF_STDERR_FILE="$err_log" \
        RDDF_PROJECT_ROOT="$project_root" \
        PYTHONPATH="$_POST_FLOW_LIB_DIR" \
        python3 -c "
import os, sys
from post_flow_analysis import analyze_and_report
cls = analyze_and_report(
    phase=os.environ['RDDF_PHASE'],
    exit_code=int(os.environ['RDDF_EXIT_CODE']),
    stderr_file=os.environ['RDDF_STDERR_FILE'],
    project_root=os.environ['RDDF_PROJECT_ROOT'],
)
if cls.user_hint:
    print(f'[{cls.root_cause}] {cls.user_hint}')
" 2>/dev/null || true
    fi
    rm -f "$err_log"
    return "$code"  # preserve original exit code
}
