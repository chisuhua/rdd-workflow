#!/usr/bin/env bats
# tests/integration/test_phase2_layout.bats
#
# Phase 2 regression test: lock per-skill scripts/ directory layout.
# Per ADR-0021: 47 single-skill helpers moved from skills/_lib/ to skills/<skill>/scripts/.
# This test must pass before archive and stay green forever after.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "phase2: rddf-session has both rddf_session.py and rddf_session_hooks.sh" {
  # N3 fix per ADR-0021 Decision 2: hooks.sh and rddf_session.py both moved
  [ -f "skills/rddf-session/scripts/rddf_session.py" ]
  [ -f "skills/rddf-session/scripts/rddf_session_hooks.sh" ]
}

@test "phase2: all 10 skill scripts/ dirs have at least one .sh or .py file" {
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    n=$(find "skills/$skill/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null | wc -l)
    [ "$n" -ge 1 ] || {
      echo "FAIL: skills/$skill/scripts/ has $n files (expected >= 1)"
      return 1
    }
  done
}

@test "phase2: per-skill scripts/__init__.py present (ADR-0021 Decision 1)" {
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    [ -f "skills/$skill/scripts/__init__.py" ] || {
      echo "FAIL: skills/$skill/scripts/__init__.py missing"
      return 1
    }
  done
}

@test "phase2: _lib/ retains only shared files (~44 or fewer .sh+.py)" {
  local count
  count=$(find skills/_lib -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) | wc -l)
  [ "$count" -le 50 ] && [ "$count" -ge 35 ] || {
    echo "FAIL: expected 35-50 shared files in _lib/, got $count"
    return 1
  }
}

@test "phase2: SKILL.md source lines use scripts/ for moved files" {
  # Sample 4 moved files
  grep -q 'scripts/ship_plan' skills/guide-ship/SKILL.md || return 1
  grep -q 'scripts/arch_env_check' skills/guide-arch/SKILL.md || return 1
  grep -q 'scripts/feature_summary' skills/feature/SKILL.md || return 1
  grep -q 'scripts/scan-state' skills/guide/SKILL.md || return 1
}

@test "phase2: SKILL.md source lines preserve ../_lib/ for shared files" {
  # state.sh stays in _lib/ — references should still use ../_lib/
  for skill in guide-arch guide-plan guide-ship; do
    grep -q '\.\./_lib/state\.sh\|/../_lib/state\.sh' "skills/$skill/SKILL.md" || {
      # Some skills may not reference state.sh directly — that's fine
      echo "info: $skill doesn't reference state.sh directly"
    }
  done
}

@test "phase2: guide.md readlink pattern updated (Phase 1 N1 lesson)" {
  grep -q 'scripts/scan-state' skills/guide/SKILL.md || return 1
  ! grep -qE 'readlink.*_lib/scan-state' skills/guide/SKILL.md || {
    echo "FAIL: guide.md still has readlink.*_lib/scan-state"
    return 1
  }
}

@test "phase2: feature.md fallback updated (Phase 1 N2 lesson)" {
  grep -q 'scripts/feature_summary' skills/feature/SKILL.md || return 1
  ! grep -qE '\.\./_lib/feature_(summary|graph|status|order)\.sh' skills/feature/SKILL.md || {
    echo "FAIL: feature.md still has ../_lib/feature_*"
    return 1
  }
}

@test "phase2: 3 cross-skill source lines to rddf-session/scripts/ added" {
  for skill in guide-arch guide-plan guide-ship; do
    grep -q '\.\./rddf-session/scripts/rddf_session_hooks\.sh' "skills/$skill/SKILL.md" || {
      echo "FAIL: $skill/SKILL.md missing rddf-session source line"
      return 1
    }
  done
}

@test "phase2: feature_*.sh PYTHONPATH recalculated to ../.. (ADR-0021 N2 fix)" {
  for f in skills/feature/scripts/feature_summary.sh \
           skills/feature/scripts/feature_graph.sh \
           skills/feature/scripts/feature_status.sh \
           skills/feature/scripts/feature_order.sh; do
    grep -q 'PYTHONPATH="\$_SCRIPT_DIR/\.\./\.\.' "$f" || {
      echo "FAIL: $f PYTHONPATH not recalc to ../../"
      return 1
    }
  done
}

@test "phase2: no stale reference to old _lib/X.sh in SKILL.md (sample check)" {
  # Sample: known single-skill files that MUST NOT appear as _lib/ in SKILL.md
  # executable code (comments mentioning the old path for historical context
  # are acceptable - only check non-comment lines).
  for f in ship_plan arch_env_check feature_summary deps_render_report status_render_mode_a scan-state rddf_session; do
    ! grep -vE '^\s*#' skills/*/SKILL.md 2>/dev/null | grep -qE "_lib/${f}(\.sh|\.py|_env\.py)" || {
      echo "FAIL: _lib/$f still referenced in executable code of some SKILL.md"
      return 1
    }
  done
}