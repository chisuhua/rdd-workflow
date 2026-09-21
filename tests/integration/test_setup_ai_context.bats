#!/usr/bin/env bats
# tests/integration/test_setup_ai_context.bats
# Integration tests for `rddf setup ai-context`

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  export TMPDIR="/tmp/rddf-setup-test-$$"
  mkdir -p "$TMPDIR"
  export RDDF_PROJECT_ROOT="$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR" 2>/dev/null || true
}

@test "setup ai-context: creates AGENTS.md in empty project" {
  run python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  [ "$status" -eq 0 ]
  [ -f "$TMPDIR/AGENTS.md" ]
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/AGENTS.md"
}

@test "setup ai-context: appends to existing .cursorrules" {
  echo "# existing rule" > "$TMPDIR/.cursorrules"
  run python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  [ "$status" -eq 0 ]
  run grep -c "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  [ "$output" -eq 1 ]
}

@test "setup ai-context: idempotent (no duplicate sentinel)" {
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  local first_blocks
  first_blocks=$(grep -c "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/AGENTS.md" 2>/dev/null || echo "0")
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  local second_blocks
  second_blocks=$(grep -c "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/AGENTS.md" 2>/dev/null || echo "0")
  [ "$first_blocks" -eq 1 ]
  [ "$second_blocks" -eq 1 ]
}

@test "setup ai-context: dry-run does not write files" {
  run python3 -m _lib.cli setup ai-context --dry-run --target "$TMPDIR"
  [ "$status" -eq 0 ]
  [ ! -f "$TMPDIR/AGENTS.md" ]
  [[ "$output" == *"[dry-run]"* ]]
}

@test "setup ai-context: --uninstall removes sentinel block" {
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/AGENTS.md"
  run python3 -m _lib.cli setup ai-context --uninstall --yes --target "$TMPDIR"
  [ "$status" -eq 0 ]
  run grep -c "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/AGENTS.md"
  [ "$output" -eq 0 ]
}

@test "setup ai-context: block ≤30 lines" {
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  local block_lines
  block_lines=$(awk '/RDD-WORKFLOW-CORE-USAGE-START/,/RDD-WORKFLOW-CORE-USAGE-END/' "$TMPDIR/AGENTS.md" | wc -l)
  [ "$block_lines" -le 30 ]
}

@test "setup ai-context: 5 structure segments present" {
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  grep -q "rdd-workflow" "$TMPDIR/AGENTS.md"
  grep -q "skill_use.*guide" "$TMPDIR/AGENTS.md"
  grep -q "rdd-arch.*rdd-planner.*rdd-builder.*rdd-verifier" "$TMPDIR/AGENTS.md"
  grep -q "rdd-quick" "$TMPDIR/AGENTS.md"
  grep -q "ai-context-bootstrap" "$TMPDIR/AGENTS.md"
}

@test "setup ai-context: multiple files all get the block" {
  echo "# cursor" > "$TMPDIR/.cursorrules"
  echo "# claude" > "$TMPDIR/CLAUDE.md"
  run python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  [ "$status" -eq 0 ]
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/CLAUDE.md"
}