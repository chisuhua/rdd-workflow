load ../test_helper

@test "scan-state: check_skill_versions detects stale skill files" {
  source "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-skill-version/skills/guide"
  cat > "$BATS_TMPDIR/test-skill-version/skills/guide/SKILL.md" <<'EOF'
---
name: guide
---
test content
EOF
  
  cd "$BATS_TMPDIR/test-skill-version"
  git init -q
  git add -A
  git commit -q -m "init"
  touch -t 209912312359 skills/guide/SKILL.md
  
  run check_skill_versions "$BATS_TMPDIR/test-skill-version"
  [[ "$output" =~ "版本滞后" ]]
}

@test "scan-state: check_skill_versions passes when no stale files" {
  source "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-skill-clean/skills/guide"
  cat > "$BATS_TMPDIR/test-skill-clean/skills/guide/SKILL.md" <<'EOF'
---
name: guide
---
test content
EOF
  
  cd "$BATS_TMPDIR/test-skill-clean"
  git init -q
  git add -A
  git commit -q -m "init"
  
  run check_skill_versions "$BATS_TMPDIR/test-skill-clean"
  [ "$status" -eq 0 ]
  [[ ! "$output" =~ "版本滞后" ]]
}
