#!/usr/bin/env bats

load ../test_helper

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$TEST_TMPDIR"
    mkdir -p "$TEST_TMPDIR/.rddf/state"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "PR3: guide_entry creates stage_guide session with goal.last_seen_offset=0 (AC-8)" {
    run python3 -c "
import sys, os
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join('$TEST_TMPDIR', '.rddf/state/sessions.json'))
sid = coord.create_session(
    kind='stage_guide',
    owner_opencode_session_id='ses_A',
    goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0},
    parent_session_id=None,
)
assert sid.startswith('rds_')
sessions = coord._store.read_unlocked()['sessions']
guides = [s for s in sessions if s['kind'] == 'stage_guide']
assert len(guides) == 1, f'expected 1 stage_guide, got {len(guides)}'
assert guides[0]['goal']['last_seen_offset'] == 0
assert guides[0]['goal']['intent'] == 'guide-orchestrator'
assert guides[0]['owner_opencode_session_id'] == 'ses_A'
"
    [ "$status" -eq 0 ]
}

@test "PR3: guide_close marks stage_guide completed (AC-8)" {
    run python3 -c "
import sys, os
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join('$TEST_TMPDIR', '.rddf/state/sessions.json'))
sid = coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                            goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
coord.update_session_status(sid, 'completed', end_reason='guide-exit')
sessions = coord._store.read_unlocked()['sessions']
guides = [s for s in sessions if s['kind'] == 'stage_guide']
assert len(guides) == 1
assert guides[0]['state'] == 'completed', f'expected completed, got {guides[0][\"state\"]}'
assert guides[0]['end_reason'] == 'guide-exit'
"
    [ "$status" -eq 0 ]
}

@test "PR3: guide polling contract — no active children skips events.jsonl read (AC-9)" {
    run python3 -c "
import sys, os
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join('$TEST_TMPDIR', '.rddf/state/sessions.json'))
coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                     goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
other_active = [s for s in coord.list_sessions(state='active') if s.owner_opencode_session_id != 'ses_A']
assert len(other_active) == 0, f'expected 0 other-owner active, got {len(other_active)}'
events_path = os.path.join('$TEST_TMPDIR', '.rddf/state/events.jsonl')
assert not os.path.exists(events_path), 'events.jsonl should not exist when no events written'
"
    [ "$status" -eq 0 ]
}

@test "PR3: guide polling contract — active child from other owner triggers events read (AC-9)" {
    run env RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes python3 -c "
import sys, os
os.environ['RDDF_ALLOW_CROSS_STAGE_PARALLEL'] = 'yes'
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.events_log import EventsLog
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join('$TEST_TMPDIR', '.rddf/state/sessions.json'))
coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                     goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
coord.create_session(kind='stage_arch', owner_opencode_session_id='ses_B',
                     goal={'intent': 'guide-arch'})
log = EventsLog(os.path.join('$TEST_TMPDIR', '.rddf/state/events.jsonl'))
log.append_event(event_type='phase_started', severity='info',
                 message='ses_B started arch', session_id='rds_x',
                 kind='stage_arch', parent_session_id=None,
                 owner_opencode_session_id='ses_B')
events = log.read_since(offset=0)
assert len(events) == 1, f'expected 1 event, got {len(events)}'
assert events[0]['context']['owner_opencode_session_id'] == 'ses_B'
"
    [ "$status" -eq 0 ]
}

@test "PR3: scan-state.sh no longer mutates sessions.json (AC-11)" {
    python3 -c "
import sys
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$TEST_TMPDIR/.rddf/state/sessions.json')
coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                     goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
"
    sessions_before=$(wc -c < "$TEST_TMPDIR/.rddf/state/sessions.json")
    run bash -c "
        set -e
        export PROJECT_ROOT='$TEST_TMPDIR'
        export OPENCODE_SESSION_ID='ses_A'
        source /workspace/project/rdd-workflow/skills/guide/scripts/scan-state.sh
        scan_session_binding '$TEST_TMPDIR' 2>/dev/null || true
    "
    [ "$status" -eq 0 ]
    sessions_after=$(wc -c < "$TEST_TMPDIR/.rddf/state/sessions.json")
    [ "$sessions_before" = "$sessions_after" ]
}

@test "PR3: same-owner guide session reuse (idempotent on re-entry)" {
    run python3 -c "
import sys, os
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join('$TEST_TMPDIR', '.rddf/state/sessions.json'))
sid1 = coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                             goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
sid2 = coord.create_session(kind='stage_guide', owner_opencode_session_id='ses_A',
                             goal={'intent': 'guide-orchestrator', 'last_seen_offset': 0})
assert sid1 == sid2, f'same-owner reuse failed: {sid1} vs {sid2}'
sessions = coord._store.read_unlocked()['sessions']
guides = [s for s in sessions if s['kind'] == 'stage_guide']
assert len(guides) == 1, f'expected 1 guide, got {len(guides)}'
"
    [ "$status" -eq 0 ]
}

@test "PR3: rddf_session_hook_guide_entry is gated by RDDF_GUIDE_SESSION_ENABLED (rollback)" {
    run env RDDF_GUIDE_SESSION_ENABLED=false bash -c "
        set -e
        export PROJECT_ROOT='$TEST_TMPDIR'
        export OPENCODE_SESSION_ID='ses_A'
        export RDDF_GUIDE_SESSION_ENABLED=false
        source /workspace/project/rdd-workflow/skills/rddf-session/scripts/rddf_session_hooks.sh
        rddf_session_hook_guide_entry
    "
    [ "$status" -eq 0 ]
    # Should NOT have created a stage_guide session
    if [ -f "$TEST_TMPDIR/.rddf/state/sessions.json" ]; then
        run python3 -c "
import sys
sys.path.insert(0, '$TEST_TMPDIR')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$TEST_TMPDIR/.rddf/state/sessions.json')
guides = [s for s in coord.list_sessions() if s['kind'] == 'stage_guide']
assert len(guides) == 0, f'expected 0 guides with RDDF_GUIDE_SESSION_ENABLED=false, got {len(guides)}'
"
        [ "$status" -eq 0 ]
    fi
}