#!/usr/bin/env bats

load ../test_helper

@test "terminal states include completed" {
  run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'completed' in _TERMINAL_STATES"
  [ "$status" -eq 0 ]
}

@test "terminal states include failed" {
  run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'failed' in _TERMINAL_STATES"
  [ "$status" -eq 0 ]
}

@test "terminal states include abandoned" {
  run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'abandoned' in _TERMINAL_STATES"
  [ "$status" -eq 0 ]
}

@test "terminal states include orphaned" {
  run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'orphaned' in _TERMINAL_STATES"
  [ "$status" -eq 0 ]
}
