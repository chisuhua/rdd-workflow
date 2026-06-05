#!/usr/bin/env bats
# tests/_lib/test_state.bats
# Unit tests for skills/_lib/state.sh helpers:
#   - safe_python_json
#   - safe_python_yaml
#
# Run: bats tests/_lib/test_state.bats

load ../test_helper
load_lib state

@test "safe_python_json returns unknown for missing file" {
  result=$(safe_python_json "/nonexistent/file.json" ".foo")
  [[ "$result" == "unknown" ]]
}

@test "safe_python_json returns value for valid file" {
  tmp=$(mktemp)
  echo '{"a": "b"}' > "$tmp"
  result=$(safe_python_json "$tmp" ".a")
  [[ "$result" == "b" ]]
  rm "$tmp"
}

@test "safe_python_json returns unknown for malformed JSON" {
  tmp=$(mktemp)
  echo "not json" > "$tmp"
  result=$(safe_python_json "$tmp" ".foo")
  [[ "$result" == "unknown" ]]
  rm "$tmp"
}

@test "safe_python_yaml returns empty for missing file" {
  result=$(safe_python_yaml "/nonexistent/file.yaml")
  [[ -z "$result" ]]
}
