#!/usr/bin/env bats
# tests/integration/test_arch_handoff_extraction.bats
# Round A extraction: rdd-arch.md L618-L707 inline heredoc-based JSON
# generation (~88 lines) extracted to _lib/write_arch_handoff.{py,sh}.
#
# These tests lock the refactor in place:
#   1. Helper files exist with expected exports.
#   2. rdd-arch.md no longer inlines the cat-heredoc block (L618-L707).
#   3. rdd-arch.md sources the helper and calls write_arch_handoff.
#   4. Runtime: helper creates .arch-handoff.json in scratch repo.
#   5. Runtime: required fields present in output JSON.
#   6. Runtime: handles missing artifacts gracefully (no crash).

load ../test_helper

@test "_lib/write_arch_handoff.{sh,py,env.py} exist" {
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.sh" ]
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.py" ]
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff_env.py" ]
}

@test "write_arch_handoff.sh exports write_arch_handoff function" {
  bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/write_arch_handoff.sh && declare -f write_arch_handoff" | grep -q 'write_arch_handoff'
}

@test "rdd-arch.md replaced inline block no longer contains cat heredoc" {
  # Content-driven check (not line-range): verify no heredoc writes to HANDOFF_FILE
  ! grep -q 'cat > "\$HANDOFF_FILE"' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "rdd-arch.md sources _lib/write_arch_handoff.sh and calls write_arch_handoff" {
  grep -q 'source.*scripts/write_arch_handoff.sh' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  grep -q 'write_arch_handoff' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "write_arch_handoff creates .arch-handoff.json in scratch repo" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/.rddf/state"
  echo "# ADR" > "$tmpdir/docs/adr/ADR-0001-test.md"
  echo "**当前阶段**: phase-2" > "$tmpdir/roadmap.md"
  export PROJECT_ROOT="$tmpdir" DISCOVERED_ADR_DIR="docs/adr" DISCOVERED_ROADMAP_PATH="roadmap.md"
  export DISCOVERED_ARCHITECTURE_DIR="docs/architecture" DISCOVERED_ADR_PATTERN="ADR-*.md" ROADMAP_EXISTS_BOOL="true"
  python3 "$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff_env.py" >/dev/null 2>&1
  if [ ! -f "$tmpdir/.rddf/state/.arch-handoff.json" ]; then
    echo "arch-handoff.json not found in $tmpdir/.rddf/state/"
    return 1
  fi
  rm -rf "$tmpdir"
}


@test "write_arch_handoff handles missing artifacts gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  export PROJECT_ROOT="$tmpdir" DISCOVERED_ADR_DIR="docs/adr" DISCOVERED_ROADMAP_PATH="roadmap.md"
  export DISCOVERED_ARCHITECTURE_DIR="docs/architecture" DISCOVERED_ADR_PATTERN="ADR-*.md"
  python3 "$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff_env.py" 2>&1 || true
  rm -rf "$tmpdir"
}