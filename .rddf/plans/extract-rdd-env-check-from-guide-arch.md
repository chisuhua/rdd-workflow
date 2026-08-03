# extract-rdd-env-check-from-guide-arch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将环境健康检查（openspec/git/build）从 `guide-arch` Phase 1 外置为独立 `rdd-env-check` skill，新增 `.rddf/state/.env-cache.json` 缓存（TTL 3600s + branch 失效），把 arch 阶段菜单首屏从 ~15 行压缩到单行 `✅ Env OK (cached 23m ago) | ADR:63 | Roadmap:✓`，同时保持 openspec 缺失阻断等现有安全网与 JSON 字段契约完全不变。

**Architecture:** 三件套分工：(1) `skills/_lib/env_checks.sh` 持有全部可复用 `_check_*` 函数（openspec/git/branch/build），DRY 单一来源；(2) `skills/rdd-env-check/scripts/env_check.sh` 调用共享函数执行完整检查并原子写 `.rddf/state/.env-cache.json`（10 字段 JSON）；(3) 重构后的 `arch_env_check.sh` 与 design/plan/ship 的 Phase 1 调用点先读 cache，命中则跳过全量检查，未命中/过期/branch 变化则降级现场跑。ADR-0016 工件发现（discover-arch-artifacts.sh）**绝不缓存**，仍在 guide-arch Phase 1 每次运行。

**Tech Stack:** bash (纯 bash，无 jq/python3 运行时依赖), bats-core (测试), openspec CLI (仅检测，不调用)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/env_checks.sh` | 新建：共享 `_check_*` 函数库（openspec/git/branch/build + cache 读写 + 10 字段 JSON 组装） |
| `skills/rdd-env-check/scripts/env_check.sh` | 新建：rdd-env-check 独立 skill 的执行脚本（完整检查 + cache 写入 + 单行状态输出） |
| `skills/rdd-env-check/SKILL.md` | 新建：独立 skill 文档（调用方式、JSON/cache 契约、TTL 覆盖、失败行为） |
| `skills/guide-arch/scripts/arch_env_check.sh` | 重构：改为 source `_lib/env_checks.sh`，先读 cache 命中即跳过，未命中降级全量检查；保留 ADR-0016 发现 + 现有 `run_arch_env_check` / `run_arch_env_setup_gate` 函数签名 |
| `skills/guide-arch/SKILL.md` | 文档更新：Phase 1 首屏展示单行状态，移除完整环境检查 transcript |
| `skills/guide-design/scripts/design_env_check.sh` | 新建：design Phase 1 同模式接入（读 cache → 命中跳过 → miss 现场跑） |
| `skills/guide-plan/scripts/plan_intake.sh` | 重构：openspec/git 检测段替换为共享 `_check_*` + cache 优先 |
| `skills/guide-ship/scripts/ship_env_check.sh` | 新建：ship Phase 1 同模式接入 |

> 注：design/ship 当前 Phase 1 无完整 env check 脚本（只有硬依赖检查），本 change 为它们新增轻量 env check 接入（读 cache + fallback），保持既有硬依赖检查不变。

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_rdd_env_check.bats` | 新建：3 个 cache 场景（命中/TTL 过期/branch 变化）+ 10 字段 JSON 契约 + openspec 缺失阻断 + 无 jq/python3 依赖 + 原子 cache 路径 + 单行首屏 |
| `tests/integration/test_arch_env_check_extraction.bats` | 既有 9 用例，回归护栏（`run_arch_env_check` 签名与输出锚点必须保持） |
| `tests/integration/test_guide_arch_skill.bats` 等 49 个既有测试 | 回归（不修改，验证行为兼容） |

---

### Task 1: 编写失败测试（RED）— 创建 test_rdd_env_check.bats

**Files:**
- Create: `tests/integration/test_rdd_env_check.bats`

- [ ] **Step 1: Write the failing test**

创建 `tests/integration/test_rdd_env_check.bats`，完整内容：

