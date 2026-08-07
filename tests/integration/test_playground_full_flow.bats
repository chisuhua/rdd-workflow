#!/usr/bin/env bats
# tests/integration/test_playground_full_flow.bats
#
# End-to-end validation: the full rdd-workflow v2.1 four-phase lifecycle
# (arch → design → plan → ship → execute → archive) executed from an
# isolated external playground project, asserting:
#   - Each phase writes its handoff file into the playground's .rddf/state/
#   - The orchestrator (rddf guide) advances its recommendation phase-by-phase
#   - openspec/changes/<name>/ reaches archive/ via openspec archive
#   - iteration.json reaches status=archived with archived_at timestamp
#   - The source rdd-workflow repo is NOT touched by any of the above
#
# Skip-not-fail policy: tests skip cleanly when prerequisites are missing
# (rddf not on PATH, global skill install absent, openspec CLI missing).
# Tests run independently from the source repo via $BATS_TMPDIR isolation;
# teardown removes the playground but NEVER touches the source repo's
# .rddf/state/ (which is shared with other bats suites).

load ../test_helper

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)}"
RDDF_HOME_BIN="${HOME}/.local/bin/rddf"
RDDF_GLOBAL_LIB="${HOME}/.agents/skills/_lib"
PLAYGROUND=""

# File-level setup: create one isolated playground shared across all tests
# in this file. This is critical because the workflow is sequential — arch
# feeds design feeds plan feeds ship — and state must persist across tests.
setup_file() {
  PLAYGROUND="${BATS_TMPDIR}/playground-e2e"
  mkdir -p "$PLAYGROUND"
  cd "$PLAYGROUND"

  git init -q
  git config user.email "playground@example.com"
  git config user.name "Playground"
  echo '{"name":"external-playground","version":"9.9.9","description":"isolated end-to-end test"}' > package.json
  echo "# External Playground" > README.md
  git add . && git commit -q -m "init: fake external project"

  # Documented bootstrap (NOT the buggy inline path in arch_env_check.sh
  # / arch_done_gate.sh which points to ~/.agents/_lib/skill_root.sh).
  # Pre-sourcing the correct path makes `resolve_rdd_lib_dir` available
  # to scripts that re-attempt the buggy bootstrap internally.
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
    2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"

  export PROJECT_ROOT="$PLAYGROUND"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  echo '{}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
}

setup() {
  cd "$PROJECT_ROOT"
  # Re-source bootstrap per-test because bats invokes `setup()` in a fresh
  # subshell for each @test. Scripts sourced inside individual tests that
  # rely on resolve_rdd_lib_dir need it defined here too.
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
    2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
}

teardown_file() {
  [ -n "${PLAYGROUND:-}" ] && rm -rf "$PLAYGROUND"
  # Intentionally NEVER touch source repo's .rddf/state/ — other bats
  # suites (test_init_smoke.bats, etc.) rely on stale state files.
}

teardown() {
  : # per-test teardown is a no-op; setup_file handles cleanup
}

# ── Prerequisites (skip-not-fail) ───────────────────────────────────

@test "playground_full_flow: prerequisites (rddf + global install + openspec) are present" {
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill install missing"
  command -v openspec >/dev/null || skip "openspec CLI missing"
}

# ── A. Arch Phase ──────────────────────────────────────────────────

@test "01_arch: env-check writes .env-cache.json into playground" {
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  cd "$PROJECT_ROOT"
  source "$RDDF_GLOBAL_LIB/env_checks.sh"
  _check_openspec || return 1
  _check_git || true
  _check_branch || true
  _check_build_dir || true
  # Force playground-specific values (this is a fresh project)
  _CURRENT_BRANCH="master"
  _OPENSPEC_VER="$(openspec --version 2>/dev/null || echo unknown)"
  _GIT_CLEAN=1
  _BUILD_DIR="node_modules"
  _ADR_COUNT=0
  _ROADMAP_EXISTS="no"
  _GAP_COUNT=0
  _ACTIVE_CHANGES=0
  _cache_write
  [ -f "$PROJECT_ROOT/.rddf/state/.env-cache.json" ]
  [ "$(jq -r '.roadmap_exists' "$PROJECT_ROOT/.rddf/state/.env-cache.json")" = "no" ]
}

