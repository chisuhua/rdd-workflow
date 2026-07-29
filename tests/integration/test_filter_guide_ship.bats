#!/usr/bin/env bats
# tests/integration/test_filter_guide_ship.bats
# filter-guide-ship-when-no-changes: suppress guide-ship option in the
# guide menu when there are no active OpenSpec changes, preventing empty
# journeys.
#
# Task 1: workflow_synthesizer._build_all_options gates guide-ship
# Task 2: scan-state.sh skips guide-ship recommendation when count is 0
# Task 3: regression smoke

load ../test_helper

# ---------------------------------------------------------------------------
# Task 1: Gate guide-ship in _build_all_options() of workflow_synthesizer.py
# ---------------------------------------------------------------------------

@test "filter_guide_ship: workflow_synthesizer marks guide-ship disabled when no active changes" {
    # FS_ACTIVE_COUNT == 0 -> guide-ship should be in "disabled" group
    # with action=None
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.workflow_synthesizer import _build_all_options
# empty iteration -> 0 active changes
opts = _build_all_options('guide-arch', None, None, None, None, ())
for o in opts:
    if o.id == 'guide-ship':
        print('GROUP=' + str(o.group))
        print('ACTION=' + str(o.action))
        break
"
    [[ "$output" == *"GROUP=disabled"* ]]
    [[ "$output" == *"ACTION=None"* ]]
}

@test "filter_guide_ship: workflow_synthesizer keeps guide-ship enabled when active changes exist" {
    # active_changes > 0 -> guide-ship stays in 'stages' group
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.workflow_synthesizer import _build_all_options
# iteration with 2 active changes
iteration = {'changes': [
    {'name': 'change-a', 'status': 'proposed'},
    {'name': 'change-b', 'status': 'proposed'},
]}
opts = _build_all_options('guide-arch', None, None, iteration, None, ())
for o in opts:
    if o.id == 'guide-ship':
        print('GROUP=' + str(o.group))
        print('ACTION=' + str(o.action))
        break
"
    [[ "$output" == *"GROUP=stages"* ]]
    [[ "$output" == *"ACTION=guide-ship"* ]]
}

# ---------------------------------------------------------------------------
# Task 2: Skip guide-ship in scan-state.sh when FS_ACTIVE_COUNT is 0
# ---------------------------------------------------------------------------

setup_scan_test() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    # No handoff files -> skip paths 1-2.5
    # roadmap.md present -> skip path 7
    # openspec/changes/ with only archive/ -> FS_ACTIVE_COUNT == 0
    echo "# Roadmap" > roadmap.md
    mkdir -p openspec/changes/archive
    mkdir -p openspec/specs
}

teardown_scan_test() {
    cd /workspace/project/rdd-workflow
    rm -rf "$TEST_DIR"
}

@test "filter_guide_ship: scan-state.sh skips guide-ship when FS_ACTIVE_COUNT is 0" {
    setup_scan_test
    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_state '$TEST_DIR'
        echo \"RECOMMEND=\$RECOMMEND\"
    "
    teardown_scan_test
    [[ "$output" == *"RECOMMEND=guide-ship"* ]] && return 1
    [[ "$output" != *"RECOMMEND=guide-ship"* ]]
}
