#!/usr/bin/env bats
#
# Integration tests for _lib/scan-state.sh (extracted from guide.md).
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
  [ -f "$REPO_ROOT/skills/guide/scripts/scan-state.sh" ]
}

@test "scan_state: defines scan_state function" {
  grep -qE '^scan_state\(\) ?\{' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "scan_state: header documents P0/P1 bug history (regression guards)" {
  grep -q "P0\|P1" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  grep -q '\$3' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  grep -q "json.load" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "scan_state: uses fixed bracket format \[openspec/ in awk regex" {
  # Regression guard for the $3 ~ /^openspec\// bracket bug
  grep -qE 'awk.*\$3.*\[openspec/' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  # And must NOT have the buggy unbracketed variant anywhere
  ! grep -qE "awk.*'\\\$3 ~ /\\^openspec\\\\\//" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "scan_state: Python heredoc uses PY_PROJECT_ROOT env var (cwd safety)" {
  grep -q "PY_PROJECT_ROOT" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  grep -q 'os.environ\[.PY_PROJECT_ROOT.\]' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  # Negative: must NOT rely on cwd relative open
  ! grep -qE "open\(['\"]improvement-suggestions.md['\"]" "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
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
    source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    scan_state
    echo "RECOMMEND=$RECOMMEND"
    echo "REASON=$REASON"
  ) 2>&1
}

@test "scan_state: v4 arch-handoff + no planner-handoff → rdd-planner (branch 1c)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  # adr_count >= 1 means arch-done is complete; without it scan_state falls
  # through to priority 1.5 (rdd-arch recover) per current contract.
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  # no .planner-handoff.json (v4), no v3 handoffs
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-planner"
  echo "$out" | grep -q "planner 阶段"
}

@test "scan_state: v3 design-handoff (legacy) → rdd-builder + legacy warning (branch 0)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  echo '{"version":1,"design_complete_at":"2026-07-01","proposals_reviewed":3,"all_proposals_have_decision":true}' > .rddf/state/.design-handoff.json
  # no .plan-handoff.json, no .planner-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "legacy"
}

@test "scan_state: v3 plan-handoff (legacy) → rdd-builder + legacy warning (branch 0)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state openspec/changes/add-x
  echo '{"active_changes":1,"current_change":"add-x"}' > .rddf/state/.plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "legacy"
}

@test "scan_state: v4 planner-handoff + active change → rdd-builder (变更执行, branch 2)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state openspec/changes/add-x
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  echo '{"schema":"planner-handoff-v1","version":1,"owner":"rdd-planner","planner_complete_at":"2026-07-01","current_sprint":"s1","recommended_route":"full","awaiting_builder":["add-x"]}' > .rddf/state/.planner-handoff.json
  # Active change is detected from the FILESYSTEM: planner-handoff-v1 defines
  # no `active_changes` field, so reading it always yielded 0.
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "变更生成已完成 → 进入变更执行"
  ! echo "$out" | grep -q "残留"
}

@test "scan_state: v3 design-handoff (legacy) → change generation, NOT ship cleanup" {
  # The v3 DESIGN handoff means "design reviewed, changes not generated yet".
  # It must NOT be routed to the "plan-handoff leftover -> ship cleanup"
  # state, which belongs to the v3 PLAN handoff.
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  echo '{"version":1,"design_complete_at":"2026-07-01","proposals_reviewed":3}' > .rddf/state/.design-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "进入变更生成"
  ! echo "$out" | grep -q "残留"
}

@test "scan_state: v3 plan-handoff with active_changes=0 → ship cleanup (v3 semantics)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  echo '{"active_changes":0}' > .rddf/state/.plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "残留"
}

@test "scan_state: corrupt planner-handoff → rdd-planner (not treated as complete)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{"adr_count":1,"arch_done_at":"2026-07-01"}' > .rddf/state/.arch-handoff.json
  printf '{"schema":"planner-handoff-v1", TRUNCATED' > .rddf/state/.planner-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-planner"
  echo "$out" | grep -q "损坏"
}

@test "scan_state: no worktree + no handoff + no roadmap → guide-arch (branch 8)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  # no roadmap.md, no handoffs
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-arch"
}

@test "scan_state: roadmap + no changes dir → rdd-builder (branch 9)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md && git add . && git commit -q -m init
  # no openspec/ at all
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "进入变更生成"
}

@test "scan_state: roadmap + changes dir + no pending proposals → rdd-builder (无活跃 change)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  git add . && git commit -q -m init
  # improvement-approved.md / .rddf/improvements/ absent → HAS_APPROVED=no, HAS_PENDING=no
  # filter: 0 active changes → rdd-builder (not ship)
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "无活跃 change"
}

@test "scan_state: improvement-approved.md with entry → rdd-builder (branch 10)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  # dual-index model: approved entry in improvement-approved.md → rdd-builder (plan)
  mkdir -p .rddf/improvements && echo "# x" > .rddf/improvements/x.md
  printf '| [x](.rddf/improvements/x.md) | P0 | 2026-07-24 | t |\n' > improvement-approved.md
  git add . && git commit -q -m init
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
  echo "$out" | grep -q "有已批准 change 待创建"
}

@test "scan_state: Python parser reads improvement-approved.md via PROJECT_ROOT, not cwd (P1-7)" {
  # If buggy: scan_state is invoked from a cwd that does NOT contain
  # improvement-approved.md → python FileNotFoundError → HAS_APPROVED="" →
  # falls through to the rdd-builder default. Correct behavior:
  # scan_state must locate the file via PROJECT_ROOT regardless of cwd.
  local r; r=$(mktemp -d); cd /tmp || return 1   # deliberately NOT $r
  mkdir -p "$r"
  (cd "$r" && git init -q -b master && git config user.email t@t && git config user.name t
   echo "# Roadmap" > roadmap.md
   mkdir -p openspec/changes && touch openspec/changes/.keep
   mkdir -p .rddf/improvements && echo "# x" > .rddf/improvements/x.md
   printf '| [x](.rddf/improvements/x.md) | P0 | 2026-07-24 | t |\n' > improvement-approved.md
   git add . && git commit -q -m init)
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=rdd-builder"
}
@test "scan_state: sources check_project_setup and removes legacy LARGE_DIRS block" {
  grep -q 'check_project_setup' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  ! grep -q 'LARGE_DIRS' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "scan_state: setup issues printed but never block (exit 0)" {
  local fixture="$BATS_TEST_TMPDIR/scan-fixture"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf 'build/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "cd '$fixture' && source '$REPO_ROOT/skills/guide/scripts/scan-state.sh' && scan_state"
  [ "$status" -eq 0 ]
}
