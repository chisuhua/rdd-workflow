load ../test_helper

SKILL_FILE="$REPO_ROOT/skills/rdd-arch/SKILL.md"

@test "adr_gate_flow: SKILL.md wires adr_gate.sh with 3-branch dispatch" {
  assert_file_contains "$SKILL_FILE" 'adr_gate\.sh'
  assert_file_contains "$SKILL_FILE" 'GATE_CLASS='
  assert_file_contains "$SKILL_FILE" 'case "\$GATE_CLASS" in'
  assert_file_contains "$SKILL_FILE" 'ARCHITECTURE)'
  assert_file_contains "$SKILL_FILE" 'GOVERNANCE)'
  assert_file_contains "$SKILL_FILE" 'IMPLEMENTATION)'
}

@test "adr_gate_flow: SKILL.md contains 3-stage dialogue instructions" {
  assert_file_contains "$SKILL_FILE" '现状挖掘'
  assert_file_contains "$SKILL_FILE" '决策对话'
  assert_file_contains "$SKILL_FILE" '草稿呈现'
  assert_file_contains "$SKILL_FILE" '5 轮'
}

@test "adr_gate_flow: SKILL.md recognizes SKIP_ADR_CONFIRM independent of SKIP_ADR_GATE" {
  assert_file_contains "$SKILL_FILE" 'SKIP_ADR_CONFIRM'
  assert_file_contains "$SKILL_FILE" 'SKIP_ADR_GATE'
}

@test "adr_gate_flow: draft covers template 12 anchors in option-1 block" {
  local block
  block=$(awk '/\*\*选项 1（创建新 ADR）执行内容\*\*/,/^\*\*选项 [23]/' "$SKILL_FILE")
  for anchor in '## Context' '## Decision' '## Consequences' '## References' \
                '### 影响范围' '### 备选方案' '### 正面' '### 负面 / 风险' '### 后续待办' \
                '> **状态**' '> **日期**' '> **决策者**'; do
    grep -qF "$anchor" <<< "$block" || { echo "missing anchor: $anchor" >&2; return 1; }
  done
}

@test "adr_gate_flow: atomic write + cancel guard (q/cancel/exit leaves no file)" {
  assert_file_contains "$SKILL_FILE" '\.tmp'
  assert_file_contains "$SKILL_FILE" 'rm -f'
  assert_file_contains "$SKILL_FILE" 'q[|]cancel[|]exit'
  assert_file_contains "$SKILL_FILE" 'mv '
}

@test "adr_gate_flow: adr_gate.sh classification preserved (regression)" {
  run bash "$PROJECT_ROOT/skills/rdd-arch/scripts/adr_gate.sh" "Define module boundary"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "ARCHITECTURE" ]]
}
