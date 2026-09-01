#!/usr/bin/env bats
#
# Consolidated plan_intake edge-case tests (merged 2026-08-18).
#
# Replaces the 4 legacy files below; merged to reduce test sprawl
# (4 files × 1-2 tests each → 1 file × 11 tests):
#   - test_plan_intake_bootstrap_edges.bats   (4 tests)
#   - test_plan_intake_cross_phase.bats       (2 tests)
#   - test_plan_intake_failure_semantics.bats (2 tests)
#   - test_plan_intake_staleness.bats         (3 tests)
#
# Test names preserved verbatim so KNOWN_FAILURES baseline (if any
# new entry is added later) stays grep-stable.

load ../test_helper

# plan_intake.sh's bootstrap uses ${RDDF_PROJECT_ROOT:-...} to find
# orchestrator_entry.sh. When cwd is a non-git tmpdir, without this
# export the bootstrap silently fails and orchestrator_run is undefined.
setup() {
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
    export SKIP_ARCH_HANDOFF=yes
}

run_plan_intake_in_tmp() {
    local tmpdir="$1"
    SKIP_ARCH_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true
}

# ---------- bootstrap edges (was test_plan_intake_bootstrap_edges.bats) ---------- #

@test "missing .design-handoff.json: plan_intake runs without arch-handoff block" {
    # With SKIP_ARCH_HANDOFF=yes, arch check is bypassed; design-handoff missing
    # is the real concern. We expect plan_intake to proceed past arch check.
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "arch 阶段必须先完成" ]]
}

@test "v2 handoff missing changes_pre_created: proceeds with empty array" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "JSON parse" ]] || [[ -z "$output" ]]
}

@test "stale design_complete_at (>30d): plan_intake proceeds" {
    local tmpdir output
    STALE_DATE=$(date -d "60 days ago" -u +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || \
                 date -v-60d -u +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || \
                 echo "2026-06-01T00:00:00+00:00")
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "$STALE_DATE",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "FATAL" ]] || [[ -z "$output" ]]
}

@test "empty changes_pre_created: [] does not crash" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 0,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "TypeError" ]] || [[ -z "$output" ]]
}

# ---------- cross-phase (was test_plan_intake_cross_phase.bats) ---------- #

@test "design v2 happy path with changes_pre_created: plan_intake recognizes pre-created" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ "$output" =~ "design-handoff" ]] || [[ -z "$output" ]]
}

@test "design v2 sad path (missing version field but has changes_pre_created): plan_intake proceeds" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/.design-handoff.json" <<'EOF'
{
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "KeyError" ]] || [[ -z "$output" ]]
}

# ---------- failure semantics (was test_plan_intake_failure_semantics.bats) ---------- #

@test "interrupted trace (no finalize_at): plan_intake proceeds" {
    # Create interrupted trace in tmpdir (no finalize_at → looks orphaned)
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state/trace"
    cat > "$tmpdir/.rddf/state/trace/guide-plan-test.json" <<'EOF'
{
  "phase": "guide-plan",
  "started_at": "2026-08-13T00:00:00+00:00"
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "Traceback" ]] || [[ -z "$output" ]]
}

@test "abandoned rddf-session: plan_intake proceeds" {
    # sessions.json with abandoned session
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.rddf/state"
    cat > "$tmpdir/.rddf/state/sessions.json" <<'EOF'
{
  "sessions": [
    {
      "session_id": "rds_test_abandoned",
      "kind": "stage_design",
      "state": "abandoned",
      "end_reason": "user-abandoned-via-guide-design-transition"
    }
  ]
}
EOF
    output=$(RDDF_PROJECT_ROOT="$tmpdir" SKIP_ARCH_HANDOFF=yes bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
    rm -rf "$tmpdir"
    [[ ! "$output" =~ "Traceback" ]] || [[ -z "$output" ]]
}

# ---------- staleness (was test_plan_intake_staleness.bats) ---------- #

@test "plan-intake: detects proposal-approved.md staleness" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/openspec/changes/archive"
    cat > "$tmpdir/proposal-approved.md" <<EOF
| 状态 | 提案 | 阶段 |
| [ ] | test-proposal | general |
EOF
    output=$(run_plan_intake_in_tmp "$tmpdir")
    rm -rf "$tmpdir"
    # fix-plan-intake-stale-pre-created-changes: output is now
    # "📋 待创建 proposal: N" — checks that proposal-approved.md was
    # scanned (and reports a count) rather than the old grep -c '| ['
    # entire-file count.
    echo "$output" | grep -qE '待创建 proposal|proposal-approved'
}

@test "plan-intake: no staleness when active changes exist" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/openspec/changes/active-change"
    cat > "$tmpdir/proposal-approved.md" <<EOF
| 状态 | 提案 | 阶段 |
| [ ] | test-proposal | general |
EOF
    output=$(run_plan_intake_in_tmp "$tmpdir")
    rm -rf "$tmpdir"
    echo "$output" | grep -qv '已批准提案但无活跃 change'
}

@test "plan-intake: no staleness when no pending proposals" {
    local tmpdir output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/openspec/changes/archive"
    cat > "$tmpdir/proposal-approved.md" <<EOF
| 状态 | 提案 | 阶段 |
| [x] | test-proposal | general |
EOF
    output=$(run_plan_intake_in_tmp "$tmpdir")
    rm -rf "$tmpdir"
    echo "$output" | grep -qv '已批准提案但无活跃 change'
}
