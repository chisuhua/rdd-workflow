#!/usr/bin/env bats
# tests/integration/test_rddf_session_owner_aware.bats
# wave3-opencode-session-injection Task 1 — RDDF_OPENCODE_SESSION_AWARE probe
# (方案 B fallback per AC-P1-3-4: fallback chain ≤3 layers when aware mode on)

load "../test_helper"

setup() {
  export TEST_CACHE_DIR="$BATS_TMPDIR/cache-aware-$$-$BATS_TEST_NUMBER"
  mkdir -p "$TEST_CACHE_DIR"
  export ORIGINAL_HOME="$HOME"
  export HOME="$TEST_CACHE_DIR"
  unset OPENCODE_SESSION_ID

  HOOKS_SCRIPT="$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
  source "$HOOKS_SCRIPT" 2>/dev/null || true
}

teardown() {
  export HOME="$ORIGINAL_HOME"
  rm -rf "$TEST_CACHE_DIR"
}

@test "RDDF_OPENCODE_SESSION_AWARE=yes reads most recent ~/.opencode/sessions dir" {
  export RDDF_OPENCODE_SESSION_AWARE="yes"
  mkdir -p "$HOME/.opencode/sessions/ses_abc123def456"
  echo "{}" > "$HOME/.opencode/sessions/ses_abc123def456/meta.json"
  touch -t "202609241200.00" "$HOME/.opencode/sessions/ses_abc123def456/meta.json"

  _rddf_resolve_owner
  [ "$RDDF_OWNER" = "ses_abc123def456" ]
  [ "$RDDF_OWNER_FROM" = "opencode-session-aware" ]
}

@test "RDDF_OPENCODE_SESSION_AWARE=yes picks newest session when multiple exist" {
  export RDDF_OPENCODE_SESSION_AWARE="yes"
  mkdir -p "$HOME/.opencode/sessions/ses_old00000001"
  echo "{}" > "$HOME/.opencode/sessions/ses_old00000001/meta.json"
  touch -t "202609230900.00" "$HOME/.opencode/sessions/ses_old00000001/meta.json"
  mkdir -p "$HOME/.opencode/sessions/ses_new00000002"
  echo "{}" > "$HOME/.opencode/sessions/ses_new00000002/meta.json"
  touch -t "202609241500.00" "$HOME/.opencode/sessions/ses_new00000002/meta.json"

  _rddf_resolve_owner
  [ "$RDDF_OWNER" = "ses_new00000002" ]
}

@test "RDDF_OPENCODE_SESSION_AWARE=no falls through to normal fallback chain" {
  export RDDF_OPENCODE_SESSION_AWARE="no"
  mkdir -p "$HOME/.opencode/sessions/ses_ignored00001"
  echo "{}" > "$HOME/.opencode/sessions/ses_ignored00001/meta.json"

  _rddf_resolve_owner
  # Without OPENCODE_SESSION_ID, falls to cache/proc/shell-pid
  [ "$RDDF_OWNER_FROM" != "opencode-session-aware" ]
  [ -n "$RDDF_OWNER" ]
}

@test "RDDF_OPENCODE_SESSION_AWARE=yes with no sessions dir falls to fallback chain" {
  export RDDF_OPENCODE_SESSION_AWARE="yes"
  # No ~/.opencode/sessions exists

  _rddf_resolve_owner
  # Must NOT be opencode-session-aware; falls through to env/cache/proc/shell-pid
  [ "$RDDF_OWNER_FROM" != "opencode-session-aware" ]
  [ -n "$RDDF_OWNER" ]
}

@test "AC-P1-3-4: OPENCODE_SESSION_ID set resolves in 1 layer (env-first)" {
  export OPENCODE_SESSION_ID="ses_platform_truth"
  # Even with a stale cache present, env wins (effective depth 1)
  mkdir -p "$HOME/.cache"
  printf 'stale-cache-owner\tproc-cmdline\n' > "$HOME/.cache/rddf-session-owner"
  chmod 600 "$HOME/.cache/rddf-session-owner"

  _rddf_resolve_owner
  [ "$RDDF_OWNER" = "ses_platform_truth" ]
  [ "$RDDF_OWNER_FROM" = "env" ]
}

@test "AC-P1-3-4: platform env beats aware probe (方案 A > 方案 B)" {
  export RDDF_OPENCODE_SESSION_AWARE="yes"
  export OPENCODE_SESSION_ID="ses_platform_authoritative"
  mkdir -p "$HOME/.opencode/sessions/ses_filesystem_probe"
  echo "{}" > "$HOME/.opencode/sessions/ses_filesystem_probe/meta.json"
  touch -t "202609241500.00" "$HOME/.opencode/sessions/ses_filesystem_probe/meta.json"

  _rddf_resolve_owner
  # Platform env var wins over the ~/.opencode/sessions probe
  [ "$RDDF_OWNER" = "ses_platform_authoritative" ]
  [ "$RDDF_OWNER_FROM" = "env" ]
}

@test "MN-OPN1: 5-layer fallback chain preserved (backward compat)" {
  unset OPENCODE_SESSION_ID
  unset RDDF_OPENCODE_SESSION_AWARE
  # No cache, no opencode proc, no sessions dir
  _rddf_resolve_owner
  # shell-pid is layer 4 fallback — chain intact
  [ -n "$RDDF_OWNER_FROM" ]
  [ -n "$RDDF_OWNER" ]
}
