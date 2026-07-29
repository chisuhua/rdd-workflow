load test_helper

@test "archive: check_incomplete_tasks detects incomplete tasks" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-arch/openspec/changes/test-incomplete"
  cat > "$BATS_TMPDIR/test-arch/openspec/changes/test-incomplete/tasks.md" <<'EOF'
## Tasks
- [ ] Task 1
- [x] Task 2
EOF
  (cd "$BATS_TMPDIR/test-arch" && run check_incomplete_tasks "test-incomplete")
  [ "$status" -eq 1 ]
  [[ "$output" =~ "未完成任务" ]]
}

@test "archive: check_incomplete_tasks passes when all complete" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-arch2/openspec/changes/test-complete"
  cat > "$BATS_TMPDIR/test-arch2/openspec/changes/test-complete/tasks.md" <<'EOF'
## Tasks
- [x] Task 1
- [x] Task 2
EOF
  (cd "$BATS_TMPDIR/test-arch2" && run check_incomplete_tasks "test-complete")
  [ "$status" -eq 0 ]
}

@test "archive: check_incomplete_tasks skips with FORCE_ARCHIVE_INCOMPLETE" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-arch3/openspec/changes/test-force"
  cat > "$BATS_TMPDIR/test-arch3/openspec/changes/test-force/tasks.md" <<'EOF'
## Tasks
- [ ] Task 1
EOF
  (cd "$BATS_TMPDIR/test-arch3" && FORCE_ARCHIVE_INCOMPLETE=yes run check_incomplete_tasks "test-force")
  [ "$status" -eq 0 ]
}

@test "archive: append_incomplete_to_suggestions writes to suggestions" {
  source "$PROJECT_ROOT/skills/_lib/archive.sh"
  
  mkdir -p "$BATS_TMPDIR/test-sugg"
  touch "$BATS_TMPDIR/test-sugg/proposal-suggestions.md"
  (cd "$BATS_TMPDIR/test-sugg" && run append_incomplete_to_suggestions "test-change" "$BATS_TMPDIR/test-sugg")
  [ "$status" -eq 0 ]
  grep -q "test-change" "$BATS_TMPDIR/test-sugg/proposal-suggestions.md"
}