```bash
#!/usr/bin/env bats
# tests/integration/test_rdd_env_check.bats
# extract-rdd-env-check-from-guide-arch: 环境健康检查外置 + cache 三场景 + JSON 契约
# 覆盖 acceptance #1-#8

load ../test_helper

SKILL_DIR="$REPO_ROOT/skills/rdd-env-check"
ENV_CHECK="$SKILL_DIR/scripts/env_check.sh"
LIB_CHECKS="$REPO_ROOT/skills/_lib/env_checks.sh"
CACHE_PATH=".rddf/state/.env-cache.json"

@test "rdd_env_check: helpers exist" {
  [ -f "$SKILL_DIR/SKILL.md" ]
  [ -f "$ENV_CHECK" ]
  [ -f "$LIB_CHECKS" ]
  grep -q '^_check_openspec()' "$LIB_CHECKS"
  grep -q '^_check_git()' "$LIB_CHECKS"
  grep -q '^_check_build_dir()' "$LIB_CHECKS"
  grep -q '_check_branch' "$LIB_CHECKS"
}

@test "rdd_env_check: 10-field JSON contract matches arch_env_check" {
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_full_check && _emit_json"
  [ "$status" -eq 0 ]
  # 10 个固定字段, 不多不少
  local fields
  fields=$(echo "$output" | grep -oE '^[a-z_]+:' | sort | tr '\n' ' ')
  echo "$fields" | grep -q 'timestamp: '
  echo "$fields" | grep -q 'ttl_s: '
  echo "$fields" | grep -q 'branch: '
  echo "$fields" | grep -q 'openspec_ver: '
  echo "$fields" | grep -q 'git_clean: '
  echo "$fields" | grep -q 'build_dir: '
  echo "$fields" | grep -q 'adr_count: '
  echo "$fields" | grep -q 'roadmap_exists: '
  echo "$fields" | grep -q 'gap_count: '
  echo "$fields" | grep -q 'active_changes: '
  [ "$(echo "$fields" | wc -w)" -eq 10 ]
}

@test "rdd_env_check: cache hit skips full check (under 100ms)" {
  # 预写一个新鲜 cache (branch 匹配)
  local tmp
  tmp=$(mktemp -d)
  (cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD > "$tmp/branch")
  local branch
  branch=$(cat "$tmp/branch")
  mkdir -p "$REPO_ROOT/.rddf/state"
  cat > "$REPO_ROOT/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_check_cached"
  # 命中路径输出单行, 含 cached 标记
  echo "$output" | grep -q 'cached'
  # 未调用 openspec 检测 (cache 命中时不该跑全量)
  local log
  log=$(bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && RDD_ENV_CHECK_DEBUG=1 _run_env_check_cached" 2>&1)
  echo "$log" | grep -q 'cached'
  rm -f "$REPO_ROOT/.rddf/state/.env-cache.json"
  rm -rf "$tmp"
}

@test "rdd_env_check: TTL expiry triggers full recheck" {
  local tmp
  tmp=$(mktemp -d)
  (cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD > "$tmp/branch")
  local branch
  branch=$(cat "$tmp/branch")
  mkdir -p "$REPO_ROOT/.rddf/state"
  # 写入过期 cache (mtime 2h 前)
  cat > "$REPO_ROOT/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  touch -d "2 hours ago" "$REPO_ROOT/.rddf/state/.env-cache.json"
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_check_cached"
  # 过期 → 未命中 cached 标记, 走了全量 (输出非单行 cached 行)
  if echo "$output" | grep -q 'cached'; then
    # 允许 fallback 也输出单行, 但必须重新检测 openspec
    echo "$output" | grep -q 'openspec'
  fi
  # cache 被覆盖 (mtime 更新)
  local new_mtime
  new_mtime=$(stat -c %Y "$REPO_ROOT/.rddf/state/.env-cache.json")
  local now
  now=$(date +%s)
  [ $((now - new_mtime)) -lt 120 ]
  rm -f "$REPO_ROOT/.rddf/state/.env-cache.json"
  rm -rf "$tmp"
}

@test "rdd_env_check: branch change invalidates cache" {
  local tmp
  tmp=$(mktemp -d)
  (cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD > "$tmp/current_branch")
  local current
  current=$(cat "$tmp/current_branch")
  local other="other-branch-name"
  [ "$current" != "$other" ] || other="another-branch-name"
  mkdir -p "$REPO_ROOT/.rddf/state"
  # 写入 branch 不匹配的 cache (mtime 新鲜)
  cat > "$REPO_ROOT/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$other","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_check_cached"
  # branch 不匹配 → 重跑并覆盖 cache.branch == 当前 branch
  local cached_branch
  cached_branch=$(python3 -c "import json;print(json.load(open('$REPO_ROOT/.rddf/state/.env-cache.json'))['branch'])" 2>/dev/null || echo "$current")
  [ "$cached_branch" = "$current" ]
  rm -f "$REPO_ROOT/.rddf/state/.env-cache.json"
  rm -rf "$tmp"
}

@test "rdd_env_check: openspec missing blocks with non-zero + repair guidance" {
  run bash -c "cd '$REPO_ROOT' && PATH=/usr/bin:/bin source '$ENV_CHECK' && _run_env_check_cached"
  # cache 不存在 + openspec 缺失 → 阻断, 退出非 0
  [ "$status" -ne 0 ]
  echo "$output" | grep -q 'openspec'
}

@test "rdd_env_check: no jq/python3 runtime dependency" {
  # 核心路径 (env check + cache 写读) 在 jq/python3 缺席时可用
  run bash -c "cd '$REPO_ROOT' && PATH='$REPO_ROOT/tests/_lib/fakebin' source '$ENV_CHECK' && _run_env_check_cached"
  # 若 cache 命中则无需工具; 若 miss 则走 bash 实现
  [ "$status" -eq 0 ] || echo "$output" | grep -q 'openspec'
}

@test "rdd_env_check: atomic cache write uses tmp + mv" {
  grep -q '\.env-cache\.json\.tmp' "$ENV_CHECK"
  grep -q 'mv ' "$ENV_CHECK"
}

@test "rdd_env_check: one-line phase 1 status" {
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _env_status_line"
  # 单行格式: ✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓
  echo "$output" | grep -q 'Env OK'
  echo "$output" | grep -q 'ADR:'
  echo "$output" | grep -q 'Roadmap:'
  [ "$(echo "$output" | wc -l)" -eq 1 ]
}

@test "rdd_env_check: arch_env_check reuses shared _check_ functions" {
  # DRY 契约: arch_env_check.sh source env_checks.sh 且引用 >= 4 处 _check_
  grep -q 'env_checks\.sh' "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh"
  local refs
  refs=$(grep -c '_check_' "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh" || true)
  [ "$refs" -ge 4 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_rdd_env_check.bats`
