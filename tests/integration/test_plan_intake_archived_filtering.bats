#!/usr/bin/env bats
# tests/integration/test_plan_intake_archived_filtering.bats
# fix-plan-intake-stale-pre-created-changes (P1, 2026-09-01):
# Lock the new classify_pre_created_changes / is_design_pre_created_pending /
# count_pending_proposals helpers introduced to filter stale design-handoff
# snapshots. Without these tests, the original "X 个已批准提案但无活跃 change"
# misleading warning can silently regress.
#
# CONTRACT:
#   is_design_pre_created_pending <name>           → exit 0 iff in array AND
#                                                    not in openspec/changes/
#                                                    AND not in archive/
#   classify_pre_created_changes <project_root>   → exports PENDING/ACTIVE/
#                                                    ARCHIVED count env vars
#   count_pending_proposals <project_root>         → prints N to stdout,
#                                                    N = approved rows that
#                                                    are neither created nor
#                                                    archived
#
# SKIP_DESIGN_HANDOFF=yes → classification is skipped (backward compatible).

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    # plan_intake.sh's bootstrap uses ${RDDF_PROJECT_ROOT:-...} to find
    # orchestrator_entry.sh. WORK_DIR is not a git repo, so without this
    # export the bootstrap silently fails and orchestrator_run is undefined.
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
    # test_helper exports PROJECT_ROOT=$REPO_ROOT, but is_design_pre_created_pending
    # reads PROJECT_ROOT to find openspec/changes/<name>. Override so the helper
    # checks the per-test WORK_DIR instead of the rdd-workflow repo itself.
    export PROJECT_ROOT="$WORK_DIR"
}

teardown() {
    rm -rf "$WORK_DIR"
}

# Write a v2 design-handoff with arbitrary pre_created list.
write_v2_handoff() {
    local pre_created_json="$1"
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-09-01T10:00:00+00:00",
  "proposals_reviewed": 3,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ${pre_created_json}
}
EOF
}

# Write an openspec/changes/<name>/ dir (active change).
write_active_change() {
    local name="$1"
    mkdir -p "$WORK_DIR/openspec/changes/$name"
}

# Write an openspec/changes/archive/<date>-<name>/ dir (archived change).
write_archived_change() {
    local name="$1"
    local date="${2:-2026-09-01}"
    mkdir -p "$WORK_DIR/openspec/changes/archive/$date-$name"
}

# =======================================================================
# is_design_pre_created_pending contract tests
# =======================================================================

@test "plan-intake-archived-filter: pending helper returns 1 when name not in array" {
    write_v2_handoff '["alpha"]'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created_pending 'gamma'
    "
    [ "$status" -eq 1 ]
}

@test "plan-intake-archived-filter: pending helper returns 0 when name in array + not created + not archived" {
    write_v2_handoff '["alpha"]'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created_pending 'alpha'
    "
    [ "$status" -eq 0 ]
}

@test "plan-intake-archived-filter: pending helper returns 1 when name in array + already created" {
    write_v2_handoff '["alpha"]'
    write_active_change 'alpha'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created_pending 'alpha'
    "
    [ "$status" -eq 1 ]
}

@test "plan-intake-archived-filter: pending helper returns 1 when name in array + already archived" {
    write_v2_handoff '["alpha"]'
    write_archived_change 'alpha' '2026-08-30'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created_pending 'alpha'
    "
    [ "$status" -eq 1 ]
}

# =======================================================================
# classify_pre_created_changes contract tests
# =======================================================================

@test "plan-intake-archived-filter: classify reports 3 pending when all names are fresh" {
    write_v2_handoff '["alpha", "beta", "gamma"]'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        classify_pre_created_changes '$WORK_DIR'
        echo \"PENDING=\$CHANGES_PENDING_COUNT ACTIVE=\$CHANGES_ACTIVE_COUNT ARCHIVED=\$CHANGES_ARCHIVED_COUNT\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"PENDING=3"* ]]
    [[ "$output" == *"ACTIVE=0"* ]]
    [[ "$output" == *"ARCHIVED=0"* ]]
}

@test "plan-intake-archived-filter: classify reports 1 pending + 2 archived when names mixed" {
    write_v2_handoff '["alpha", "beta", "gamma"]'
    write_archived_change 'alpha' '2026-08-30'
    write_archived_change 'gamma' '2026-08-31'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        classify_pre_created_changes '$WORK_DIR'
        echo \"PENDING=\$CHANGES_PENDING_COUNT ACTIVE=\$CHANGES_ACTIVE_COUNT ARCHIVED=\$CHANGES_ARCHIVED_COUNT\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"PENDING=1"* ]]
    [[ "$output" == *"ACTIVE=0"* ]]
    [[ "$output" == *"ARCHIVED=2"* ]]
}

