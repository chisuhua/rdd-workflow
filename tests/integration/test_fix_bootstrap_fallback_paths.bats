#!/usr/bin/env bats
# tests/integration/test_fix_bootstrap_fallback_paths.bats
#
# Regression test for fix-bootstrap-fallback-paths.
# Verifies that no runtime script or SKILL.md surface contains the obsolete
# fallback literal `$HOME/.agents/_lib/skill_root.sh` (missing `skills/`).
#
# The correct global install path is: $HOME/.agents/skills/_lib/skill_root.sh
# The obsolete (buggy) path was:     $HOME/.agents/_lib/skill_root.sh
#
# This test covers the acceptance criterion:
# "No supported runtime/documentation surface contains $HOME/.agents/_lib/skill_root.sh"

load ../test_helper

OBSOLETE_PATTERN='\$HOME/\.agents/_lib/skill_root\.sh'
CORRECT_PATTERN='\$HOME/\.agents/skills/_lib/skill_root\.sh'

# Files that are EXCLUDED from the scan (change artifacts / test fixtures / docs)
EXCLUDED_PATHS=(
  "openspec/changes/"
  "tests/integration/test_playground_full_flow.bats"
  ".rddf/improvements/"
  "docs/superpowers/"
)

# Runtime surfaces: SKILL.md files and runtime shell scripts
RUNTIME_SKILL_MDS=(
  "skills/status/SKILL.md"
  "skills/roadmap/SKILL.md"
  "skills/guide-design/SKILL.md"
  "skills/propose/SKILL.md"
  "skills/feature/SKILL.md"
  "skills/execute/SKILL.md"
  "skills/guide-ship/SKILL.md"
  "skills/deps/SKILL.md"
  "skills/guide-plan/SKILL.md"
)

RUNTIME_SCRIPTS=(
  "skills/guide-design/scripts/design_env_check.sh"
  "skills/guide-arch/scripts/write_arch_handoff.sh"
  "skills/guide-arch/scripts/arch_env_check.sh"
  "skills/guide-arch/scripts/arch_done_gate.sh"
  "skills/rdd-env-check/scripts/env_check.sh"
  "skills/guide-ship/scripts/ship_env_check.sh"
  "skills/guide-plan/scripts/plan_intake.sh"
  "skills/guide-plan/scripts/plan_done_gate.sh"
)

# ── Helper: check a single file for the obsolete literal ───────────────

check_file_for_obsolete_literal() {
  local file="$1"
  local content
  content=$(grep -n "$OBSOLETE_PATTERN" "$file" 2>/dev/null || true)
  if [ -n "$content" ]; then
    echo "FOUND obsolete literal in $file:"
    echo "$content"
    return 1
  fi
  return 0
}

# ── Helper: check a single file uses the correct literal ────────────────

check_file_for_correct_literal() {
  local file="$1"
  local content
  # Only check files that actually source skill_root.sh
  content=$(grep -n "skill_root\.sh" "$file" 2>/dev/null || true)
  if [ -z "$content" ]; then
    return 0  # File doesn't reference skill_root.sh at all - skip
  fi
  # Verify the correct path appears
  if grep -q "$CORRECT_PATTERN" "$file" 2>/dev/null; then
    return 0
  fi
  echo "WARNING: $file sources skill_root.sh but may not use correct path"
  return 0  # Warning only, not a hard failure
}

# ── Test: no obsolete literal in any SKILL.md runtime surface ──────────

@test "bootstrap_fallback: no obsolete \$HOME/.agents/_lib/skill_root.sh in SKILL.md surfaces" {
  local failures=0
  local output=""

  for skill_md in "${RUNTIME_SKILL_MDS[@]}"; do
    local full_path="${REPO_ROOT}/$skill_md"
    if [ ! -f "$full_path" ]; then
      continue  # Skip missing files
    fi
    local result
    result=$(check_file_for_obsolete_literal "$full_path" 2>&1) || true
    if [ -n "$result" ]; then
      output="$output"$'\n'"$result"
      failures=$((failures + 1))
    fi
  done

  if [ $failures -gt 0 ]; then
    echo "=== OBSOLETE LITERAL FOUND IN $failures SKILL.md file(s) ==="
    echo "$output"
    echo "=== ACCEPTANCE CRITERION FAILED ==="
    echo "All runtime SKILL.md surfaces must use: \$HOME/.agents/skills/_lib/skill_root.sh"
    [ "$failures" -eq 0 ]
  fi
}

# ── Test: no obsolete literal in any runtime shell script ───────────────

