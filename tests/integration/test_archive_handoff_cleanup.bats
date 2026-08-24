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

# ---------------------------------------------------------------------------
# Stale-state cleanup (clean-stale-plan-handoff-on-ship-done, P1)
# regression tests — lock behavior added in the fix:
#   - current_change is cleared when it matches the archived change
#   - current_change is preserved when it points to a DIFFERENT change
#   - active_changes never goes negative (decrement guard)
#   - ship_started_at cleared when active_changes reaches 0 (ship-done)
#   - last_ship_completed_at recorded as audit trail
#   - execution_mode_decisions preserved across cleanup
# ---------------------------------------------------------------------------

@test "archive: cleanup_plan_handoff clears current_change when it matches" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  mkdir -p "$BATS_TMPDIR/test-current-match/.rddf/state"
  cat > "$BATS_TMPDIR/test-current-match/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 1, "current_change": "fix-foo", "ship_started_at": "2026-08-22T13:00:00+00:00"}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-current-match" "fix-foo"
  [ "$status" -eq 0 ]

  # current_change must be null after archive
  grep -q '"current_change": null' "$BATS_TMPDIR/test-current-match/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff preserves current_change when it differs" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  mkdir -p "$BATS_TMPDIR/test-current-differ/.rddf/state"
  cat > "$BATS_TMPDIR/test-current-differ/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 2, "current_change": "fix-foo"}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-current-differ" "fix-bar"
  [ "$status" -eq 0 ]

  # current_change must remain "fix-foo" since cleanup target was "fix-bar"
  grep -q '"current_change": "fix-foo"' "$BATS_TMPDIR/test-current-differ/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff never decrements active_changes below 0" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  mkdir -p "$BATS_TMPDIR/test-floor/.rddf/state"
  cat > "$BATS_TMPDIR/test-floor/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 0}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-floor" "any-change"
  [ "$status" -eq 0 ]

  # active_changes must stay at 0, not become -1
  grep -q '"active_changes": 0' "$BATS_TMPDIR/test-floor/.rddf/state/.plan-handoff.json"
  ! grep -q '"active_changes": -1' "$BATS_TMPDIR/test-floor/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff clears ship_started_at on ship-done" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  mkdir -p "$BATS_TMPDIR/test-ship-done/.rddf/state"
  cat > "$BATS_TMPDIR/test-ship-done/.rddf/state/.plan-handoff.json" <<'EOF'
{"active_changes": 1, "current_change": "last-change", "ship_started_at": "2026-08-22T13:00:00+00:00"}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-ship-done" "last-change"
  [ "$status" -eq 0 ]

  # ship_started_at must be null after final archive (active_changes=0)
  grep -q '"ship_started_at": null' "$BATS_TMPDIR/test-ship-done/.rddf/state/.plan-handoff.json"
  # last_ship_completed_at must be set as audit trail
  grep -q "last_ship_completed_at" "$BATS_TMPDIR/test-ship-done/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff preserves execution_mode_decisions" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  mkdir -p "$BATS_TMPDIR/test-exec-mode/.rddf/state"
  cat > "$BATS_TMPDIR/test-exec-mode/.rddf/state/.plan-handoff.json" <<'EOF'
{
  "active_changes": 1,
  "current_change": "fix-ship",
  "execution_mode_decisions": {
    "fix-ship": {"mode": "lightweight", "confidence": "high"}
  }
}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-exec-mode" "fix-ship"
  [ "$status" -eq 0 ]

  # execution_mode_decisions is ship history — must survive cleanup
  grep -q '"mode": "lightweight"' "$BATS_TMPDIR/test-exec-mode/.rddf/state/.plan-handoff.json"
  grep -q '"confidence": "high"' "$BATS_TMPDIR/test-exec-mode/.rddf/state/.plan-handoff.json"
}

@test "archive: cleanup_plan_handoff ends in ship-done invariant state" {
  source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

  # Final-state invariant: when active_changes==0, current_change AND ship_started_at must both be null
  mkdir -p "$BATS_TMPDIR/test-invariant/.rddf/state"
  cat > "$BATS_TMPDIR/test-invariant/.rddf/state/.plan-handoff.json" <<'EOF'
{
  "active_changes": 1,
  "current_change": "final-change",
  "ship_started_at": "2026-08-22T13:00:00+00:00",
  "execution_mode_decisions": {"final-change": {"mode": "worktree"}}
}
EOF

  run cleanup_plan_handoff "$BATS_TMPDIR/test-invariant" "final-change"
  [ "$status" -eq 0 ]

  # Final-state invariant: active_changes=0 ∧ current_change=null ∧ ship_started_at=null
  local handoff_file="$BATS_TMPDIR/test-invariant/.rddf/state/.plan-handoff.json"
  grep -q '"active_changes": 0' "$handoff_file"
  grep -q '"current_change": null' "$handoff_file"
  grep -q '"ship_started_at": null' "$handoff_file"
  # But execution_mode_decisions persisted as ship history
  grep -q '"mode": "worktree"' "$handoff_file"
}
