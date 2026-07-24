#!/usr/bin/env bats

# T8 (P0-5): deps.md Step 5 must write real content (not a placeholder heredoc)
# to .rddf/state/.deps-output.md. These are static tests against the markdown source —
# functional execution requires the openspec CLI which is not present in CI.
# The tests guard against regression of the placeholder text and verify that
# the heredoc references real variables from Step 2.

load ../test_helper

@test "deps.md Step 5 no longer contains placeholder text" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  # The old pattern was: "（5a-5e 的全部内容写入此文件，格式见下文）"
  ! grep -q "5a-5e 的全部内容写入此文件" "$REPO_ROOT/skills/deps/SKILL.md"
}

@test "deps.md has real implementation in Step 5" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  # v2.0.6 extraction: Step 5 inline heredoc extracted to
  # skills/deps/scripts/deps_render_report.sh (bash wrapper) +
  # skills/deps/scripts/deps_output.py::render_markdown_report (Python).
  # Verify SKILL.md sources the wrapper and the wrapper writes the output.
  grep -q 'scripts/deps_render_report.sh' "$REPO_ROOT/skills/deps/SKILL.md"
  grep -q 'render_deps_report' "$REPO_ROOT/skills/deps/SKILL.md"
  # The bash wrapper must reference the DEPS_OUTPUT file path
  grep -q 'DEPS_OUTPUT' "$REPO_ROOT/skills/deps/scripts/deps_render_report.sh"
  # The Python helper must have a for-loop generating rows from candidates
  grep -q 'for name in candidates' "$REPO_ROOT/skills/deps/scripts/deps_output.py"
}

@test "deps.md output template references \$CANDIDATES" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  # Should use real variables, not just placeholder
  grep -q '\${CANDIDATES\[@\]}' "$REPO_ROOT/skills/deps/SKILL.md"
}

@test "deps.md output mentions AI placeholder disclaimer" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  grep -q "AI 语义分析未启用" "$REPO_ROOT/skills/deps/SKILL.md"
}
