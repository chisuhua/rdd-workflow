load ../test_helper

@test "archive: cleanup_plan_handoff adds archived_at timestamp" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-handoff/.rddf/state"
  cat > "$BATS_TMPDIR/test-handoff/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 2, "archived_changes": []}
EOF
  
  run cleanup_plan_handoff "$BATS_TMPDIR/test-handoff" "test-change"
  [ "$status" -eq 0 ]
  
  grep -q "archived_at" "$BATS_TMPDIR/test-handoff/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff decrements active_changes" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-decrement/.rddf/state"
  cat > "$BATS_TMPDIR/test-decrement/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 3, "archived_changes": ["old-change"]}
EOF
  
  run cleanup_plan_handoff "$BATS_TMPDIR/test-decrement" "test-change"
  [ "$status" -eq 0 ]
  
  grep -q '"active_changes": 2' "$BATS_TMPDIR/test-decrement/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff appends to archived_changes" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-append-arch/.rddf/state"
  cat > "$BATS_TMPDIR/test-append-arch/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 1}
EOF
  
  run cleanup_plan_handoff "$BATS_TMPDIR/test-append-arch" "new-archived"
  [ "$status" -eq 0 ]
  
  grep -q "new-archived" "$BATS_TMPDIR/test-append-arch/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff skips when no handoff file" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-no-handoff"
  
  run cleanup_plan_handoff "$BATS_TMPDIR/test-no-handoff" "test-change"
  [ "$status" -eq 0 ]
}
