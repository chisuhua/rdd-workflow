#!/usr/bin/env bats
# Verify skills/rdd-arch/scripts/roadmap_incremental_update.sh uses the bash helper
# _resolve_project_root (per fix-skill-layer-resolution-bash).
#
# The script previously manually re-implemented RDDF_PROJECT_ROOT env check +
# git probe fallback at lines 25-33. After the refactor, it MUST call the
# bash helper from skills/_lib/orchestrator_entry.sh:33 instead.
#
# Strategy: pure grep-based static checks (no execution). The bats test
# framework loads test_helper.bash which sets PROJECT_ROOT; we read the
# target script and assert structural properties.

load "../test_helper"

SCRIPT_PATH="${PROJECT_ROOT}/skills/rdd-arch/scripts/roadmap_incremental_update.sh"

@test "roadmap_incremental_update.sh: calls _resolve_project_root bash helper" {
    # The helper MUST be referenced (not manually duplicated).
    [ -f "${SCRIPT_PATH}" ]
    grep -q "_resolve_project_root" "${SCRIPT_PATH}"
}

@test "roadmap_incremental_update.sh: no manual RDDF_PROJECT_ROOT env check" {
    # The old manual error message 'RDDF_PROJECT_ROOT is required' MUST be gone.
    ! grep -q "RDDF_PROJECT_ROOT is required" "${SCRIPT_PATH}"
}

@test "roadmap_incremental_update.sh: exports RDDF_PROJECT_ROOT after resolution" {
    # The script MUST still export RDDF_PROJECT_ROOT (semantics parity).
    grep -q "export RDDF_PROJECT_ROOT" "${SCRIPT_PATH}"
}

@test "roadmap_incremental_update.sh: sources orchestrator_entry.sh" {
    # The helper MUST be sourced (not just referenced by name).
    grep -q "orchestrator_entry.sh" "${SCRIPT_PATH}"
}