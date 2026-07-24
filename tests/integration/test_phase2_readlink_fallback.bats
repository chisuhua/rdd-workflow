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

@test "phase2_readlink_fallback: guide.md scan-state path resolves at runtime" {
  # Phase 2: guide.md no longer uses readlink -f for scan-state.sh directly.
  # Instead, it delegates to guide_entry.sh which contains the 4-tier path
  # resolution fallback. The SKILL.md should reference scripts/guide_entry.sh.
  grep -q 'scripts/guide_entry.sh' skills/guide/SKILL.md || {
    echo "FAIL: guide.md does not reference scripts/guide_entry.sh"
    return 1
  }
  # Verify the target file exists
  [ -f "skills/guide/scripts/guide_entry.sh" ] || {
    echo "FAIL: scripts/guide_entry.sh missing in guide/scripts/"
    return 1
  }
  # Verify guide_entry.sh sources scan-state.sh from the scripts/ dir
  grep -q 'scan-state\.sh' skills/guide/scripts/guide_entry.sh || {
    echo "FAIL: guide_entry.sh does not reference scan-state.sh"
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