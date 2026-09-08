#!/usr/bin/env bats
# tests/integration/test_filter_guide_ship.bats
# filter-guide-ship-when-no-changes: suppress the ship option (rdd-builder
# 变更执行) in the guide menu when there are no active OpenSpec changes,
# preventing empty journeys.
#
# v4 migration note: guide-ship was merged into rdd-builder (ADR-0042/0043).
# The "ship" menu option now uses id="rdd-builder" (group="stages" when active
# changes exist, group="disabled"/action=None otherwise).
#
# Task 1: workflow_synthesizer._build_all_options gates the ship option
# Task 2: scan-state.sh skips ship recommendation when count is 0
# Task 3: regression smoke

load ../test_helper

# ---------------------------------------------------------------------------
# Task 1: Gate the ship option in _build_all_options() of workflow_synthesizer.py
# ---------------------------------------------------------------------------

@test "filter_guide_ship: workflow_synthesizer marks ship disabled when no active changes" {
    # FS_ACTIVE_COUNT == 0 -> ship option should be in "disabled" group
    # with action=None
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.workflow_synthesizer import _build_all_options
# empty iteration -> 0 active changes
opts = _build_all_options('rdd-arch', None, None, None, None, ())
for o in opts:
    if o.label == '变更执行':
        print('GROUP=' + str(o.group))
        print('ACTION=' + str(o.action))
        break
"
    [[ "$output" == *"GROUP=disabled"* ]]
    [[ "$output" == *"ACTION=None"* ]]
}

@test "filter_guide_ship: workflow_synthesizer keeps ship enabled when active changes exist" {
    # active_changes > 0 -> ship option stays in 'stages' group
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.workflow_synthesizer import _build_all_options
# iteration with 2 active changes (5th positional arg = iteration)
iteration = {'changes': [
    {'name': 'change-a', 'status': 'proposed'},
    {'name': 'change-b', 'status': 'proposed'},
]}
opts = _build_all_options('rdd-arch', None, None, None, iteration, ())
for o in opts:
    if o.label == '变更执行':
        print('GROUP=' + str(o.group))
        print('ACTION=' + str(o.action))
        break
"
    [[ "$output" == *"GROUP=stages"* ]]
    [[ "$output" == *"ACTION=rdd-builder"* ]]
}

# ---------------------------------------------------------------------------
# Task 2: Skip ship in scan-state.sh when FS_ACTIVE_COUNT is 0
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

@test "filter_guide_ship: scan-state.sh skips ship when FS_ACTIVE_COUNT is 0" {
    setup_scan_test
    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_state '$TEST_DIR'
        echo \"RECOMMEND=\$RECOMMEND\"
    "
    teardown_scan_test
    [[ "$output" != *"RECOMMEND=guide-ship"* ]]
    # v4: ship is rdd-builder; with 0 active changes scan_state falls through
    # to the default branch (enter 变更生成), NOT the ship branch.
    [[ "$output" == *"RECOMMEND=rdd-builder"* ]]
}

# ---------------------------------------------------------------------------
# Task 3: Regression smoke test
# ---------------------------------------------------------------------------

@test "filter_guide_ship: existing scan_state tests still pass (no regression)" {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    echo "# Roadmap" > roadmap.md
    mkdir -p openspec/changes/archive
    mkdir -p openspec/specs
    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_state '$TEST_DIR' > /dev/null 2>&1 || true
    "
    cd /workspace/project/rdd-workflow
    rm -rf "$TEST_DIR"
    [ -n "$status" ]
}

@test "filter_guide_ship: ship recommended when active change dir exists" {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    echo "# Roadmap" > roadmap.md
    mkdir -p openspec/changes/archive
    mkdir -p openspec/changes/some-active-change
    mkdir -p openspec/specs
    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_state '$TEST_DIR'
        echo \"RECOMMEND=\$RECOMMEND\"
    "
    cd /workspace/project/rdd-workflow
    rm -rf "$TEST_DIR"
    [[ "$output" == *"RECOMMEND=rdd-builder"* ]]
}
