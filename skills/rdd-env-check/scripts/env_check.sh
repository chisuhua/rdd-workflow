#!/usr/bin/env bash
# skills/rdd-env-check/scripts/env_check.sh — 独立环境健康检查脚本
# Exports: _run_env_full_check, _run_env_check_cached
#
# 调用方 source 本文件后调用:
#   _run_env_check_cached  — 读 cache, 命中输出单行; miss/过期/branch 变化 → 全量 + 覆盖 cache
#   _run_env_full_check    — 无条件全量检查 (写 cache + 输出 10 字段 JSON)
#
# 依赖 _lib/env_checks.sh (共享 _check_* 函数)

# 定位共享库: worktree 内优先相对路径, 再回退 skill_root.sh 解析。
_ENV_CHECK_SELF="${BASH_SOURCE[0]:-$0}"
_ENV_CHECK_DIR="$(cd "$(dirname "$_ENV_CHECK_SELF")" && pwd)"
_LIB_DIR="$_ENV_CHECK_DIR/../../_lib"

if [ -f "$_LIB_DIR/env_checks.sh" ]; then
  source "$_LIB_DIR/env_checks.sh"
else
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh" 2>/dev/null
  if command -v resolve_rdd_lib_dir >/dev/null 2>&1 && [ -f "$(resolve_rdd_lib_dir)/env_checks.sh" ]; then
    source "$(resolve_rdd_lib_dir)/env_checks.sh"
  fi
fi

_run_env_full_check() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  cd "$project_root" 2>/dev/null || true

  _check_openspec || return 1
  _check_git
  _check_branch
  _check_build_dir
  _check_gh

  # ADR-0016 工件路径发现 → 4 个 discovered_* 写入 .env-cache.json
  local discovered_adr_dir="docs/adr" discovered_roadmap="roadmap.md" discovered_arch="docs/architecture" discovered_pattern="ADR-*.md"
  if [ "${SKIP_AUTO_DISCOVERY:-no}" = "yes" ]; then
    echo "✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)"
    discovered_adr_dir=""
    discovered_roadmap=""
    discovered_arch=""
    discovered_pattern=""
  elif [ -f "$_LIB_DIR/discover-arch-artifacts.sh" ]; then
    source "$_LIB_DIR/discover-arch-artifacts.sh" 2>/dev/null
    discovered_adr_dir=$(discover_adr_dir 2>/dev/null || echo "$discovered_adr_dir")
    discovered_roadmap=$(discover_roadmap 2>/dev/null || echo "$discovered_roadmap")
    discovered_arch=$(discover_architecture_dir 2>/dev/null || echo "$discovered_arch")
    discovered_pattern=$(discover_adr_pattern 2>/dev/null || echo "$discovered_pattern")
  fi
  # Oracle C1: env-var 传递, 禁止 bash $VAR 字符串插值到 Python.
  export DISCOVERED_ADR_DIR="$discovered_adr_dir"
  export DISCOVERED_ROADMAP_PATH="$discovered_roadmap"
  export DISCOVERED_ARCHITECTURE_DIR="$discovered_arch"
  export DISCOVERED_ADR_PATTERN="$discovered_pattern"

  _ADR_COUNT=$(ls -d "$project_root/$discovered_adr_dir/"ADR-*.md 2>/dev/null | wc -l | tr -d '[:space:]')
  _ROADMAP_EXISTS=$([ -f "$project_root/$discovered_roadmap" ] && echo "yes" || echo "no")
  _GAP_COUNT=$(ls "$project_root/$discovered_arch/"*-gap-analysis.md 2>/dev/null | wc -l | tr -d '[:space:]')
  _ACTIVE_CHANGES=$(ls -d "$project_root"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')

  _cache_write
  _emit_json
  return 0
}

_run_env_check_cached() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  cd "$project_root" 2>/dev/null || true

  _check_branch
  if _cache_valid; then
    _cache_read
    _env_status_line
    return 0
  fi

  # miss / 过期 / branch 变化 → 全量 (openspec 缺失时阻断)
  _run_env_full_check || return 1
  _cache_read
  _env_status_line
}
