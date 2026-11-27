#!/usr/bin/env bats
# test_rdd_verify_dry_run_without_iteration.bats
#
# End-to-end proof for change fix-verifier-discovery-disk-derive:
# a project with NO `.rddf/state/iteration.json` must still get a non-empty
# batch verifier queue. Before the change the queue read iteration.json and
# returned a silent `[]`, so `rddf rdd-verify` verified nothing while the
# per-change `--stage` path kept working.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d "$BATS_TMPDIR/verify-disk-XXXXXX")"
  cd "$TEST_TMP"
  git init -q
  git config user.email "t@t"
  git config user.name "T"
  # `.rddf/state/` must exist for the CLI to treat this as a rdd-workflow project,
  # but `iteration.json` deliberately does NOT — that is the case under test.
  mkdir -p "$TEST_TMP/openspec/changes/c-done" "$TEST_TMP/openspec/changes/c-half" \
           "$TEST_TMP/.rddf/state"
  echo "- [x] task" > "$TEST_TMP/openspec/changes/c-done/tasks.md"
  printf -- '- [x] a\n- [ ] b\n' > "$TEST_TMP/openspec/changes/c-half/tasks.md"
  git add . && git commit -q -m init
  # 注意：**不**创建 .rddf/state/iteration.json —— 这正是被测前提。
}

teardown() {
  cd /
  rm -rf "$TEST_TMP"
}

@test "dry-run lists the task-complete change without iteration.json" {
  run bash "$REPO_ROOT/rddf" rdd-verify --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"c-done"* ]]
  [[ "$output" != *"c-half"* ]]
}

@test "no iteration.json is not created as a side effect" {
  run bash "$REPO_ROOT/rddf" rdd-verify --dry-run
  [ "$status" -eq 0 ]
  [ ! -f "$TEST_TMP/.rddf/state/iteration.json" ]
}

@test "empty queue names the reason on stderr instead of staying silent" {
  rm -rf "$TEST_TMP/openspec/changes"/*
  run bash "$REPO_ROOT/rddf" rdd-verify --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"No eligible changes to verify (empty queue)."* ]]
  [[ "$output" == *"no active change"* ]]
}
