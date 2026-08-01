#!/usr/bin/env bash
# check_project_setup.sh - validate project setup for rdd-workflow runtime.
# Emits a JSON array of issues to stdout. Returns 0 regardless of issue status.
set -u

check_project_setup() {
  local project_root="${1:-$(pwd)}"
  local gitignore="$project_root/.gitignore"
  local issues=()

  # Helper: emit one issue object
  _emit_issue() {
    local name="$1" status="$2" severity="$3" fix_command="$4" detail="$5"
    printf '{"name":"%s","status":"%s","severity":"%s","fix_command":"%s","detail":"%s"}' \
      "$name" "$status" "$severity" "$fix_command" "$detail"
  }

  # Check 1: .rddf/state/ must be ignored
  if [ ! -f "$gitignore" ]; then
    issues+=("$(_emit_issue "rddf_state_ignored" "fail" "error" "echo '.rddf/state/' >> .gitignore" "现状: .gitignore 不存在; 期望: 包含 .rddf/state/")")
  elif grep -qE '^\.rddf/state/' "$gitignore" || grep -qE '^\.rddf/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_state_ignored" "pass" "info" "" "现状: .rddf/state/ 已忽略; 期望: 同上")")
  else
    issues+=("$(_emit_issue "rddf_state_ignored" "fail" "error" "echo '.rddf/state/' >> .gitignore" "现状: .gitignore 无 .rddf/state/; 期望: 包含 .rddf/state/")")
  fi

  # Check 2: .rddf/wt/ must be ignored
  if grep -qE '^\.rddf/wt/' "$gitignore" || grep -qE '^\.rddf/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_wt_ignored" "pass" "info" "" "现状: .rddf/wt/ 已忽略; 期望: 同上")")
  else
    issues+=("$(_emit_issue "rddf_wt_ignored" "fail" "error" "echo '.rddf/wt/' >> .gitignore" "现状: .gitignore 无 .rddf/wt/; 期望: 包含 .rddf/wt/")")
  fi

  # Check 3: .rddf/plans/ must NOT be ignored (regression detection)
  if grep -qE '^\.rddf/plans/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_plans_not_ignored" "fail" "error" "sed -i '/^\\.rddf\\/plans\\//d' .gitignore" "现状: .rddf/plans/ 被忽略; 期望: 不应被忽略(执行契约路径)")")
  else
    issues+=("$(_emit_issue "rddf_plans_not_ignored" "pass" "info" "" "现状: .rddf/plans/ 未被忽略; 期望: 同上")")
  fi

  printf '[%s]\n' "$(IFS=,; echo "${issues[*]}")"
}

# Allow sourcing without running
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  check_project_setup "$@"
fi
