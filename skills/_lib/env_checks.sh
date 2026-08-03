#!/usr/bin/env bash
# skills/_lib/env_checks.sh — 共享环境健康检查函数库 (extract-rdd-env-check-from-guide-arch)
# Exports: _check_openspec, _check_git, _check_branch, _check_build_dir,
#          _cache_read, _cache_write, _cache_valid, _emit_json, _env_status_line
#
# 单一来源 (DRY): rdd-env-check/scripts/env_check.sh 与 guide-arch/scripts/arch_env_check.sh
# 均 source 本库。运行路径仅依赖 bash + git + openspec (无 jq/python3)。

# 检测 openspec CLI。找到则设置 _OPENSPEC_PATH/_OPENSPEC_VER 返回 0; 缺失打印修复指引返回 1。
_check_openspec() {
  local p
  for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
    [ -x "$p" ] && _OPENSPEC_PATH="$p" && break
  done
  if [ -z "${_OPENSPEC_PATH:-}" ]; then
    echo "❌ openspec CLI 未找到"
    echo "   请安装: npm install -g openspec-cli"
    return 1
  fi
  _OPENSPEC_VER="$("$_OPENSPEC_PATH" --version 2>/dev/null || echo "?")"
  return 0
}

# git 工作区脏文件计数。设置 _GIT_CLEAN (0=干净)。
_check_git() {
  _GIT_CLEAN=$(git status --porcelain 2>/dev/null | grep -c . || true)
}

# 当前分支。设置 _CURRENT_BRANCH。
_check_branch() {
  _CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
}

# 构建目录检测 (按项目类型)。设置 _BUILD_DIR / _PROJECT_TYPE。
_check_build_dir() {
  if [ -f "Cargo.toml" ]; then
    _BUILD_DIR="target"; _PROJECT_TYPE="Rust"
  elif [ -f "package.json" ]; then
    _BUILD_DIR="node_modules"; _PROJECT_TYPE="Node.js"
  elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    _BUILD_DIR="venv"; _PROJECT_TYPE="Python"
  elif [ -f "CMakeLists.txt" ] || [ -f "Makefile" ]; then
    _BUILD_DIR="build"; _PROJECT_TYPE="C++/Make"
  else
    _BUILD_DIR="build"; _PROJECT_TYPE="Unknown"
  fi
}

# cache 有效判定: 存在 + mtime < TTL + branch 匹配。返回 0 有效。
# 依赖 _CURRENT_BRANCH 已设置 (调用方先跑 _check_branch)。
_cache_valid() {
  local cache_file="${RDD_ENV_CACHE_FILE:-.rddf/state/.env-cache.json}"
  local ttl="${RDD_ENV_CACHE_TTL:-3600}"
  [ "$ttl" -eq 0 ] 2>/dev/null && return 1
  [ -f "$cache_file" ] || return 1
  local now mtime
  now=$(date +%s)
  mtime=$(stat -c %Y "$cache_file" 2>/dev/null || echo 0)
  [ $((now - mtime)) -lt "$ttl" ] || return 1
  local cached_branch
  cached_branch=$(grep -oE '"branch":"[^"]*"' "$cache_file" 2>/dev/null | head -1 | sed 's/.*:"//; s/"//')
  [ "$cached_branch" = "$_CURRENT_BRANCH" ]
}

# 读 cache 到全局变量 (供单行状态输出)。调用方须先验证 _cache_valid。
_cache_read() {
  local cache_file="${RDD_ENV_CACHE_FILE:-.rddf/state/.env-cache.json}"
  # 用纯 bash 提取 10 字段 (无 jq 依赖)
  local raw
  raw=$(cat "$cache_file" 2>/dev/null)
  _CACHE_TS=$(echo "$raw" | grep -oE '"timestamp":"[0-9]*"' | head -1 | grep -oE '[0-9]+')
  _CACHE_BRANCH=$(echo "$raw" | grep -oE '"branch":"[^"]*"' | head -1 | sed 's/.*:"//; s/"//')
  _CACHE_ADR=$(echo "$raw" | grep -oE '"adr_count":"[0-9]*"' | head -1 | grep -oE '[0-9]+')
  _CACHE_ROADMAP=$(echo "$raw" | grep -oE '"roadmap_exists":"[^"]*"' | head -1 | sed 's/.*:"//; s/"//')
}

# 原子写 cache: 写 .tmp 后 mv (同目录 atomic rename)。10 字段固定集合。
_cache_write() {
  local cache_file="${RDD_ENV_CACHE_FILE:-.rddf/state/.env-cache.json}"
  local ttl="${RDD_ENV_CACHE_TTL:-3600}"
  mkdir -p "$(dirname "$cache_file")"
  local tmp="${cache_file}.tmp"
  cat > "$tmp" <<EOF
{"timestamp":"$(date +%s)","ttl_s":"$ttl","branch":"$_CURRENT_BRANCH","openspec_ver":"$_OPENSPEC_VER","git_clean":"$_GIT_CLEAN","build_dir":"$_BUILD_DIR","adr_count":"$_ADR_COUNT","roadmap_exists":"$_ROADMAP_EXISTS","gap_count":"$_GAP_COUNT","active_changes":"$_ACTIVE_CHANGES"}
EOF
  mv "$tmp" "$cache_file"
}

# 输出 10 字段 JSON (逐行 key: value, 供测试解析与兼容 arch_env_check 契约)。
_emit_json() {
  echo "timestamp: $(date +%s)"
  echo "ttl_s: ${RDD_ENV_CACHE_TTL:-3600}"
  echo "branch: ${_CURRENT_BRANCH:-unknown}"
  echo "openspec_ver: ${_OPENSPEC_VER:-?}"
  echo "git_clean: ${_GIT_CLEAN:-0}"
  echo "build_dir: ${_BUILD_DIR:-build}"
  echo "adr_count: ${_ADR_COUNT:-0}"
  echo "roadmap_exists: ${_ROADMAP_EXISTS:-no}"
  echo "gap_count: ${_GAP_COUNT:-0}"
  echo "active_changes: ${_ACTIVE_CHANGES:-0}"
}

# 单行状态: ✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓
# 依赖 _cache_read 已填充 _CACHE_TS/_CACHE_ADR/_CACHE_ROADMAP。
_env_status_line() {
  local ago=""
  if [ -n "${_CACHE_TS:-}" ]; then
    local mins
    mins=$(( ( $(date +%s) - _CACHE_TS ) / 60 ))
    ago=" (cached ${mins}m ago)"
  fi
  local roadmap_mark="✗"
  [ "${_CACHE_ROADMAP:-no}" = "yes" ] && roadmap_mark="✓"
  echo "✅ Env OK${ago} | ADR:${_CACHE_ADR:-0} | Roadmap:${roadmap_mark}"
}
