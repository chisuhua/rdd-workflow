#!/usr/bin/env bats
# tests/integration/test_arch_env_check_extraction.bats
# Round A extraction: rdd-arch.md Phase 1 Steps 1-5 (L92-L189, ~96 lines)
# was a single inline bash code block. Extracted to
# _lib/arch_env_check.sh::run_arch_env_check().
#
# 2026-11-17: the "arch gap analysis" line this helper used to print was removed
# per ADR-0057 (rdd-arch simplified to ADR + theme doc; the gap-analysis
# artifact type was deleted). The corresponding assertion below now checks for
# `主题架构文档` — the line the helper prints today. Keeping the old string made
# this test red for weeks while KNOWN_FAILURES.txt claimed it passed (it was
# also hidden from the full gate: this file does two `cp -r "$REPO_ROOT"` and
# blows the 30s per-file timeout, so collect_bats_failures.sh skipped it).
#
# 2026-11-19: that "hidden from the gate" problem is FIXED, and it was not a
# timeout-budget problem — it was a runtime problem. The file used to copy the
# WHOLE repo twice (`cp -r "$REPO_ROOT"` = 208M / 17973 files, .git included)
# and run the helper 11 more times inside the REAL repo (~3s each, dominated
# by `orchestrator_run`). Idle runtime was 66s; under load it crossed the
# regression gate's per-file cap (30s + 120s retry) ⇒ the file was reported
# "unevaluated" ⇒ **the gate turned red for a reason unrelated to the code
# under test**. `KNOWN_UNEVALUATED.txt` is empty by design (CI is shrink-only),
# so the only fix is to make the file fast.
#
# Strategy now: ONE minimal copy per file (setup_file), containing only the
# subtrees the helper reads (skills / _lib / docs / .rddf/roadmap / openspec).
# That copy is 24M / 2802 files / ~2s and the helper inside it takes ~1s (no
# .git ⇒ no work-tree probe, no 18k-file status scan). Idle runtime ≈ 18s,
# i.e. inside the 30s per-file budget ⇒ evaluated at level 1, no retry.
#
# These tests lock the refactor in place:
#   1. arch_env_check.sh exists with run_arch_env_check function.
#   2. rdd-arch.md L92-L189 inline block removed.
#   3. rdd-arch.md sources and calls run_arch_env_check.
#   4. Helper runs without error from a project root.
#   5. Helper sets PROJECT_ROOT.
#   6. Helper returns 1 when openspec CLI is missing.
#   7. Helper prints ADR/roadmap/theme-doc/change counts.
#   8. Helper prints artifact discovery (ADR-0016) section.

load ../test_helper

# The inline block spans L92-L189 in rdd-arch.md.
REPLACED_RANGE="92,189p"

# Minimal copy of the repo: only the subtrees the helper reads.
# (skills: the script + shared libs; _lib: env_checks + discover-arch-artifacts;
#  docs: ADR/theme-doc dirs; .rddf/roadmap: feature fragments; openspec: the
#  change/spec trees the CLI counts.)
copy_minimal_repo() {
  local dest="$1"
  mkdir -p "$dest/.rddf" "$dest/openspec"
  # mandatory: the helper sources these
  cp -r "$REPO_ROOT/skills" "$dest/"
  cp -r "$REPO_ROOT/_lib" "$dest/"
  cp -r "$REPO_ROOT/docs" "$dest/"
  # optional: only the counts/fragments depend on them (the helper prints the
  # labels unconditionally, so a missing tree degrades the numbers, not the
  # output shape)
  cp -r "$REPO_ROOT/.rddf/roadmap" "$dest/.rddf/" 2>/dev/null || true
  cp "$REPO_ROOT/.rddf/roadmap.md" "$dest/.rddf/" 2>/dev/null || true
  cp -r "$REPO_ROOT/openspec/changes" "$dest/openspec/" 2>/dev/null || true
  cp -r "$REPO_ROOT/openspec/specs" "$dest/openspec/" 2>/dev/null || true
  cp "$REPO_ROOT/openspec/config.yaml" "$dest/openspec/" 2>/dev/null || true
}

# Fixture path is DERIVED, not passed through a variable set in setup_file:
# a `setup_file`-scoped variable is not reliably visible to the test bodies in
# every bats invocation, and when it is empty the failure surfaces as the
# useless `cd: null directory` (seen on a bare CI runner). `BATS_FILE_TMPDIR`
# itself is not guaranteed either, hence the BATS_TMPDIR fallback.
fixture_repo() {
  printf '%s/arch-env-check-repo' "${BATS_FILE_TMPDIR:-${BATS_TMPDIR:-/tmp}}"
}

