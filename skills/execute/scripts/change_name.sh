#!/usr/bin/env bash
# skills/execute/scripts/change_name.sh — shared CHANGE_NAME derivation helper
# Exports: ensure_change_name
#
# Explicit-value-first, branch-derived-second, repairable-error semantics.
# - Return immediately when CHANGE_NAME is already non-empty (export remains).
# - Otherwise read the current git branch and require the openspec/ prefix.
# - On failure, emit a Chinese repair hint and exit non-zero without guessing.

ensure_change_name() {
  if [ -n "${CHANGE_NAME:-}" ]; then
    export CHANGE_NAME
    return 0
  fi

  if ! command -v git >/dev/null 2>&1; then
    printf '❌ 无法推导 change 名称：git 命令不可用，请设置 CHANGE_NAME\n' >&2
    return 1
  fi

  local current_branch
  current_branch=$(git branch --show-current 2>/dev/null || true)
  if [ -z "$current_branch" ] || [ "$current_branch" = "unknown" ]; then
    printf '❌ 无法推导 change 名称：当前不在 git 仓库内，请设置 CHANGE_NAME\n' >&2
    return 1
  fi

  if [[ "$current_branch" != openspec/* ]]; then
    printf '❌ 无法推导 change 名称：当前分支 %q 不在 openspec/* 下，请设置 CHANGE_NAME\n' "$current_branch" >&2
    return 1
  fi

  CHANGE_NAME="${current_branch#openspec/}"
  export CHANGE_NAME
  return 0
}