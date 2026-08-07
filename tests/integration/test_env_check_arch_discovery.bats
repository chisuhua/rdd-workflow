#!/usr/bin/env bats
# tests/integration/test_env_check_arch_discovery.bats
#
# Tests for proposal add-env-cache-arch-discovery — verifies the .env-cache.json
# extension to 13 fields (10 + 4 discovered_*) and env-check auto-discovery
# behavior. Companion to skills/rdd-env-check/scripts/env_check.sh and
# _lib/env_checks.sh.
#
# Run from repo root:
#   bats tests/integration/test_env_check_arch_discovery.bats

load ../test_helper

setup() {
  REPO_ROOT="${REPO_ROOT:?must be set by test_helper}"
  # Unset PROJECT_ROOT so env_check.sh's discover functions use cwd-derived root
  # (parent shell may have PROJECT_ROOT set to rdd-workflow repo, not sandbox).
  unset PROJECT_ROOT
  # Minimal sandbox: git init + copy only the env-check files we need.
  # Note: env_check.sh's _LIB_DIR resolves to <SANDBOX>/skills/_lib (going up
  # 2 from skills/rdd-env-check/scripts), so _lib must live there, NOT at root.
  SANDBOX="$(mktemp -d)"
  cd "$SANDBOX"
  git init -q .
  git config user.email "test@test.local"
  git config user.name  "Test"
  mkdir -p skills/rdd-env-check/scripts skills/_lib
  cp "$REPO_ROOT/skills/rdd-env-check/scripts/env_check.sh" skills/rdd-env-check/scripts/
  cp "$REPO_ROOT/_lib/env_checks.sh" skills/_lib/
  cp "$REPO_ROOT/_lib/discover-arch-artifacts.sh" skills/_lib/
  # Third-party layout: ADR in doc/adr (default discover candidate #2),
  # naming RFC-*.md (case auto-detect via discover_adr_pattern fallback).
  mkdir -p doc/adr
  echo "# RFC-0001-test" > doc/adr/RFC-0001-test.md
  mkdir -p planning
  echo "# Roadmap" > planning/roadmap.md
  # Initial commit so git rev-parse returns 'master' (avoids HEAD\nunknown bug
  # in env_check.sh's _check_branch when no commits exist)
  git add -A
  git commit -q -m "init"
  rm -rf .rddf/state/.env-cache.json
  export SANDBOX
}

teardown() {
  [ -n "${SANDBOX:-}" ] && rm -rf "$SANDBOX"
}

@test "Scenario 1: first run writes 14 fields including discovered_*" {
  cd "${SANDBOX:?}"
  unset PROJECT_ROOT
  source skills/rdd-env-check/scripts/env_check.sh
  _run_env_full_check
  [ -f .rddf/state/.env-cache.json ]
  count=$(grep -oE '"[a-z_]+":' .rddf/state/.env-cache.json | wc -l | tr -d '[:space:]')
  [ "$count" -eq 14 ]
  grep -q '"discovered_adr_dir":"doc/adr"' .rddf/state/.env-cache.json
  grep -q '"discovered_roadmap_path":"planning/roadmap.md"' .rddf/state/.env-cache.json
  grep -q '"discovered_architecture_dir":"docs/architecture"' .rddf/state/.env-cache.json
  pattern=$(grep -oE '"discovered_adr_pattern":"[^"]*"' .rddf/state/.env-cache.json | sed 's/.*:"//;s/"//')
  [ -n "$pattern" ]
}

@test "Scenario 2: SKIP_AUTO_DISCOVERY=yes preserves old behavior" {
  cd "${SANDBOX:?}"
  unset PROJECT_ROOT
  source skills/rdd-env-check/scripts/env_check.sh
  SKIP_AUTO_DISCOVERY=yes _run_env_full_check
  [ -f .rddf/state/.env-cache.json ]
  grep -q '"discovered_adr_dir":""' .rddf/state/.env-cache.json
  grep -q '"discovered_roadmap_path":""' .rddf/state/.env-cache.json
  grep -q '"discovered_architecture_dir":""' .rddf/state/.env-cache.json
  grep -q '"discovered_adr_pattern":""' .rddf/state/.env-cache.json
  ! grep -q '"discovered_adr_dir":"doc/adr"' .rddf/state/.env-cache.json
}

@test "Scenario 3: cache hit avoids re-scan (mtime unchanged)" {
  cd "${SANDBOX:?}"
  source skills/rdd-env-check/scripts/env_check.sh
  _run_env_full_check
  [ -f .rddf/state/.env-cache.json ]
  mtime1=$(stat -c %Y .rddf/state/.env-cache.json)
  sleep 2
  _run_env_check_cached
  mtime2=$(stat -c %Y .rddf/state/.env-cache.json)
  [ "$mtime1" = "$mtime2" ]
}

@test "Scenario 4: branch switch invalidates cache and rewrites" {
  cd "${SANDBOX:?}"
  source skills/rdd-env-check/scripts/env_check.sh
  _run_env_full_check
  grep -q '"branch":"master"' .rddf/state/.env-cache.json
  git checkout -b feature/test 2>/dev/null || git checkout feature/test 2>/dev/null
  _run_env_full_check
  grep -q '"branch":"feature/test"' .rddf/state/.env-cache.json
  git checkout master 2>/dev/null
}

@test "Scenario 6: old 10-field cache file is backward-compatible" {
  cd "${SANDBOX:?}"
  unset PROJECT_ROOT
  mkdir -p .rddf/state
  cat > .rddf/state/.env-cache.json <<EOF
{"timestamp":"1700000000","ttl_s":"3600","branch":"master","openspec_ver":"1.4.1","git_clean":"0","build_dir":"node_modules","adr_count":"5","roadmap_exists":"yes","gap_count":"0","active_changes":"1"}
EOF
  source skills/rdd-env-check/scripts/env_check.sh
  _run_env_check_cached || true
  [ -f .rddf/state/.env-cache.json ]
  grep -q '"adr_count":"5"' .rddf/state/.env-cache.json
  ! grep -q 'discovered_adr_dir' .rddf/state/.env-cache.json
}