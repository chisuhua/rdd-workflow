#!/usr/bin/env bats
load ../test_helper

@test "check_project_setup: passing project emits valid JSON array" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT'"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -m json.tool >/dev/null
}
