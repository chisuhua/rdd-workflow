#!/usr/bin/env bats
# tests/integration/test_rddf_session_owner_stability.bats
# P0 fix-rddf-session-owner-stability — 3-layer fallback verification
# 覆盖 5 个验收标准:
#   1. env var 优先
#   2. /proc cmdline 探测
#   3. cache file 跨调用复用
#   4. shell PID 兜底 (无 opencode 进程)
#   5. TTL expiry 重新探测

load "../test_helper"

setup() {
  # 每个 test 用独立 cache file, 避免互相污染
  export TEST_CACHE_DIR="$BATS_TMPDIR/cache-$$-$BATS_TEST_NUMBER"
  mkdir -p "$TEST_CACHE_DIR"
  # 临时 monkey-patch $HOME 让 _rddf_resolve_owner 写到这里
  export ORIGINAL_HOME="$HOME"
  export HOME="$TEST_CACHE_DIR"

  # Source hook script 拿到 _rddf_resolve_owner 函数
  HOOKS_SCRIPT="$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  source "$HOOKS_SCRIPT" 2>/dev/null || true
}

teardown() {
  export HOME="$ORIGINAL_HOME"
  rm -rf "$TEST_CACHE_DIR"
}

@test "env var 优先: OPENCODE_SESSION_ID 设置时使用 env, 忽略 cache/proc/shell" {
  export OPENCODE_SESSION_ID="env-uuid-abc123"
  _rddf_resolve_owner
  [ "$RDDF_OWNER" = "env-uuid-abc123" ]
  [ "$RDDF_OWNER_FROM" = "env" ]
}

@test "cache file TTL 内复用: 第二次调用读 cache 而非重新探测" {
  # Pre-populate cache
  mkdir -p "$HOME/.cache"
  printf 'cached-owner-xyz\tproc-cmdline\n' > "$HOME/.cache/rddf-session-owner"
  chmod 600 "$HOME/.cache/rddf-session-owner"
  unset OPENCODE_SESSION_ID

  _rddf_resolve_owner
  [ "$RDDF_OWNER" = "cached-owner-xyz" ]
  [ "$RDDF_OWNER_FROM" = "cached-file" ]
}

@test "cache file TTL 过期 (1h+) 触发重新探测" {
  # Pre-populate cache with old mtime
  mkdir -p "$HOME/.cache"
  printf 'stale-owner\tproc-cmdline\n' > "$HOME/.cache/rddf-session-owner"
  chmod 600 "$HOME/.cache/rddf-session-owner"
  # Force mtime to 2h ago
  touch -d "2 hours ago" "$HOME/.cache/rddf-session-owner"
  unset OPENCODE_SESSION_ID

  _rddf_resolve_owner
  # 应 NOT 等于 stale-owner
  [ "$RDDF_OWNER" != "stale-owner" ]
  # 兜底到 shell-pid (无 opencode cmdline 探测)
  [ "$RDDF_OWNER_FROM" = "shell-pid" ] || [ "$RDDF_OWNER_FROM" = "proc-cmdline" ]
}

@test "无 opencode 进程 + 无 cache 时返回合法 owner (env/proc/shell 任一)" {
  unset OPENCODE_SESSION_ID
  # 明确无 cache
  rm -f "$HOME/.cache/rddf-session-owner"
  _rddf_resolve_owner
  # 3 种合法 source: env | proc-cmdline | shell-pid | cached-file
  case "$RDDF_OWNER_FROM" in
    env|proc-cmdline|shell-pid|cached-file) ;;
    *) echo "unexpected source: $RDDF_OWNER_FROM"; return 1 ;;
  esac
  # 兜底格式: $(hostname -s)_<pid>
  EXPECTED_REGEX="^$(hostname -s)_[0-9]+$"
  [[ "$RDDF_OWNER" =~ $EXPECTED_REGEX ]]
}

@test "cache file 权限 0600: 写入新探测结果时 chmod 600" {
  unset OPENCODE_SESSION_ID
  rm -f "$HOME/.cache/rddf-session-owner"
  _rddf_resolve_owner
  if [ -f "$HOME/.cache/rddf-session-owner" ]; then
    PERMS=$(stat -c %a "$HOME/.cache/rddf-session-owner" 2>/dev/null || stat -f %Lp "$HOME/.cache/rddf-session-owner" 2>/dev/null)
    [ "$PERMS" = "600" ]
  fi
}

@test "OPENCODE_SESSION_ID_FROM 通过 hook 函数被 export (5 处全部)" {
  # 验证 5 个 hook 函数都正确 export OPENCODE_SESSION_ID_FROM
  for fn in rddf_session_hook_entry rddf_session_hook_close rddf_session_hook_heartbeat rddf_session_hook_attach rddf_session_hook_detach; do
    export OPENCODE_SESSION_ID="test-owner-$fn"
    # 调用 hook (会失败, 但 export 应该已发生)
    $fn stage_test_$fn test 2>/dev/null || true
    # 函数体外 OPENCODE_SESSION_ID_FROM 仍应被 export (因为 _rddf_resolve_owner export)
    [ -n "$OPENCODE_SESSION_ID_FROM" ]
  done
}
