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

# gh CLI 可用性检测 (ADR-0027 §1.0 reporter 前置依赖). 设置 _GH_AVAILABLE.
# 三态: "yes:user" (安装 + 认证) / "no:gh-missing" / "no:not-authed".
# 非阻塞: 缺 gh 不阻断 phase 入口, 仅 reporter L2 路径不可用.
_check_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    _GH_AVAILABLE="no:gh-missing"
    return 0
  fi
  if ! timeout 5 gh auth status >/dev/null 2>&1; then
    _GH_AVAILABLE="no:not-authed"
    return 0
  fi
  local user
  user=$(timeout 5 gh api user --jq .login 2>/dev/null | tr -d '[:space:]')
  # gh API returns {"message":"..."} on 5xx; only accept a real login shape.
  if [[ "$user" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*$ ]]; then
    _GH_AVAILABLE="yes:$user"
  else
    _GH_AVAILABLE="yes:unknown"
  fi
  return 0
}

# .gitignore 硬防护一致性检测 (add-gitignore-hard-protection).
# 设置 _GITIGNORE_PROTECTED: yes/no/n-a.
# 规则:
#   git.openspec_tracked=false + .gitignore 缺 openspec/ → warn (缺硬防护,
#     任何 git add -A 会把 openspec/ 重新拉进 git)
#   git.openspec_tracked=false + .gitignore 有 openspec/ → 静默通过
#   git.openspec_tracked=true/缺省 + .gitignore 有 openspec/ → 反向不一致
#     (rdd-workflow commit_archive_moves 会 git add 被 ignore 的路径 → 空 commit)
#   缺省 + 无 ignore → 静默 (传统 tracked 项目)
# 非阻塞: 仅 warning, 不影响 phase 入口. 不触碰 15 字段 cache 契约.
# Auto-fix (opt-in): RDDF_ENV_FIX_GITIGNORE=yes 且 false+缺失 → 幂等追加 openspec/.
_check_gitignore() {
  _GITIGNORE_PROTECTED="n/a"
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

  local tracked="true"
  if [ -f "$project_root/.rddf/project.yaml" ] && [ -f "$project_root/_lib/project_config.sh" ]; then
    # shellcheck disable=SC1090
    source "$project_root/_lib/project_config.sh"
    tracked=$(project_yaml_get "git.openspec_tracked" "true")
  fi

  local gitignore_file="$project_root/.gitignore"
  local has_entry="no"
  if [ -f "$gitignore_file" ] && grep -qxE '[[:space:]]*openspec/[[:space:]]*' "$gitignore_file" 2>/dev/null; then
    has_entry="yes"
  fi

  case "$tracked" in
    false|False)
      if [ "$has_entry" = "yes" ]; then
        _GITIGNORE_PROTECTED="yes"
        return 0
      fi
      _GITIGNORE_PROTECTED="no"
      echo "⚠️  gitignore guard missing: openspec/ not in .gitignore (git.openspec_tracked=false)"
      echo "   修复: echo 'openspec/' >> .gitignore"
      if [ "$(git ls-files openspec/ 2>/dev/null | head -1)" != "" ]; then
        echo "   混合状态 (openspec/ 有历史 tracked 文件): 一次性切换 git rm -r --cached openspec/"
      fi
      if [ "${RDDF_ENV_FIX_GITIGNORE:-no}" = "yes" ]; then
        if [ ! -f "$gitignore_file" ] || ! grep -qxF 'openspec/' "$gitignore_file"; then
          printf '\n# rdd-workflow: git.openspec_tracked=false — keep openspec/ out of git\nopenspec/\n' >> "$gitignore_file"
          echo "✅ 已追加 openspec/ 到 .gitignore (RDDF_ENV_FIX_GITIGNORE=yes)"
        fi
      fi
      ;;
    *)
      if [ "$has_entry" = "yes" ]; then
        _GITIGNORE_PROTECTED="no"
        echo "⚠️  反向不一致: .gitignore 忽略 openspec/ 但 git.openspec_tracked 未设 false —"
        echo "   rdd-workflow 的 commit_archive_moves 会 git add 被 ignore 的路径 (空 commit/no-op)。"
        echo "   修复: 二选一 — 设 .rddf/project.yaml git.openspec_tracked: false, 或从 .gitignore 移除 openspec/"
      else
        _GITIGNORE_PROTECTED="n/a"
      fi
      ;;
  esac
  return 0
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
  # 用纯 bash 提取 13 字段 (无 jq 依赖)
  local raw
  raw=$(cat "$cache_file" 2>/dev/null)
  _CACHE_TS=$(echo "$raw" | grep -oE '"timestamp":"?[0-9]+"?' | head -1 | grep -oE '[0-9]+')
  _CACHE_BRANCH=$(echo "$raw" | grep -oE '"branch":"[^"]*"' | head -1 | sed 's/.*:"//; s/"//')
  _CACHE_ADR=$(echo "$raw" | grep -oE '"adr_count":"?[0-9]+"?' | head -1 | grep -oE '[0-9]+')
  _CACHE_ROADMAP=$(echo "$raw" | grep -oE '"roadmap_exists":"[^"]*"' | head -1 | sed 's/.*:"//; s/"//')
}

# 原子写 cache: 写 .tmp 后 mv (同目录 atomic rename). 14 字段固定集合.
_cache_write() {
  local cache_file="${RDD_ENV_CACHE_FILE:-.rddf/state/.env-cache.json}"
  local ttl="${RDD_ENV_CACHE_TTL:-3600}"
  mkdir -p "$(dirname "$cache_file")"
  local tmp="${cache_file}.tmp"
  cat > "$tmp" <<EOF
{"timestamp":"$(date +%s)","ttl_s":"$ttl","branch":"$_CURRENT_BRANCH","openspec_ver":"$_OPENSPEC_VER","git_clean":"$_GIT_CLEAN","build_dir":"$_BUILD_DIR","adr_count":"$_ADR_COUNT","roadmap_exists":"$_ROADMAP_EXISTS","gap_count":"$_GAP_COUNT","active_changes":"$_ACTIVE_CHANGES","discovered_adr_dir":"${DISCOVERED_ADR_DIR:-}","discovered_roadmap_path":"${DISCOVERED_ROADMAP_PATH:-}","discovered_architecture_dir":"${DISCOVERED_ARCHITECTURE_DIR:-}","discovered_adr_pattern":"${DISCOVERED_ADR_PATTERN:-}","gh_available":"${_GH_AVAILABLE:-no}"}
EOF
  mv "$tmp" "$cache_file"
}

# 输出 14 字段 JSON (逐行 key: value, 供测试解析与兼容 arch_env_check 契约).
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
  echo "discovered_adr_dir: ${DISCOVERED_ADR_DIR:-}"
  echo "discovered_roadmap_path: ${DISCOVERED_ROADMAP_PATH:-}"
  echo "discovered_architecture_dir: ${DISCOVERED_ARCHITECTURE_DIR:-}"
  echo "discovered_adr_pattern: ${DISCOVERED_ADR_PATTERN:-}"
  echo "gh_available: ${_GH_AVAILABLE:-no}"
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
