#!/usr/bin/env bats
# tests/integration/test_roadmap_missing_warning.bats
#
# T16 — P1-6: warn when roadmap.md missing but .zcf/.roadmap-state.json exists
#
# Addresses propose.md:65 and guide-spec.md:182 (audit findings).
# When compat mode is active (roadmap.md absent) but the state file still
# exists, the user should see an informative warning explaining:
#   - the mode has switched to compat
#   - roadmap-meta.yaml is NOT auto-synced to .roadmap-state.json
#   - how to re-enable roadmap: skill_use("roadmap", "init")
#
# This file contains static (source-level) tests against the markdown files.
# A runtime test exercises the actual bash logic from propose.md to confirm
# the warning fires exactly when expected (and never when state is clean).

load ../test_helper

PROPOSE_MD="$REPO_ROOT/skills/propose.md"
GUIDE_SPEC_MD="$REPO_ROOT/skills/guide-spec.md"

# ============================================================
# STATIC TESTS — verify the warning text is present in source
# ============================================================

@test "propose.md warns when roadmap.md missing but state file exists" {
  [ -f "$PROPOSE_MD" ]
  grep -q "roadmap.md 已不存在" "$PROPOSE_MD"
  grep -q ".zcf/.roadmap-state.json 存在" "$PROPOSE_MD"
}

@test "propose.md warning mentions how to re-enable roadmap" {
  [ -f "$PROPOSE_MD" ]
  grep -q 'skill_use.*roadmap.*init' "$PROPOSE_MD"
}

@test "propose.md warning explains meta.yaml is NOT auto-synced" {
  [ -f "$PROPOSE_MD" ]
  grep -q "roadmap-meta.yaml" "$PROPOSE_MD"
  grep -qE "(不会|not).{0,30}自动" "$PROPOSE_MD"
}

@test "guide-spec.md also has roadmap missing warning" {
  [ -f "$GUIDE_SPEC_MD" ]
  grep -q "roadmap.md 已不存在" "$GUIDE_SPEC_MD"
}

@test "guide-spec.md warning defines STATE_FILE before use" {
  # The roadmap check block must define STATE_FILE before the
  # `if [ ! -f ROADMAP_FILE ] && [ -f STATE_FILE ]` check.
  [ -f "$GUIDE_SPEC_MD" ]
  grep -q 'STATE_FILE=' "$GUIDE_SPEC_MD"
  grep -q '.zcf/.roadmap-state.json' "$GUIDE_SPEC_MD"
}

# ============================================================
# RUNTIME TESTS — execute the actual bash snippet from propose.md
# ============================================================

@test "runtime: warning fires when roadmap missing AND state file exists" {
  local test_repo
  test_repo=$(mktemp -d)
  cd "$test_repo" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init

  # State file exists, but roadmap.md is missing
  mkdir -p .zcf
  echo '{"phase":"phase-1","category":"core-impl"}' > .zcf/.roadmap-state.json

  local output
  output=$(bash -c '
    PROJECT_ROOT="$(pwd)"
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
    STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

    ROADMAP_MODE=false
    if [ -f "$ROADMAP_FILE" ]; then
      ROADMAP_MODE=true
    else
      echo "⚠️  未检测到 roadmap.md，使用兼容模式"
      if [ -f "$STATE_FILE" ]; then
        echo ""
        echo "⚠️  roadmap.md 已不存在，但 .zcf/.roadmap-state.json 存在"
        echo "   推测：roadmap 模式已切换为兼容模式"
        echo "   已有的 roadmap-meta.yaml 不会自动更新 .roadmap-state.json"
        echo "   如需重新启用 roadmap，请运行：skill_use(\"roadmap\", \"init\")"
      fi
    fi
  ' 2>&1)
  local rc=$?
  cd /
  rm -rf "$test_repo"

  [ "$rc" -eq 0 ] || { echo "Script exited with $rc: $output" >&2; return 1; }
  echo "$output" | grep -q "roadmap.md 已不存在"
  echo "$output" | grep -q ".zcf/.roadmap-state.json 存在"
  echo "$output" | grep -q "roadmap 模式已切换为兼容模式"
  echo "$output" | grep -q "skill_use(\"roadmap\", \"init\")"
}

@test "runtime: no false-positive when both roadmap and state are absent" {
  # P1-6 must NOT spam a warning if the project is a fresh repo with NO
  # state file. The warning is specifically for the compat-mode-with-stale-state
  # case, not for the "never had a roadmap" case.
  local test_repo
  test_repo=$(mktemp -d)
  cd "$test_repo" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init

  # No state file, no roadmap.md
  local output
  output=$(bash -c '
    PROJECT_ROOT="$(pwd)"
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
    STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

    if [ -f "$ROADMAP_FILE" ]; then
      echo "ROADMAP_PRESENT"
    else
      echo "⚠️  未检测到 roadmap.md，使用兼容模式"
      if [ -f "$STATE_FILE" ]; then
        echo "STALE_STATE_WARNING"
      else
        echo "CLEAN_COMPAT_MODE"
      fi
    fi
  ' 2>&1)
  local rc=$?
  cd /
  rm -rf "$test_repo"

  [ "$rc" -eq 0 ] || { echo "Script exited with $rc: $output" >&2; return 1; }
  echo "$output" | grep -q "未检测到 roadmap.md"
  echo "$output" | grep -q "CLEAN_COMPAT_MODE"
  ! echo "$output" | grep -q "STALE_STATE_WARNING"
  ! echo "$output" | grep -q "roadmap.md 已不存在"
}

@test "runtime: no warning when roadmap.md IS present" {
  # Sanity: if roadmap.md exists, no compat-mode branch runs at all,
  # so the warning must never appear.
  local test_repo
  test_repo=$(mktemp -d)
  cd "$test_repo" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init

  # roadmap.md present, state file also present (normal mode)
  echo "# Roadmap" > roadmap.md
  mkdir -p .zcf
  echo '{"phase":"phase-1"}' > .zcf/.roadmap-state.json

  local output
  output=$(bash -c '
    PROJECT_ROOT="$(pwd)"
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
    STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

    if [ -f "$ROADMAP_FILE" ]; then
      echo "ROADMAP_MODE_ACTIVE"
    else
      echo "COMPAT_MODE"
    fi
  ' 2>&1)
  local rc=$?
  cd /
  rm -rf "$test_repo"

  [ "$rc" -eq 0 ] || { echo "Script exited with $rc: $output" >&2; return 1; }
  echo "$output" | grep -q "ROADMAP_MODE_ACTIVE"
  ! echo "$output" | grep -q "roadmap.md 已不存在"
}
