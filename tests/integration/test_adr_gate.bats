load test_helper

@test "adr_gate: classifies ARCHITECTURE decision" {
  run bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}

@test "adr_gate: classifies GOVERNANCE decision" {
  run bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "Update ci pipeline"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "GOVERNANCE" ]]
}

@test "adr_gate: classifies IMPLEMENTATION decision" {
  run bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "Fix typo in readme"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "IMPLEMENTATION" ]]
}

@test "adr_gate: skips with SKIP_ADR_GATE" {
  SKIP_ADR_GATE=yes run bash "$PROJECT_ROOT/skills/guide-arch/scripts/adr_gate.sh" "Fix typo"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}
