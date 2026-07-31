load ../test_helper

@test "archive-gate: blocks change with 0 completed tasks" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-gate/openspec/changes/test-zero"
  cat > "$BATS_TMPDIR/test-gate/openspec/changes/test-zero/tasks.md" <<'EOF'
## Tasks
- [ ] Task 1
- [ ] Task 2
EOF
  (cd "$BATS_TMPDIR/test-gate" && run archive_gate_check "test-zero")
  [ "$status" -eq 1 ]
  [[ "$output" =~ "未实现" ]]
}

@test "archive-gate: passes change with completed tasks" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-gate2/openspec/changes/test-done"
  cat > "$BATS_TMPDIR/test-gate2/openspec/changes/test-done/tasks.md" <<'EOF'
## Tasks
- [x] Task 1
- [x] Task 2
EOF
  (cd "$BATS_TMPDIR/test-gate2" && run archive_gate_check "test-done")
  [ "$status" -eq 0 ]
}

@test "archive-gate: skips with FORCE_ARCHIVE_INCOMPLETE" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-gate3/openspec/changes/test-force"
  cat > "$BATS_TMPDIR/test-gate3/openspec/changes/test-force/tasks.md" <<'EOF'
## Tasks
- [ ] Task 1
EOF
  (cd "$BATS_TMPDIR/test-gate3" && FORCE_ARCHIVE_INCOMPLETE=yes run archive_gate_check "test-force")
  [ "$status" -eq 0 ]
}
