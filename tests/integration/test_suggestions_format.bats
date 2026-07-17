#!/usr/bin/env bats
# tests/integration/test_suggestions_format.bats
#
# T18 — proposal-suggestions.md format normalization (P1-7)
# Verifies the new JSON container format and the read_suggestions /
# write_suggestions helpers in skills/_lib/state.sh.
#
# Tests cover (per the task spec's test list):
#   1. read_suggestions returns valid JSON for new format
#   2. read_suggestions returns empty for missing file
#   3. read_suggestions returns empty for malformed JSON
#   4. write_suggestions creates backup of old format file
#   5. read_suggestions handles empty list
#   6. propose.md and consumers reference JSON helpers

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init
  # shellcheck source=/dev/null
  source "$REPO_ROOT/skills/_lib/state.sh"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

# -----------------------------------------------------------------------
# 1. read_suggestions returns valid JSON for new format
# -----------------------------------------------------------------------
@test "read_suggestions returns valid JSON for new format" {
  echo '[{"name": "test-1", "priority": "P0"}]' > proposal-suggestions.md
  result=$(read_suggestions)
  [ "$result" = '[{"name": "test-1", "priority": "P0"}]' ]
}

# -----------------------------------------------------------------------
# 2. read_suggestions returns empty for missing file
# -----------------------------------------------------------------------
@test "read_suggestions returns empty for missing file" {
  result=$(read_suggestions /nonexistent/file.md)
  [ "$result" = "[]" ]
}

# -----------------------------------------------------------------------
# 3. read_suggestions returns empty for malformed JSON
# -----------------------------------------------------------------------
@test "read_suggestions returns empty for malformed JSON" {
  echo "not json" > proposal-suggestions.md
  result=$(read_suggestions 2>/dev/null)
  [ "$result" = "[]" ]
}

# -----------------------------------------------------------------------
# 4. write_suggestions creates backup of old format file
# -----------------------------------------------------------------------
@test "write_suggestions creates backup of old format file" {
  cat > proposal-suggestions.md << 'OLD'
- name: old-format
  description: |
    ## 架构依据
    This is old format
OLD
  run write_suggestions proposal-suggestions.md '[]'
  [ "$status" -eq 0 ]
  [ -f proposal-suggestions.md.bak ]
  # The new file is the JSON we just wrote
  cat proposal-suggestions.md | grep -q '\[\]'
}

# -----------------------------------------------------------------------
# 5. read_suggestions handles empty list
# -----------------------------------------------------------------------
@test "read_suggestions handles empty list" {
  echo '[]' > proposal-suggestions.md
  result=$(read_suggestions)
  [ "$result" = "[]" ]
}

# -----------------------------------------------------------------------
# 6. propose.md and consumers reference JSON helpers
# -----------------------------------------------------------------------
@test "propose.md and consumers reference JSON helpers" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  # propose.md must have a json.load call (the new P1-7 format)
  grep -qE "json\.load\(" "$REPO_ROOT/skills/propose/SKILL.md"
  # And the new format doc must exist
  [ -f "$REPO_ROOT/docs/proposal-suggestions-format.md" ]
  # And the helpers must exist in state.sh
  grep -qE "^read_suggestions\(\)" "$REPO_ROOT/skills/_lib/state.sh"
  grep -qE "^write_suggestions\(\)" "$REPO_ROOT/skills/_lib/state.sh"
}

# -----------------------------------------------------------------------
# Bonus: write_suggestions refuses non-JSON data
# -----------------------------------------------------------------------
@test "write_suggestions refuses non-JSON data" {
  echo '[]' > proposal-suggestions.md
  run write_suggestions proposal-suggestions.md 'not json {{'
  [ "$status" -ne 0 ]
  # Original file unchanged
  cat proposal-suggestions.md | grep -q '\[\]'
}

# -----------------------------------------------------------------------
# Bonus: read_suggestions warns and returns [] for legacy YAML+Markdown
# -----------------------------------------------------------------------
@test "read_suggestions warns and returns empty for legacy format" {
  cat > proposal-suggestions.md << 'OLD'
- name: legacy
  description: |
    ## 架构依据
    ADR-001
OLD
  result=$(read_suggestions 2>/dev/null)
  [ "$result" = "[]" ]
}

# -----------------------------------------------------------------------
# Bonus: write_suggestions succeeds with valid multi-entry JSON
# -----------------------------------------------------------------------
@test "write_suggestions accepts valid multi-entry JSON" {
  data='[{"name":"a","priority":"P0"},{"name":"b","priority":"P1"}]'
  run write_suggestions proposal-suggestions.md "$data"
  [ "$status" -eq 0 ]
  run read_suggestions proposal-suggestions.md
  [ "$status" -eq 0 ]
  # Round-trip: the file contains both names
  cat proposal-suggestions.md | grep -q '"name": "a"'
  cat proposal-suggestions.md | grep -q '"name": "b"'
}
