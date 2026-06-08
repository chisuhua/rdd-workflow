#!/usr/bin/env bats
# tests/integration/test_deps_subagent.bats
#
# Locks the implementation of Step 3 subagent semantic analysis in
# skills/deps.md. Covers the 3 placeholder sites that were replaced:
#   - L345 (original) → 3e "子代理调用 (task API)" sub-section
#   - L499 (original) → Step 5 heredoc dynamic branch
#   - L566 (original) → 5e "AI 分析建议（动态输出）" sub-section
#
# Compatibility:
#   - test_deps_skill.bats (structural coverage of skills/deps.md)
#   - test_deps_output.bats (output format of .zcf/.deps-output.md)
#   - test_ai_disclaimer.bats (fallback marker string)
#
# Run: bats tests/integration/test_deps_subagent.bats

load ../test_helper
load_lib deps-subagent

setup() {
  f="$REPO_ROOT/skills/deps.md"
  [ -f "$f" ] || skip "deps.md not found"
}

@test "deps.md Step 3 contains subagent call syntax" {
  deps_subagent_call_marker "$f"
}

@test "deps.md L345 no longer contains the original TODO placeholder" {
  ! grep -qE '<!-- TODO:.*子代理.*语义.*分析.*尚未实现' "$f"
}

@test "deps.md Step 5 heredoc no longer hardcodes 'TODO.*deps.md L320'" {
  ! grep -qE 'TODO.*deps\.md L320' "$f"
}

@test "deps.md 5e section no longer hardcodes 'TODO.*deps.md L320'" {
  # Extract 5e section and assert no TODO L320 reference
  section_5e=$(deps_md_extract_step5 "$f" | awk '
    /^#### 5e\./ { in_5e=1; next }
    in_5e && /^#### / { exit }
    in_5e { print }
  ')
  if echo "$section_5e" | grep -qE 'TODO.*deps\.md L320'; then
    return 1
  fi
}

@test "deps.md documents fallback path for subagent failure" {
  # The plan requires at least 2 matches (Step 3f section + Step 5 fallback marker)
  count=$(grep -cE '降级|fallback' "$f")
  [ "$count" -ge 2 ]
}

@test "deps.md Step 3 subagent call references all 3 artifacts" {
  step3=$(deps_md_extract_step3 "$f")
  echo "$step3" | grep -q 'proposal\.md'
  echo "$step3" | grep -q 'design\.md'
  echo "$step3" | grep -q 'tasks\.md'
}

@test "deps.md Step 5 heredoc has dynamic branch (AI_RESULT_FILE or fallback)" {
  # Extract the heredoc block (after "## 🧠 AI 分析建议")
  ai_section=$(awk '
    /^## 🧠 AI 分析建议/ { in_ai=1; next }
    in_ai { print }
  ' "$f" | head -50)
  # Must contain either the success-path variable, the fallback marker, or "fallback" keyword
  echo "$ai_section" | grep -qE 'AI_RESULT_FILE|fallback|降级'
}

@test "deps.md fallback marker preserves 'AI 语义分析未启用' string (downstream compat)" {
  grep -q "AI 语义分析未启用" "$f"
}