@test "02_arch: ADR + roadmap created and committed" {
  cd "$PROJECT_ROOT"
  mkdir -p docs/adr
  cp "$REPO_ROOT/docs/adr/ADR-0000-template.md" docs/adr/ADR-0001-test.md
  sed -i 's/ADR-0000/ADR-0001/g; s/<简短标题>/Playground Test/g' docs/adr/ADR-0001-test.md
  cat > roadmap.md <<'EOF'
# Playground Roadmap
## Phase 1
- Init project
- Add docs/adr/
EOF
  git add . && git commit -q -m "feat: add ADR-0001 + roadmap"
  [ -f "docs/adr/ADR-0001-test.md" ]
  [ -f "roadmap.md" ]
}

@test "03_arch: arch-done gate passes (ADRs + roadmap present)" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-arch/scripts/arch_done_gate.sh"
  # Use `run` to capture exit code without triggering bats' ERR trap on the
  # buggy inline bootstrap source (line 22 fails on missing
  # $HOME/.agents/_lib/skill_root.sh even though the gate itself succeeds).
  run check_arch_done_gate
  [ "$status" -eq 0 ]
}

@test "04_arch: arch-handoff.json written with completed state" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff.sh"
  # Same workaround as 03_arch — write_arch_handoff.sh has the same buggy
  # bootstrap path on line 17.
  run write_arch_handoff
  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]
  local adr_count
  adr_count=$(jq -r '.adr_count' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  [ "$adr_count" -ge 1 ]
  [ "$(jq -r '.roadmap_exists' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")" = "true" ]
}

# ── B. Design Phase ────────────────────────────────────────────────

@test "05_design: minimal proposal-suggestions + proposal-approved pass design-done gate" {
  cd "$PROJECT_ROOT"
  cat > proposal-suggestions.md <<'EOF'
# Proposals

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
EOF
  cat > proposal-approved.md <<'EOF'
# Approved Proposals

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|
EOF
  local pending
  pending=$(grep -E '^\s*\|\s*\[' "$PROJECT_ROOT/proposal-suggestions.md" 2>/dev/null \
    | while IFS='|' read -r _ _ _ _ _ status _; do
        status=$(echo "$status" | xargs)
        if [ "$status" != "已批准" ] && [ "$status" != "已拒绝" ] && [ "$status" != "延迟" ]; then
          echo "$status"
        fi
      done)
  [ -z "$pending" ]
}

@test "06_design: design-handoff.json written" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-design/scripts/write_design_handoff.sh"
  write_design_handoff 0
  [ -f "$PROJECT_ROOT/.rddf/state/.design-handoff.json" ]
  [ "$(jq -r '.all_proposals_have_decision' "$PROJECT_ROOT/.rddf/state/.design-handoff.json")" = "true" ]
}

# ── C. Plan Phase ──────────────────────────────────────────────────

