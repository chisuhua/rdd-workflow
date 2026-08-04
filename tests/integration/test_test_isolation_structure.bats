#!/usr/bin/env bats
# tests/integration/test_test_isolation_structure.bats
# Structural guard: main-repo-scenario tests must not read live worktree/branch/open-spec state.

load ../test_helper

@test "structure: main-repo-scenario tests do not read real repo worktree/branch state" {
  local offenders=()

  # test_select_worktree_extraction.bats runs auto_detect in $REPO_ROOT
  if grep -nE "cd '\$\{REPO_ROOT\}'|cd '\$REPO_ROOT'.*auto_detect_worktree_context|cd \"\$REPO_ROOT\".*auto_detect_worktree_context" \
       "$REPO_ROOT/tests/integration/test_select_worktree_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_select_worktree_extraction.bats: auto_detect in REPO_ROOT")
  fi

  # test_select_worktree_extraction.bats uses git branch --show-current in REPO_ROOT
  if grep -nE '^\s*CURRENT=\$\(git branch --show-current\)' \
       "$REPO_ROOT/tests/integration/test_select_worktree_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_select_worktree_extraction.bats: git branch --show-current in REPO_ROOT")
  fi

  # test_adr_0015_wiring.bats checks real archive files
  if grep -nE '\$REPO_ROOT/openspec/changes/archive/' \
       "$REPO_ROOT/tests/integration/test_adr_0015_wiring.bats" >/dev/null 2>&1; then
    offenders+=("test_adr_0015_wiring.bats: real archive path assertions")
  fi

  # test_status_render_mode_a_extraction.bats runs helper in $REPO_ROOT
  if grep -nE 'cd "\$REPO_ROOT".*render_status_mode_a' \
       "$REPO_ROOT/tests/integration/test_status_render_mode_a_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_status_render_mode_a_extraction.bats: render_status_mode_a in REPO_ROOT")
  fi

  # test_rdd_env_check.bats reads real branch and writes cache to REPO_ROOT
  if grep -nE 'cd "\$REPO_ROOT".*git rev-parse --abbrev-ref HEAD' \
       "$REPO_ROOT/tests/integration/test_rdd_env_check.bats" >/dev/null 2>&1; then
    offenders+=("test_rdd_env_check.bats: real branch reads in REPO_ROOT")
  fi

  if [ "${#offenders[@]}" -gt 0 ]; then
    printf 'FAIL: %s\n' "${offenders[@]}"
    return 1
  fi
}