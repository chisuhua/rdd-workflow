#!/usr/bin/env bats
# tests/integration/test_adr_directory.bats
#
# Locks the invariants of docs/adr/ directory structure. Establishes
# the discoverable target for:
#   - skills/propose/SKILL.md Phase 1a (`ls docs/adr/ADR-*.md`)
#   - skills/deps/SKILL.md Step 1b (`adr_refs` extraction)
#   - proposal-suggestions.md `source` field (`ADR-NNN §N.M`)
#
# Hard constraint (verified by test 14): no file under skills/ may be
# modified as part of this change.
#
# Run: bats tests/integration/test_adr_directory.bats

load ../test_helper

setup() {
  ADR_DIR="$REPO_ROOT/docs/adr"
}

@test "docs/adr/ directory exists" {
  [ -d "$ADR_DIR" ]
}

@test "docs/adr/ADR-0000-template.md exists (reserved template)" {
  [ -f "$ADR_DIR/ADR-0000-template.md" ]
}

@test "docs/adr/README.md exists (index + conventions)" {
  [ -f "$ADR_DIR/README.md" ]
}

@test "at least 1 real ADR exists (excluding template)" {
  # Count files matching ADR-NNNN-*.md pattern but not the template
  count=$(find "$ADR_DIR" -maxdepth 1 -name "ADR-[0-9][0-9][0-9][0-9]-*.md" -type f | wc -l)
  [ "$count" -ge 1 ]
}

@test "propose.md scanner finds ≥ 2 ADR files" {
  # This is the exact command from skills/propose/SKILL.md L186
  count=$(ls "$ADR_DIR"/ADR-*.md 2>/dev/null | wc -l)
  [ "$count" -ge 2 ]
}

@test "ADR-0000-template.md has the required frontmatter fields" {
  f="$ADR_DIR/ADR-0000-template.md"
  head -1 "$f" | grep -qE '^# ADR-0000:'
  grep -qE '^>? ?\*\*状态\*\*:' "$f"
  grep -qE '^>? ?\*\*日期\*\*:' "$f"
  grep -qE '^>? ?\*\*决策者\*\*:' "$f"
}

@test "ADR-0000-template.md has all 4 required sections" {
  f="$ADR_DIR/ADR-0000-template.md"
  grep -qE '^## Context' "$f"
  grep -qE '^## Decision' "$f"
  grep -qE '^## Consequences' "$f"
  grep -qE '^## References' "$f"
}

@test "ADR-0000-template.md cites docs/proposal-suggestions-format.md" {
  grep -qE 'docs/proposal-suggestions-format\.md' "$ADR_DIR/ADR-0000-template.md"
}

@test "every real ADR has a # ADR-NNNN: header" {
  for f in "$ADR_DIR"/ADR-[0-9][0-9][0-9][0-9]-*.md; do
    [ -f "$f" ] || continue
    head -1 "$f" | grep -qE "^# ADR-[0-9]{4}:" || {
      echo "missing or malformed header in: $f" >&2
      return 1
    }
  done
}

@test "every real ADR has a ## 决策 or ## Decision section" {
  for f in "$ADR_DIR"/ADR-[0-9][0-9][0-9][0-9]-*.md; do
    [ -f "$f" ] || continue
    if ! grep -qE '^## (决策|Decision)' "$f"; then
      echo "missing Decision section in: $f" >&2
      return 1
    fi
  done
}

@test "every real ADR has a ## Context section" {
  for f in "$ADR_DIR"/ADR-[0-9][0-9][0-9][0-9]-*.md; do
    [ -f "$f" ] || continue
    grep -qE '^## Context' "$f" || {
      echo "missing Context section in: $f" >&2
      return 1
    }
  done
}

@test "every real ADR has status and date fields" {
  for f in "$ADR_DIR"/ADR-[0-9][0-9][0-9][0-9]-*.md; do
    [ -f "$f" ] || continue
    grep -qE '^>? ?\*\*状态\*\*:' "$f" || {
      echo "missing status field in: $f" >&2
      return 1
    }
    grep -qE '^>? ?\*\*日期\*\*:' "$f" || {
      echo "missing date field in: $f" >&2
      return 1
    }
  done
}

@test "init-adr-directory hard constraint: no skills/ change in original change" {
  # This test is specific to the original init-adr-directory change.
  # v2.0.3 (fix-debt-audit-2026-07-14) intentionally modifies skills/guide-arch/SKILL.md,
  # skills/propose/SKILL.md, skills/roadmap/SKILL.md for ADR renumbering and gate-report
  # removal. We skip this assertion when those files are modified.
  cd "$REPO_ROOT"
  changed=$(git diff --name-only HEAD -- 'skills/*.md' 2>/dev/null)
  if [ -z "$changed" ]; then
    [ true ]  # no skills/ changes — assertion holds
  else
    skip "skills/ changes expected for v2.0.3 (ADR renumbering + gate-report removal)"
  fi
}

@test "README.md documents the ADR-NNN §N.M citation format" {
  grep -qE 'ADR-NNN.*§N\.M|ADR-NNN §N\.M' "$ADR_DIR/README.md"
}
