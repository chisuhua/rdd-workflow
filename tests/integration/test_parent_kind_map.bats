#!/usr/bin/env bats

load ../test_helper

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$TEST_TMPDIR"
    mkdir -p "$PROJECT_ROOT/.rddf/state"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "PR2: stage_arch resolves parent to stage_guide when guide exists (via hooks.sh)" {
    run bash -c "
        set -e
        export PROJECT_ROOT='$PROJECT_ROOT'
        export OPENCODE_SESSION_ID='ses_A'
        export RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes
        source '$BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry 'stage_guide' 'guide-orchestrator' 'guide' 'observer'
        rddf_session_hook_entry 'stage_arch' 'guide-arch' 'arch' 'work'
    "
    [ "$status" -eq 0 ]

    # Verify linkage
    python3 -c "
import sys
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$TEST_TMPDIR/.rddf/state/sessions.json')
sessions = coord._store.read_unlocked()['sessions']
arch = [s for s in sessions if s['kind'] == 'stage_arch'][0]
guide = [s for s in sessions if s['kind'] == 'stage_guide'][0]
assert arch['parent_session_id'] == guide['session_id'], 'parent link broken'
"
    [ "$status" -eq 0 ]
}

@test "PR2: stage_arch parent is null when no stage_guide exists (backward compat)" {
    run bash -c "
        set -e
        export PROJECT_ROOT='$TEST_TMPDIR'
        export OPENCODE_SESSION_ID='ses_A'
        source '$BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry 'stage_arch' 'guide-arch' 'arch' 'work'
    "
    [ "$status" -eq 0 ]

    python3 -c "
import sys
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$TEST_TMPDIR/.rddf/state/sessions.json')
sessions = coord._store.read_unlocked()['sessions']
arch = [s for s in sessions if s['kind'] == 'stage_arch'][0]
assert arch['parent_session_id'] is None, 'expected None parent'
"
    [ "$status" -eq 0 ]
}

@test "PR2: owner-scoped parent lookup filters other owners (Metis B3)" {
    # Test the underlying list_sessions owner-scoped filter directly (what hooks.sh PYEOF uses).
    # Avoids bash -c + bats $status quirk for long multi-step sequences.
    run python3 -c "
import sys, os
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$TEST_TMPDIR/.rddf/state/sessions.json')
# ses_other creates stage_arch
coord.create_session(kind='stage_arch', owner_opencode_session_id='ses_other',
                     goal={'intent': 'guide-arch'})
# ses_main creates stage_guide
coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_main',
                     goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
# Owner-scoped lookup: ses_main looking for active stage_arch should find NONE (Metis B3 fix)
parents = coord.list_sessions(kind='stage_arch', owner_opencode_session_id='ses_main', state='active')
assert len(parents) == 0, f'owner filter broken: got {len(parents)} stage_arch for ses_main, expected 0'
"
    [ "$status" -eq 0 ]
}