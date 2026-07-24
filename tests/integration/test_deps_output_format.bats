#!/usr/bin/env bats
# tests/integration/test_deps_output_format.bats
#
# Locks the .rddf/state/.deps-output.md output format produced by skills/deps/SKILL.md
# Step 5. Independent of the subagent call — guards against Step 5 heredoc
# regressions in the Mermaid / 5-section structure.
#
# The 5 sections of .rddf/state/.deps-output.md:
#   1. 依赖图 (Mermaid)
#   2. 阶段预检 (roadmap-meta.yaml)
#   3. 状态表 (per-change ready/blocked)
#   4. 推荐执行顺序
#   5. AI 建议 (5a/5b/5c/5d/5e — only 5a/5b/5c/5d/5e tested here)
#
# Run: bats tests/integration/test_deps_output_format.bats

load ../test_helper

setup() {
  f="$REPO_ROOT/skills/deps/SKILL.md"
  [ -f "$f" ] || skip "deps.md not found"
}

@test "deps.md Step 5 emits Mermaid code block" {
  grep -qE '^```mermaid' "$f"
}

@test "deps.md Mermaid block uses directed or bidirectional edges" {
  grep -qE -- '\-\->|<\-\->' "$f"
}

@test "deps.md Step 5 emits 5e section header" {
  grep -qE '^#### 5e\.' "$f"
}

@test "deps.md 5e section is structurally present (has a body, not just header)" {
  body=$(awk '
    /^#### 5e\./ { in_5e=1; next }
    in_5e && /^#### / { exit }
    in_5e { print }
  ' "$f")
  [ -n "$body" ]
}

@test "deps.md Step 5 writes to .rddf/state/.deps-output.md" {
  # v2.0.6 extraction: the cat heredoc moved to the bash wrapper
  # (deps_render_report.sh) which delegates to Python (open(..., "w")).
  # Verify the output path is referenced in both the wrapper and SKILL.md.
  grep -q '\.rddf/state/\.deps-output\.md' "$f"
  grep -q 'DEPS_OUTPUT' "$REPO_ROOT/skills/deps/scripts/deps_render_report.sh"
  grep -q 'deps-output' "$REPO_ROOT/skills/deps/scripts/deps_render_report.sh"
}
