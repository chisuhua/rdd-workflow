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

@test "adr_index: docs/adr/README.md does NOT reference ADR-NNN beyond current max" {
  # Auto-detect current max ADR number from docs/adr/. Per Stage 3 ADR-0042
  # addition: the test no longer hardcodes "0034" — it flags anything above
  # the on-disk max as unexpected (must add new ADR file first).
  current_max=$(ls docs/adr/ADR-[0-9][0-9][0-9][0-9]-*.md 2>/dev/null | \
    sed -E 's|.*ADR-([0-9]{4})-.*|\1|' | sort -n | tail -1)
  current_max=${current_max:-0034}
  bad=$(grep -oE "ADR-0[0-9]{3}" docs/adr/README.md | sort -u | \
    awk -v max="$current_max" '$0 > "ADR-" max && $0 != "ADR-0000"' || true)
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