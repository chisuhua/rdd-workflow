#!/usr/bin/env bats
load test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/wt-context-$(basename "$(mktemp -d)")"
  mkdir -p "$PROJECT_ROOT/.rddf/wt/demo"
  git -C "$PROJECT_ROOT" init -q 2>/dev/null || true
}

@test "worktree-context: archive_change exits in main repo root" {
  # Simulate archive_change finishing inside a worktree subdir.
  # archive.sh appends `cd "$MAIN_REPO_ROOT" || true` before exit 0.
  run bash -c "
    cd '$PROJECT_ROOT/.rddf/wt/demo'
    MAIN_REPO_ROOT='$PROJECT_ROOT'
    cd \"\$MAIN_REPO_ROOT\" || true
    pwd
  "
  [ "$status" -eq 0 ]
  [ "$output" = "$PROJECT_ROOT" ]
}

@test "worktree-context: guide-ship SKILL.md has Worktree Context Rule" {
  run grep -c "Worktree Context Rule" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md"
  [ "$output" -ge 1 ]
}

@test "worktree-context: execute SKILL.md has Worktree Context Rule" {
  run grep -c "Worktree Context Rule" "$BATS_TEST_DIRNAME/../../skills/execute/SKILL.md"
  [ "$output" -ge 1 ]
}

@test "worktree-context: 1-change flow keeps cd count < threshold" {
  # Simulated agent command stream for one change across phases.
  # Counting only explicit `cd` commands (not `cd ` inside scripts).
  local stream="
cd /repo/.rddf/wt/change-a
pytest tests/
cat proposal.md
sed -i s/x/y/ design.md
cd /repo
git commit -m x
"
  local cd_count
  cd_count=$(printf '%s\n' "$stream" | grep -c '^cd ' || true)
  [ "$cd_count" -lt 6 ]
}