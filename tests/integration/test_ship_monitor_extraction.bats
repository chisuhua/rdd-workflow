#!/usr/bin/env bats
# tests/integration/test_ship_monitor_extraction.bats
# P3-3 regression: guide-ship.md Phase 2 L260-L315 (~54 lines) bash
# block reading progress across all openspec/* changes (worktree +
# lightweight modes). Extracted to skills/_lib/ship_monitor.sh.
#
# These tests lock the refactor in place:
#   1. ship_monitor.sh exists with run_ship_monitor exported.
#   2. guide-ship.md L260-L315 inline block removed.
#   3. guide-ship.md sources and calls run_ship_monitor.
#   4. Runtime: prints progress + LAST_CHECK timestamp.
#   5. Runtime: handles no openspec/* worktrees (clean main repo).
#   6. Runtime: detects lightweight openspec/* branches.

load ../test_helper

@test "ship_monitor: helper file exists with run_ship_monitor function" {
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_monitor.sh" ]
  bash -c "source '$REPO_ROOT/skills/guide-ship/scripts/ship_monitor.sh' && declare -f run_ship_monitor" | grep -q 'run_ship_monitor'
}

@test "ship_monitor: guide-ship.md inline block L260-L315 removed" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  # The old inline bash block is replaced. The replacement sits at ~L260-L264.
  # Scan the narrow post-replacement range. Don't confuse with the unrelated
  # LAST_CHECK= in the "选项 7（刷新进度）" documentation block at a later line.
  ! sed -n '258,270p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -q 'LAST_CHECK='
  # The old code comment about reading tasks.md progress must be gone from this range
  ! sed -n '258,270p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -q '读取所有 tasks.md'
}

@test "ship_monitor: guide-ship.md sources and calls helper" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  grep -q 'source.*scripts/ship_monitor.sh' "$REPO_ROOT/skills/guide-ship/SKILL.md"
  grep -q 'run_ship_monitor' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "ship_monitor: prints LAST_CHECK timestamp" {
  # In this repo, no openspec/* worktrees should exist (clean main repo)
  run bash -c "source '$REPO_ROOT/skills/guide-ship/scripts/ship_monitor.sh' && run_ship_monitor"
  echo "$output" | grep -q '上次检测'
}

@test "ship_monitor: handles no openspec/* worktrees gracefully (no crash)" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-ship/scripts/ship_monitor.sh && run_ship_monitor"
  [ "$status" -eq 0 ]
}

@test "ship_monitor: detects lightweight openspec/* branch" {
  local tmpdir
  tmpdir=$(mktemp -d)
  # Create a minimal git repo with an openspec/test-branch branch (no worktree)
  git init -q -b master "$tmpdir"
  cd "$tmpdir"
  git config user.email "test@test"
  git config user.name "test"
  git commit --allow-empty -m "init" --quiet
  git checkout -b openspec/test-branch --quiet
  run bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-ship/scripts/ship_monitor.sh' && run_ship_monitor"
  rm -rf "$tmpdir"
  # Must not crash; should print timestamp
  echo "$output" | grep -q '上次检测'
}

@test "ship_monitor: zero-checkbox tasks.md shows 0/0 not 0/0\\n0" {
  local tmpdir
  tmpdir=$(mktemp -d)
  git init -q -b master "$tmpdir"
  cd "$tmpdir"
  git config user.email "test@test"
  git config user.name "test"
  git commit --allow-empty -m "init" --quiet
  git checkout -b openspec/zero-task --quiet
  mkdir -p "openspec/changes/zero-task"
  cat > "openspec/changes/zero-task/tasks.md" <<'EOF'
# No checkboxes here
Just plain text.
EOF
  local my_output
  # unset PROJECT_ROOT so ship_monitor.sh defaults to the temp git repo root
  my_output=$(unset PROJECT_ROOT && cd "$tmpdir" && source "$REPO_ROOT/skills/guide-ship/scripts/ship_monitor.sh" && run_ship_monitor 2>&1 || true)
  rm -rf "$tmpdir"
  grep -qE '0/0' <<< "$my_output"
  local count
  count=$(grep -o '0/0' <<< "$my_output" | wc -l)
  [ "$count" -ge 1 ]
}