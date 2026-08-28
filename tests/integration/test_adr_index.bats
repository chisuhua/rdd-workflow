#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "adr_index: docs/adr/README.md status table covers all real ADRs (0001-0023)" {
  for n in 0001 0005 0010 0015 0017 0018 0019 0020 0021 0022 0023; do
    if ! grep -qE "ADR-${n}\b" docs/adr/README.md; then
      echo "docs/adr/README.md missing ADR-${n} reference"
      return 1
    fi
  done
}

@test "adr_index: docs/adr/README.md does NOT reference ADR-NNN beyond 0034" {
  # Valid ADR range: 0000 (template) + 0001-0034 (real). adr-index-auto-sync change
  # #2 has regenerated the README table to cover all 34 real ADRs.
  # Flag only ADR-0035+ as unexpected (must add new file on disk first).
  bad=$(grep -oE "ADR-0[0-9]{3}" docs/adr/README.md | sort -u | grep -E "ADR-0(0[3-9][0-9]|[1-9][0-9]{2})" | grep -v -E "ADR-003[0-4]\b" || true)
  [ -z "$bad" ]
}

@test "adr_index: no ADR-0013 duplicate exists on disk (incremental-skeleton-planning renumbered to ADR-0020)" {
  # After v2.0.2 renumbering, only ADR-0013-extract-scan-state.md should remain as 0013
  count=$(find docs/adr -maxdepth 1 -name 'ADR-0013-*.md' | wc -l)
  if [ "$count" -ne 1 ]; then
    echo "Expected exactly 1 ADR-0013 file, found $count"
    return 1
  fi
  [ -f "docs/adr/ADR-0020-incremental-skeleton-planning.md" ]
}

@test "adr_index: docs/adr/README.md status table is consistent with disk" {
  missing=""
  for adr in $(find docs/adr -maxdepth 1 -name 'ADR-*.md' | sort); do
    base=$(basename "$adr")
    if ! grep -qF "$base" docs/adr/README.md; then
      missing="${missing}${base} "
    fi
  done
  [ -z "$missing" ]
}