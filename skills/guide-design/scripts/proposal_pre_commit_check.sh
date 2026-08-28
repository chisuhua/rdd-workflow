#!/usr/bin/env bash
# proposal_pre_commit_check.sh <proposal-file> [project_root]
#
# Pre-commit quality gate for `.rddf/improvements/*.md` proposal files.
# Verifies that a proposal meets the 6 structural quality criteria the
# design phase requires before the proposal is registered to
# proposal-suggestions.md / proposal-approved.md:
#
#   1. ## Why       section  (架构依据)  - architecture rationale / problem statement
#   2. ## What Changes        (范围)     - In Scope / Out of Scope
#   3. ## Acceptance section  (验收标准) - >=3 checkboxes
#   4. ADR reference                     - ADR-NNNN appears >=1 time
#   5. Capabilities           (技术约束) - >=2 MUST clauses
#   6. Impact                 (技术约束) - >=1 MUST NOT clause
#
# Each criterion is matched against the documented English section header
# OR its Chinese alias, so both the canonical English format and the
# repo's existing Chinese 5-section format are accepted.
#
# Usage:
#   proposal_pre_commit_check.sh <file>            # check one proposal
#   proposal_pre_commit_check.sh --all             # check every .rddf/improvements/*.md
#
# Exit codes:
#   0   all criteria pass
#   1   one or more criteria failed (each failed criterion is listed)
#   2   usage error (missing / --all with no improvements dir)
#   127 target file does not exist
#
# Env vars:
#   SKIP_PROPOSAL_QUALITY_CHECK=yes  emergency bypass -> always exit 0
#
# This is a read-only checker: it never modifies the proposal content.

set -uo pipefail

# Resolve project root (2nd positional, else env, else git).
PROJECT_ROOT="${2:-${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"

# Emergency bypass (documented in the improvement file as MUST).
if [[ "${SKIP_PROPOSAL_QUALITY_CHECK:-}" == "yes" ]]; then
  echo "ℹ️  SKIP_PROPOSAL_QUALITY_CHECK=yes: proposal quality check skipped"
  exit 0
fi

usage() {
  echo "usage: proposal_pre_commit_check.sh <proposal-file|--all> [project_root]" >&2
}

# --- criterion helpers -------------------------------------------------------

# has_section <file> <header1> <header2>
# True when the file contains a top-level `## <header>` for either alias.
has_section() {
  local file="$1" h1="$2" h2="$3"
  grep -qE "^##[[:space:]]+(${h1}|${h2})" "$file"
}

check_why() {
  if ! has_section "$1" "Why" "架构依据"; then
    echo "  ❌ missing '## Why' section (架构依据) - architecture rationale"
    return 1
  fi
  return 0
}

check_what_changes() {
  if ! has_section "$1" "What Changes" "范围"; then
    echo "  ❌ missing '## What Changes' section (范围) - In Scope / Out of Scope"
    return 1
  fi
  return 0
}

check_acceptance() {
  if ! has_section "$1" "Acceptance" "验收标准"; then
    echo "  ❌ missing '## Acceptance' section (验收标准)"
    return 1
  fi
  local count
  count=$(grep -cE '^\s*-\s*\[ \]' "$1" || true)
  if [[ "$count" -lt 3 ]]; then
    echo "  ❌ '## Acceptance' has $count checkbox(es) (min 3)"
    return 1
  fi
  return 0
}

check_adr_reference() {
  if ! grep -qE 'ADR-[0-9]{4}' "$1"; then
    echo "  ❌ missing ADR reference (must reference >=1 ADR-NNNN)"
    return 1
  fi
  return 0
}

check_capabilities() {
  local count
  count=$(grep -oE '\bMUST\b' "$1" | wc -l)
  if [[ "$count" -lt 2 ]]; then
    echo "  ❌ Capabilities/技术约束 has only $count MUST clause(s) (min 2)"
    return 1
  fi
  return 0
}

check_impact() {
  if ! grep -q 'MUST NOT' "$1"; then
    echo "  ❌ missing 'MUST NOT' clause in Impact/技术约束"
    return 1
  fi
  return 0
}

# --- per-file runner ---------------------------------------------------------

check_one() {
  local file="$1"
  local failed=0
  local results

  results=$( {
    check_why "$file"
    check_what_changes "$file"
    check_acceptance "$file"
    check_adr_reference "$file"
    check_capabilities "$file"
    check_impact "$file"
  } 2>&1 )

  if [[ -n "$results" ]]; then
    echo "❌ proposal quality check FAILED: $file"
    echo "$results"
    failed=1
  else
    echo "✅ proposal quality check PASSED: $file"
  fi
  return "$failed"
}

# --- entry point -------------------------------------------------------------

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  usage
  exit 2
fi

if [[ "$TARGET" == "--all" ]]; then
  imp_dir="$PROJECT_ROOT/.rddf/improvements"
  if [[ ! -d "$imp_dir" ]]; then
    echo "❌ no .rddf/improvements directory at $imp_dir" >&2
    exit 2
  fi
  any_failed=0
  for f in "$imp_dir"/*.md; do
    [[ -e "$f" ]] || continue
    check_one "$f" || any_failed=1
  done
  exit "$any_failed"
fi

if [[ ! -f "$TARGET" ]]; then
  echo "❌ proposal file not found: $TARGET" >&2
  exit 127
fi

check_one "$TARGET"
exit $?
