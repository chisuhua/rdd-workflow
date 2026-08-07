#!/usr/bin/env bash
# skills/guide-design/scripts/design_env_check.sh — design Phase 1 环境检查接入
# Exports: run_design_env_check()
# 模式: 读 cache → 命中输出单行; miss/过期/branch 变化 → 现场全量 + 覆盖 cache
# 保持既有硬依赖检查 (arch-handoff) 不变, 本脚本只负责环境健康快照

run_design_env_check() {
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