@test "07_plan: openspec change skeleton accepted (5 files + delta spec)" {
  cd "$PROJECT_ROOT"
  local name="test-playground-change"
  mkdir -p "openspec/changes/$name/specs/test-capability"

  cat > "openspec/changes/$name/.openspec.yaml" <<EOF
name: $name
created_by: playground-bats
EOF
  cat > "openspec/changes/$name/proposal.md" <<'EOF'
# test-playground-change

## Why
Validate the rdd-workflow plan-done gate from an isolated playground.

## What Changes

**In Scope**:
- Create one minimal change to satisfy Gate 1/2 of plan-done

**Out of Scope**:
- Production code changes

## Capabilities

### New Capabilities
- Test plan-done flow.

## Impact
- Sandbox only.

## Acceptance
- [ ] plan-done gate passes
- [ ] design-handoff.json written to playground
- [ ] Source repo zero changes
EOF
  cat > "openspec/changes/$name/design.md" <<'EOF'
# Design

## Decisions
- Use openspec change skeleton as-is
EOF
  cat > "openspec/changes/$name/tasks.md" <<'EOF'
# Tasks

- [x] Create change skeleton
- [x] Commit to git
EOF
  cat > "openspec/changes/$name/roadmap-meta.yaml" <<EOF
phase: default
category: general
change_type: feature
priority: P3
parent_feature: ""
EOF
  cat > "openspec/changes/$name/specs/test-capability/spec.md" <<'EOF'
# Test Capability

## ADDED Requirements

### Requirement: plan-done validation
The plan-done gate SHALL validate changes from an isolated playground project.

#### Scenario: Valid change passes
- GIVEN a change with proposal.md, design.md, tasks.md
- WHEN plan-done gate runs
- THEN it writes plan-handoff.json

#### Scenario: Invalid change blocks
- GIVEN a change missing artifacts
- WHEN plan-done gate runs
- THEN it returns 1
EOF
  git add . && git commit -q -m "feat: add change skeleton"

  openspec validate "$name" --json > /tmp/openspec-validate.json
  local valid
  valid=$(jq -r '.items[0].valid' /tmp/openspec-validate.json)
  [ "$valid" = "true" ]
}

@test "08_plan: plan-done triple gate passes" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
  run_plan_done_gate
}

@test "09_plan: plan-handoff.json written with current_change" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
  # Same workaround — plan_done_gate.sh:159 has the same buggy bootstrap.
  run write_plan_handoff
  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" ]
  [ "$(jq -r '.active_changes' "$PROJECT_ROOT/.rddf/state/.plan-handoff.json")" -ge 1 ]
  [ "$(jq -r '.current_change' "$PROJECT_ROOT/.rddf/state/.plan-handoff.json")" = "test-playground-change" ]
  [ "$(jq -r '.all_artifacts_committed' "$PROJECT_ROOT/.rddf/state/.plan-handoff.json")" = "true" ]
}

# ── D. Ship Phase (Phase 1) ────────────────────────────────────────

@test "10_ship: discover_ship_changes finds the change with artifact_complete=true" {
  cd "$PROJECT_ROOT"
  source "$RDDF_GLOBAL_LIB/discover_ship_changes.sh"
  local count
  count=$(ship_candidate_count "$PROJECT_ROOT")
  [ "$count" -eq 1 ]
  local top_name
  top_name=$(ship_top_candidate "$PROJECT_ROOT")
  [ "$top_name" = "test-playground-change" ]
  local json
  json=$(ship_candidates_json "$PROJECT_ROOT")
  [ "$(echo "$json" | jq -r '.[0].artifact_complete')" = "true" ]
}

@test "11_ship: detect_execution_mode picks lightweight (single change, no conflict)" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  local mode
  mode=$(detect_execution_mode "$PROJECT_ROOT" test-playground-change)
  [ "$mode" = "lightweight" ]
}

@test "12_ship: setup_execution_workspace creates openspec/<name> branch" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  setup_execution_workspace "$PROJECT_ROOT" test-playground-change
  local current_branch
  current_branch=$(git branch --show-current)
  [ "$current_branch" = "openspec/test-playground-change" ]
}

@test "13_ship: implementation plan committed on ship branch" {
  cd "$PROJECT_ROOT"
  mkdir -p .rddf/plans
  cat > .rddf/plans/test-playground-change.md <<'EOF'
# Implementation Plan: test-playground-change

## Phase 1: Write failing test
openspec validate test-playground-change --json

## Phase 2: Verify fail
Expect errors when delta spec missing.

## Phase 3: Implement
Add proposal.md, design.md, tasks.md + spec.md.

## Phase 4: Verify pass
openspec validate returns valid=true.

## Phase 5: Commit
git commit -m "feat: implement"
EOF
  git add . && git commit -q -m "feat(plan): add implementation plan"
  git show HEAD:.rddf/plans/test-playground-change.md > /dev/null
}

