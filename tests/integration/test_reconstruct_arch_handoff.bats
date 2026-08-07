#!/usr/bin/env bats
load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/recon-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  mkdir -p "$PROJECT_ROOT/docs/adr"
  mkdir -p "$PROJECT_ROOT/docs/architecture"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

@test "reconstruct_arch_handoff: writes valid v1 schema handoff" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0002-test.md"
  touch "$PROJECT_ROOT/roadmap.md"
  touch "$PROJECT_ROOT/docs/architecture/overview.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]

  # Validate JSON shape
  jq -e '.version == 1' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.discovered == true' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.adr_dir == "docs/adr"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.adr_pattern | test("ADR-")' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.roadmap_path == "roadmap.md"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.architecture_dir == "docs/architecture"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
}
