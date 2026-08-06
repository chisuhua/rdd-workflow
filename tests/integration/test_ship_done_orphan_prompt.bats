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
    source "$REPO_ROOT/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: returns 0 when sessions.json is corrupt" {
  _make_sessions_json "$repo" '{not valid}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: counts only orphaned sessions" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_000000000001","state":"orphaned"},{"session_id":"rds_000000000002","state":"active"},{"session_id":"rds_000000000003","state":"completed"}]}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}

@test "ship-done: 3 orphans + 0 changes shows option 5 and lists ids" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_a1b5","state":"orphaned"},{"session_id":"rds_1221","state":"orphaned"},{"session_id":"rds_0569","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"✅ 所有 changes 已处理完毕"* ]]
  [[ "$output" == *"⚠️ 发现 3 个 orphaned rddf-sessions (rds_a1b5, rds_1221, rds_0569)"* ]]
  [[ "$output" == *"5. 🧹 清理 3 个 orphaned sessions"* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: 0 orphans + 0 changes matches baseline output" {
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" != *"orphaned"* ]]
  [[ "$output" != *"5."* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: 1 orphan + 1 change shows 还有 header and option 5" {
  mkdir -p "$repo/openspec/changes/example-change"
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_9999","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📋 还有"* ]]
  [[ "$output" == *"⚠️ 发现 1 个 orphaned rddf-sessions (rds_9999)"* ]]
  [[ "$output" == *"5. 🧹 清理 1 个 orphaned sessions"* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: more than 3 orphans truncates list with +N more" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_0001","state":"orphaned"},{"session_id":"rds_0002","state":"orphaned"},{"session_id":"rds_0003","state":"orphaned"},{"session_id":"rds_0004","state":"orphaned"},{"session_id":"rds_0005","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"rds_0001, rds_0002, rds_0003 ... +2 more"* ]]
  [[ "$output" != *"rds_0004"* ]]
  [[ "$output" != *"rds_0005"* ]]
}
