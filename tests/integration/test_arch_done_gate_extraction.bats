#!/usr/bin/env bats
# tests/integration/test_arch_done_gate_extraction.bats
# Round B extraction: rdd-arch.md Phase 5 arch-done dual gate (~38 lines)
# extracted to _lib/arch_done_gate.sh::check_arch_done_gate().
#
# These tests lock the refactor in place:
#   1. arch_done_gate.sh exists with check_arch_done_gate function.
#   2. rdd-arch.md inline gate markers removed.
#   3. rdd-arch.md sources and calls helper.
#   4. Gate passes with ADRs + roadmap present.
#   5. Gate fails when no ADRs.
#   6. Gate fails when roadmap missing.

load ../test_helper

@test "arch_done_gate_helper_exists" {
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/arch_done_gate.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_done_gate.sh && declare -f check_arch_done_gate" | grep -q 'check_arch_done_gate'
}

@test "guide_arch_inline_gate_block_removed" {
  # Chinese markers from inline gate block must not appear after extraction
  ! grep -q '门控 1: ADR 数量检查' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  ! grep -q '门控 2: roadmap 存在性检查' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "guide_arch_invokes_helper" {
  grep -q 'source.*scripts/arch_done_gate.sh' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
  grep -q 'check_arch_done_gate' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "check_arch_done_gate_passes_with_adr_and_roadmap" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/_lib"
  mkdir -p "$tmpdir/skills/_lib"
  echo "# ADR-0001-test" > "$tmpdir/docs/adr/ADR-0001-test.md"
  echo "**当前阶段**: test" > "$tmpdir/roadmap.md"
  # Stub discover-arch-artifacts.sh
  cat > "$tmpdir/_lib/discover-arch-artifacts.sh" <<'EOF'
discover_all() {
  DISCOVERED_ADR_DIR="docs/adr"
  DISCOVERED_ROADMAP_PATH="roadmap.md"
  DISCOVERED_ADR_PATTERN="ADR-*.md"
  export DISCOVERED_ADR_DIR DISCOVERED_ROADMAP_PATH DISCOVERED_ADR_PATTERN
}
EOF
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_done_gate.sh' && check_arch_done_gate" >/dev/null 2>&1
  local rc=$?
  rm -rf "$tmpdir"
  [ "$rc" -eq 0 ]
}

@test "check_arch_done_gate_fails_without_adr" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/_lib"
  mkdir -p "$tmpdir/skills/_lib"
  echo "**当前阶段**: test" > "$tmpdir/roadmap.md"
  cat > "$tmpdir/_lib/discover-arch-artifacts.sh" <<'EOF'
discover_all() {
  DISCOVERED_ADR_DIR="docs/adr"
  DISCOVERED_ROADMAP_PATH="roadmap.md"
  DISCOVERED_ADR_PATTERN="ADR-*.md"
  export DISCOVERED_ADR_DIR DISCOVERED_ROADMAP_PATH DISCOVERED_ADR_PATTERN
}
EOF
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_done_gate.sh' && check_arch_done_gate" >"$BATS_TMPDIR/gate.out" 2>&1 || true
  rm -rf "$tmpdir"
  grep -q '❌ 失败: 至少需要 1 个 ADR' "$BATS_TMPDIR/gate.out"
}

@test "check_arch_done_gate_fails_without_roadmap" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/docs/adr" "$tmpdir/_lib"
  mkdir -p "$tmpdir/skills/_lib"
  echo "# ADR-0001-test" > "$tmpdir/docs/adr/ADR-0001-test.md"
  # No roadmap.md
  cat > "$tmpdir/_lib/discover-arch-artifacts.sh" <<'EOF'
discover_all() {
  DISCOVERED_ADR_DIR="docs/adr"
  DISCOVERED_ROADMAP_PATH="roadmap.md"
  DISCOVERED_ADR_PATTERN="ADR-*.md"
  export DISCOVERED_ADR_DIR DISCOVERED_ROADMAP_PATH DISCOVERED_ADR_PATTERN
}
EOF
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/rdd-arch/scripts/arch_done_gate.sh' && check_arch_done_gate" >"$BATS_TMPDIR/gate.out" 2>&1 || true
  rm -rf "$tmpdir"
  grep -q '❌ 失败: roadmap 不存在' "$BATS_TMPDIR/gate.out"
}
