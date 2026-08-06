#!/usr/bin/env bats
load ../test_helper

setup() {
  BATS_TEST_TMPDIR="${BATS_TEST_TMPDIR:-$BATS_TMPDIR/test-passing-$$}"
  mkdir -p "$BATS_TEST_TMPDIR"
  (cd "$BATS_TEST_TMPDIR" && git init -q && \
    echo ".rddf/state/" > .gitignore && \
    echo ".rddf/wt/" >> .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  export PASSING_FIXTURE="$BATS_TEST_TMPDIR"
}

@test "check_project_setup: passing project emits valid JSON array" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT'"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -m json.tool >/dev/null
}

@test "check_project_setup: rddf_state_ignored passes on repo" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq -r '.[] | select(.name==\"rddf_state_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}

@test "check_project_setup: rddf_plans_not_ignored passes on repo" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq -r '.[] | select(.name==\"rddf_plans_not_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}

@test "check_project_setup: openspec_cli_available passes when CLI present" {
  if ! command -v openspec >/dev/null 2>&1; then
    skip "openspec CLI not installed"
  fi
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq -r '.[] | select(.name==\"openspec_cli_available\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}

@test "check_project_setup: git_head_exists passes in repo" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq -r '.[] | select(.name==\"git_head_exists\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}

@test "check_project_setup: large_untracked_dirs severity is safe_auto_fix or info" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq -r '.[] | select(.name==\"large_untracked_dirs\") | .severity'"
  [ "$status" -eq 0 ]
  [[ "$output" == "safe_auto_fix" || "$output" == "info" ]]
}

@test "check_project_setup: missing rddf_state_ignored → status=fail severity=error" {
  local fixture="$BATS_TEST_TMPDIR/missing-state"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    echo ".rddf/wt/" > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq '.[] | select(.name==\"rddf_state_ignored\") | {status, severity}'"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r .status)" = "fail" ]
  [ "$(echo "$output" | jq -r .severity)" = "error" ]
}

@test "check_project_setup: missing rddf_wt_ignored fix_command suggests echo to .gitignore" {
  local fixture="$BATS_TEST_TMPDIR/missing-wt"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    echo ".rddf/state/" > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"rddf_wt_ignored\") | .fix_command'"
  [ "$status" -eq 0 ]
  [[ "$output" == *".rddf/wt/"* ]]
  [[ "$output" == *".gitignore"* ]]
}

@test "check_project_setup: plans regression — rddf_plans_not_ignored status=fail" {
  local fixture="$BATS_TEST_TMPDIR/plans-ignored"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf '.rddf/state/\n.rddf/wt/\n.rddf/plans/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"rddf_plans_not_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "fail" ]
}

@test "check_project_setup: no gitignore → rddf_state_ignored fail + suggested creation command" {
  local fixture="$BATS_TEST_TMPDIR/no-gitignore"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init)
  rm -f "$fixture/.gitignore"
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$fixture' 2>/dev/null | jq '.[] | select(.name==\"rddf_state_ignored\") | {status, fix_command}'"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r .status)" = "fail" ]
  [[ "$(echo "$output" | jq -r .fix_command)" == *"echo"* ]]
  [[ "$(echo "$output" | jq -r .fix_command)" == *".gitignore"* ]]
}

@test "check_project_setup: large untracked dir → severity=safe_auto_fix" {
  local fixture="$BATS_TEST_TMPDIR/large-untracked"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf '.rddf/state/\n.rddf/wt/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  mkdir -p "$fixture/bigbuild"
  dd if=/dev/zero of="$fixture/bigbuild/blob" bs=1M count=11 status=none
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"large_untracked_dirs\") | .severity'"
  [ "$status" -eq 0 ]
  [ "$output" = "safe_auto_fix" ]
  rm -f "$fixture/bigbuild/blob"
}

@test "check_project_setup: JSON schema — every issue has name/status/severity/fix_command/detail" {
  run bash -c "source '$REPO_ROOT/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | has(\"name\") and has(\"status\") and has(\"severity\") and has(\"fix_command\") and has(\"detail\")' | sort -u"
  [ "$status" -eq 0 ]
  [ "$output" = "true" ]
}
