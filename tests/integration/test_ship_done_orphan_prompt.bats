#!/usr/bin/env bats
# tests/integration/test_ship_done_orphan_prompt.bats
# Matrix regression tests for ship-done orphan prompt.

load ../test_helper

_make_sessions_json() {
  local repo="$1"
  shift
  mkdir -p "$repo/.rddf/state"
  printf '%s' "$*" > "$repo/.rddf/state/sessions.json"
}

_run_check_remaining_work() {
  local repo="$1"
  bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/guide-ship/scripts/ship_done.sh"
    check_remaining_work "$1"
  ' _ "$repo"
}

setup() {
  repo=$(mktemp -d)
  git init -q "$repo"
  git -C "$repo" config user.email "t@t"
  git -C "$repo" config user.name "t"
  touch "$repo/init"
  git -C "$repo" add init && git -C "$repo" commit -q -m init
}

teardown() {
  rm -rf "$repo"
}

@test "count_orphaned_sessions: returns 0 when sessions.json is missing" {
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: returns 0 when sessions.json is corrupt" {
  _make_sessions_json "$repo" '{not valid}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: counts only orphaned sessions" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_000000000001","state":"orphaned"},{"session_id":"rds_000000000002","state":"active"},{"session_id":"rds_000000000003","state":"completed"}]}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}
