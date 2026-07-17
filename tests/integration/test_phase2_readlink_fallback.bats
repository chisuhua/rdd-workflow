#!/usr/bin/env bats
# tests/integration/test_phase2_readlink_fallback.bats
#
# Phase 2 regression test: lock the manual fixes for Phase 1's two known
# readlink/fallback traps (N1 + N2 from Phase 1 lessons).
# Without these, the affected skills would silently break in piped execution.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "phase2_readlink_fallback: guide.md readlink path resolves at runtime" {
  # Phase 1 N1: guide.md:41 uses readlink -f wrapper. After Phase 2 must point to scripts/.
  line=$(grep -n 'readlink.*scan-state' skills/guide/SKILL.md | head -1 | cut -d: -f2-)
  [ -n "$line" ] || {
    echo "FAIL: guide.md readlink pattern not found"
    return 1
  }
  # The pattern should reference scripts/scan-state.sh, not _lib/scan-state.sh
  echo "$line" | grep -q 'scripts/scan-state\.sh' || {
    echo "FAIL: guide.md readlink pattern still references old _lib/ path"
    echo "  line: $line"
    return 1
  }
  # Verify the target file exists
  [ -f "skills/guide/scripts/scan-state.sh" ] || {
    echo "FAIL: scripts/scan-state.sh missing in guide/scripts/"
    return 1
  }
}

@test "phase2_readlink_fallback: feature.md primary paths use scripts/" {
  # Phase 1 N2: feature.md primary paths (lines 50-53) should use scripts/
  for f in feature_summary feature_graph feature_status feature_order; do
    grep -q "scripts/$f\.sh" skills/feature/SKILL.md || {
      echo "FAIL: feature.md missing scripts/$f.sh reference"
      return 1
    }
  done
  # And NO ../_lib/feature_*.sh should remain (the original trap)
  for f in feature_summary feature_graph feature_status feature_order; do
    ! grep -q "\.\./_lib/$f\.sh" skills/feature/SKILL.md || {
      echo "FAIL: feature.md still has ../_lib/$f.sh"
      return 1
    }
  done
}

@test "phase2_readlink_fallback: feature.md fallback _SCRIPT_DIR is per-skill" {
  # The piped-execution fallback (BASH_SOURCE=/dev/fd/N) sets _SCRIPT_DIR
  # so that scripts/ resolves correctly.
  for f in feature_summary feature_graph feature_status feature_order; do
    # Lines 50-53 should be `source "$_SCRIPT_DIR/scripts/$f.sh"`
    grep -q "\"\$_SCRIPT_DIR/scripts/$f\.sh\"" skills/feature/SKILL.md || {
      echo "FAIL: feature.md missing \$_SCRIPT_DIR/scripts/$f.sh"
      return 1
    }
  done
}

@test "phase2_readlink_fallback: rddf_session_hooks.sh has new import path" {
  # N3 fix per ADR-0021 Decision 2
  f="skills/rddf-session/scripts/rddf_session_hooks.sh"
  [ -f "$f" ] || {
    echo "FAIL: $f missing"
    return 1
  }
  # Should NOT have any old `from skills._lib.rddf_session import`
  ! grep -q "from skills\._lib\.rddf_session import" "$f" || {
    echo "FAIL: rddf_session_hooks.sh still has old import path"
    return 1
  }
  # Should have new path
  grep -q "from skills\.rddf_session\.scripts\.rddf_session import" "$f" || {
    echo "FAIL: rddf_session_hooks.sh missing new import path"
    return 1
  }
}