setup_file() {
  copy_minimal_repo "$(fixture_repo)"
}

setup() {
  MIN_REPO="$(fixture_repo)"
  if [ ! -d "$MIN_REPO" ]; then
    echo "fixture missing: $MIN_REPO (BATS_FILE_TMPDIR='${BATS_FILE_TMPDIR:-}', BATS_TMPDIR='${BATS_TMPDIR:-}')" >&2
    return 1
  fi
}

teardown_file() {
  rm -rf "$(fixture_repo)"
}

@test "arch_env_check_helper_exists" {
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/arch_env_check.sh" ]
  grep -q 'run_arch_env_check()' "$REPO_ROOT/skills/rdd-arch/scripts/arch_env_check.sh"
  # Verify the function is sourceable (sourced from the copy: same bytes, but
  # it keeps the helper out of the real repo's post-flow state writes)
  bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && declare -f run_arch_env_check" | grep -q 'run_arch_env_check'
}

@test "guide_arch_inline_block_removed" {
  [ -f "$REPO_ROOT/skills/rdd-arch/SKILL.md" ]
  # After extraction, L92-L189 should no longer contain inline openspec-detection bash
  local count
  count=$(sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/rdd-arch/SKILL.md" | grep -c 'command -v openspec' || true)
  [ "$count" -eq 0 ]
}

@test "guide_arch_invokes_helper" {
  [ -f "$REPO_ROOT/skills/rdd-arch/SKILL.md" ]
  grep -q 'source.*scripts/arch_env_check.sh' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  grep -q 'run_arch_env_check' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "run_arch_env_check_runs_in_repo" {
  bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" >/dev/null
}

@test "run_arch_env_check_sets_project_root" {
  bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check >/dev/null && test -n \"\$PROJECT_ROOT\""
}

@test "run_arch_env_check_fails_when_openspec_missing" {
  # Mock PATH to exclude openspec
  local output
  output=$(PATH=/usr/bin:/bin bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q 'openspec CLI 未找到'
}

@test "run_arch_env_check_discovers_counts" {
  local output
  output=$(bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q '现有 ADR'
  echo "$output" | grep -q 'Roadmap'
  echo "$output" | grep -q '主题架构文档'
  echo "$output" | grep -q '活动 changes'
}

@test "run_arch_env_check_sources_discover_helper" {
  local output
  output=$(bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q '工件发现 (ADR-0016)'
}

@test "run_arch_env_check_fallback_when_discover_missing" {
  # Move discover script aside temporarily, run helper, verify fallback shows defaults
  local tmpdir
  tmpdir=$(mktemp -d)
  copy_minimal_repo "$tmpdir/repo"
  rm "$tmpdir/repo/_lib/discover-arch-artifacts.sh"
  output=$(bash -c "cd '$tmpdir/repo' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1)
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
  run bash -c "source '$REPO_ROOT/skills/rdd-arch/scripts/arch_env_check.sh' && run_arch_env_setup_gate '$fixture'"
  [ "$status" -ne 0 ]
  [[ "$output" == *".rddf/state/"* ]]
}

# AC-4: improve-roadmap-feature-discovery — display active feature fragments
# in arch_env_check output (per AGENTS.md L206 follow-up)
@test "arch_env_check_ac4_prints_feature_fragments_section" {
  local output
  output=$(bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  echo "$output" | grep -q '活跃 Feature Fragments (跨 phase 追踪)'
}

@test "arch_env_check_ac4_includes_fragment_table" {
  local output
  output=$(bash -c "cd '$MIN_REPO' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1) || true
  # When fragments exist, table row should be visible (feat-fix-archive-gaps-v2 is shipped)
  echo "$output" | grep -q 'feat-fix-archive-gaps-v2'
}

@test "arch_env_check_ac4_suppresses_when_no_active_features" {
  # When --no-archived output is empty, the section should NOT be printed.
  # Strategy: temporarily move the fragments directory aside so list-features
  # returns "no features found", then restore.
  local output tmpdir
  tmpdir=$(mktemp -d)
  copy_minimal_repo "$tmpdir/repo"
  mv "$tmpdir/repo/.rddf/roadmap/features" "$tmpdir/features.bak"
  output=$(bash -c "cd '$tmpdir/repo' && source skills/rdd-arch/scripts/arch_env_check.sh && run_arch_env_check" 2>&1)
  rm -rf "$tmpdir"
  # Section header must NOT appear
  ! echo "$output" | grep -q '活跃 Feature Fragments (跨 phase 追踪)'
}
