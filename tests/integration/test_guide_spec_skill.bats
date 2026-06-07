#!/usr/bin/env bats
# tests/integration/test_guide_spec_skill.bats
#
# Structural / metadata coverage for skills/guide-spec.md.
# Locks the frontmatter, the proposal/design/tasks artifacts
# ownership, the 4 sub-skill references (propose/roadmap/deps/guide-ship),
# and the 4-phase structure (setup/roadmap/propose/deps).
#
# Run: bats tests/integration/test_guide_spec_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/guide-spec.md"
}

@test "guide_spec_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "guide-spec" ]
  [ "$(skill_meta_field "$f" user-invocable)" = "true" ]
}

@test "guide_spec_skill owns proposal/design/tasks artifacts" {
  grep -qE 'openspec/changes/<name>/\{?proposal,design,tasks\}?\.md' "$f" || \
  grep -qE 'openspec/changes' "$f"
  grep -q 'proposal\.md' "$f"
  grep -q 'design\.md' "$f"
  grep -q 'tasks\.md' "$f"
}

@test "guide_spec_skill references all 4 sub-skills" {
  grep -q 'propose' "$f"
  grep -q 'roadmap' "$f"
  grep -q 'deps' "$f"
  grep -q 'guide-ship' "$f"
}

@test "guide_spec_skill covers 4 phases (setup/roadmap/propose/deps)" {
  # Phase numbering in the file is 1, 1.5, 2, 2.5, 3
  grep -qE '^##+[[:space:]]+Phase 1' "$f"
  grep -qE '^##+[[:space:]]+Phase 2' "$f"
  grep -qE '^##+[[:space:]]+Phase 3' "$f"
  # Phase 4 may be embedded in another heading; check for the deps
  # sub-skill invocation as a proxy.
  grep -qE 'deps' "$f"
}
