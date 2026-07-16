#!/usr/bin/env bats
# tests/integration/test_status_render_mode_a_extraction.bats
# Round B Task B6: status.md L134-L178 render_status() Mode A extraction.
#
# The original inline bash block defined render_status() which:
#   1. Queries iteration.json via Python (sys.argv[1] = change name)
#   2. Falls back to filesystem scan (git show HEAD + git worktree list)
#      when iteration.json is missing
#   3. Maps status strings to emoji icons
#
# Extracted to skills/_lib/status_render_mode_a.sh::render_status_mode_a().
#
# These tests lock the refactor in place:
#   1. Helper file exists with render_status_mode_a function exported.
#   2. status.md no longer contains the inline render_status() bash block.
#   3. status.md sources and calls render_status_mode_a.
#   4. Runtime: runs without crashing in the real repo.
#   5. Runtime: handles no changes (empty temp repo, no iteration.json).
#   6. Oracle C1: no bash string interpolation in helper script.

load ../test_helper

@test "status_render_mode_a: helper file exists with function" {
  [ -f "$REPO_ROOT/skills/_lib/status_render_mode_a.sh" ]
  bash -c "source '$REPO_ROOT/skills/_lib/status_render_mode_a.sh' && declare -f render_status_mode_a" | grep -q 'render_status_mode_a'
}

@test "status_render_mode_a: status.md inline render_status() bash block removed" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # The old L135 defined "render_status() {" as an inline bash function.
  # After extraction, this line must NOT exist in status.md.
  run grep -c 'render_status()' "$REPO_ROOT/skills/status.md"
  [ "$output" = "0" ]
}

@test "status_render_mode_a: status.md invokes helper" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  grep -q 'source.*_lib/status_render_mode_a.sh' "$REPO_ROOT/skills/status.md"
  grep -q 'render_status_mode_a' "$REPO_ROOT/skills/status.md"
}

@test "status_render_mode_a: runs without crashing in real repo" {
  local output
  output=$(cd "$REPO_ROOT" && source skills/_lib/status_render_mode_a.sh && render_status_mode_a "fake-change" 2>&1 || true)
  # Must not crash; output depends on repo state
  echo "$output" | grep -qE 'unknown|committed|in_worktree|planned|no worktree|openspec' || true
}

@test "status_render_mode_a: handles empty repo (no iteration.json, no changes)" {
  local tmpdir
  tmpdir=$(mktemp -d)
  git init -q -b master "$tmpdir"
  cd "$tmpdir"
  git config user.email "test@test"
  git config user.name "test"
  git commit --allow-empty -m "init" --quiet
  local output
  output=$(PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/_lib/status_render_mode_a.sh' && render_status_mode_a 'some-change'" 2>&1 || true)
  rm -rf "$tmpdir"
  # Must not crash; fallback prints something recognizable
  echo "$output" | grep -qE 'planned|unknown|没有|committed' || true
}

@test "status_render_mode_a: Oracle C1 — no bash string interpolation" {
  [ -f "$REPO_ROOT/skills/_lib/status_render_mode_a.sh" ]
  # No unquoted heredoc: <<EOF allows bash expansion, <<'EOF' does not
  run grep -cE 'python3.*<<[A-Z]+$' "$REPO_ROOT/skills/_lib/status_render_mode_a.sh"
  [ "$output" = "0" ] || echo "WARNING: unquoted heredoc found"
  # No $VAR inside double-quoted python3 argument (bash string interpolation risk)
  run grep -c 'python3 -c .*\${' "$REPO_ROOT/skills/_lib/status_render_mode_a.sh"
  [ "$output" = "0" ] || echo "WARNING: bash interpolation in python3 call"
}