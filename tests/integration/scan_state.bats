#!/usr/bin/env bats
#
# Integration tests for skills/_lib/scan-state.sh (extracted from guide.md).
#
# Coverage:
#   - Static: source-file presence + grep for tokens that prove design
#   - Runtime: 11 priority branches (each as separate @test) against real
#     git repos created with `mktemp -d` (Pattern C from test_roadmap_missing_warning.bats)
#
# Conventions:
#   - mktemp -d in @test body, not BATS_TEST_TMPDIR (per AGENTS.md + README)
#   - source scan-state.sh via load_lib scan-state (test_helper.bash:22-37)
#   - assert via echo "$output" | grep -q "<keyword>"
#
# Run: bats tests/integration/scan_state.bats

load ../test_helper

# ---- Static tests (no git repo required) --------------------------------

@test "scan_state: library file exists" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
}

@test "scan_state: defines scan_state function" {
  grep -qE '^scan_state\(\) ?\{' "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: header documents P0/P1 bug history (regression guards)" {
  grep -q "P0\|P1" "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q '\$3' "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q "json.load" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: uses fixed bracket format \[openspec/ in awk regex" {
  # Regression guard for the $3 ~ /^openspec\// bracket bug
  grep -qE 'awk.*\$3.*\[openspec/' "$REPO_ROOT/skills/_lib/scan-state.sh"
  # And must NOT have the buggy unbracketed variant anywhere
  ! grep -qE "awk.*'\\\$3 ~ /\\^openspec\\\\\//" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: Python heredoc uses PY_PROJECT_ROOT env var (cwd safety)" {
  grep -q "PY_PROJECT_ROOT" "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q 'os.environ\[.PY_PROJECT_ROOT.\]' "$REPO_ROOT/skills/_lib/scan-state.sh"
  # Negative: must NOT rely on cwd relative open
  ! grep -qE "open\(['\"]proposal-suggestions.md['\"]" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

# ---- Runtime tests (Pattern C: mktemp -d in @test body) ------------------
#
# Helper: runs scan_state() inside the given test_repo and prints RECOMMEND
# and REASON on stdout (one per line) for grep-based assertions.

_run_scan() {
  local repo="$1"
  (
    cd "$repo" || exit 1
    export PROJECT_ROOT="$repo"
    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    scan_state
    echo "RECOMMEND=$RECOMMEND"
    echo "REASON=$REASON"
  )
}

@test "scan_state: arch-handoff + no plan-handoff → guide-plan (branch 1)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{}' > .rddf/state/.arch-handoff.json
  # no .plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}

@test "scan_state: plan-handoff exists → guide-ship (branch 2)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{}' > .rddf/state/.plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-ship"
}

@test "scan_state: no worktree + no handoff + no roadmap → guide-arch (branch 8)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  # no roadmap.md, no handoffs
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-arch"
}

@test "scan_state: roadmap + no changes dir → guide-plan (branch 9)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md && git add . && git commit -q -m init
  # no openspec/ at all
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}

@test "scan_state: roadmap + changes dir + no pending proposals → guide-ship (default)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  git add . && git commit -q -m init
  # proposal-suggestions.md absent → HAS_PENDING=no → guide-ship default
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-ship"
  echo "$out" | grep -q "无待创建 change"
}

@test "scan_state: proposal-suggestions.md with status=待创建 → guide-plan (branch 10)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  # proposal-suggestions.md is a JSON array (P1-7 requires json.load, not grep)
  printf '[{"title":"x","status":"待创建"}]' > proposal-suggestions.md
  git add . && git commit -q -m init
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
  echo "$out" | grep -q "待创建"
}

@test "scan_state: Python parser reads proposal-suggestions.md via PROJECT_ROOT, not cwd (P1-7)" {
  # If buggy: scan_state is invoked from a cwd that does NOT contain
  # proposal-suggestions.md → python FileNotFoundError → HAS_PENDING="" →
  # falls through to default branch 11 → guide-ship. Correct behavior:
  # scan_state must locate the file via PROJECT_ROOT regardless of cwd.
  local r; r=$(mktemp -d); cd /tmp || return 1   # deliberately NOT $r
  mkdir -p "$r"
  (cd "$r" && git init -q -b master && git config user.email t@t && git config user.name t
   echo "# Roadmap" > roadmap.md
   mkdir -p openspec/changes && touch openspec/changes/.keep
   printf '[{"status":"待创建"}]' > proposal-suggestions.md
   git add . && git commit -q -m init)
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}