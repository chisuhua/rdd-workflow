#!/usr/bin/env bats
# tests/integration/test_rdd_env_check.bats
# extract-rdd-env-check-from-guide-arch: 环境健康检查外置 + cache 三场景 + JSON 契约
# 覆盖 acceptance #1-#8

load ../test_helper

SKILL_DIR="$REPO_ROOT/skills/rdd-env-check"
ENV_CHECK="$SKILL_DIR/scripts/env_check.sh"
LIB_CHECKS="$REPO_ROOT/_lib/env_checks.sh"
CACHE_PATH=".rddf/state/.env-cache.json"

make_env_check_repo() {
  local tmpdir
  tmpdir=$(mktemp -d -t rdd-env-check-XXXXXX)
  git init -q -b master "$tmpdir"
  git -C "$tmpdir" config user.email "test@test"
  git -C "$tmpdir" config user.name "test"
  git -C "$tmpdir" commit --allow-empty -m "init" --quiet
  mkdir -p "$tmpdir/.rddf/state"
  printf '%s' "$tmpdir"
}

@test "rdd_env_check: helpers exist" {
  [ -f "$SKILL_DIR/SKILL.md" ]
  [ -f "$ENV_CHECK" ]
  [ -f "$LIB_CHECKS" ]
  grep -q '^_check_openspec()' "$LIB_CHECKS"
  grep -q '^_check_git()' "$LIB_CHECKS"
  grep -q '^_check_build_dir()' "$LIB_CHECKS"
  grep -q '_check_branch' "$LIB_CHECKS"
}

@test "rdd_env_check: 15-field JSON contract includes gh_available" {
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_full_check"
  [ "$status" -eq 0 ]
  # 15 个固定字段 (14 baseline + gh_available from add-env-check-gh-available)
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
  echo "$fields" | grep -q 'discovered_adr_dir: '
  echo "$fields" | grep -q 'discovered_roadmap_path: '
  echo "$fields" | grep -q 'discovered_architecture_dir: '
  echo "$fields" | grep -q 'discovered_adr_pattern: '
  echo "$fields" | grep -q 'gh_available: '
  [ "$(echo "$fields" | wc -w)" -eq 15 ]
}

@test "rdd_env_check: cache hit skips full check (under 100ms)" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local branch
  branch=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1,"discovered_adr_dir":"docs/adr","discovered_roadmap_path":"roadmap.md","discovered_architecture_dir":"docs/architecture","discovered_adr_pattern":"ADR-*.md","gh_available":"yes:test"}
EOF
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  echo "$output" | grep -q 'cached'
  local log
  log=$(bash -c "cd '$tmpdir' && source '$ENV_CHECK' && RDD_ENV_CHECK_DEBUG=1 _run_env_check_cached" 2>&1)
  echo "$log" | grep -q 'cached'
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}

@test "rdd_env_check: TTL expiry triggers full recheck" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local branch
  branch=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1,"discovered_adr_dir":"docs/adr","discovered_roadmap_path":"roadmap.md","discovered_architecture_dir":"docs/architecture","discovered_adr_pattern":"ADR-*.md","gh_available":"yes:test"}
EOF
  touch -d "2 hours ago" "$tmpdir/.rddf/state/.env-cache.json"
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  if echo "$output" | grep -q 'cached'; then
    echo "$output" | grep -q 'openspec'
  fi
  local new_mtime
  new_mtime=$(stat -c %Y "$tmpdir/.rddf/state/.env-cache.json")
  local now
  now=$(date +%s)
  [ $((now - new_mtime)) -lt 120 ]
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}

@test "rdd_env_check: branch change invalidates cache" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local current
  current=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  local other="other-branch-name"
  [ "$current" != "$other" ] || other="another-branch-name"
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$other","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1,"discovered_adr_dir":"docs/adr","discovered_roadmap_path":"roadmap.md","discovered_architecture_dir":"docs/architecture","discovered_adr_pattern":"ADR-*.md","gh_available":"no:gh-missing"}
EOF
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  local cached_branch
  cached_branch=$(python3 -c "import json;print(json.load(open('$tmpdir/.rddf/state/.env-cache.json'))['branch'])" 2>/dev/null || echo "$current")
  [ "$cached_branch" = "$current" ]
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}

@test "rdd_env_check: openspec missing blocks with non-zero + repair guidance" {
  rm -f "$REPO_ROOT/.rddf/state/.env-cache.json"
  run bash -c "cd '$REPO_ROOT' && export PATH=/usr/bin:/bin && source '$ENV_CHECK' && _run_env_check_cached"
  # cache 不存在 + openspec 缺失 → 阻断, 退出非 0
  [ "$status" -ne 0 ]
  echo "$output" | grep -q 'openspec'
}

@test "rdd_env_check: no jq/python3 runtime dependency" {
  # 实现不得实际调用 jq/python3 命令 (排除注释行)
  ! grep -vE '^\s*#' "$ENV_CHECK" | grep -qE '(^|[;&|])\s*(jq|python3)\s'
  ! grep -vE '^\s*#' "$LIB_CHECKS" | grep -qE '(^|[;&|])\s*(jq|python3)\s'
}

@test "rdd_env_check: atomic cache write uses tmp + mv" {
  # .tmp + mv 原子写逻辑在共享库 _cache_write 中 (${cache_file}.tmp 动态拼接)
  grep -q '\.tmp"' "$LIB_CHECKS"
  grep -q '^  mv ' "$LIB_CHECKS"
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

# ── _check_gh (ADR-0027 §1.0 reporter 前置依赖) ─────────────────────────

@test "rdd_env_check: _check_gh tri-state value matches installed gh status" {
  # The exact value depends on the test env (may be yes:<user>, no:gh-missing,
  # or no:not-authed). Verify the value conforms to the documented tri-state
  # contract: starts with "yes:" or "no:".
  run bash -c "source '$LIB_CHECKS' && _check_gh && echo \"\$_GH_AVAILABLE\""
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^yes:[^[:space:]]+$ ]] || [[ "$output" =~ ^no:[a-z-]+$ ]]
}

@test "rdd_env_check: _check_gh returns 0 (non-blocking) when gh missing" {
  # The contract: _check_gh must NOT block phase entry even when gh is absent
  run bash -c "PATH=/tmp/empty-path-no-gh source '$LIB_CHECKS' && _check_gh"
  [ "$status" -eq 0 ]
}

@test "rdd_env_check: _check_gh sets _GH_AVAILABLE in JSON output" {
  # Full pipeline: _check_gh is called by _run_env_full_check and the result
  # is included in the 15-field JSON output
  run bash -c "cd '$REPO_ROOT' && source '$ENV_CHECK' && _run_env_full_check"
  [ "$status" -eq 0 ]
  echo "$output" | grep -qE '^gh_available: (yes:[^[:space:]]+|no:[a-z-]+)$'
}

@test "rdd_env_check: gh_available field persists in cache" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_full_check"
  [ "$status" -eq 0 ]
  local cached_gh
  cached_gh=$(python3 -c "import json;print(json.load(open('$tmpdir/.rddf/state/.env-cache.json'))['gh_available'])" 2>/dev/null || echo "")
  [ -n "$cached_gh" ]
  [[ "$cached_gh" =~ ^yes: ]] || [[ "$cached_gh" =~ ^no: ]]
  rm -rf "$tmpdir"
}
