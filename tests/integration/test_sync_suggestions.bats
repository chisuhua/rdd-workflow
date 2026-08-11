#!/usr/bin/env bats
# tests/integration/test_sync_suggestions.bats
# Tests for sync_suggestions, sweep_stale_suggestions, and append_approved
load ../test_helper

@test "sync: sync_suggestions approved removes row from suggestions" {
  source "$PROJECT_ROOT/_lib/state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-sync"
  cat > "$BATS_TMPDIR/test-sync/proposal-suggestions.md" <<'EOF'
| [test-change](.rddf/improvements/test-change.md) | P1 | 来源 | 2026-01-01 | 待讨论 |
EOF
  
  run sync_suggestions "$BATS_TMPDIR/test-sync" "test-change" "approved"
  [ "$status" -eq 0 ]
  # Row should be removed (not updated with "approved" text)
  ! grep -q "test-change" "$BATS_TMPDIR/test-sync/proposal-suggestions.md"
}

@test "sync: sync_suggestions deferred updates status column" {
  source "$PROJECT_ROOT/_lib/state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-defer"
  cat > "$BATS_TMPDIR/test-defer/proposal-suggestions.md" <<'EOF'
| [test-defer-change](.rddf/improvements/test-defer-change.md) | P1 | 来源 | 2026-01-01 | 待讨论 |
EOF
  
  run sync_suggestions "$BATS_TMPDIR/test-defer" "test-defer-change" "deferred" "2026-07-30"
  [ "$status" -eq 0 ]
  # Row should remain with updated status
  grep -q "已延迟" "$BATS_TMPDIR/test-defer/proposal-suggestions.md"
}

@test "sync: append_approved calls sync_suggestions (removes row)" {
  source "$PROJECT_ROOT/_lib/state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-append"
  cat > "$BATS_TMPDIR/test-append/proposal-approved.md" <<'EOF'
## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|

## 已实施
EOF
  cat > "$BATS_TMPDIR/test-append/proposal-suggestions.md" <<'EOF'
| [test-append-change](.rddf/improvements/test-append-change.md) | P1 | 来源 | 2026-01-01 | 待讨论 |
EOF
  
  run append_approved "$BATS_TMPDIR/test-append" "test-append-change" "P1"
  [ "$status" -eq 0 ]
  # Row should be removed from suggestions (new behavior: approved = remove)
  ! grep -q "test-append-change" "$BATS_TMPDIR/test-append/proposal-suggestions.md"
  # Entry should be in approved table
  grep -q "test-append-change" "$BATS_TMPDIR/test-append/proposal-approved.md"
}