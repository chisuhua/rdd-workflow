#!/usr/bin/env bats
# tests/integration/test_propose_phase4_extraction.bats
# P0-1: propose.md Phase 4 (lines 443-796, 353 lines) extracted to
# _lib/propose_change.sh + _lib/propose_change.py. These tests lock:
#   1. Helper exists with propose_create_change + propose_finalize_change
#   2. propose.md no longer inlines the 353-line block
#   3. propose.md invokes the helper
#   4. Runtime: skeleton mode writes correct artifacts
#   5. Runtime: full mode (propose_finalize_change) updates iteration.json
#   6. Runtime: handles missing roadmap-state gracefully
#   7. Runtime: artifact loop 580-608 preserved as-is (pseudo-code)
#   8. Runtime: Step 4e docs (30 lines /opsx:propose explanation) removed

load ../test_helper

@test "_lib/propose_change.sh exists with both functions" {
  [ -f "$REPO_ROOT/skills/propose/scripts/propose_change.sh" ]
  grep -q '^propose_create_change()' "$REPO_ROOT/skills/propose/scripts/propose_change.sh"
  grep -q '^propose_finalize_change()' "$REPO_ROOT/skills/propose/scripts/propose_change.sh"
}

@test "propose.md Phase 4 no longer inlines the 353-line block" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  # After extraction: the long inline heredocs are gone.
  # THIS_SESSION_CREATED+= is PRESERVED (used by Phase 5 for commit tracking).
  # Original block had: openspec new change + jq + nested Python heredocs.
  # Verify none of these inline patterns remain in Phase 4 range.
  ! grep -qE 'jq -r --arg req' "$REPO_ROOT/skills/propose/SKILL.md"
  # Original had 4 PYEOF heredocs in Phase 4 — should now have 1 (skeleton status update only)
  local py_count
  py_count=$(grep -c 'PYEOF' "$REPO_ROOT/skills/propose/SKILL.md")
  [ "$py_count" -le 2 ]  # skeleton update + safe_python_json (Phase 0) at most
}

@test "propose.md Phase 4 invokes the helper" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  grep -q 'scripts/propose_change.sh' "$REPO_ROOT/skills/propose/SKILL.md"
}

@test "propose.md Step 4e docs (30 lines /opsx:propose explanation) removed" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  ! grep -q '用结构化需求描述作为 openspec-propose 的输入' "$REPO_ROOT/skills/propose/SKILL.md"
}

@test "propose.md preserves pseudo-code artifact loop (NOT extracted)" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  # The half-implemented loop should still be there
  grep -q 'for each artifact_id in artifact_order' "$REPO_ROOT/skills/propose/SKILL.md"
}

@test "propose.md Phase 4 block is now thin (≤30 lines per bash block)" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  # After extraction, each bash block in Phase 4 should be a thin wrapper.
  # Extract the bash block under "## Phase 4"
  local max_block
  max_block=$(awk '
    /^## Phase 4:/ {found=1; next}
    found && /^```bash$/ {n++; lines=0; capture=1; next}
    capture && /^```$/ {if (n>0 && lines>max) max=lines; n=0; capture=0; next}
    capture {lines++}
    END {print max+0}
  ' "$REPO_ROOT/skills/propose/SKILL.md")
  [ "$max_block" -le 30 ]
}

@test "propose_create_change skeleton mode writes proposal.md + roadmap-meta.yaml + updates iteration" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"
  python3 -c "
import sys; sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  propose_create_change my-change --skeleton phase-1 arch-design P2
  # proposal.md + roadmap-meta.yaml should exist
  [ -f openspec/changes/my-change/proposal.md ]
  [ -f openspec/changes/my-change/roadmap-meta.yaml ]
  # iteration.json updated to status=planned
  python3 -c "
import json, sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
loaded = it.load('$TEST_REPO')
match = next(c for c in loaded['changes'] if c['name'] == 'my-change')
assert match['status'] == 'planned', f'status={match[\"status\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "propose_finalize_change updates iteration.json (status=proposed)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"
  python3 -c "
import sys; sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
from skills._lib import roadmap_state as rs
it.save('$TEST_REPO', it.create_empty())
rs.init_state('$TEST_REPO/.rddf/state/roadmap-state.json', 'phase-1')
"
  mkdir -p openspec/changes/c1
  propose_finalize_change c1 phase-1 arch-design P2 "arch-design:Architecture Design\ninfra-setup:Infrastructure Setup\ncore-impl:Core Implementation\ncore-test:Core Test"
  python3 -c "
import json
with open('.rddf/state/iteration.json') as f:
    data = json.load(f)
match = next(c for c in data['changes'] if c['name'] == 'c1')
assert match['status'] == 'proposed', f'status: {match[\"status\"]}'
assert match['phase'] == 'phase-1', f'phase: {match[\"phase\"]}'
assert match['category'] == 'arch-design', f'category: {match[\"category\"]}'
assert match['priority'] == 'P2', f'priority: {match[\"priority\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "propose_finalize_change handles missing roadmap-state gracefully" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/propose/scripts/propose_change.sh"
  # Only init iteration, NOT roadmap-state
  python3 -c "
import sys; sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  mkdir -p openspec/changes/c1
  run propose_finalize_change c1 phase-1 arch-design P2 "arch-design:Architecture"
  [ "$status" = "0" ]
  python3 -c "
import json
with open('.rddf/state/iteration.json') as f:
    data = json.load(f)
match = next(c for c in data['changes'] if c['name'] == 'c1')
assert match['status'] == 'proposed'
"
  rm -rf "$TEST_REPO"
}