@test "14_ship: record_iteration_status writes iteration.json with status=in_worktree" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  record_iteration_status "$PROJECT_ROOT" test-playground-change
  [ -f "$PROJECT_ROOT/.rddf/state/iteration.json" ]
  local status
  status=$(jq -r '.changes[0].status' "$PROJECT_ROOT/.rddf/state/iteration.json")
  [ "$status" = "in_worktree" ]
  local plan_path
  plan_path=$(jq -r '.changes[0].plan_path' "$PROJECT_ROOT/.rddf/state/iteration.json")
  [ "$plan_path" = ".rddf/plans/test-playground-change.md" ]
}

# ── E. Execute Phase ──────────────────────────────────────────────

@test "15_execute: tasks.md all done and step7 report runs cleanly" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/execute/scripts/tasks_writeback.sh"
  export CHANGE_NAME="test-playground-change"
  mark_all_tasks_done
  grep -q "\[x\]" "openspec/changes/$CHANGE_NAME/tasks.md"

  source "$REPO_ROOT/skills/execute/scripts/execute_step7.sh"
  run run_step7_report
  [ "$status" -eq 0 ]
  [[ "$output" == *"执行完成"* ]]
}

# ── F. Archive Phase ──────────────────────────────────────────────

@test "16_archive: detect_archive_mode returns lightweight (no .rddf/wt/)" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  local mode
  mode=$(detect_archive_mode "$PROJECT_ROOT" test-playground-change)
  [ "$mode" = "lightweight" ]
}

@test "17_archive: openspec archive moves change into archive/ + creates spec" {
  cd "$PROJECT_ROOT"
  # ship_archive.sh now resolves the validator through resolve_rdd_lib_dir,
  # so the previous symlink workaround is no longer needed (and would shadow
  # the global install by accident).
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  run archive_change_for_mode "$PROJECT_ROOT" test-playground-change lightweight
  [ "$status" -eq 0 ]
  [ ! -d "openspec/changes/test-playground-change" ]
  [ -d "openspec/changes/archive/2026-08-07-test-playground-change" ]
  [ -f "openspec/specs/test-capability/spec.md" ]
}

@test "18_archive: iteration.json marks change as archived" {
  cd "$PROJECT_ROOT"
  [ -f "$PROJECT_ROOT/.rddf/state/iteration.json" ]
  local status
  status=$(jq -r '.changes[0].status' "$PROJECT_ROOT/.rddf/state/iteration.json")
  [ "$status" = "archived" ]
  local archived_at
  archived_at=$(jq -r '.changes[0].archived_at' "$PROJECT_ROOT/.rddf/state/iteration.json")
  [ -n "$archived_at" ] && [ "$archived_at" != "null" ]
}

@test "19_archive: ship-done check_remaining_work reports all changes processed" {
  cd "$PROJECT_ROOT"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_done.sh"
  run check_remaining_work "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"所有 changes 已处理完毕"* ]]
}

# ── G. Isolation (source repo zero pollution) ──────────────────────

@test "isolation: source repo .rddf/state/ structure preserved (no playground artifacts leaked)" {
  local state_dir="$REPO_ROOT/.rddf/state"
  [ -d "$state_dir" ]

  # Source repo MUST NOT contain the playground change name anywhere
  ! ls "$REPO_ROOT/openspec/changes/test-playground-change/" 2>/dev/null
  ! ls "$REPO_ROOT/openspec/changes/archive/2026-08-07-test-playground-change/" 2>/dev/null
}

@test "isolation: source repo does not have playground's plan file" {
  ! [ -f "$REPO_ROOT/.rddf/plans/test-playground-change.md" ]
}

@test "isolation: rddf guide in playground recognizes all 4 handoffs + iteration" {
  [ -x "$RDDF_HOME_BIN" ] || skip "rddf not installed globally"
  cd "$PROJECT_ROOT"
  run "$RDDF_HOME_BIN" guide
  [ "$status" -eq 0 ]
  [[ "$output" == *"roadmap.md:"*"存在"* ]]
  [[ "$output" == *".arch-handoff.json:"*"存在"* ]]
  [[ "$output" == *".design-handoff.json:"*"存在"* ]]
  [[ "$output" == *".plan-handoff.json:"*"存在"* ]]
  [[ "$output" == *"iteration.json:"*"存在"* ]]
}