Expected: 全部 FAIL —— `skills/rdd-env-check/` 不存在、`_lib/env_checks.sh` 不存在、`arch_env_check.sh` 尚无 `_check_*` 引用。

- [ ] **Step 3: Run regression baseline**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_arch_env_check_extraction.bats`
Expected: 9 个用例 PASS（当前 `arch_env_check.sh` 仍满足既有断言）。

- [ ] **Step 4: 记录失败用例清单**

在测试输出中确认以下 RED 断言（写入手记，Task 2/3 逐个转绿）：
1. helpers exist — FAIL（3 个新文件不存在）
2. 10-field JSON contract — FAIL（`_emit_json` 未定义）
3. cache hit — FAIL（`_run_env_check_cached` 未定义）
4. TTL expiry — FAIL
5. branch change — FAIL
6. openspec missing — FAIL（无缓存逻辑，PATH 清理后 `_run_env_check_cached` 未定义）
7. no jq/python3 — FAIL
8. atomic cache write — FAIL（无 `.tmp` 逻辑）
9. one-line status — FAIL（`_env_status_line` 未定义）
10. DRY ≥4 refs — FAIL（arch_env_check.sh 无 `_check_` 引用）

- [ ] **Step 5: Commit（测试与实现同批提交 — 先不 commit，见 Task 4 Step 5）**

（本 Task 仅写测试文件，暂不 commit，避免中间态。）

---

### Task 2: 实现共享函数库（GREEN）— 创建 `skills/_lib/env_checks.sh`

**Files:**
- Create: `skills/_lib/env_checks.sh`

- [ ] **Step 1: 写共享 `_check_*` 函数库**

创建 `skills/_lib/env_checks.sh`，完整内容：

```bash
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
  _CACHE_TS=$(echo "$raw" | grep -oE '"timestamp":[0-9]+' | head -1 | grep -oE '[0-9]+')
  _CACHE_BRANCH=$(echo "$raw" | grep -oE '"branch":"[^"]*"' | head -1 | sed 's/.*:"//; s/"//')
  _CACHE_ADR=$(echo "$raw" | grep -oE '"adr_count":[0-9]+' | head -1 | grep -oE '[0-9]+')
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
```

- [ ] **Step 2: 验证新库可 source 且函数存在**

Run: `cd "$REPO_ROOT" && bash -c 'source skills/_lib/env_checks.sh && declare -F _check_openspec _check_git _check_branch _check_build_dir _cache_valid _cache_write _emit_json _env_status_line'`
Expected: 全部函数已声明（无 "not found"）。

- [ ] **Step 3: 跑新测试验证 helper 用例转绿**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_rdd_env_check.bats`
Expected: 不再报 "command not found: env_checks.sh"，但核心用例（cache hit/JSON 契约等）仍 RED（`env_check.sh` 尚未实现 `_run_env_check_cached`）。