@test "bootstrap_fallback: no obsolete \$HOME/.agents/_lib/skill_root.sh in runtime scripts" {
  local failures=0
  local output=""

  for script in "${RUNTIME_SCRIPTS[@]}"; do
    local full_path="${REPO_ROOT}/$script"
    if [ ! -f "$full_path" ]; then
      continue  # Skip missing files
    fi
    local result
    result=$(check_file_for_obsolete_literal "$full_path" 2>&1) || true
    if [ -n "$result" ]; then
      output="$output"$'\n'"$result"
      failures=$((failures + 1))
    fi
  done

  if [ $failures -gt 0 ]; then
    echo "=== OBSOLETE LITERAL FOUND IN $failures runtime script(s) ==="
    echo "$output"
    echo "=== ACCEPTANCE CRITERION FAILED ==="
    echo "All runtime scripts must use: \$HOME/.agents/skills/_lib/skill_root.sh"
    [ "$failures" -eq 0 ]
  fi
}

# ── Test: SKILL.md surfaces that source skill_root.sh use the correct literal ─

@test "bootstrap_fallback: SKILL.md surfaces sourcing skill_root.sh use correct path" {
  local failures=0
  local output=""

  for skill_md in "${RUNTIME_SKILL_MDS[@]}"; do
    local full_path="${REPO_ROOT}/$skill_md"
    if [ ! -f "$full_path" ]; then
      continue
    fi
    # Check if this file sources skill_root.sh
    if grep -q "skill_root\.sh" "$full_path" 2>/dev/null; then
      # It should use the correct path (with /skills/)
      if ! grep -q '\$HOME/\.agents/skills/_lib/skill_root\.sh' "$full_path" 2>/dev/null; then
        output="$output"$'\n'"$skill_md: does not contain correct path \$HOME/.agents/skills/_lib/skill_root.sh"
        failures=$((failures + 1))
      fi
    fi
  done

  if [ $failures -gt 0 ]; then
    echo "=== SKILL.md SURFACES MISSING CORRECT PATH: $failures ==="
    echo "$output"
    [ "$failures" -eq 0 ]
  fi
}

# ── Test: external project bootstrap with corrected path succeeds ─────────

@test "bootstrap_fallback: external project bootstrap with corrected path succeeds" {
  local RDDF_GLOBAL_LIB="${HOME}/.agents/skills/_lib"

  # Verify the global lib actually exists (from install.sh --global)
  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh not installed (run install.sh --global)"

  local EXTERNAL_ROOT="${BATS_TMPDIR}/external-bootstrap-test-$$"
  mkdir -p "$EXTERNAL_ROOT"
  cd "$EXTERNAL_ROOT"

  # Init git repo
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"

  # Set PROJECT_ROOT to external project (no local copy)
  export PROJECT_ROOT="$EXTERNAL_ROOT"

  # Run the CORRECT bootstrap pattern (what the fixed SKILL.md docs will show)
  run bash -c '
    set -e
    source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" \
      2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
    type resolve_rdd_skill_dir >/dev/null
    type resolve_rdd_lib_dir >/dev/null
    echo "BOOTSTRAP_OK"
  '

  rm -rf "$EXTERNAL_ROOT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"BOOTSTRAP_OK"* ]]
}

# ── Test: resolve_rdd_skill_dir resolves to global skills path ─────────

@test "bootstrap_fallback: resolve_rdd_skill_dir resolves to global skills path" {
  local RDDF_GLOBAL_LIB="${HOME}/.agents/skills/_lib"

  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh not installed"

  export PROJECT_ROOT="${BATS_TMPDIR}/no-such-project-$$"

  # shellcheck source=/dev/null
  source "$RDDF_GLOBAL_LIB/skill_root.sh"

  local result
  result="$(resolve_rdd_skill_dir guide-arch)"

  [ "$result" = "$HOME/.agents/skills/guide-arch" ]
  [ -d "$result" ]
  [ -f "$result/SKILL.md" ]
}

# ── Test: resolve_rdd_lib_dir resolves to global skills/_lib path ───────

@test "bootstrap_fallback: resolve_rdd_lib_dir resolves to global skills/_lib path" {
  local RDDF_GLOBAL_LIB="${HOME}/.agents/skills/_lib"

  [ -f "$RDDF_GLOBAL_LIB/skill_root.sh" ] || skip "global skill_root.sh not installed"

  export PROJECT_ROOT="${BATS_TMPDIR}/no-such-project-$$"

  # shellcheck source=/dev/null
  source "$RDDF_GLOBAL_LIB/skill_root.sh"

  local result
  result="$(resolve_rdd_lib_dir)"

  [ "$result" = "$HOME/.agents/skills/_lib" ]
  [ -d "$result" ]
}
