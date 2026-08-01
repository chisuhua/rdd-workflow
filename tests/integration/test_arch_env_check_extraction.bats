#!/usr/bin/env bats
# tests/integration/test_arch_env_check_extraction.bats
# Round A extraction: guide-arch.md Phase 1 Steps 1-5 (L92-L189, ~96 lines)
# was a single inline bash code block. Extracted to
# skills/_lib/arch_env_check.sh::run_arch_env_check().
#
# These tests lock the refactor in place:
#   1. arch_env_check.sh exists with run_arch_env_check function.
#   2. guide-arch.md L92-L189 inline block removed.
#   3. guide-arch.md sources and calls run_arch_env_check.
#   4. Helper runs without error from repo root.
#   5. Helper sets PROJECT_ROOT.
#   6. Helper returns 1 when openspec CLI is missing.
#   7. Helper prints ADR/roadmap/gap/change counts.
#   8. Helper prints artifact discovery (ADR-0016) section.

load ../test_helper

# The inline block spans L92-L189 in guide-arch.md.
REPLACED_RANGE="92,189p"

@test "arch_env_check_helper_exists" {
  [ -f "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh" ]
  grep -q 'run_arch_env_check()' "$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh"
  # Verify the function is sourceable
  bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && declare -f run_arch_env_check" | grep -q 'run_arch_env_check'
}

@test "guide_arch_inline_block_removed" {
  [ -f "$REPO_ROOT/skills/guide-arch/SKILL.md" ]
  # After extraction, L92-L189 should no longer contain inline openspec-detection bash
  local count
  count=$(sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-arch/SKILL.md" | grep -c 'command -v openspec' || true)
  [ "$count" -eq 0 ]
}

@test "guide_arch_invokes_helper" {
  [ -f "$REPO_ROOT/skills/guide-arch/SKILL.md" ]
  grep -q 'source.*scripts/arch_env_check.sh' "$REPO_ROOT/skills/guide-arch/SKILL.md"
  grep -q 'run_arch_env_check' "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "run_arch_env_check_runs_in_repo" {
  bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check" >/dev/null
}

@test "run_arch_env_check_sets_project_root" {
  bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check >/dev/null && test -n \"\$PROJECT_ROOT\""
}

@test "run_arch_env_check_fails_when_openspec_missing" {
  # Mock PATH to exclude openspec
  local output
  output=$(PATH=/usr/bin:/bin bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q 'openspec CLI 未找到'
}

@test "run_arch_env_check_discovers_counts" {
  local output
  output=$(bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q '现有 ADR'
  echo "$output" | grep -q 'Roadmap'
  echo "$output" | grep -q '架构差距分析'
  echo "$output" | grep -q '活动 changes'
}

@test "run_arch_env_check_sources_discover_helper" {
  local output
  output=$(bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q '工件发现 (ADR-0016)'
}

@test "run_arch_env_check_fallback_when_discover_missing" {
  # Move discover script aside temporarily, run helper, verify fallback shows defaults
  local tmpdir
  tmpdir=$(mktemp -d)
  cp -r "$REPO_ROOT" "$tmpdir/repo"
  rm "$tmpdir/repo/skills/_lib/discover-arch-artifacts.sh"
  output=$(bash -c "cd '$tmpdir/repo' && source skills/guide-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1)
  rm -rf "$tmpdir"
  # Discover section always shown, using fallback defaults when helper missing
  echo "$output" | grep -q '现有 ADR'
  echo "$output" | grep -q '工件发现 (ADR-0016)'
  echo "$output" | grep -q 'docs/adr'
}

@test "arch_env_check: setup gate — failing project returns 1" {
  local fixture="$BATS_TEST_TMPDIR/failing-setup"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf 'build/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh' && run_arch_env_setup_gate '$fixture'"
  [ "$status" -ne 0 ]
  [[ "$output" == *".rddf/state/"* ]]
}