- [ ] **Step 4: 回归既有测试**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_arch_env_check_extraction.bats`
Expected: 9 用例仍 PASS（本库是纯新增，arch_env_check.sh 未改）。

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/env_checks.sh
git commit -m "feat(_lib): add shared env_checks.sh with _check_* functions + cache helpers"
```

---

### Task 3: 实现独立 skill（GREEN）— 创建 `skills/rdd-env-check/`

**Files:**
- Create: `skills/rdd-env-check/scripts/env_check.sh`
- Create: `skills/rdd-env-check/SKILL.md`

- [ ] **Step 1: 创建执行脚本 env_check.sh**

创建 `skills/rdd-env-check/scripts/env_check.sh`，完整内容：

```bash
#!/usr/bin/env bash
# skills/rdd-env-check/scripts/env_check.sh — 独立环境健康检查脚本
# Exports: _run_env_full_check, _run_env_check_cached
#
# 调用方 source 本文件后调用:
#   _run_env_check_cached  — 读 cache → 命中输出单行; miss/过期/branch 变化 → 全量 + 覆盖 cache
#   _run_env_full_check    — 无条件全量检查 (写 cache + 输出 10 字段 JSON)
#
# 依赖 skills/_lib/env_checks.sh (共享 _check_* 函数)

_run_env_full_check() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  cd "$project_root" 2>/dev/null || true

  _check_openspec || return 1
  _check_git
  _check_branch
  _check_build_dir

  # ADR-0016 工件计数 (此处仅计数; 发现逻辑保留在 guide-arch, 本脚本不缓存发现结果)
  local discovered_adr_dir="docs/adr" discovered_roadmap="roadmap.md" discovered_arch="docs/architecture"
  source "${project_root:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh" 2>/dev/null
  if command -v resolve_rdd_lib_dir >/dev/null 2>&1 && [ -f "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh" ]; then
    source "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh"
    discover_adr_dir >/dev/null 2>&1
    discover_roadmap >/dev/null 2>&1
    discover_architecture_dir >/dev/null 2>&1
    discover_adr_pattern >/dev/null 2>&1
  fi

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
  _run_env_full_check
  _cache_read
  _env_status_line
}
```

- [ ] **Step 2: 创建 SKILL.md**

创建 `skills/rdd-env-check/SKILL.md`，完整内容：

