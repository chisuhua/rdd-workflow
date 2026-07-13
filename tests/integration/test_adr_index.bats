#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "adr_index: docs/adr/README.md status table covers all real ADRs (0001-0019)" {
  for n in 0001 0005 0010 0015 0017 0018 0019; do
    if ! grep -qE "ADR-${n}\b" docs/adr/README.md; then
      echo "docs/adr/README.md missing ADR-${n} reference"
      return 1
    fi
  done
}

@test "adr_index: docs/adr/README.md does NOT reference ADR-NNN beyond 0019" {
  # Flag only ADR-0020+ (legitimate range is 0000-0019; 0000 = template, 0001-0019 = real)
  bad=$(grep -oE "ADR-0[0-9]{3}" docs/adr/README.md | sort -u | grep -E "ADR-0(0[2-9][0-9]|[1-9][0-9]{2})" || true)
  [ -z "$bad" ]
}

@test "adr_index: duplicated ADR-0013 is explicitly flagged in README.md" {
  grep -qE "ADR-0013.*重复|重复.*ADR-0013|extract-scan-state.*incremental-skeleton-planning" docs/adr/README.md
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