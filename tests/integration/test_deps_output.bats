#!/usr/bin/env bats

# T8 (P0-5): deps.md Step 5 must write real content (not a placeholder heredoc)
# to .zcf/.deps-output.md. These are static tests against the markdown source —
# functional execution requires the openspec CLI which is not present in CI.
# The tests guard against regression of the placeholder text and verify that
# the heredoc references real variables from Step 2.

load ../test_helper

@test "deps.md Step 5 no longer contains placeholder text" {
  [ -f "$REPO_ROOT/skills/deps.md" ]
  # The old pattern was: "（5a-5e 的全部内容写入此文件，格式见下文）"
  ! grep -q "5a-5e 的全部内容写入此文件" "$REPO_ROOT/skills/deps.md"
}

@test "deps.md has real implementation in Step 5" {
  [ -f "$REPO_ROOT/skills/deps.md" ]
  # Should have heredoc writing actual content (with variables, not literal text)
  grep -q 'cat > "\$DEPS_OUTPUT"' "$REPO_ROOT/skills/deps.md"
  # Should have a for-loop generating rows from the CANDIDATES array
  grep -q 'for name in' "$REPO_ROOT/skills/deps.md"
}

@test "deps.md output template references \$CANDIDATES" {
  [ -f "$REPO_ROOT/skills/deps.md" ]
  # Should use real variables, not just placeholder
  grep -q '\${CANDIDATES\[@\]}' "$REPO_ROOT/skills/deps.md"
}

@test "deps.md output mentions AI placeholder disclaimer" {
  [ -f "$REPO_ROOT/skills/deps.md" ]
  grep -q "AI 语义分析未启用" "$REPO_ROOT/skills/deps.md"
}