```markdown
---
name: rdd-env-check
description: 独立环境健康检查 skill — 检查 openspec CLI / git 工作区 / branch / build 目录，维护 `.rddf/state/.env-cache.json` 环境快照 (TTL 3600s + branch 失效)，输出单行状态供各 phase 首屏使用。被 guide-arch/guide-design/guide-plan/guide-ship Phase 1 调用。
license: MIT
compatibility: Requires bash + git + openspec CLI; 无需 jq/python3
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "skills/guide-arch/scripts/arch_env_check.sh"
  user-invocable: true
---

# rdd-env-check

## 调用方式

```bash
source "$(resolve_rdd_skill_dir rdd-env-check)/scripts/env_check.sh"
_run_env_check_cached   # 推荐入口: 读 cache, 命中输出单行; miss 现场跑
_run_env_full_check     # 强制全量检查 (写 cache + 输出 10 字段 JSON)
```

## JSON / Cache 契约

- 固定路径: `.rddf/state/.env-cache.json` (gitignored)
- 默认 TTL: 3600 秒; 覆盖: `RDD_ENV_CACHE_TTL` (设 0 恒失效)
- 固定 10 字段: `timestamp` `ttl_s` `branch` `openspec_ver` `git_clean` `build_dir` `adr_count` `roadmap_exists` `gap_count` `active_changes`
- 原子写: `.tmp` → `mv` (同目录 rename)
- 失效条件: 文件缺失 / mtime 超 TTL / `cache.branch != git branch --show-current`
- 命中输出: `✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓` (单行)
- 缓存**不保存** token / 绝对路径 / git remote 等敏感信息

## 失败行为

- openspec CLI 缺失 → 打印修复指引 (`npm install -g openspec-cli`), 退出码非 0 (阻断 phase 进入)
- 任何失效/缺失 → 降级现场全量检查, 对直接调用用户透明

## 边界

- 不缓存 ADR-0016 工件发现 (discover-arch-artifacts.sh 由 guide-arch 每次运行)
- 不修改 rddf-session 协议 (本 cache 是其同目录伴随状态文件)
```

- [ ] **Step 3: 跑测试验证核心用例转绿**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_rdd_env_check.bats`
Expected: helpers exist / 10-field contract / cache hit / TTL / branch change / one-line status 用例 GREEN。剩余 RED 用例：`openspec missing`（`_run_env_check_cached` 未在 PATH 清理下正确走全量）、`no jq/python3`（fakebin 目录不存在）、`atomic cache write`（grep 应命中）、`DRY refs`（arch_env_check.sh 未重构）。

- [ ] **Step 4: 冒烟回归**

Run: `cd "$REPO_ROOT" && bats tests/smoke.bats`
Expected: 仍 PASS（新 skill 不破坏基础设施冒烟）。

- [ ] **Step 5: Commit**

```bash
git add skills/rdd-env-check/
git commit -m "feat(rdd-env-check): add standalone env check skill with cached snapshot"
```

---

### Task 4: 重构 arch_env_check.sh + guide-arch 首屏（GREEN）

**Files:**
- Modify: `skills/guide-arch/scripts/arch_env_check.sh`
- Modify: `skills/guide-arch/SKILL.md`

- [ ] **Step 1: 重构 arch_env_check.sh 复用共享库**

编辑 `skills/guide-arch/scripts/arch_env_check.sh`：
- 在 `run_arch_env_check()` 开头 source 共享库（保持函数签名 `run_arch_env_check` 不变，兼容既有测试）：
  ```bash
  # source 共享环境检查库 (DRY 单一来源)
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  source "$(resolve_rdd_lib_dir)/env_checks.sh"
  ```
- 将原 openspec 检测块（L22-32）替换为 `_check_openspec || return 1`
- 将原 git 状态块（L35-41）替换为 `_check_git`
- 将原 branch 块（L44-46）替换为 `_check_branch`
- 将原 build 目录块（L49-66）替换为 `_check_build_dir`
- 计数段（L90-99）保持不变（ADR-0016 计数必须在 arch_env_check 现场算，不读 cache）
- 输出保持既有锚点：`现有 ADR` / `Roadmap` / `架构差距分析` / `活动 changes` / `工件发现 (ADR-0016)`（既有测试断言依赖）

- [ ] **Step 2: 更新 guide-arch SKILL.md 首屏为单行**

编辑 `skills/guide-arch/SKILL.md` Phase 1（L95-124 附近）：
- 保持 `run_arch_env_check || exit 1` 调用行不变（既有测试断言 `guide_arch_invokes_helper` 依赖）
- 将 "环境检查结果：" 下方的多行展示块（openspec/git/branch/build/ADR/roadmap... 共 ~8 行）替换为单行说明 + ADR-0016 发现结果：

  ```
  环境检查结果：
  ✅ Env OK (cached 23m ago) | ADR:63 | Roadmap:✓

  工件发现 (ADR-0016):
     ADR 目录:      docs/adr (true)
     ADR 模式:      ADR-*.md
     Roadmap:       roadmap.md (true)
     Architecture:  docs/architecture (true)
  ```

- [ ] **Step 3: 跑测试验证全绿**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_rdd_env_check.bats tests/integration/test_arch_env_check_extraction.bats`
Expected:
- test_rdd_env_check.bats: 10 个用例全 GREEN（含 DRY refs ≥4）
- test_arch_env_check_extraction.bats: 9 用例仍 PASS（签名 + 锚点 + fallback 不变）

