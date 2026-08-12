#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_env_check.sh — ship Phase 1 环境检查接入
# Exports: run_ship_env_check()
# 模式: 读 cache → 命中输出单行; miss/过期/branch 变化 → 现场全量 + 覆盖 cache

# ADR-0027 script-plane trigger (see add-post-flow-analysis change)
export RDDF_PHASE="${RDDF_PHASE:-guide-ship}"
source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
trap 'post_flow_on_err' ERR

run_ship_env_check() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  if [ -f "$project_root/skills/rdd-env-check/scripts/env_check.sh" ]; then
    source "$project_root/skills/rdd-env-check/scripts/env_check.sh"
  else
    source "${project_root:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh" 2>/dev/null
    source "$(resolve_rdd_skill_dir rdd-env-check)/scripts/env_check.sh" 2>/dev/null
  fi
  _run_env_check_cached
}
