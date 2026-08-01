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

  # Check 4: openspec CLI must be available
  if command -v openspec >/dev/null 2>&1 && openspec --version >/dev/null 2>&1; then
    issues+=("$(_emit_issue "openspec_cli_available" "pass" "info" "" "现状: openspec --version 成功; 期望: 同上")")
  else
    issues+=("$(_emit_issue "openspec_cli_available" "fail" "error" "参见 rdd-workflow INSTALL.md 安装 openspec CLI" "现状: openspec --version 失败; 期望: 命令可用")")
  fi

  # Check 5: git HEAD must exist
  if (cd "$project_root" && git rev-parse HEAD >/dev/null 2>&1); then
    issues+=("$(_emit_issue "git_head_exists" "pass" "info" "" "现状: git rev-parse HEAD 成功; 期望: 同上")")
  else
    issues+=("$(_emit_issue "git_head_exists" "fail" "error" "git commit --allow-empty -m 'initial commit'" "现状: git rev-parse HEAD 失败; 期望: 至少存在一次提交")")
  fi

  # Check 6: large untracked directories (>10MB) → safe_auto_fix
  local large_dirs=""
  while IFS= read -r dir; do
    local size_mb
    size_mb=$(du -sm "$project_root/$dir" 2>/dev/null | awk '{print $1}')
    if [ -n "$size_mb" ] && [ "$size_mb" -gt 10 ] 2>/dev/null; then
      large_dirs="$large_dirs $dir(${size_mb}MB)"
    fi
  done < <(cd "$project_root" && git ls-files --others --exclude-standard --directory 2>/dev/null | awk -F/ '{print $1}' | sort -u)

  if [ -n "$large_dirs" ]; then
    issues+=("$(_emit_issue "large_untracked_dirs" "warn" "safe_auto_fix" "echo '$large_dirs' | xargs -I{} sh -c 'echo {}/ >> .gitignore'" "现状: 大目录未跟踪:$large_dirs; 期望: 加入 .gitignore")")
  else
    issues+=("$(_emit_issue "large_untracked_dirs" "pass" "info" "" "现状: 无 >10MB 未跟踪目录; 期望: 同上")")
  fi

  printf '[%s]\n' "$(IFS=,; echo "${issues[*]}")"
}

# Allow sourcing without running
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  check_project_setup "$@"
fi
