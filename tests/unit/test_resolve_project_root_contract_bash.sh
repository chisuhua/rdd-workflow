#!/usr/bin/env bats
# Verify skills/_lib/orchestrator_entry.sh::_resolve_project_root satisfies
# the contract defined in skills/_lib/_resolve_project_root_contract.yaml
# (per consolidate-resolve-project-root-helpers).
#
# All 4 contract invariants tested:
#   - invariant_env_override (RDDF_PROJECT_ROOT env var)
#   - invariant_git_probe (git rev-parse --show-toplevel, per ADR-0033)
#   - invariant_cwd_fallback (cwd as-is when no git repo)
#   - invariant_function_signature (returns absolute path string)
#
# Strategy: source orchestrator_entry.sh in isolated env, invoke
# _resolve_project_root, assert return value matches contract.

load "../test_helper"

HELPER_FILE="${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"

# Helper: source the helper file in a clean env (per add-skill-layer
# test pollution discovery: some tests leak RDDF_PROJECT_ROOT via
# cli_main.main()'s os.environ.setdefault at _lib/cli/__main__.py:203).
source_helper() {
    # shellcheck disable=SC1090
    ( unset RDDF_PROJECT_ROOT; source "${HELPER_FILE}" )
}

@test "bash helper: invariant_env_override returns env var path" {
    # Contract: if RDDF_PROJECT_ROOT env var set, return its value.
    run bash -c "
        export RDDF_PROJECT_ROOT='/explicit/override/path'
        source '${HELPER_FILE}'
        _resolve_project_root
    "
    [ "$status" -eq 0 ]
    [ "$output" = "/explicit/override/path" ]
}

@test "bash helper: invariant_git_probe returns git toplevel" {
    # Contract: if env var unset and cwd in git repo, return git toplevel.
    # Run in a known git repo (this very repo).
    run bash -c "
        unset RDDF_PROJECT_ROOT
        cd '${PROJECT_ROOT}'
        source '${HELPER_FILE}'
        _resolve_project_root
    "
    [ "$status" -eq 0 ]
    [ "$output" = "${PROJECT_ROOT}" ]
}

@test "bash helper: invariant_cwd_fallback returns cwd when not in git" {
    # Contract: if env var unset and cwd NOT in git repo, return cwd as-is.
    # Use /tmp which is typically not a git repo.
    run bash -c "
        unset RDDF_PROJECT_ROOT
        cd /tmp
        source '${HELPER_FILE}'
        _resolve_project_root
    "
    [ "$status" -eq 0 ]
    [ "$output" = "/tmp" ]
}

@test "bash helper: invariant_function_signature returns absolute path string" {
    # Contract: returns string (non-empty) representing an absolute path.
    # Use git probe to get a known absolute path.
    run bash -c "
        unset RDDF_PROJECT_ROOT
        cd '${PROJECT_ROOT}'
        source '${HELPER_FILE}'
        _resolve_project_root
    "
    [ "$status" -eq 0 ]
    [ -n "$output" ]
    [[ "$output" == /* ]]  # starts with / (absolute path)
}