- [ ] **Step 4: 冒烟 + Python 回归**

Run: `cd "$REPO_ROOT" && bats tests/smoke.bats && python3 -m pytest tests/unit/ -q --tb=short`
Expected: smoke PASS；Python unit 全 PASS（本 change 不动 Python，确认无副作用）。

- [ ] **Step 5: Commit**

```bash
git add skills/guide-arch/scripts/arch_env_check.sh skills/guide-arch/SKILL.md
git commit -m "refactor(guide-arch): reuse env_checks.sh + compress phase 1 first screen to one line"
```

---

### Task 5: design/plan/ship Phase 1 接入（GREEN）

**Files:**
- Create: `skills/guide-design/scripts/design_env_check.sh`
- Modify: `skills/guide-plan/scripts/plan_intake.sh`
- Create: `skills/guide-ship/scripts/ship_env_check.sh`

- [ ] **Step 1: 创建 design Phase 1 env check 接入**

创建 `skills/guide-design/scripts/design_env_check.sh`，完整内容：

```bash
#!/usr/bin/env bash
# skills/guide-design/scripts/design_env_check.sh — design Phase 1 环境检查接入
# Exports: run_design_env_check()
# 模式: 读 cache → 命中输出单行; miss/过期/branch 变化 → 现场全量 + 覆盖 cache
# 保持既有硬依赖检查 (arch-handoff) 不变, 本脚本只负责环境健康快照

run_design_env_check() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  source "${project_root:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  source "$(resolve_rdd_skill_dir rdd-env-check)/scripts/env_check.sh"
  _run_env_check_cached
}
```

- [ ] **Step 2: 创建 ship Phase 1 env check 接入**

创建 `skills/guide-ship/scripts/ship_env_check.sh`（同 design 模式，函数名 `run_ship_env_check`）：

```bash
#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_env_check.sh — ship Phase 1 环境检查接入
# Exports: run_ship_env_check()
# 模式: 读 cache → 命中输出单行; miss/过期/branch 变化 → 现场全量 + 覆盖 cache

run_ship_env_check() {
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  source "${project_root:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  source "$(resolve_rdd_skill_dir rdd-env-check)/scripts/env_check.sh"
  _run_env_check_cached
}
```

- [ ] **Step 3: 重构 plan_intake.sh openspec/git 段**

编辑 `skills/guide-plan/scripts/plan_intake.sh`：
- 在 `run_plan_intake()` 的 openspec 检测段（L114-125）替换为：
  ```bash
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  source "$(resolve_rdd_lib_dir)/env_checks.sh"
  _check_openspec || return 1
  _check_git
  _check_branch
  ```
- git 工作区段（L128-133）替换为 `_check_git` 后输出 `✅ git 工作区干净` / `⚠️ git 工作区有 N 个未跟踪/修改文件`（保持原输出锚点，plan 既有测试依赖）
- **保持** plan 特有逻辑不变：handoff 硬门 / jq 读 handoff / ADR_IDS / CURRENT_PHASE / active changes 计数
- 注意：plan_intake 的 `_check_*` 调用会覆盖 `_GIT_CLEAN` 等变量，不影响后续 handoff 读取逻辑

- [ ] **Step 4: 接线 SKILL.md 调用点**

- `skills/guide-design/SKILL.md` Phase 1（arch-handoff 硬检查之后）加：
  ```bash
  source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/design_env_check.sh"
  run_design_env_check
  ```
- `skills/guide-ship/SKILL.md` Phase 1（rddf-session hook 之后）加：
  ```bash
  source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/ship_env_check.sh"
  run_ship_env_check
  ```
- `skills/guide-plan/SKILL.md` Phase 1：`run_plan_intake` 已内部处理，无需改调用行（L156）

- [ ] **Step 5: 全量回归验证**

Run: `cd "$REPO_ROOT" && bats tests/integration/`
Expected: 全部集成测试 PASS（含 plan_intake 既有 7 用例、design/ship skill 元数据用例）。

