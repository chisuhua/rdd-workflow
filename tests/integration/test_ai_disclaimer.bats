#!/usr/bin/env bats

load ../test_helper

# P2-4: deps.md 5e section must explicitly disclaim that AI semantic
# analysis is NOT implemented. The historical docs showed example
# AI-generated output (semantic dependencies, granularity evaluation,
# reorganization suggestions) which mislead users into expecting
# features that don't exist. The 5e section must be a placeholder.

@test "deps.md has AI placeholder disclaimer" {
  [ -f "skills/deps.md" ]
  grep -q "AI 语义分析未启用" skills/deps.md
}

@test "deps.md mentions TODO location for AI analysis" {
  [ -f "skills/deps.md" ]
  grep -q "TODO.*deps.md L320" skills/deps.md
}

@test "deps.md disclaimer is in 5e section" {
  [ -f "skills/deps.md" ]
  # Should appear after the 5d boundary (#### 5d. 冲突警告摘要 OR ## 冲突警告)
  # and before end of file. The AI disclaimer must be in the 5e section.
  awk '
    /^#### 5d\./ || /^## 冲突警告/ { in_5e=1; next }
    in_5e && /AI 语义分析未启用/ { found=1; exit }
    END { exit !found }
  ' skills/deps.md
}
