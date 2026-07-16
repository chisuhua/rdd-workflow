#!/usr/bin/env bats
# tests/integration/test_arch_gap_analysis_extraction.bats
# Round B extraction: guide-arch.md L343-L431 (~85 lines, 2 inline bash blocks)
# — gap analysis generator + viewer. Extracted to
# skills/_lib/arch_gap_analysis.sh exposing:
#   - generate_gap_analysis <slug>  — creates docs/architecture/<slug>-gap-analysis.md
#   - list_gap_analyses             — prints numbered list of existing gap analyses
#
# These tests lock the refactor in place:
#   1. arch_gap_analysis.sh exists with both functions exported.
#   2. guide-arch.md no longer contains gap analysis heredoc / viewer inline text.
#   3. guide-arch.md sources and calls both helpers.
#   4. generate_gap_analysis creates the expected file with template sections.
#   5. list_gap_analyses finds existing files.
#   6. list_gap_analyses handles empty directory.
#   7. Both helpers honor DISCOVERED_ARCHITECTURE_DIR env var.

load ../test_helper

@test "arch_gap_analysis_helper_exists" {
  [ -f "$REPO_ROOT/skills/_lib/arch_gap_analysis.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/_lib/arch_gap_analysis.sh && declare -f generate_gap_analysis && declare -f list_gap_analyses" | grep -q 'generate_gap_analysis'
}

@test "guide_arch_inline_gap_block_removed" {
  # After extraction, L343-L431 should no longer contain the gap analysis heredoc
  # template text or viewer text.
  ! grep -q '请提供差距分析主题' "$REPO_ROOT/skills/guide-arch.md"
  ! grep -q '现有差距分析列表' "$REPO_ROOT/skills/guide-arch.md"
}

@test "guide_arch_invokes_helper" {
  grep -q 'source.*_lib/arch_gap_analysis.sh' "$REPO_ROOT/skills/guide-arch.md"
  grep -q 'generate_gap_analysis' "$REPO_ROOT/skills/guide-arch.md"
  grep -q 'list_gap_analyses' "$REPO_ROOT/skills/guide-arch.md"
}

@test "generate_gap_analysis_creates_file" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  # Unset PROJECT_ROOT so the helper uses pwd (tmpdir), not the real repo root
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/_lib/arch_gap_analysis.sh' && generate_gap_analysis 'test-slug'" >/dev/null 2>&1
  assert_file_exists "$tmpdir/docs/architecture/test-slug-gap-analysis.md"
  rm -rf "$tmpdir"
}

@test "generate_gap_analysis_file_has_template_sections" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/_lib/arch_gap_analysis.sh' && generate_gap_analysis 'sample'" >/dev/null 2>&1
  local file="$tmpdir/docs/architecture/sample-gap-analysis.md"
  assert_file_exists "$file"
  grep -q '目标架构' "$file"
  grep -q '当前架构' "$file"
  grep -q '差距清单' "$file"
  grep -q '补齐路径' "$file"
  grep -q '参考资料' "$file"
  rm -rf "$tmpdir"
}

@test "list_gap_analyses_finds_existing" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  touch "$tmpdir/docs/architecture/existing-1-gap-analysis.md"
  touch "$tmpdir/docs/architecture/existing-2-gap-analysis.md"
  output=$(bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/_lib/arch_gap_analysis.sh' && list_gap_analyses" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q 'existing-1'
  echo "$output" | grep -q 'existing-2'
}

@test "list_gap_analyses_handles_empty" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/architecture"
  output=$(bash -c "cd '$tmpdir' && unset PROJECT_ROOT && source '$REPO_ROOT/skills/_lib/arch_gap_analysis.sh' && list_gap_analyses" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE '暂无|空|0 '
}

@test "arch_gap_analysis_uses_discovery_env_var" {
  # Honor DISCOVERED_ARCHITECTURE_DIR env var from arch_env_check.sh
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/custom/architecture"
  bash -c "cd '$tmpdir' && unset PROJECT_ROOT && export DISCOVERED_ARCHITECTURE_DIR='custom/architecture' && source '$REPO_ROOT/skills/_lib/arch_gap_analysis.sh' && generate_gap_analysis 'test'" >/dev/null 2>&1
  assert_file_exists "$tmpdir/custom/architecture/test-gap-analysis.md"
  rm -rf "$tmpdir"
}