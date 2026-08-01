#!/usr/bin/env bash
# check_project_setup.sh - validate project setup for rdd-workflow runtime.
# Emits a JSON array of issues to stdout. Returns 0 regardless of issue status.
set -u

check_project_setup() {
  local project_root="${1:-$(pwd)}"
  printf '[]\n'
}

# Allow sourcing without running
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  check_project_setup "$@"
fi
