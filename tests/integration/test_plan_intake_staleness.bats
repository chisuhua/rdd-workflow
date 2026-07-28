#!/usr/bin/env bats
# tests/integration/test_plan_intake_staleness.bats
# plan_intake staleness detection: pending proposals vs active changes.

load ../test_helper

@test "plan-intake: detects proposal-approved.md staleness" {
  local tmpdir output
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/archive"
  cat > "$tmpdir/proposal-approved.md" <<EOF
| 状态 | 提案 | 阶段 |
| [ ] | test-proposal | general |
EOF
  output=$(SKIP_ARCH_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE 'proposal-approved|已批准提案'
}

@test "plan-intake: no staleness when active changes exist" {
  local tmpdir output
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/active-change"
  cat > "$tmpdir/proposal-approved.md" <<EOF
| 状态 | 提案 | 阶段 |
| [ ] | test-proposal | general |
EOF
  output=$(SKIP_ARCH_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
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
  output=$(SKIP_ARCH_HANDOFF=yes bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && run_plan_intake" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qv '已批准提案但无活跃 change'
}
