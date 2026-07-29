load test_helper

@test "sync: sync_suggestions updates suggestions.md status" {
  source "$PROJECT_ROOT/skills/_lib/state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-sync"
  cat > "$BATS_TMPDIR/test-sync/proposal-suggestions.md" <<'EOF'
| [test-change](improvements/test-change.md) | P1 | 2026-01-01 | 待讨论 |
EOF
  
  run sync_suggestions "$BATS_TMPDIR/test-sync" "test-change" "approved"
  [ "$status" -eq 0 ]
  grep -q "approved" "$BATS_TMPDIR/test-sync/proposal-suggestions.md"
}

@test "sync: append_approved calls sync_suggestions" {
  source "$PROJECT_ROOT/skills/_lib/state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-append"
  cat > "$BATS_TMPDIR/test-append/proposal-approved.md" <<'EOF'
## 已批准提案

| [name](improvements/name.md) | P1 | time | guide-arch |
---|---|---|---

## 已实施
EOF
  cat > "$BATS_TMPDIR/test-append/proposal-suggestions.md" <<'EOF'
| [test-append-change](improvements/test-append-change.md) | P1 | 2026-01-01 | 待讨论 |
EOF
  
  run append_approved "$BATS_TMPDIR/test-append" "test-append-change" "P1"
  [ "$status" -eq 0 ]
  grep -q "approved" "$BATS_TMPDIR/test-append/proposal-suggestions.md"
}
