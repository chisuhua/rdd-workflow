#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "install_lib: skills/ has __init__.py (Python package marker)" {
  [ -f "skills/__init__.py" ]
}

@test "install_lib: skills/_lib/ has __init__.py (Python sub-package marker)" {
  [ -f "skills/_lib/__init__.py" ]
}

@test "install_lib: install.sh copies skills/_lib/*.py (recursive)" {
  # The install.sh copy loop uses `find ... -prune` with a cp inside,
  # so check for find+_lib+prune or _lib/schemas mkdir as evidence
  # that the install script handles the _lib distribution.
  run grep -E 'find.*_lib.*prune|find.*_lib.*\\.py|_lib/schemas|cp.*\\.json' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: install.sh copies skills/_lib/*.sh (bash helpers)" {
  # Regression: prior to this fix, install.sh and INSTALL.md only copied
  # *.py and *.json from _lib/. This silently broke runtime bash helpers
  # like archive.sh, worktree.sh, state.sh, scan-state.sh,
  # discover-arch-artifacts.sh, status_helpers.sh — all of which are
  # sourced by skills/*.md via `source ... _lib/<name>.sh`. After a
  # fresh `skill_use("INSTALL")`, downstream projects had no _lib/*.sh
  # files, so every `source` call in status.md / guide-ship.md failed
  # with "No such file or directory".
  #
  # This test asserts the install script's find filter now includes *.sh.
  run grep -nE "name '?\\*\\.sh'?" install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
  # Also assert INSTALL.md mirrors this (since it ships install-spec-workflow.sh).
  run grep -nE "name '?\\*\\.sh'?" skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: source repo has _lib/*.sh files to distribute (retains shared)" {
  # Phase 2: 46 single-skill helpers moved to per-skill scripts/.
  # _lib/ retains ~45 shared files (.sh + .py), including state.sh, worktree.sh,
  # archive.sh, discover-arch-artifacts.sh, status_helpers.sh.
  local n
  n=$(find skills/_lib -maxdepth 1 -name '*.sh' | wc -l)
  [ "$n" -ge 4 ] || {
    echo "FAIL: expected at least 4 shared _lib/*.sh files, got $n"
    return 1
  }
}

@test "install_lib: install.sh excludes __pycache__ / plugins / schedulers" {
  run grep -E '__pycache__|plugins|schedulers' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md L100 mirrors install.sh (also copies _lib)" {
  run grep -nE '_lib.*\.py|skills/_lib' skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md fallback lists all 13 skills (or dynamic)" {
  # The fallback either hardcodes 13 skill names OR derives them dynamically
  # from the skills/ directory on disk. Verify either form is present.
  #
  # Form A: hardcoded — at least 13 distinct quoted skill-name tokens
  # Form B: dynamic derivation — uses `ls "$PACKAGE_DIR/skills/"*.md`
  escaped_count=$(grep -oE '\\\\"[A-Za-z0-9_-]+\\\\"' skills/INSTALL.md | sort -u | wc -l)
  unescaped_count=$(grep -oE '"[A-Za-z0-9_-]+"' skills/INSTALL.md | sort -u | wc -l)
  has_dynamic=$(grep -cE 'ls .*PACKAGE_DIR/skills/.*\.md' skills/INSTALL.md || true)
  if [ "$escaped_count" -lt 13 ] && [ "$unescaped_count" -lt 13 ] && [ "$has_dynamic" -eq 0 ]; then
    echo "INSTALL.md fallback lacks 13 hardcoded skill names AND no dynamic derivation"
    return 1
  fi
}

@test "install_lib: INSTALL.md L3 description uses count-based phrasing (no enumerated names)" {
  # Description should NOT contain a comma-separated list of skill names inside parentheses
  desc=$(sed -n '1,15p' skills/INSTALL.md | grep -E "description:")
  # If it lists skill names separated by /, that's the fragile form
  if echo "$desc" | grep -qE "全部 [0-9]+ 个子技能.*\(.*/.*\)"; then
    # Check that the parenthetical list has fewer entries than claimed
    count_in_paren=$(echo "$desc" | sed -E 's/.*\((.*)\).*/\1/' | tr '/' '\n' | wc -l)
    claimed=$(echo "$desc" | grep -oE '全部 [0-9]+' | grep -oE '[0-9]+')
    if [ -n "$claimed" ] && [ "$count_in_paren" -lt "$claimed" ]; then
      echo "INSTALL.md description claims $claimed but lists $count_in_paren names"
      return 1
    fi
  fi
}

@test "install_lib: _lib/schemas/*.json are listed in install" {
  run grep -E 'schemas.*\.json|_lib/schemas' install.sh skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}
