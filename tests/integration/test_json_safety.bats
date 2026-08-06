#!/usr/bin/env bats
# tests/integration/test_json_safety.bats
#
# T22 — json.load error handling (P2-3)
# Tests verify the safe_python_json helper (from _lib/state.sh) returns
# "unknown" gracefully for missing / malformed / empty JSON files, and that
# the consumer markdown files (roadmap.md, propose.md) reference the helper
# instead of using raw json.load(open(...)) one-liners.
#
# P2-3 audit finding: bare json.load(open(file)) invocations would crash the
# parent script on a missing or malformed state file. T2 introduced
# safe_python_json() which wraps the call in try/except. T22 replaces the
# remaining one-liner call sites in roadmap.md (gate-report, get_current_phase)
# and hardens the propose.md state update path (read+write needs a different
# pattern: safe_python_json pre-check + inline try/except).
#
# Run: bats tests/integration/test_json_safety.bats

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init
  source "$REPO_ROOT/_lib/state.sh"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "safe_python_json returns unknown for missing file" {
  result=$(safe_python_json "/nonexistent/file.json" "current_phase")
  [ "$result" = "unknown" ]
}

@test "safe_python_json returns value for valid file" {
  tmp=$(mktemp)
  echo '{"current_phase": "phase-2", "other": "x"}' > "$tmp"
  result=$(safe_python_json "$tmp" "current_phase")
  [ "$result" = "phase-2" ]
  rm "$tmp"
}

@test "safe_python_json returns unknown for malformed JSON" {
  tmp=$(mktemp)
  echo "not json {{{" > "$tmp"
  result=$(safe_python_json "$tmp" "current_phase")
  [ "$result" = "unknown" ]
  rm "$tmp"
}

@test "safe_python_json handles empty object" {
  tmp=$(mktemp)
  echo '{}' > "$tmp"
  result=$(safe_python_json "$tmp" "current_phase")
  [ "$result" = "unknown" ]
  rm "$tmp"
}

@test "roadmap.md uses safe_python_json helper" {
  [ -f "$REPO_ROOT/skills/roadmap/SKILL.md" ]
  grep -q "safe_python_json" "$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "propose.md uses safe_python_json helper" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  grep -q "safe_python_json" "$REPO_ROOT/skills/propose/SKILL.md"
}
