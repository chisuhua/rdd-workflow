#!/usr/bin/env bats

# Pre-commit proposal quality gate tests.
# Exercises skills/guide-design/scripts/proposal_pre_commit_check.sh against
# .rddf/improvements-style proposal fixtures (canonical English headers).

load ../test_helper

CHECK_SCRIPT="$REPO_ROOT/skills/guide-design/scripts/proposal_pre_commit_check.sh"

# Builds a complete (passing) proposal fixture with all 6 quality criteria:
#   Why / What Changes / Acceptance(>=3 boxes) / ADR / >=2 MUST / >=1 MUST NOT
# Extra lines appended via $2 are used to build broken variants.
make_proposal() {
  local file="$1"
  shift
  cat > "$file" <<'EOF'
## Why

Architecture rationale with ADR-0028.

## What Changes

### In Scope

- add the check helper

### Out of Scope

- CI config

## Capabilities

- MUST run under 30s
- MUST be read-only

## Impact

- MUST NOT modify proposal content

## Acceptance

- [ ] helper exists
- [ ] tests pass
- [ ] docs updated
EOF
  printf '%s\n' "$@" >> "$file"
}

@test "pre-commit-quality: high-quality proposal PASSES (exit 0)" {
  local file="$BATS_TMPDIR/good-$$.md"
  make_proposal "$file"
  run bash "$CHECK_SCRIPT" "$file"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASSED"* ]]
}

@test "pre-commit-quality: missing ## Why section FAILS (exit 1)" {
  local file="$BATS_TMPDIR/no-why-$$.md"
  make_proposal "$file"
  # Remove the Why section (header + 3 body lines).
  sed -i '/^## Why$/,+3d' "$file"
  run bash "$CHECK_SCRIPT" "$file"
  [ "$status" -eq 1 ]
  [[ "$output" == *"## Why"* ]]
}

@test "pre-commit-quality: Acceptance with fewer than 3 checkboxes FAILS (exit 1)" {
  local file="$BATS_TMPDIR/few-boxes-$$.md"
  make_proposal "$file"
  # Keep only 1 checkbox: delete the two trailing `- [ ]` lines.
  sed -i '/^\- \[ \] tests pass$/d; /^\- \[ \] docs updated$/d' "$file"
  run bash "$CHECK_SCRIPT" "$file"
  [ "$status" -eq 1 ]
  [[ "$output" == *"checkbox"* ]]
}

@test "pre-commit-quality: missing ADR reference FAILS (exit 1)" {
  local file="$BATS_TMPDIR/no-adr-$$.md"
  make_proposal "$file"
  sed -i 's/ADR-0028/design-gate/' "$file"
  run bash "$CHECK_SCRIPT" "$file"
  [ "$status" -eq 1 ]
  [[ "$output" == *"ADR"* ]]
}

@test "pre-commit-quality: missing ## Impact MUST NOT clause FAILS (exit 1)" {
  local file="$BATS_TMPDIR/no-mustnot-$$.md"
  make_proposal "$file"
  sed -i '/MUST NOT/d' "$file"
  run bash "$CHECK_SCRIPT" "$file"
  [ "$status" -eq 1 ]
  [[ "$output" == *"MUST NOT"* ]]
}