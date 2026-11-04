load ../test_helper

bats_require_minimum_version 1.5.0

@test "adr_gate: classifies ARCHITECTURE decision" {
  run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}

@test "adr_gate: classifies GOVERNANCE decision" {
  run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Update ci pipeline"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "GOVERNANCE" ]]
}

@test "adr_gate: classifies IMPLEMENTATION decision" {
  run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Fix typo in readme"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "IMPLEMENTATION" ]]
}

@test "adr_gate: skips with SKIP_ADR_GATE" {
  SKIP_ADR_GATE=yes run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Fix typo"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}

@test "adr_gate: advisory mode emits a note for IMPLEMENTATION (stderr)" {
  run --separate-stderr bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "rv32i-fetch-skid-buffer"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "IMPLEMENTATION" ]]
  [[ "$stderr" =~ "advisory" ]]
}

@test "adr_gate: advisory mode stays silent for ARCHITECTURE" {
  run --separate-stderr bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
  [[ "$stderr" != *"advisory"* ]]
}

@test "adr_gate: ADR_GATE_MODE=block suppresses the advisory note" {
  run --separate-stderr env ADR_GATE_MODE=block bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Fix typo in readme"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "IMPLEMENTATION" ]]
  [[ "$stderr" != *"advisory"* ]]
}

@test "adr_gate: ADR_GATE_CLASS override wins over the keyword heuristic" {
  run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "rv32i-fetch-skid-buffer"
  [[ "$output" =~ "IMPLEMENTATION" ]]
  run env ADR_GATE_CLASS=ARCHITECTURE bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "rv32i-fetch-skid-buffer"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}
