load test_helper

@test "scan-state: detects stale arch-handoff with 0 ADRs but filesystem has files" {
  source "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-stale/.rddf/state"
  mkdir -p "$BATS_TMPDIR/test-stale/docs/adr"
  echo "ADR content" > "$BATS_TMPDIR/test-stale/docs/adr/ADR-0001-test.md"
  
  cat > "$BATS_TMPDIR/test-stale/.rddf/state/.arch-handoff.json" <<'EOF'
{"adr_count": 0, "adr_dir": "docs/adr"}
EOF
  
  run check_arch_handoff_stale "$BATS_TMPDIR/test-stale"
  [[ "$output" =~ "arch-handoff 记录 0 ADRs" ]]
}

@test "scan-state: no warning when handoff adr_count matches filesystem" {
  source "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-fresh/.rddf/state"
  mkdir -p "$BATS_TMPDIR/test-fresh/docs/adr"
  echo "ADR content" > "$BATS_TMPDIR/test-fresh/docs/adr/ADR-0001-test.md"
  
  cat > "$BATS_TMPDIR/test-fresh/.rddf/state/.arch-handoff.json" <<'EOF'
{"adr_count": 1, "adr_dir": "docs/adr"}
EOF
  
  run check_arch_handoff_stale "$BATS_TMPDIR/test-fresh"
  [[ ! "$output" =~ "可能过期" ]]
}

@test "scan-state: no warning when handoff file missing" {
  source "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
  
  mkdir -p "$BATS_TMPDIR/test-nohandoff"
  
  run check_arch_handoff_stale "$BATS_TMPDIR/test-nohandoff"
  [ "$status" -eq 0 ]
  [[ ! "$output" =~ "可能过期" ]]
}
