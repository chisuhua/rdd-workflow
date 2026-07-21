#!/usr/bin/env bats
# tests/integration/test_propose_parent_feature.bats
#
# Integration tests for skills/propose/scripts/propose_change.sh PARENT_FEATURE
# env-var passing. Covers create_skeleton_change and propose_finalize_change.

load ../test_helper

@test "propose: bash wrapper passes PARENT_FEATURE to create_skeleton_change" {
  tmp_proj="$BATS_TMPDIR/pf-test-$$"
  mkdir -p "$tmp_proj"
  echo "[]" > "$tmp_proj/proposal-suggestions.md"

  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  PROJECT_ROOT="$tmp_proj" PARENT_FEATURE="feature-x" \
    propose_create_change "test-change" "--skeleton" "phase-1" "general" "P2"

  # Verify iteration.json contains parent_feature
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'test-change'), None)
assert match is not None, 'change not found in iteration.json'
assert match.get('parent_feature') == 'feature-x', f'parent_feature mismatch: {match}'
"

  # Verify roadmap-meta.yaml contains parent_feature
  yaml_path="$tmp_proj/openspec/changes/test-change/roadmap-meta.yaml"
  [ -f "$yaml_path" ]
  grep -q 'parent_feature: "feature-x"' "$yaml_path"
}

@test "propose: bash wrapper passes PARENT_FEATURE to finalize_change" {
  tmp_proj="$BATS_TMPDIR/pf-finalize-$$"
  mkdir -p "$tmp_proj/openspec/changes/c1"
  echo "[]" > "$tmp_proj/proposal-suggestions.md"

  # Pre-create iteration.json so update_iteration_proposed can load
  mkdir -p "$tmp_proj/.rddf/state"
  python3 -c "
import json, os
data = {'version': 4, 'updated_at': '2026-07-21T00:00:00+00:00', 'current_phase': 'phase-1', 'changes': []}
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json'), 'w') as f:
    json.dump(data, f)
"

  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  PROJECT_ROOT="$tmp_proj" PARENT_FEATURE="feature-y" \
    propose_finalize_change "c1" "phase-1" "core-impl" "P2" "core-impl:Core"

  # Verify iteration.json
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'c1'), None)
assert match is not None
assert match.get('parent_feature') == 'feature-y', f'expected feature-y, got {match.get(\"parent_feature\")}'
"

  # Verify roadmap-meta.yaml
  yaml_path="$tmp_proj/openspec/changes/c1/roadmap-meta.yaml"
  grep -q 'parent_feature: "feature-y"' "$yaml_path"
}

@test "propose: bash wrapper without PARENT_FEATURE is backward compatible" {
  tmp_proj="$BATS_TMPDIR/pf-noenv-$$"
  mkdir -p "$tmp_proj"
  echo "[]" > "$tmp_proj/proposal-suggestions.md"

  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"

  # No PARENT_FEATURE env var - should not crash
  PROJECT_ROOT="$tmp_proj" \
    propose_create_change "test-change" "--skeleton" "phase-1" "general" "P2"

  # iteration.json should not have parent_feature field
  python3 -c "
import json, os
with open(os.path.join('$tmp_proj', '.rddf', 'state', 'iteration.json')) as f:
    data = json.load(f)
match = next((c for c in data['changes'] if c['name'] == 'test-change'), None)
assert match is not None
assert match.get('parent_feature') is None, f'expected None, got {match.get(\"parent_feature\")}'
"
}
