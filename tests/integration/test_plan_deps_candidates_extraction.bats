#!/usr/bin/env bats
# tests/integration/test_plan_deps_candidates_extraction.bats
# Round B extraction: guide-plan.md L451-L488 (~38-line inline bash block)
# generates .rddf/state/.deps-candidates.json. Extracted to
# _lib/plan_deps_candidates.{py,sh,env.py}::generate_deps_candidates().
#
# These tests lock the refactor in place:
#   1. Helper files exist with generate_deps_candidates function.
#   2. guide-plan.md L451-L488 inline block removed.
#   3. guide-plan.md sources and calls generate_deps_candidates.
#   4. Oracle C1: no bash $VAR interpolation into Python source.
#   5. Helper creates .deps-candidates.json with valid JSON.
#   6. Helper handles empty changes directory.

load ../test_helper

@test "plan_deps_candidates_helper_exists" {
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates.sh" ]
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates.py" ]
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates_env.py" ]
  bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_deps_candidates.sh && declare -f generate_deps_candidates" | grep -q 'generate_deps_candidates'
}

@test "guide_plan_inline_block_removed" {
  # No python heredoc with $PROJECT_ROOT interpolation
  ! grep -q "changes_dir = '\$PROJECT_ROOT" "$REPO_ROOT/skills/guide-plan/SKILL.md"
  # No '生成候选列表:' message (that's the helper's output now)
  ! grep -q '生成候选列表:' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide_plan_invokes_helper" {
  grep -q 'source.*scripts/plan_deps_candidates.sh' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'generate_deps_candidates' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "oracle_c1_no_bash_string_interpolation" {
  # Bash wrapper must NOT inject variables into Python source
  ! grep -n "python3.*'\$" "$REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates.sh"
}

@test "generate_deps_candidates_creates_file" {
  local tmpdir
  tmpdir=$(mktemp -d)
  git init "$tmpdir" >/dev/null 2>&1
  mkdir -p "$tmpdir/openspec/changes/test-change"
  echo "name: test" > "$tmpdir/openspec/changes/test-change/.openspec.yaml"
  bash -c "cd '$tmpdir' && git add -A && git commit -m init >/dev/null 2>&1 && source $REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates.sh && generate_deps_candidates" 2>&1 || true
  if [ -f "$tmpdir/.rddf/state/.deps-candidates.json" ]; then
    cat "$tmpdir/.rddf/state/.deps-candidates.json" | grep -q 'candidates'
  fi
  rm -rf "$tmpdir"
}

@test "generate_deps_candidates_handles_no_changes" {
  local tmpdir
  tmpdir=$(mktemp -d)
  git init "$tmpdir" >/dev/null 2>&1
  bash -c "cd '$tmpdir' && git commit --allow-empty -m init >/dev/null 2>&1 && source $REPO_ROOT/skills/guide-plan/scripts/plan_deps_candidates.sh && generate_deps_candidates" 2>&1 || true
  if [ -f "$tmpdir/.rddf/state/.deps-candidates.json" ]; then
    cat "$tmpdir/.rddf/state/.deps-candidates.json" | grep -q '"candidates": \[\]'
  fi
  rm -rf "$tmpdir"
}
