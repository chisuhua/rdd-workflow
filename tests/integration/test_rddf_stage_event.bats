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

@test "PR2: EventsLog.append_event writes phase_started (AC-7 unit-level)" {
    python3 -c "
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
from skills.rddf_session.scripts.events_log import EventsLog
log = EventsLog(os.path.join('$PROJECT_ROOT', '.rddf/state/events.jsonl'))
log.append_event(
    event_type='phase_started', severity='info', message='test event 1',
    session_id='rds_a', kind='stage_arch',
    parent_session_id=None, owner_opencode_session_id='ses_A',
)
"
    events_file="$TEST_TMPDIR/.rddf/state/events.jsonl"
    [ -f "$events_file" ]
    grep -q '"event_type": "phase_started"' "$events_file"
    grep -q '"kind": "stage_arch"' "$events_file"
}

@test "PR2: EventsLog.append_event writes phase_completed (AC-7 unit-level)" {
    python3 -c "
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
from skills.rddf_session.scripts.events_log import EventsLog
log = EventsLog(os.path.join('$PROJECT_ROOT', '.rddf/state/events.jsonl'))
log.append_event(event_type='phase_started', severity='info', message='started',
                 session_id='rds_a', kind='stage_arch',
                 parent_session_id=None, owner_opencode_session_id='ses_A')
log.append_event(event_type='phase_completed', severity='info', message='arch-done',
                 session_id='rds_a', kind='stage_arch',
                 parent_session_id=None, owner_opencode_session_id='ses_A')
"
    events_file="$TEST_TMPDIR/.rddf/state/events.jsonl"
    [ -f "$events_file" ]
    grep -q '"event_type": "phase_completed"' "$events_file"
    grep -q 'arch-done' "$events_file"
}

@test "PR2: hooks.sh rddf_session_hook_entry writes phase_started (AC-7 wiring)" {
    bash -c "
set -e
export PROJECT_ROOT='$PROJECT_ROOT'
export OPENCODE_SESSION_ID='ses_A'
export RDDF_EVENTS_LOG_ENABLED='yes'
source '$BATS_TEST_DIRNAME/../../skills/rddf-session/scripts/rddf_session_hooks.sh'
rddf_session_hook_entry 'stage_arch' 'guide-arch' 'test' 'outcome'
"
    events_file="$TEST_TMPDIR/.rddf/state/events.jsonl"
    [ -f "$events_file" ]
    grep -q '"event_type": "phase_started"' "$events_file"
}