#!/usr/bin/env bats

load ../test_helper

# P2-4: deps.md 5e section must explicitly disclaim that AI semantic
# analysis is NOT implemented (or, post-implement-deps-subagent-analysis,
# that the subagent fallback path was taken).
#
# Note: as of `implement-deps-subagent-analysis`, the disclaimer is
# dynamic — emitted only on the fallback path; the AI success path
# emits a subagent report instead. The string `AI 语义分析未启用`
# remains in the file as a fallback sentinel for downstream consumers
# (see test_deps_subagent.bats case 8).

@test "deps.md has AI placeholder disclaimer" {
  [ -f "skills/deps/SKILL.md" ]
  grep -q "AI 语义分析未启用" skills/deps/SKILL.md
}

@test "deps.md fallback path is documented for AI analysis" {
  # Replaces the obsolete "TODO L320" location test. The TODO L320
  # reference was a stale pointer (the real placeholder was at L345).
  # The new design documents the fallback as a first-class path.
  [ -f "skills/deps/SKILL.md" ]
  grep -qE "(降级|fallback).*subagent|AI 子代理.*fallback" skills/deps/SKILL.md
}

@test "deps.md disclaimer is in 5e section" {
  [ -f "skills/deps/SKILL.md" ]
  # Should appear after the 5d boundary (#### 5d. 冲突警告摘要 OR ## 冲突警告)
  # and before end of file. The AI disclaimer (or fallback marker) must
  # be in the 5e section.
  awk '
    /^#### 5d\./ || /^## 冲突警告/ { in_5e=1; next }
    in_5e && /AI 语义分析未启用/ { found=1; exit }
    END { exit !found }
  ' skills/deps/SKILL.md
}