@test "plan-intake-archived-filter: classify reports 0 pending + 3 archived when all names archived" {
    write_v2_handoff '["alpha", "beta", "gamma"]'
    write_archived_change 'alpha' '2026-08-30'
    write_archived_change 'beta' '2026-08-31'
    write_archived_change 'gamma' '2026-09-01'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        classify_pre_created_changes '$WORK_DIR'
        echo \"PENDING=\$CHANGES_PENDING_COUNT ACTIVE=\$CHANGES_ACTIVE_COUNT ARCHIVED=\$CHANGES_ARCHIVED_COUNT\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"PENDING=0"* ]]
    [[ "$output" == *"ACTIVE=0"* ]]
    [[ "$output" == *"ARCHIVED=3"* ]]
}

@test "plan-intake-archived-filter: classify reports 1 active when name in openspec/changes/" {
    write_v2_handoff '["alpha", "beta"]'
    write_active_change 'alpha'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        classify_pre_created_changes '$WORK_DIR'
        echo \"PENDING=\$CHANGES_PENDING_COUNT ACTIVE=\$CHANGES_ACTIVE_COUNT ARCHIVED=\$CHANGES_ARCHIVED_COUNT\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"PENDING=1"* ]]
    [[ "$output" == *"ACTIVE=1"* ]]
    [[ "$output" == *"ARCHIVED=0"* ]]
}

# =======================================================================
# check_design_handoff output format tests (regression lock)
# =======================================================================

@test "plan-intake-archived-filter: check_design_handoff shows new format with classification when all archived" {
    write_v2_handoff '["alpha", "beta"]'
    write_archived_change 'alpha' '2026-08-30'
    write_archived_change 'beta' '2026-08-31'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    # New format: "(v2 schema, K 个预建 changes: P 待处理, A 已创建, M 已归档)"
    [[ "$output" == *"v2 schema"* ]]
    [[ "$output" == *"2 个预建 changes"* ]]
    [[ "$output" == *"0 待处理"* ]]
    [[ "$output" == *"2 已归档"* ]]
    # No misleading "可能需运行 propose" warning
    [[ "$output" != *"可能需运行 propose"* ]]
}

@test "plan-intake-archived-filter: check_design_handoff shows v1 format when array empty" {
    write_v2_handoff '[]'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    # v1-style: no "K 个预建 changes" suffix when array empty
    [[ "$output" == *"v1 schema"* ]]
    [[ "$output" != *"个预建 changes"* ]]
}

@test "plan-intake-archived-filter: SKIP_DESIGN_HANDOFF=yes skips classification" {
    write_v2_handoff '["alpha"]'
    write_archived_change 'alpha' '2026-08-30'
    run bash -c "
        export SKIP_DESIGN_HANDOFF=yes
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP_DESIGN_HANDOFF"* ]]
}

# =======================================================================
# count_pending_proposals contract tests
# =======================================================================

@test "plan-intake-archived-filter: count_pending_proposals returns 0 when all approved are archived" {
    # Build a minimal proposal-approved.md: 2 approved + 1 implemented section.
    cat > "$WORK_DIR/proposal-approved.md" <<'EOF'
# Approved proposals

## 已批准提案

| 提案 | 优先级 | 批准时间 |
|------|--------|----------|
| [arch-alpha](.rddf/improvements/arch-alpha.md) | P1 | 2026-08-01 |
| [arch-beta](.rddf/improvements/arch-beta.md) | P1 | 2026-08-01 |

## 已实施

| 提案 | 优先级 | 批准时间 |
|------|--------|----------|
| [arch-gamma](.rddf/improvements/arch-gamma.md) | P2 | 2026-07-15 |
EOF
    write_archived_change 'arch-alpha' '2026-08-30'
    write_archived_change 'arch-beta' '2026-08-31'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        count_pending_proposals '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    [ "$output" = "0" ]
}

@test "plan-intake-archived-filter: count_pending_proposals returns N when N are pending" {
    cat > "$WORK_DIR/proposal-approved.md" <<'EOF'
# Approved proposals

## 已批准提案

| 提案 | 优先级 | 批准时间 |
|------|--------|----------|
| [arch-pending-1](.rddf/improvements/arch-pending-1.md) | P1 | 2026-09-01 |
| [arch-pending-2](.rddf/improvements/arch-pending-2.md) | P1 | 2026-09-01 |
| [arch-done](.rddf/improvements/arch-done.md) | P2 | 2026-08-01 |

## 已实施

| 提案 | 优先级 | 批准时间 |
|------|--------|----------|
| [arch-old](.rddf/improvements/arch-old.md) | P3 | 2026-07-15 |
EOF
    write_archived_change 'arch-done' '2026-09-01'
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        count_pending_proposals '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    [ "$output" = "2" ]
}

@test "plan-intake-archived-filter: count_pending_proposals returns 0 when no proposal-approved.md" {
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        count_pending_proposals '$WORK_DIR'
    "
    [ "$status" -eq 0 ]
    [ "$output" = "0" ]
}
