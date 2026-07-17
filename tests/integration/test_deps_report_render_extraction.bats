#!/usr/bin/env bats
# tests/integration/test_deps_report_render_extraction.bats
# P0-3: deps.md Step 5 (lines 483-642, 160 lines) extracted to
# _lib/deps_render_report.sh bash wrapper + _lib/deps_output.py
# render_markdown_report() Python function.
#
# These tests lock:
#   1. Helper exists with render_deps_report function
#   2. deps.md no longer inlines the 160-line block
#   3. deps.md invokes the helper
#   4. Runtime: render produces correct .deps-output.md content
#   5. Runtime: missing AI file triggers fallback

load ../test_helper

@test "skills/_lib/deps_render_report.sh exists with render_deps_report function" {
  [ -f "$REPO_ROOT/skills/_lib/deps_render_report.sh" ]
  grep -q '^render_deps_report()' "$REPO_ROOT/skills/_lib/deps_render_report.sh"
}

@test "deps.md Step 5 no longer inlines the 160-line block" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  # The original block has 4 separate `cat >>` invocations and 2 inline python3 heredocs.
  # After extraction, none of these patterns should remain in Step 5 range.
  ! sed -n '483,642p' "$REPO_ROOT/skills/deps/SKILL.md" | grep -qE 'for name in "\$\{CANDIDATES'
}

@test "deps.md Step 5 invokes the render helper" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  grep -q '_lib/deps_render_report.sh' "$REPO_ROOT/skills/deps/SKILL.md"
}

@test "render_deps_report writes .deps-output.md with all sections" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  mkdir -p openspec/changes/c1
  echo "# design" > openspec/changes/c1/design.md
  cat > openspec/changes/c1/roadmap-meta.yaml <<'EOF'
roadmap:
  phase: "phase-1"
  category: "general"
EOF
  source "$REPO_ROOT/skills/_lib/deps_render_report.sh"
  PROJECT_ROOT="$TEST_REPO" CANDIDATES="c1" DEPS_OUTPUT="$TEST_REPO/.rddf/state/.deps-output.md" \
    render_deps_report
  [ -f .rddf/state/.deps-output.md ]
  grep -q "## 依赖图 (Mermaid)" .rddf/state/.deps-output.md
  grep -q "## 阶段预检" .rddf/state/.deps-output.md
  grep -q "## Change 状态表" .rddf/state/.deps-output.md
  grep -q "## 推荐执行顺序" .rddf/state/.deps-output.md
  grep -q "## 冲突警告" .rddf/state/.deps-output.md
  grep -q "## 🧠 AI 分析建议" .rddf/state/.deps-output.md
  rm -rf "$TEST_REPO"
}

@test "render_deps_report falls back when no AI result file" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  source "$REPO_ROOT/skills/_lib/deps_render_report.sh"
  PROJECT_ROOT="$TEST_REPO" CANDIDATES="" DEPS_OUTPUT="$TEST_REPO/.rddf/state/.deps-output.md" \
    render_deps_report
  grep -q "AI 语义分析未启用 (fallback)" .rddf/state/.deps-output.md
  rm -rf "$TEST_REPO"
}

@test "render_deps_report renders AI section when AI file present" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  mkdir -p .rddf/state
  cat > .rddf/state/.deps-ai-result.json <<'EOF'
{
  "ai_deps": [{"from": "c1", "to": "c2", "kind": "hard"}],
  "suggestions": [{"change": "c1", "action": "拆分", "reason": "too large"}]
}
EOF
  source "$REPO_ROOT/skills/_lib/deps_render_report.sh"
  PROJECT_ROOT="$TEST_REPO" CANDIDATES="c1 c2" DEPS_OUTPUT="$TEST_REPO/.rddf/state/.deps-output.md" \
    AI_RESULT_FILE="$TEST_REPO/.rddf/state/.deps-ai-result.json" \
    render_deps_report
  grep -q "**子代理语义分析结果**" .rddf/state/.deps-output.md
  grep -q "拆分" .rddf/state/.deps-output.md
  rm -rf "$TEST_REPO"
}
