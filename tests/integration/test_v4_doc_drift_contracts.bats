#!/usr/bin/env bats
#
# test_v4_doc_drift_contracts.bats
#
# Doc-contract tests locking the v4 4-stage architecture + rdd-quick bypass
# representation in user-facing and architectural documentation.
#
# Origin: per `openspec/changes/fix-doc-drift-v4-architecture/proposal.md`
# (audit 2026-09-09). Each test below corresponds to one AC or one Scenar# io
# in `openspec/changes/fix-doc-drift-v4-architecture/specs/doc-architecture-v4-sync/spec.md`.
#
# Pre-patch fail check (AC-6): all 10 tests should FAIL on the pre-patch tree
# (run after `git stash` of the doc edits) and PASS on the post-patch tree.
# This locks the test as a meaningful regression detector rather than a
# "passes on both sides" no-op.

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

# -----------------------------------------------------------------------------
# Test 1: README.md does not contain "五阶段" (stale v3 wording)
# Corresponds to: AC-1, AC-2
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md does not contain '五阶段' (stale v3 wording)" {
  run grep -nE "五阶段" README.md
  if [ "$status" -eq 0 ]; then
    echo "README.md still references '五阶段':"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 2: README.md does not contain "five-phase" (English stale wording)
# Corresponds to: AC-2
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md does not contain 'five-phase' or '5 phases'" {
  run grep -niE "five-phase|five phase|5 phases" README.md
  if [ "$status" -eq 0 ]; then
    echo "README.md still references 5-phase model:"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 3: README.md directory tree includes rdd-planner and rdd-quick
# Corresponds to: AC-1 (directory tree)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md directory tree includes rdd-planner and rdd-quick" {
  # Extract the directory tree section using sed (awk range has subtle issues
  # when start pattern matches end pattern's prefix).
  tree_section=$(sed -n '/^## 目录结构/,/^## /p' README.md | head -n -1)
  if ! echo "$tree_section" | grep -q "rdd-planner"; then
    echo "README.md directory tree missing rdd-planner"
    return 1
  fi
  if ! echo "$tree_section" | grep -q "rdd-quick"; then
    echo "README.md directory tree missing rdd-quick"
    return 1
  fi
  # Ensure rdd-builder appears at most once in directory tree (was 3x in pre-patch)
  builder_count=$(echo "$tree_section" | grep -c "rdd-builder/SKILL.md")
  if [ "$builder_count" -gt 1 ]; then
    echo "README.md directory tree has $builder_count rdd-builder/SKILL.md entries (expected at most 1)"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 4: docs/architecture/overview.md does not contain "five-phase" or "5 phases"
# Corresponds to: AC-2, AC-5
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/overview.md does not contain 'five-phase' or '5 phases'" {
  run grep -niE "five-phase|five phase|5 phases" docs/architecture/overview.md
  if [ "$status" -eq 0 ]; then
    echo "docs/architecture/overview.md still references 5-phase model:"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 5: docs/architecture/overview.md L123 region does not contain inverted rule
# Corresponds to: AC-5
# The inverted rule said "four phases is stale" but v4 IS four stages.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/overview.md L123 inverted rule is corrected" {
  # The inverted rule appears in the "Why Five Phases" section's last paragraph.
  # After the fix, the heading should be "Why Four Stages" and the rule text
  # should mention "four stages" as the current model, not as "stale".
  if grep -nE "any doc that still says .three phases. or .four phases. is stale" docs/architecture/overview.md > /dev/null 2>&1; then
    echo "docs/architecture/overview.md still has the inverted rule 'four phases is stale':"
    grep -n "four phases.*stale\|stale.*four phases" docs/architecture/overview.md
    return 1
  fi
  # Also check for "Why Five Phases" heading (should be renamed)
  if grep -nE "^## Why Five Phases" docs/architecture/overview.md > /dev/null 2>&1; then
    echo "docs/architecture/overview.md still has 'Why Five Phases' heading (should be 'Why Four Stages')"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 6: docs/architecture/workflow-phases.md does not reference guide-* skill names
# Corresponds to: AC-3, AC-10
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md does not reference guide-* skill names" {
  # Exclude historical 'guide-spec' reference which is a valid historical note
  for skill in guide-arch guide-design guide-plan guide-ship; do
    if grep -nE "skill_use.*\"$skill\"|entry skill.*$skill|Entry skill: \`$skill\`" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
      echo "docs/architecture/workflow-phases.md still references $skill"
      grep -n "$skill" docs/architecture/workflow-phases.md | head -3
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Test 7: skills/rdd-arch/SKILL.md L34 does not contain self-reference bug
# Corresponds to: AC-4
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/rdd-arch/SKILL.md L34 does not contain self-reference bug" {
  if grep -nE "从 .rdd-arch. 重命名为 .rdd-arch." skills/rdd-arch/SKILL.md > /dev/null 2>&1; then
    echo "skills/rdd-arch/SKILL.md L34 still has self-reference bug:"
    grep -n "从 .rdd-arch. 重命名为" skills/rdd-arch/SKILL.md
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 8: skills/rdd-arch/SKILL.md does not contain "五阶段"
# Corresponds to: AC-4
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/rdd-arch/SKILL.md does not contain '五阶段'" {
  run grep -nE "五阶段" skills/rdd-arch/SKILL.md
  if [ "$status" -eq 0 ]; then
    echo "skills/rdd-arch/SKILL.md still references '五阶段':"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 9: skills/ has 5 rdd-* stage skills and 0 guide-* stage skills
# Corresponds to: AC-8 (skills directory layout)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/ has 5 rdd-* stage skills and 0 guide-* stage skills" {
  # Expected rdd-* stage skills
  for skill in rdd-arch rdd-planner rdd-builder rdd-verifier rdd-quick; do
    if [ ! -d "skills/$skill" ]; then
      echo "skills/$skill directory missing"
      return 1
    fi
    if [ ! -f "skills/$skill/SKILL.md" ]; then
      echo "skills/$skill/SKILL.md missing"
      return 1
    fi
  done
  # Deprecated guide-* stage skills (excludes guide/ which is the standalone recommender)
  for skill in guide-arch guide-design guide-plan guide-ship guide-spec; do
    if [ -d "skills/$skill" ]; then
      echo "skills/$skill directory exists (should have been removed by Wave 3 per ADR-0044)"
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Test 10: docs/architecture/workflow-phases.md references canonical verifier state path
# Corresponds to: AC-3
# Canonical path per rdd-verifier/SKILL.md is .rddf/state/verifier/<change>.json
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md uses canonical verifier state path" {
  # The deprecated path was .rdd/state/.rdd-verifier-state.json
  if grep -nE "\.rdd/state/\.rdd-verifier-state\.json" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
    echo "docs/architecture/workflow-phases.md still references deprecated .rdd-verifier-state.json path:"
    grep -n "\.rdd-verifier-state" docs/architecture/workflow-phases.md
    return 1
  fi
  # The canonical path should be referenced
  if ! grep -nE "\.rddf/state/verifier/.*<change>" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
    echo "docs/architecture/workflow-phases.md does not reference canonical .rddf/state/verifier/<change>.json path"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Bonus Test 11: ac-verifier is not cited as a sub-skill in workflow-phases.md
# Corresponds to: AC-3 (deprecation per ADR-0045)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md does not reference deprecated ac-verifier" {
  if grep -nE "Sub-skills:.*ac-verifier" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
    echo "docs/architecture/workflow-phases.md still cites ac-verifier as a sub-skill (deprecated per ADR-0045)"
    return 1
  fi
}
