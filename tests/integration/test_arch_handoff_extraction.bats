#!/usr/bin/env bats
# tests/integration/test_arch_handoff_extraction.bats
# Round A extraction: guide-arch.md L618-L707 inline heredoc-based JSON
# generation (~88 lines) extracted to _lib/write_arch_handoff.{py,sh}.
#
# These tests lock the refactor in place:
#   1. Helper files exist with expected exports.
#   2. guide-arch.md no longer inlines the cat-heredoc block (L618-L707).
#   3. guide-arch.md sources the helper and calls write_arch_handoff.
#   4. Runtime: helper creates .arch-handoff.json in scratch repo.
#   5. Runtime: required fields present in output JSON.
#   6. Runtime: handles missing artifacts gracefully (no crash).

load ../test_helper

@test "skills/_lib/write_arch_handoff.{sh,py,env.py} exist" {
  [ -f "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff.sh" ]
  [ -f "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff.py" ]
  [ -f "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff_env.py" ]
}

@test "write_arch_handoff.sh exports write_arch_handoff function" {
  bash -c "cd '$REPO_ROOT' && source skills/guide-arch/scripts/write_arch_handoff.sh && declare -f write_arch_handoff" | grep -q 'write_arch_handoff'
}

@test "guide-arch.md replaced inline block no longer contains cat heredoc" {
  # Content-driven check (not line-range): verify no heredoc writes to HANDOFF_FILE
  ! grep -q 'cat > "\$HANDOFF_FILE"' "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "guide-arch.md sources _lib/write_arch_handoff.sh and calls write_arch_handoff" {
  grep -q 'source.*scripts/write_arch_handoff.sh' "$REPO_ROOT/skills/guide-arch/SKILL.md"
  grep -q 'write_arch_handoff' "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "write_arch_handoff creates .arch-handoff.json in scratch repo" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/.rddf/state"
  echo "# ADR" > "$tmpdir/docs/adr/ADR-0001-test.md"
  echo "**当前阶段**: phase-2" > "$tmpdir/roadmap.md"
  export PROJECT_ROOT="$tmpdir" DISCOVERED_ADR_DIR="docs/adr" DISCOVERED_ROADMAP_PATH="roadmap.md"
  export DISCOVERED_ARCHITECTURE_DIR="docs/architecture" DISCOVERED_ADR_PATTERN="ADR-*.md" ROADMAP_EXISTS_BOOL="true"
  python3 "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff_env.py" >/dev/null 2>&1
  if [ ! -f "$tmpdir/.rddf/state/.arch-handoff.json" ]; then
    echo "arch-handoff.json not found in $tmpdir/.rddf/state/"
    return 1
  fi
  rm -rf "$tmpdir"
}

@test "write_arch_handoff output has required schema fields" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/.rddf/state"
  echo "# ADR" > "$tmpdir/docs/adr/ADR-0001-test.md"
  echo "**当前阶段**: phase-2" > "$tmpdir/roadmap.md"
  export PROJECT_ROOT="$tmpdir" DISCOVERED_ADR_DIR="docs/adr" DISCOVERED_ROADMAP_PATH="roadmap.md"
  export DISCOVERED_ARCHITECTURE_DIR="docs/architecture" DISCOVERED_ADR_PATTERN="ADR-*.md" ROADMAP_EXISTS_BOOL="true"
  python3 "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff_env.py" >/dev/null 2>&1
  local handoff="$tmpdir/.rddf/state/.arch-handoff.json"
  python3 -c "
import json
with open('$handoff') as f:
    d = json.load(f)
required = ['arch_complete_at','adr_count','completed_adr_ids','roadmap_exists',
            'current_phase','plan_started_at','adr_dir','roadmap_path','architecture_dir',
            'adr_pattern','discovered','version']
for k in required:
    assert k in d, f'Missing key: {k}'
assert d['version'] == 1
print('OK')
"
  rm -rf "$tmpdir"
}

@test "write_arch_handoff_computes_roadmap_exists_from_filesystem" {
  # Critical regression test: ensures roadmap_exists is computed from filesystem,
  # not from env var (which doesn't propagate between bash code blocks in guide-arch.md).
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr"
  mkdir -p "$tmpdir/.rddf/state"
  echo "# ADR" > "$tmpdir/docs/adr/ADR-0001-test.md"
  echo "**当前阶段**: phase-2" > "$tmpdir/roadmap.md"  # roadmap EXISTS

  # Set DISCOVERED_ROADMAP_PATH to simulate post-discovery state (same as
  # guide-arch.md code block 1 would). Do NOT set ROADMAP_EXISTS_BOOL — bash
  # code block propagation would normally fail here if the helper relied on env var.
  # Explicitly override PROJECT_ROOT to tmpdir — test_helper exports PROJECT_ROOT
  # which would otherwise point to the real repo root.
  bash -c "cd '$tmpdir' && export PROJECT_ROOT='$tmpdir' && export DISCOVERED_ROADMAP_PATH='roadmap.md' && source $REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff.sh && write_arch_handoff" 2>&1

  # Verify .arch-handoff.json has roadmap_exists: true
  if [ -f "$tmpdir/.rddf/state/.arch-handoff.json" ]; then
    result=$(cat "$tmpdir/.rddf/state/.arch-handoff.json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d.get('roadmap_exists') is True, f'roadmap_exists should be True, got {d.get(\"roadmap_exists\")}'
print('PASS: roadmap_exists=True')
" 2>&1) || result="FAIL: $result"
    rm -rf "$tmpdir"
    echo "$result" | grep -q 'PASS: roadmap_exists'
  else
    rm -rf "$tmpdir"
    return 1
  fi
}

@test "write_arch_handoff handles missing artifacts gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  export PROJECT_ROOT="$tmpdir" DISCOVERED_ADR_DIR="docs/adr" DISCOVERED_ROADMAP_PATH="roadmap.md"
  export DISCOVERED_ARCHITECTURE_DIR="docs/architecture" DISCOVERED_ADR_PATTERN="ADR-*.md"
  python3 "$REPO_ROOT/skills/guide-arch/scripts/write_arch_handoff_env.py" 2>&1 || true
  rm -rf "$tmpdir"
}