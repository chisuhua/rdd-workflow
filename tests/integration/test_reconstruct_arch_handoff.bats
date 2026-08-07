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
  touch "$PROJECT_ROOT/docs/adr/ADR-0002-other.md"
  touch "$PROJECT_ROOT/roadmap.md"
  touch "$PROJECT_ROOT/docs/architecture/overview.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]

  local handoff="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  # Validate all 12 required schema fields
  jq -e '.version == 1' "$handoff" >/dev/null
  jq -e '.arch_complete_at | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}")' "$handoff" >/dev/null
  jq -e '.adr_count == 2' "$handoff" >/dev/null
  jq -e '.completed_adr_ids | length == 2' "$handoff" >/dev/null
  jq -e '.completed_adr_ids | contains(["0001", "0002"])' "$handoff" >/dev/null
  jq -e '.roadmap_exists == true' "$handoff" >/dev/null
  jq -e '.current_phase | type == "string"' "$handoff" >/dev/null
  jq -e '.plan_started_at != null' "$handoff" >/dev/null
  jq -e '.adr_dir == "docs/adr"' "$handoff" >/dev/null
  jq -e '.roadmap_path == "roadmap.md"' "$handoff" >/dev/null
  jq -e '.architecture_dir == "docs/architecture"' "$handoff" >/dev/null
  jq -e '.adr_pattern == "ADR-*.md"' "$handoff" >/dev/null

  # discovered must be an object with nested metadata
  jq -e '.discovered | type == "object"' "$handoff" >/dev/null
  jq -e '.discovered.adr_dir | (.found and (.created | type == "boolean") and (.candidates_tried | type == "number"))' "$handoff" >/dev/null
  jq -e '.discovered.roadmap_path.found == true' "$handoff" >/dev/null
  jq -e '.discovered.architecture_dir.found == true' "$handoff" >/dev/null

  # Reconstruction metadata
  jq -e '.reconstructed_at | type == "string"' "$handoff" >/dev/null
  jq -e '.reconstructed_from == "filesystem-evidence"' "$handoff" >/dev/null
}