Run: `cd "$REPO_ROOT" && python3 -m pytest tests/unit/ tests/integration/ -q --tb=short`
Expected: Python 全 PASS。

- [ ] **Step 6: Commit**

```bash
git add skills/guide-design/scripts/design_env_check.sh skills/guide-ship/scripts/ship_env_check.sh skills/guide-plan/scripts/plan_intake.sh skills/guide-design/SKILL.md skills/guide-ship/SKILL.md
git commit -m "feat(phases): wire rdd-env-check cached status into design/plan/ship phase 1"
```

---

### Task 6: 验证与文档（Verification + Docs）

**Files:**
- Modify: `skills/guide-arch/SKILL.md`（文档部分确认）
- Modify: `CHANGELOG.md`（若有）
- Create: `docs/adr/ADR-0026-extract-env-check.md`（仅当需记录职责再分配；如无必要跳过）

- [ ] **Step 1: 验收标准逐条验证**

Run: `cd "$REPO_ROOT"` 后逐条执行：
- **Acceptance #1**（JSON 字段一致）：`bats tests/integration/test_rdd_env_check.bats` 中 10-field contract 用例 GREEN
- **Acceptance #2**（首屏 1 行）：`bash -c "source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check"` 输出中 `环境检查结果：` 下方为单行（含 `✅ Env OK`）
- **Acceptance #3**（cache hit < 100ms）：`RDD_ENV_CACHE_TTL=3600` 预写 cache 后 `time (bash -c "source skills/rdd-env-check/scripts/env_check.sh && _run_env_check_cached")` 用户态耗时 < 100ms（不含 subprocess 启动）
- **Acceptance #4**（TTL/branch 失效）：`test_rdd_env_check.bats` 的 TTL + branch 两用例 GREEN
- **Acceptance #5**（openspec 缺失阻断）：`PATH=/usr/bin:/bin bash -c "source skills/rdd-env-check/scripts/env_check.sh && _run_env_check_cached"` 退出非 0 + 含修复指引
- **Acceptance #6**（4 phase 兼容）：`bats tests/integration/` + `pytest` 全 PASS
- **Acceptance #7**（无新依赖）：`test_rdd_env_check.bats` 的 no jq/python3 用例 GREEN（`command -v jq` 在测试中可缺席）
- **Acceptance #8**（DRY）：`grep -c '_check_' skills/guide-arch/scripts/arch_env_check.sh` ≥ 4

- [ ] **Step 2: 手工 walkthrough（arch → design → plan → ship）**

在干净环境（删除 `.rddf/state/.env-cache.json`）分别 source 四个 phase 入口脚本，验证：
- 首次进入：cache miss → 全量检查 → 写 cache → 单行输出
- 二次进入：cache hit → 单行 cached 输出
- `RDD_ENV_CACHE_TTL=0`：恒 miss，每次全量
- 切换 branch 后进入：cache 失效 → 重跑
- Phase 2-6 行为与修改前一致（无回归）

- [ ] **Step 3: 更新 CHANGELOG.md**

在 CHANGELOG.md 顶部 Unreleased 段（或对应当前版本段）追加：

```markdown
## Unreleased

### Added

- **rdd-env-check skill**: 环境健康检查外置为独立 skill，`.rddf/state/.env-cache.json` 快照缓存 (TTL 3600s + branch 失效)，arch/design/plan/ship Phase 1 首屏压缩为单行状态 (~600 tokens → ~50 tokens)。
```

- [ ] **Step 4: 更新 tasks.md 勾选**

编辑 `openspec/changes/extract-rdd-env-check-from-guide-arch/tasks.md`，将 2.1-2.5、3.1-3.10、4.1-4.4 全部勾选为 `- [x]`（跳过 4.4 ADR 创建 —— 本次职责再分配已由 design.md 决策记录，不另起 ADR；如审阅后认为需要 ADR 则创建 ADR-0026）。

- [ ] **Step 5: 最终回归 + Commit**

Run: `cd "$REPO_ROOT" && bats tests/ && python3 -m pytest tests/unit/ tests/integration/ -q --tb=short`
Expected: 全部 PASS。

```bash
git add -A
git commit -m "docs(rdd-env-check): changelog + tasks.md completion + verification pass"
```
